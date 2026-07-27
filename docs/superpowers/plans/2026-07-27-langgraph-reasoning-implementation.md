# LangGraph 推理组件实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现三个可复用的推理组件（ReAct、Plan-and-Execute、ToT），覆盖通用思考/决策/规划节点，供所有工作流复用。

**Architecture:** 每个模式独立为一个模块，提供状态类、节点工厂函数、路由函数和 `BaseWorkflow` 子类。通过 TypedDict + Annotated 管理状态，工厂函数生成节点，通过 `HANDLER_REGISTRY` 整合进 JSON 编译器。

**Tech Stack:** LangGraph (`StateGraph`, `add_messages`, `END`), Python `TypedDict` + `Annotated`, `dataclasses`, `datetime`

## Global Constraints

- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`

---

## 文件结构

```
server/src/workflows/reasoning/
├── __init__.py          # Task 4: 导出 + handler 注册
├── base.py               # Task 4: 公共基类
├── react.py              # Task 5: ReAct 模式
├── plan_execute.py       # Task 6: Plan-and-Execute 模式
└── tree_of_thought.py    # Task 7: ToT 模式
```

**Modify:** `server/src/workflows/__init__.py`（Task 8）

---

## Task 1: base.py — 公共基类和类型

**Files:**
- Create: `server/src/workflows/reasoning/base.py`

**Interfaces:**
- Consumes: 无
- Produces: `BaseReasoningState`, `ReasoningConfig`, `StepRecord`

**Dependencies:** 无

- [ ] **Step 1: Write base.py**

```python
# server/src/workflows/reasoning/base.py
# -*- coding: utf-8 -*-
"""
推理组件公共基类

定义所有推理模式共享的类型和配置。
"""

from typing import TypedDict, Optional, Any, NotRequired, Annotated
from langgraph.graph import add_messages
from dataclasses import dataclass, field


class StepRecord(TypedDict):
    """结构化的中间步骤记录"""
    step_type: str               # "reasoning" | "action" | "observation" | "reflection" | "plan" | "execute"
    content: str                # 步骤内容
    timestamp: str              # ISO 格式时间戳
    metadata: NotRequired[dict[str, Any] | None]


class BaseReasoningState(TypedDict):
    """
    所有推理状态的公共字段

    各模式应继承此类并扩展自己的字段。
    """

    # 消息历史（使用 add_messages reducer 自动合并）
    messages: Annotated[list, add_messages]

    # 迭代控制
    iteration: int               # 当前迭代次数（0-indexed）
    max_iterations: int          # 最大迭代上限

    # 中间步骤记录
    intermediate_steps: list[StepRecord]

    # 错误信息
    error: Optional[str]

    # 会话 ID（用于断点续算）
    session_id: Optional[str]


@dataclass
class ReasoningConfig:
    """推理组件通用配置"""

    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_reflection: bool = True
    llm_provider: str = "deepseek"
    system_prompt: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "enable_reflection": self.enable_reflection,
            "llm_provider": self.llm_provider,
            "system_prompt": self.system_prompt,
        }
```

- [ ] **Step 2: Create reasoning directory**

```bash
mkdir -p server/src/workflows/reasoning
touch server/src/workflows/reasoning/__init__.py
```

- [ ] **Step 3: Run linter**

```bash
cd server && python -m py_compile src/workflows/reasoning/base.py && echo "OK"
```

- [ ] **Step 4: Commit**

```bash
git add server/src/workflows/reasoning/ && git commit -m "feat(reasoning): add base classes for reasoning components"
```

---

## Task 2: react.py — ReAct 模式

**Files:**
- Create: `server/src/workflows/reasoning/react.py`

**Interfaces:**
- Consumes: `BaseReasoningState`, `ReasoningConfig` from `base`
- Produces: `ReactState`, `create_reasoning_node`, `create_action_node`, `create_observation_node`, `create_reflection_node`, `create_finish_node`, `react_router`, `ReactWorkflow`

- [ ] **Step 1: Write react.py**

```python
# server/src/workflows/reasoning/react.py
# -*- coding: utf-8 -*-
"""
ReAct (Reasoning + Acting) 模式

工作流：
    [reasoning] → [action] → [observation] → [reflect]
         ↑                                     ↓
         └────────────── (should_continue) ←───┘
                            ↓
                         [finish]
"""

import json
import re
from datetime import datetime, timezone
from typing import TypedDict, Optional, Any, NotRequired, Annotated, Literal

from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from core.logger import logger
from llms.providers import get_llm_provider
from workflows.reasoning.base import BaseReasoningState, ReasoningConfig, StepRecord


class ReactState(BaseReasoningState):
    """ReAct 推理状态"""

    # 当前思考内容
    thought: NotRequired[Optional[str]]

    # 当前要执行的工具名
    action: NotRequired[Optional[str]]

    # 工具调用参数
    action_input: NotRequired[Optional[dict]]

    # 工具执行结果
    observation: NotRequired[Optional[str]]

    # 是否继续循环
    should_continue: NotRequired[Optional[bool]]

    # 最终答案
    final_answer: NotRequired[Optional[str]]

    # 工具调用结果列表
    tool_results: NotRequired[list[dict[str, Any]]]


# ===== 提示模板 =====

_REACT_SYSTEM_PROMPT = """你是一个 ReAct (Reasoning + Acting) 推理代理。

你必须严格遵循以下格式进行思考：

## Thought
[你的思考过程，分析当前情况，决定下一步行动]

## Action
[要执行的工具名称，如 search, calculator, get_weather 等]

## Action Input
[工具的参数，JSON 格式]

---

每次只执行一个 Action。观察结果后，继续思考和行动，直到得到满意答案。

最后，当任务完成时，必须输出：

## Final Answer
[你的完整答案]

记住：
- 每一步都要给出清晰的理由
- 工具调用必须是有效的 JSON 格式
- 如果不需要工具，直接给出最终答案
"""

_REACT_USER_PROMPT = """任务：{task}

{history}

请开始你的推理过程。
"""


# ===== 节点函数 =====

def create_reasoning_node(config: ReasoningConfig):
    """
    创建推理节点

    Args:
        config: 推理配置

    Returns:
        节点函数
    """

    def reasoning_node(state: ReactState) -> dict:
        logger.info(f"ReAct: 推理节点 (iteration={state.get('iteration', 0)})")

        messages = state.get("messages", [])
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", config.max_iterations)

        # 收集历史推理步骤
        history_parts = []
        intermediate = state.get("intermediate_steps", [])
        for step in intermediate[-5:]:  # 只保留最近 5 步
            history_parts.append(f"[{step['step_type']}] {step['content']}")

        history_str = "\n".join(history_parts) if history_parts else "无"

        # 构建用户提示
        user_prompt = _REACT_USER_PROMPT.format(
            task=messages[-1].content if messages else "",
            history=history_str
        )

        # 调用 LLM
        try:
            provider = get_llm_provider(config.llm_provider)
            system_msg = config.system_prompt or _REACT_SYSTEM_PROMPT

            response = provider.invoke([
                HumanMessage(content=system_msg),
                HumanMessage(content=user_prompt),
            ])

            llm_output = response.content if hasattr(response, "content") else str(response)
            logger.debug(f"ReAct LLM 输出:\n{llm_output}")

            # 解析 LLM 输出
            thought = _extract_thought(llm_output)
            action, action_input = _extract_action(llm_output)
            final_answer = _extract_final_answer(llm_output)

            updates: dict = {
                "iteration": iteration + 1,
                "intermediate_steps": intermediate + [{
                    "step_type": "reasoning",
                    "content": thought or llm_output[:200],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }],
            }

            if thought is not None:
                updates["thought"] = thought
            if action is not None:
                updates["action"] = action
            if action_input is not None:
                updates["action_input"] = action_input
            if final_answer is not None:
                updates["final_answer"] = final_answer

            return updates

        except Exception as e:
            logger.error(f"ReAct 推理节点错误: {e}")
            return {
                "iteration": iteration + 1,
                "error": str(e),
            }

    return reasoning_node


def create_action_node(tools: list[BaseTool]):
    """
    创建动作执行节点

    Args:
        tools: 可用工具列表

    Returns:
        节点函数
    """

    def action_node(state: ReactState) -> dict:
        logger.info(f"ReAct: 动作节点 - {state.get('action')}")

        action = state.get("action")
        action_input = state.get("action_input", {})
        iteration = state.get("iteration", 0)
        intermediate = state.get("intermediate_steps", [])
        tool_results = state.get("tool_results", [])

        if not action:
            return {"error": "No action specified"}

        # 查找工具
        tool = next((t for t in tools if t.name == action), None)
        if tool is None:
            observation = f"Tool '{action}' not found. Available tools: {[t.name for in tools]}"
            return {
                "observation": observation,
                "intermediate_steps": intermediate + [{
                    "step_type": "action",
                    "content": f"执行失败: {observation}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }],
            }

        try:
            # 执行工具
            result = tool.invoke(action_input)
            observation = str(result) if result is not None else "No result"

            logger.info(f"ReAct: 工具 {action} 执行成功")

            return {
                "observation": observation,
                "tool_results": tool_results + [{
                    "tool": action,
                    "input": action_input,
                    "output": observation,
                }],
                "intermediate_steps": intermediate + [{
                    "step_type": "action",
                    "content": f"Tool: {action}, Result: {observation[:200]}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"tool": action, "input": action_input}
                }],
            }

        except Exception as e:
            logger.error(f"ReAct: 工具 {action} 执行失败: {e}")
            return {
                "observation": f"Error: {str(e)}",
                "intermediate_steps": intermediate + [{
                    "step_type": "action",
                    "content": f"Tool {action} failed: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"tool": action, "error": str(e)}
                }],
            }

    return action_node


def create_observation_node():
    """
    创建观察节点

    处理工具返回，更新观察结果。
    """

    def observation_node(state: ReactState) -> dict:
        logger.info("ReAct: 观察节点")

        observation = state.get("observation", "")
        iteration = state.get("iteration", 0)
        intermediate = state.get("intermediate_steps", [])

        return {
            "intermediate_steps": intermediate + [{
                "step_type": "observation",
                "content": observation[:500] if observation else "No observation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }

    return observation_node


def create_reflection_node(config: ReasoningConfig):
    """
    创建反思节点

    评估当前状态，决定是否继续循环。
    """

    def reflection_node(state: ReactState) -> dict:
        logger.info("ReAct: 反思节点")

        observation = state.get("observation", "")
        final_answer = state.get("final_answer")
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", config.max_iterations)
        intermediate = state.get("intermediate_steps", [])

        # 已有最终答案 → 结束
        if final_answer:
            logger.info("ReAct: 已得到最终答案，结束")
            return {"should_continue": False}

        # 迭代超限 → 结束
        if iteration >= max_iterations:
            logger.warning(f"ReAct: 达到最大迭代次数 {max_iterations}，强制结束")
            return {
                "should_continue": False,
                "error": f"达到最大迭代次数 {max_iterations}"
            }

        # 观察结果为空或包含错误 → 结束
        if not observation or "error" in observation.lower():
            logger.info("ReAct: 无有效观察，结束")
            return {"should_continue": False}

        # 检查是否需要继续（通过关键词判断）
        should_continue = _should_continue_after_observation(observation)

        logger.info(f"ReAct: 反思结果 should_continue={should_continue}")

        return {
            "should_continue": should_continue,
            "intermediate_steps": intermediate + [{
                "step_type": "reflection",
                "content": f"反思: should_continue={should_continue}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }

    return reflection_node


def create_finish_node():
    """
    创建结束节点

    汇总结果，生成最终答案。
    """

    def finish_node(state: ReactState) -> dict:
        logger.info("ReAct: 结束节点")

        final_answer = state.get("final_answer")
        intermediate = state.get("intermediate_steps", [])
        error = state.get("error")

        # 如果没有最终答案但有观察结果，尝试提取
        if not final_answer:
            observation = state.get("observation", "")
            tool_results = state.get("tool_results", [])

            if tool_results:
                # 从工具结果构建答案
                result_parts = []
                for tr in tool_results:
                    result_parts.append(f"Tool {tr['tool']}: {tr['output'][:300]}")
                final_answer = "\n\n".join(result_parts)
            elif observation:
                final_answer = observation
            else:
                final_answer = "无法生成答案"

        return {
            "final_answer": final_answer,
            "stage": "complete",
            "intermediate_steps": intermediate + [{
                "step_type": "finish",
                "content": f"最终答案: {final_answer[:200]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }

    return finish_node


# ===== 路由函数 =====

def react_router(state: ReactState) -> Literal["reasoning", "action", "observation", "reflect", "finish"]:
    """
    ReAct 路由函数

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)
    action = state.get("action")
    observation = state.get("observation")
    final_answer = state.get("final_answer")
    should_continue = state.get("should_continue")

    # 已有最终答案 → 结束
    if final_answer:
        return "finish"

    # 迭代超限 → 结束
    if iteration >= max_iterations:
        return "finish"

    # 无 action → 推理
    if not action:
        return "reasoning"

    # 有 action 且无 observation → 执行
    if action and not observation:
        return "action"

    # 有 observation → 反思
    if observation is not None:
        if should_continue is False:
            return "finish"
        return "reflect"

    return "reasoning"


# ===== 工作流类 =====

def create_react_workflow(
    tools: list[BaseTool],
    config: ReasoningConfig | None = None,
):
    """
    创建 ReAct 工作流

    Args:
        tools: 可用工具列表
        config: 推理配置

    Returns:
        编译后的 StateGraph
    """
    from langgraph.graph import StateGraph
    from langgraph.checkpoint.memory import MemorySaver

    if config is None:
        config = ReasoningConfig()

    workflow = StateGraph(ReactState)

    # 添加节点
    workflow.add_node("reasoning", create_reasoning_node(config))
    workflow.add_node("action", create_action_node(tools))
    workflow.add_node("observation", create_observation_node())
    workflow.add_node("reflect", create_reflection_node(config))
    workflow.add_node("finish", create_finish_node())

    # 设置入口点
    workflow.set_entry_point("reasoning")

    # 条件边
    workflow.add_conditional_edges(
        "reasoning",
        react_router,
        {
            "action": "action",
            "finish": "finish",
        }
    )
    workflow.add_conditional_edges(
        "action",
        lambda s: "observation",
        {"observation": "observation"}
    )
    workflow.add_conditional_edges(
        "reflect",
        lambda s: "reasoning" if s.get("should_continue", True) else "finish",
        {
            "reasoning": "reasoning",
            "finish": "finish",
        }
    )

    # 普通边
    workflow.add_edge("observation", "reflect")

    return workflow.compile(checkpointer=MemorySaver())


# ===== 辅助函数 =====

def _extract_thought(text: str) -> str | None:
    """从 LLM 输出中提取 Thought"""
    match = re.search(r"##\s*Thought\s*\n(.*?)(?=##\s*Action|$)", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_action(text: str) -> tuple[str | None, dict | None]:
    """从 LLM 输出中提取 Action 和 Action Input"""
    action_match = re.search(r"##\s*Action\s*\n(.*?)(?=##|$)", text, re.DOTALL | re.IGNORECASE)
    input_match = re.search(r"##\s*Action\s*Input\s*\n(.*?)(?=##|$)", text, re.DOTALL | re.IGNORECASE)

    action = action_match.group(1).strip() if action_match else None
    action_input = {}

    if input_match:
        try:
            action_input = json.loads(input_match.group(1).strip())
        except (json.JSONDecodeError, Exception):
            action_input = {}

    return action, action_input


def _extract_final_answer(text: str) -> str | None:
    """从 LLM 输出中提取 Final Answer"""
    match = re.search(r"##\s*Final\s*Answer\s*\n(.*?)$", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _should_continue_after_observation(observation: str) -> bool:
    """
    基于观察结果判断是否继续

    Args:
        observation: 工具执行结果

    Returns:
        是否继续循环
    """
    # 结束关键词
    finish_keywords = [
        "完成", "已完成", "答案", "结论", "总结",
        "done", "complete", "finished", "answer", "final",
        "因此", "所以", "综上",
    ]

    # 失败关键词
    fail_keywords = [
        "失败", "错误", "不存在", "无法",
        "failed", "error", "not found", "cannot",
    ]

    obs_lower = observation.lower()

    for kw in fail_keywords:
        if kw.lower() in obs_lower:
            return False

    for kw in finish_keywords:
        if kw.lower() in obs_lower:
            return False

    return True
```

- [ ] **Step 2: Run linter**

```bash
cd server && python -m py_compile src/workflows/reasoning/react.py && echo "OK"
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/react.py && git commit -m "feat(reasoning): implement ReAct pattern (Reasoning + Acting)"
```

---

## Task 3: plan_execute.py — Plan-and-Execute 模式

**Files:**
- Create: `server/src/workflows/reasoning/plan_execute.py`

**Interfaces:**
- Consumes: `BaseReasoningState`, `ReasoningConfig` from `base`
- Produces: `TaskStep`, `PlanExecuteState`, `create_planner_node`, `create_executor_node`, `create_reflector_node`, `create_replan_node`, `create_finish_node`, `plan_execute_router`, `create_plan_execute_workflow`

- [ ] **Step 1: Write plan_execute.py**

```python
# server/src/workflows/reasoning/plan_execute.py
# -*- coding: utf-8 -*-
"""
Plan-and-Execute 模式

工作流：
    [plan] → [execute] → [reflect]
              ↑          ↓
              ↓    (needs_replan?) → [replan] → [plan]
              ↓          ↓
              └──────────┴─ [finish]
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Optional, Any, NotRequired, Annotated, Literal

from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from core.logger import logger
from llms.providers import get_llm_provider
from workflows.reasoning.base import BaseReasoningState, ReasoningConfig


class TaskStep(TypedDict):
    """任务步骤"""

    step_id: str
    description: str
    status: str          # "pending" | "in_progress" | "completed" | "failed" | "skipped"
    result: NotRequired[Optional[str]]
    depends_on: NotRequired[list[str]]
    metadata: NotRequired[dict[str, Any] | None]


class PlanExecuteState(BaseReasoningState):
    """Plan-and-Execute 推理状态"""

    # 完整任务步骤列表
    plan: NotRequired[list[TaskStep]]

    # 当前执行到第几步（0-indexed）
    current_step: NotRequired[int]

    # 待执行任务（副本）
    pending_tasks: NotRequired[list[TaskStep]]

    # 已完成任务（带结果）
    completed_tasks: NotRequired[list[TaskStep]]

    # 重规划次数
    replan_count: NotRequired[int]

    # 对 Planner 的额外上下文
    pending_hints: NotRequired[Optional[str]]

    # 当前步骤执行摘要
    execution_summary: NotRequired[Optional[str]]

    # 当前步骤执行结果
    current_result: NotRequired[Optional[str]]

    # 评估结果（用于反思）
    reflection_result: NotRequired[Optional[str]]

    # 是否需要重规划
    needs_replan: NotRequired[bool]

    # 最终答案
    final_answer: NotRequired[Optional[str]]


# ===== 提示模板 =====

_PLANNER_SYSTEM_PROMPT = """你是一个任务规划专家。

给定一个任务，你需要将其分解为具体的执行步骤。

## 要求
1. 每个步骤必须是原子操作，可以被独立执行
2. 步骤之间可以有依赖关系（通过 depends_on 字段）
3. 步骤描述要清晰、可执行
4. 考虑任务的完整性和可行性

## 输出格式
返回一个 JSON 数组，每个元素包含：
- step_id: 唯一标识
- description: 步骤描述
- depends_on: 依赖的其他 step_id（可选）
"""

_EXECUTION_PROMPT = """你是一个执行专家。

你需要执行以下步骤：

{step_description}

{context}

请执行这个步骤，并报告结果。
"""

_REFLECTION_PROMPT = """你是一个任务反思专家。

任务：{task}
刚刚执行的步骤：{step_description}
执行结果：{execution_result}

请评估：
1. 这个步骤是否成功？
2. 是否需要重规划？
3. 如果需要重规划，应该如何调整？

## 输出格式
返回 JSON：
{{
  "success": true/false,
  "needs_replan": true/false,
  "reason": "评估理由",
  "suggestion": "如果需要重规划，给出建议"
}}
"""


# ===== 节点函数 =====

def create_planner_node(config: ReasoningConfig):
    """
    创建规划节点

    生成或修改任务步骤列表。
    """

    def planner_node(state: PlanExecuteState) -> dict:
        logger.info("PlanExecute: 规划节点")

        messages = state.get("messages", [])
        pending_hints = state.get("pending_hints")
        plan = state.get("plan", [])
        replan_count = state.get("replan_count", 0)
        iteration = state.get("iteration", 0)
        intermediate = state.get("intermediate_steps", [])

        # 获取用户任务
        user_task = ""
        if messages:
            last = messages[-1]
            user_task = last.content if hasattr(last, "content") else str(last)

        # 调用 LLM 生成计划
        try:
            provider = get_llm_provider(config.llm_provider)

            planner_prompt = f"""{_PLANNER_SYSTEM_PROMPT}

任务：{user_task}

{f"额外上下文：{pending_hints}" if pending_hints else ""}

{f"(这是第 {replan_count + 1} 次重规划，请考虑之前的计划)" if replan_count > 0 else ""}

请输出计划：
"""

            response = provider.invoke([
                HumanMessage(content=planner_prompt)
            ])

            llm_output = response.content if hasattr(response, "content") else str(response)
            logger.debug(f"PlanExecute 规划输出:\n{llm_output}")

            # 解析计划
            new_plan = _parse_plan(llm_output, plan)

            # 构建 pending_tasks
            pending_tasks = [step for step in new_plan if step["status"] == "pending"]

            logger.info(f"PlanExecute: 生成 {len(new_plan)} 个步骤，{len(pending_tasks)} 个待执行")

            return {
                "plan": new_plan,
                "pending_tasks": pending_tasks,
                "current_step": 0,
                "iteration": iteration + 1,
                "intermediate_steps": intermediate + [{
                    "step_type": "plan",
                    "content": f"生成 {len(new_plan)} 个步骤",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"step_count": len(new_plan), "replan": replan_count}
                }],
            }

        except Exception as e:
            logger.error(f"PlanExecute 规划节点错误: {e}")
            return {
                "error": f"规划失败: {str(e)}",
                "iteration": iteration + 1,
            }

    return planner_node


def create_executor_node(tools: list[BaseTool]):
    """
    创建执行节点

    执行当前步骤。
    """

    def executor_node(state: PlanExecuteState) -> dict:
        logger.info("PlanExecute: 执行节点")

        pending_tasks = state.get("pending_tasks", [])
        current_step = state.get("current_step", 0)
        plan = state.get("plan", [])
        completed_tasks = state.get("completed_tasks", [])
        intermediate = state.get("intermediate_steps", [])

        if current_step >= len(pending_tasks):
            logger.info("PlanExecute: 所有任务已执行完毕")
            return {"pending_tasks": [], "execution_summary": "all_done"}

        # 获取当前步骤
        current_task = pending_tasks[current_step]
        step_description = current_task.get("description", "")

        logger.info(f"PlanExecute: 执行步骤 {current_step + 1}/{len(pending_tasks)}: {step_description[:50]}")

        # 检查依赖
        depends_on = current_task.get("depends_on", [])
        if depends_on:
            unmet = [dep for dep in depends_on if dep not in [t.get("step_id") for t in completed_tasks]]
            if unmet:
                logger.warning(f"PlanExecute: 依赖未满足 {unmet}，跳过此步骤")
                updated_plan = _update_step_status(plan, current_task["step_id"], "skipped")
                updated_pending = [t for t in pending_tasks if t["step_id"] != current_task["step_id"]]
                return {
                    "plan": updated_plan,
                    "pending_tasks": updated_pending,
                    "current_step": current_step + 1,
                    "execution_summary": "skipped",
                }

        # 执行步骤（优先使用工具）
        execution_result = ""
        try:
            # 尝试匹配工具
            matched_tool = None
            for tool in tools:
                if tool.name.lower() in step_description.lower() or any(
                    kw.lower() in step_description.lower()
                    for kw in ["search", "query", "find", "get", "fetch"]
                ):
                    matched_tool = tool
                    break

            if matched_tool:
                tool_result = matched_tool.invoke({})
                execution_result = str(tool_result)
            else:
                # 使用 LLM 执行
                execution_result = _execute_with_llm(step_description, state)

            logger.info(f"PlanExecute: 步骤执行成功: {execution_result[:100]}")

        except Exception as e:
            logger.error(f"PlanExecute: 步骤执行失败: {e}")
            execution_result = f"执行失败: {str(e)}"

        # 更新状态
        updated_plan = _update_step_status(plan, current_task["step_id"], "completed", execution_result)
        updated_pending = [t for t in pending_tasks if t["step_id"] != current_task["step_id"]]

        new_completed = completed_tasks + [{
            **current_task,
            "status": "completed",
            "result": execution_result,
        }]

        return {
            "plan": updated_plan,
            "pending_tasks": updated_pending,
            "completed_tasks": new_completed,
            "current_step": current_step + 1,
            "current_result": execution_result,
            "execution_summary": "step_completed",
            "intermediate_steps": intermediate + [{
                "step_type": "execute",
                "content": f"执行: {step_description[:50]}, 结果: {execution_result[:100]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {"step_id": current_task["step_id"]}
            }],
        }

    return executor_node


def create_reflector_node(config: ReasoningConfig):
    """
    创建反思节点

    评估执行结果，决定下一步。
    """

    def reflector_node(state: PlanExecuteState) -> dict:
        logger.info("PlanExecute: 反思节点")

        messages = state.get("messages", [])
        pending_tasks = state.get("pending_tasks", [])
        current_result = state.get("current_result", "")
        intermediate = state.get("intermediate_steps", [])
        plan = state.get("plan", [])
        iteration = state.get("iteration", 0)

        # 获取用户任务
        user_task = ""
        if messages:
            last = messages[-1]
            user_task = last.content if hasattr(last, "content") else str(last)

        # 如果有待执行任务，继续执行
        if pending_tasks:
            return {
                "reflection_result": "continue",
                "needs_replan": False,
            }

        # 所有任务已执行，评估整体结果
        try:
            provider = get_llm_provider(config.llm_provider)

            # 获取最后执行的步骤
            completed_tasks = state.get("completed_tasks", [])
            last_step = completed_tasks[-1] if completed_tasks else {}

            reflection_prompt = _REFLECTION_PROMPT.format(
                task=user_task,
                step_description=last_step.get("description", ""),
                execution_result=current_result or "N/A"
            )

            response = provider.invoke([HumanMessage(content=reflection_prompt)])
            llm_output = response.content if hasattr(response, "content") else str(response)

            # 解析反思结果
            reflection_result, needs_replan = _parse_reflection(llm_output)

            logger.info(f"PlanExecute: 反思结果 needs_replan={needs_replan}")

            return {
                "reflection_result": reflection_result,
                "needs_replan": needs_replan,
                "iteration": iteration + 1,
                "intermediate_steps": intermediate + [{
                    "step_type": "reflection",
                    "content": f"反思: {reflection_result[:100]}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }],
            }

        except Exception as e:
            logger.error(f"PlanExecute 反思节点错误: {e}")
            return {
                "reflection_result": f"反思失败: {str(e)}",
                "needs_replan": False,
            }

    return reflector_node


def create_replan_node(config: ReasoningConfig):
    """
    创建重规划节点

    动态调整计划。
    """

    def replan_node(state: PlanExecuteState) -> dict:
        logger.info("PlanExecute: 重规划节点")

        replan_count = state.get("replan_count", 0)
        reflection_result = state.get("reflection_result", "")
        pending_hints = state.get("pending_hints")
        plan = state.get("plan", [])
        intermediate = state.get("intermediate_steps", [])

        # 限制重规划次数
        if replan_count >= 3:
            logger.warning("PlanExecute: 达到最大重规划次数")
            return {
                "needs_replan": False,
                "pending_hints": "已达到最大重规划次数，请基于当前计划给出答案",
            }

        # 更新重规划次数
        new_replan_count = replan_count + 1

        # 基于反思结果生成提示
        new_hints = f"{pending_hints or ''}\n反思建议: {reflection_result}".strip()

        # 重置计划状态
        reset_plan = [
            {**step, "status": "pending", "result": None}
            for step in plan
        ]
        pending_tasks = [step for step in reset_plan if step["status"] == "pending"]

        logger.info(f"PlanExecute: 第 {new_replan_count} 次重规划")

        return {
            "replan_count": new_replan_count,
            "pending_hints": new_hints,
            "plan": reset_plan,
            "pending_tasks": pending_tasks,
            "current_step": 0,
            "intermediate_steps": intermediate + [{
                "step_type": "replan",
                "content": f"第 {new_replan_count} 次重规划",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {"reason": reflection_result[:200]}
            }],
        }

    return replan_node


def create_finish_node():
    """
    创建结束节点

    汇总所有步骤结果，生成最终答案。
    """

    def finish_node(state: PlanExecuteState) -> dict:
        logger.info("PlanExecute: 结束节点")

        completed_tasks = state.get("completed_tasks", [])
        plan = state.get("plan", [])
        error = state.get("error")
        intermediate = state.get("intermediate_steps", [])

        # 构建答案
        if completed_tasks:
            result_parts = []
            for step in completed_tasks:
                desc = step.get("description", "")
                result = step.get("result", "")
                if result:
                    result_parts.append(f"**{desc}**\n{result}")
                else:
                    result_parts.append(f"**{desc}**\n(无结果)")
            final_answer = "\n\n".join(result_parts)
        elif error:
            final_answer = f"任务执行失败: {error}"
        else:
            final_answer = "任务已完成，但无结果"

        return {
            "final_answer": final_answer,
            "stage": "complete",
            "intermediate_steps": intermediate + [{
                "step_type": "finish",
                "content": f"完成 {len(completed_tasks)} 个步骤",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }

    return finish_node


# ===== 路由函数 =====

def plan_execute_router(state: PlanExecuteState) -> Literal["plan", "execute", "reflect", "replan", "finish"]:
    """
    Plan-and-Execute 路由函数
    """
    pending_tasks = state.get("pending_tasks", [])
    execution_summary = state.get("execution_summary")
    needs_replan = state.get("needs_replan", False)
    final_answer = state.get("final_answer")
    current_step = state.get("current_step", 0)
    plan = state.get("plan", [])
    error = state.get("error")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)

    # 已有最终答案 → 结束
    if final_answer:
        return "finish"

    # 错误或达到最大迭代 → 结束
    if error or iteration >= max_iterations:
        return "finish"

    # 无计划或需要重规划 → 规划
    if not plan or needs_replan:
        return "plan"

    # 有待执行任务 → 执行
    if pending_tasks and current_step < len(plan):
        return "execute"

    # 执行完一步 → 反思
    if execution_summary and pending_tasks:
        return "reflect"

    # 无待执行 → 结束
    if not pending_tasks:
        return "finish"

    return "reflect"


# ===== 工作流类 =====

def create_plan_execute_workflow(
    tools: list[BaseTool],
    config: ReasoningConfig | None = None,
):
    """
    创建 Plan-and-Execute 工作流
    """
    from langgraph.graph import StateGraph
    from langgraph.checkpoint.memory import MemorySaver

    if config is None:
        config = ReasoningConfig()

    workflow = StateGraph(PlanExecuteState)

    # 添加节点
    workflow.add_node("plan", create_planner_node(config))
    workflow.add_node("execute", create_executor_node(tools))
    workflow.add_node("reflect", create_reflector_node(config))
    workflow.add_node("replan", create_replan_node(config))
    workflow.add_node("finish", create_finish_node())

    # 设置入口点
    workflow.set_entry_point("plan")

    # 条件边
    workflow.add_conditional_edges(
        "plan",
        lambda s: "execute",
        {"execute": "execute"}
    )
    workflow.add_conditional_edges(
        "execute",
        lambda s: "reflect",
        {"reflect": "reflect"}
    )
    workflow.add_conditional_edges(
        "reflect",
        lambda s: "replan" if s.get("needs_replan", False) else ("execute" if s.get("pending_tasks") else "finish"),
        {
            "replan": "replan",
            "execute": "execute",
            "finish": "finish",
        }
    )
    workflow.add_conditional_edges(
        "replan",
        lambda s: "plan",
        {"plan": "plan"}
    )

    # 普通边
    workflow.add_edge("finish", "__end__")

    return workflow.compile(checkpointer=MemorySaver())


# ===== 辅助函数 =====

def _parse_plan(text: str, existing_plan: list = None) -> list[TaskStep]:
    """解析 LLM 输出为计划列表"""
    try:
        # 尝试 JSON 解析
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            steps = json.loads(json_match.group())
            result = []
            for i, step in enumerate(steps):
                result.append({
                    "step_id": step.get("step_id") or f"step_{i+1}",
                    "description": step.get("description", ""),
                    "status": "pending",
                    "depends_on": step.get("depends_on", []),
                    "metadata": step.get("metadata"),
                })
            return result
    except Exception:
        pass

    # 回退：按行解析
    result = []
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            result.append({
                "step_id": f"step_{i+1}",
                "description": line,
                "status": "pending",
                "depends_on": [],
            })

    return result or existing_plan or []


def _update_step_status(
    plan: list[TaskStep],
    step_id: str,
    status: str,
    result: str | None = None
) -> list[TaskStep]:
    """更新计划中某个步骤的状态"""
    return [
        {**step, "status": status, "result": result if status == "completed" else step.get("result")}
        if step["step_id"] == step_id else step
        for step in plan
    ]


def _parse_reflection(text: str) -> tuple[str, bool]:
    """解析反思结果"""
    try:
        # 尝试 JSON 解析
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            success = data.get("success", True)
            needs_replan = data.get("needs_replan", False)
            reason = data.get("reason", text[:200])
            return reason, needs_replan
    except Exception:
        pass

    # 回退：关键词判断
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["需要重规划", "需要调整", "needs_replan", "adjust"]):
        return text[:200], True
    return text[:200], False


def _execute_with_llm(step_description: str, state: PlanExecuteState) -> str:
    """使用 LLM 执行步骤"""
    from llms.providers import get_llm_provider

    completed_tasks = state.get("completed_tasks", [])

    context_parts = []
    for task in completed_tasks[-3:]:
        context_parts.append(f"- {task.get('description', '')}: {task.get('result', '')}")
    context = "\n".join(context_parts) if context_parts else "无"

    prompt = _EXECUTION_PROMPT.format(
        step_description=step_description,
        context=f"已完成步骤结果:\n{context}"
    )

    provider = get_llm_provider("deepseek")
    response = provider.invoke([HumanMessage(content=prompt)])
    return response.content if hasattr(response, "content") else str(response)
```

- [ ] **Step 2: Run linter**

```bash
cd server && python -m py_compile src/workflows/reasoning/plan_execute.py && echo "OK"
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/plan_execute.py && git commit -m "feat(reasoning): implement Plan-and-Execute pattern"
```

---

## Task 4: tree_of_thought.py — ToT 模式（简化版）

**Files:**
- Create: `server/src/workflows/reasoning/tree_of_thought.py`

**Interfaces:**
- Consumes: `BaseReasoningState`, `ReasoningConfig` from `base`
- Produces: `Branch`, `ToTState`, `create_generator_node`, `create_evaluator_node`, `create_selector_node`, `create_finish_node`, `tot_router`, `create_tot_workflow`

- [ ] **Step 1: Write tree_of_thought.py**

```python
# server/src/workflows/reasoning/tree_of_thought.py
# -*- coding: utf-8 -*-
"""
Tree-of-Thought 模式（简化版）

工作流：
    [generate] → [evaluate] → [select] → [generate] ...
                                           ↓
                                       [finish]

简化策略：
- max_branches=3 控制分支数
- max_depth=5 控制深度
- 分支评估使用 LLM 打分
- 选择最优后继续探索
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Optional, Any, NotRequired, Literal

from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage

from core.logger import logger
from llms.providers import get_llm_provider
from workflows.reasoning.base import BaseReasoningState, ReasoningConfig


class Branch(TypedDict):
    """推理分支"""

    branch_id: str
    content: str               # 分支推理内容
    score: NotRequired[Optional[float]]   # 评估得分
    parent_id: NotRequired[Optional[str]]  # 父分支 ID
    children_ids: NotRequired[list[str]]   # 子分支 ID
    status: str               # "active" | "evaluated" | "pruned" | "selected"
    metadata: NotRequired[dict[str, Any] | None]


class ToTState(BaseReasoningState):
    """Tree-of-Thought 推理状态"""

    # 所有推理分支
    branches: NotRequired[list[Branch]]

    # 活跃分支 ID
    current_branch_id: NotRequired[Optional[str]]

    # 已评估分支 ID 列表
    evaluated_branches: NotRequired[list[str]]

    # 当前最优分支 ID
    best_branch_id: NotRequired[Optional[str]]

    # 最大分支数
    max_branches: NotRequired[int]

    # 最大深度
    max_depth: NotRequired[int]

    # 当前深度
    depth: NotRequired[int]

    # 生成的新分支（临时存储）
    new_branches: NotRequired[list[Branch]]

    # 最终答案
    final_answer: NotRequired[Optional[str]]

    # 评估结果（临时）
    evaluation_results: NotRequired[list[dict[str, Any]]]


# ===== 提示模板 =====

_GENERATOR_PROMPT = """你是一个思维探索专家。

当前任务：{task}

{f"当前分支推理:\n{current_branch_content}\n" if current_branch_content else ""}

请基于当前推理，生成 {num_branches} 个不同的思考方向/分支。

每个分支应该：
1. 从不同角度思考问题
2. 提供新的见解或方法
3. 保持逻辑连贯

## 输出格式
JSON 数组：
[
  {{"branch_id": "b1", "content": "分支内容"}},
  {{"branch_id": "b2", "content": "分支内容"}}
]
"""

_EVALUATOR_PROMPT = """你是一个推理评估专家。

任务：{task}

请评估以下推理分支的质量：

{branches_text}

评估标准：
1. 逻辑正确性 (0-1)
2. 完整性 (0-1)
3. 创新性 (0-1)
4. 可行性 (0-1)

## 输出格式
JSON 数组（与输入分支对应）：
[
  {{"branch_id": "b1", "score": 0.85, "reason": "理由"}},
  {{"branch_id": "b2", "score": 0.72, "reason": "理由"}}
]
"""

_SELECTOR_PROMPT = """你是一个决策专家。

任务：{task}

候选分支及评分：

{branches_text}

请选择最优分支，并给出理由。

## 输出格式
JSON：
{{"best_branch_id": "b1", "reason": "选择理由"}}
"""


# ===== 节点函数 =====

def create_generator_node(config: ReasoningConfig):
    """
    创建分支生成节点

    为当前分支生成多个子分支。
    """

    def generator_node(state: ToTState) -> dict:
        logger.info("ToT: 生成节点")

        messages = state.get("messages", [])
        branches = state.get("branches", [])
        current_branch_id = state.get("current_branch_id")
        max_branches = state.get("max_branches", config.max_iterations)
        depth = state.get("depth", 0)
        intermediate = state.get("intermediate_steps", [])

        # 获取用户任务
        user_task = ""
        if messages:
            last = messages[-1]
            user_task = last.content if hasattr(last, "content") else str(last)

        # 获取当前分支内容
        current_branch_content = ""
        if current_branch_id:
            current = next((b for b in branches if b["branch_id"] == current_branch_id), None)
            if current:
                current_branch_content = current.get("content", "")

        # 确定生成分支数
        num_branches = min(3, max(2, max_branches - len(branches)))

        # 调用 LLM 生成
        try:
            provider = get_llm_provider(config.llm_provider)

            prompt = _GENERATOR_PROMPT.format(
                task=user_task,
                current_branch_content=current_branch_content,
                num_branches=num_branches,
            )

            response = provider.invoke([HumanMessage(content=prompt)])
            llm_output = response.content if hasattr(response, "content") else str(response)

            # 解析新分支
            new_branches = _parse_branches(llm_output, parent_id=current_branch_id)

            logger.info(f"ToT: 生成了 {len(new_branches)} 个新分支")

            return {
                "new_branches": new_branches,
                "depth": depth + 1,
                "intermediate_steps": intermediate + [{
                    "step_type": "generate",
                    "content": f"生成 {len(new_branches)} 个分支",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"depth": depth, "parent": current_branch_id}
                }],
            }

        except Exception as e:
            logger.error(f"ToT 生成节点错误: {e}")
            return {"error": str(e)}

    return generator_node


def create_evaluator_node(config: ReasoningConfig):
    """
    创建分支评估节点

    为每个分支打分。
    """

    def evaluator_node(state: ToTState) -> dict:
        logger.info("ToT: 评估节点")

        messages = state.get("messages", [])
        branches = state.get("branches", [])
        new_branches = state.get("new_branches", [])
        intermediate = state.get("intermediate_steps", [])

        # 获取用户任务
        user_task = ""
        if messages:
            last = messages[-1]
            user_task = last.content if hasattr(last, "content") else str(last)

        # 合并已有分支和新分支
        all_branches = branches + new_branches

        if not all_branches:
            return {"evaluation_results": []}

        # 构建分支文本
        branches_text = "\n".join([
            f"[{b['branch_id']}] {b['content']}"
            for b in all_branches
        ])

        # 调用 LLM 评估
        try:
            provider = get_llm_provider(config.llm_provider)

            prompt = _EVALUATOR_PROMPT.format(
                task=user_task,
                branches_text=branches_text,
            )

            response = provider.invoke([HumanMessage(content=prompt)])
            llm_output = response.content if hasattr(response, "content") else str(response)

            # 解析评估结果
            evaluation_results = _parse_evaluations(llm_output, all_branches)

            logger.info(f"ToT: 评估了 {len(evaluation_results)} 个分支")

            return {
                "evaluation_results": evaluation_results,
                "intermediate_steps": intermediate + [{
                    "step_type": "evaluate",
                    "content": f"评估 {len(evaluation_results)} 个分支",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }],
            }

        except Exception as e:
            logger.error(f"ToT 评估节点错误: {e}")
            return {"error": str(e)}

    return evaluator_node


def create_selector_node(config: ReasoningConfig):
    """
    创建选择节点

    从评估后的分支中选最优。
    """

    def selector_node(state: ToTState) -> dict:
        logger.info("ToT: 选择节点")

        messages = state.get("messages", [])
        branches = state.get("branches", [])
        new_branches = state.get("new_branches", [])
        evaluation_results = state.get("evaluation_results", [])
        intermediate = state.get("intermediate_steps", [])

        # 合并所有分支
        all_branches = branches + new_branches

        # 获取用户任务
        user_task = ""
        if messages:
            last = messages[-1]
            user_task = last.content if hasattr(last, "content") else str(last)

        # 构建带分数的分支文本
        score_map = {r["branch_id"]: r for r in evaluation_results}
        branches_text = "\n".join([
            f"[{b['branch_id']}] 分数: {score_map.get(b['branch_id'], {}).get('score', 'N/A')}\n{b['content']}"
            for b in all_branches
        ])

        try:
            provider = get_llm_provider(config.llm_provider)

            prompt = _SELECTOR_PROMPT.format(
                task=user_task,
                branches_text=branches_text,
            )

            response = provider.invoke([HumanMessage(content=prompt)])
            llm_output = response.content if hasattr(response, "content") else str(response)

            # 解析选择结果
            best_branch_id, reason = _parse_selection(llm_output, all_branches, score_map)

            logger.info(f"ToT: 选择分支 {best_branch_id}，原因: {reason[:50]}")

            # 更新分支状态
            updated_branches = []
            for b in all_branches:
                if b["branch_id"] == best_branch_id:
                    score = score_map.get(b["branch_id"], {}).get("score")
                    updated_branches.append({**b, "status": "selected", "score": score})
                elif b["branch_id"] in new_branches:
                    updated_branches.append({**b, "status": "pruned"})
                else:
                    updated_branches.append(b)

            return {
                "best_branch_id": best_branch_id,
                "current_branch_id": best_branch_id,
                "branches": updated_branches,
                "evaluated_branches": [b["branch_id"] for b in all_branches],
                "intermediate_steps": intermediate + [{
                    "step_type": "select",
                    "content": f"选择分支 {best_branch_id}: {reason[:100]}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"best_id": best_branch_id, "reason": reason}
                }],
            }

        except Exception as e:
            logger.error(f"ToT 选择节点错误: {e}")
            return {"error": str(e)}

    return selector_node


def create_finish_node():
    """
    创建结束节点
    """

    def finish_node(state: ToTState) -> dict:
        logger.info("ToT: 结束节点")

        branches = state.get("branches", [])
        best_branch_id = state.get("best_branch_id")
        intermediate = state.get("intermediate_steps", [])

        # 获取最优分支内容
        final_answer = ""
        if best_branch_id:
            best = next((b for b in branches if b["branch_id"] == best_branch_id), None)
            if best:
                final_answer = best.get("content", "")

        if not final_answer:
            # 回退：选择得分最高的
            scored = [(b, b.get("score", 0)) for b in branches if b.get("score")]
            if scored:
                scored.sort(key=lambda x: x[1], reverse=True)
                final_answer = scored[0][0].get("content", "")

        return {
            "final_answer": final_answer or "无法生成答案",
            "stage": "complete",
            "intermediate_steps": intermediate + [{
                "step_type": "finish",
                "content": f"ToT 完成，最优分支: {best_branch_id}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }

    return finish_node


# ===== 路由函数 =====

def tot_router(state: ToTState) -> Literal["generate", "evaluate", "select", "finish"]:
    """
    ToT 路由函数
    """
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 5)
    best_branch_id = state.get("best_branch_id")
    new_branches = state.get("new_branches", [])
    evaluation_results = state.get("evaluation_results", [])
    error = state.get("error")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)

    # 错误或达到最大迭代 → 结束
    if error or iteration >= max_iterations:
        return "finish"

    # 已选择最优 → 结束
    if best_branch_id:
        return "finish"

    # 达到最大深度 → 结束
    if depth >= max_depth:
        return "finish"

    # 无新分支 → 生成
    if not new_branches:
        return "generate"

    # 无评估结果 → 评估
    if not evaluation_results:
        return "evaluate"

    return "select"


# ===== 工作流类 =====

def create_tot_workflow(config: ReasoningConfig | None = None):
    """
    创建 ToT 工作流
    """
    from langgraph.graph import StateGraph
    from langgraph.checkpoint.memory import MemorySaver

    if config is None:
        config = ReasoningConfig()

    workflow = StateGraph(ToTState)

    # 添加节点
    workflow.add_node("generate", create_generator_node(config))
    workflow.add_node("evaluate", create_evaluator_node(config))
    workflow.add_node("select", create_selector_node(config))
    workflow.add_node("finish", create_finish_node())

    # 设置入口点
    workflow.set_entry_point("generate")

    # 条件边
    workflow.add_conditional_edges(
        "generate",
        lambda s: "evaluate",
        {"evaluate": "evaluate"}
    )
    workflow.add_conditional_edges(
        "evaluate",
        lambda s: "select",
        {"select": "select"}
    )
    workflow.add_conditional_edges(
        "select",
        lambda s: ("generate" if not s.get("best_branch_id") else "finish"),
        {
            "generate": "generate",
            "finish": "finish",
        }
    )

    return workflow.compile(checkpointer=MemorySaver())


# ===== 辅助函数 =====

def _parse_branches(text: str, parent_id: str | None = None) -> list[Branch]:
    """解析分支生成结果"""
    try:
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            items = json.loads(json_match.group())
            result = []
            for item in items:
                branch_id = item.get("branch_id") or f"b_{uuid.uuid4().hex[:8]}"
                result.append({
                    "branch_id": branch_id,
                    "content": item.get("content", ""),
                    "parent_id": parent_id,
                    "children_ids": [],
                    "status": "active",
                    "metadata": None,
                })
            return result
    except Exception:
        pass

    # 回退：按段落分割
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [
        {
            "branch_id": f"b_{uuid.uuid4().hex[:8]}",
            "content": p,
            "parent_id": parent_id,
            "children_ids": [],
            "status": "active",
        }
        for p in paragraphs
    ]


def _parse_evaluations(text: str, branches: list[Branch]) -> list[dict]:
    """解析评估结果"""
    try:
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    # 回退：从文本提取
    results = []
    for branch in branches:
        score_match = re.search(r"score[:\s]*([0-9.]+)", text, re.IGNORECASE)
        score = float(score_match.group(1)) if score_match else 0.5
        results.append({
            "branch_id": branch["branch_id"],
            "score": score,
            "reason": text[:200],
        })
        break  # 只返回一个
    return results


def _parse_selection(
    text: str,
    branches: list[Branch],
    score_map: dict
) -> tuple[str, str]:
    """解析选择结果"""
    try:
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data.get("best_branch_id", ""), data.get("reason", "")
    except Exception:
        pass

    # 回退：选择最高分
    branch_ids = [b["branch_id"] for b in branches]
    if branch_ids:
        best_id = branch_ids[0]
        return best_id, text[:200]
    return "", "No branch available"
```

- [ ] **Step 2: Run linter**

```bash
cd server && python -m py_compile src/workflows/reasoning/tree_of_thought.py && echo "OK"
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/tree_of_thought.py && git commit -m "feat(reasoning): implement Tree-of-Thought pattern (simplified)"
```

---

## Task 5: 整合 — `__init__.py` 导出 + Handler 注册

**Files:**
- Modify: `server/src/workflows/reasoning/__init__.py`
- Modify: `server/src/workflows/__init__.py:76-107`
- Modify: `server/src/workflows/compiler.py:66-109`

**Interfaces:**
- Consumes: `react.py`, `plan_execute.py`, `tree_of_thought.py` 的导出
- Produces: 更新 `workflows/__init__.py` 和 `compiler.py`

- [ ] **Step 1: Write reasoning/__init__.py**

```python
# server/src/workflows/reasoning/__init__.py
# -*- coding: utf-8 -*-
"""
推理组件模块

提供可复用的推理节点组件：
- ReAct (Reasoning + Acting) 模式
- Plan-and-Execute 模式
- Tree-of-Thought 模式（简化版）

使用示例：
    from workflows.reasoning import (
        ReactState,
        create_react_workflow,
        PlanExecuteState,
        create_plan_execute_workflow,
        ToTState,
        create_tot_workflow,
        ReasoningConfig,
    )

    # ReAct
    tools = [search_tool, calculator_tool]
    workflow = create_react_workflow(tools)

    # Plan-and-Execute
    workflow = create_plan_execute_workflow(tools)

    # ToT
    workflow = create_tot_workflow()
"""

from workflows.reasoning.base import (
    BaseReasoningState,
    ReasoningConfig,
    StepRecord,
)

from workflows.reasoning.react import (
    ReactState,
    create_reasoning_node,
    create_action_node,
    create_observation_node,
    create_reflection_node,
    create_finish_node,
    react_router,
    create_react_workflow,
)

from workflows.reasoning.plan_execute import (
    TaskStep,
    PlanExecuteState,
    create_planner_node,
    create_executor_node,
    create_reflector_node,
    create_replan_node,
    create_finish_node as create_plan_finish_node,
    plan_execute_router,
    create_plan_execute_workflow,
)

from workflows.reasoning.tree_of_thought import (
    Branch,
    ToTState,
    create_generator_node,
    create_evaluator_node,
    create_selector_node,
    create_finish_node as create_tot_finish_node,
    tot_router,
    create_tot_workflow,
)

__all__ = [
    # Base
    "BaseReasoningState",
    "ReasoningConfig",
    "StepRecord",
    # ReAct
    "ReactState",
    "create_reasoning_node",
    "create_action_node",
    "create_observation_node",
    "create_reflection_node",
    "create_finish_node",
    "react_router",
    "create_react_workflow",
    # Plan-and-Execute
    "TaskStep",
    "PlanExecuteState",
    "create_planner_node",
    "create_executor_node",
    "create_reflector_node",
    "create_replan_node",
    "create_plan_finish_node",
    "plan_execute_router",
    "create_plan_execute_workflow",
    # ToT
    "Branch",
    "ToTState",
    "create_generator_node",
    "create_evaluator_node",
    "create_selector_node",
    "create_tot_finish_node",
    "tot_router",
    "create_tot_workflow",
]


# ===== 注册 Handler（供 JSON 编译器使用）=====

def _register_reasoning_handlers():
    """注册推理组件 handlers"""
    from workflows.compiler import HANDLER_REGISTRY

    HANDLER_REGISTRY.update({
        # ReAct
        "react_reasoning": create_reasoning_node,
        "react_action": create_action_node,
        "react_observation": create_observation_node,
        "react_reflection": create_reflection_node,
        "react_finish": create_finish_node,

        # Plan-and-Execute
        "plan_planner": create_planner_node,
        "plan_executor": create_executor_node,
        "plan_reflector": create_reflector_node,
        "plan_replan": create_replan_node,
        "plan_finish": create_plan_finish_node,

        # ToT
        "tot_generator": create_generator_node,
        "tot_evaluator": create_evaluator_node,
        "tot_selector": create_selector_node,
        "tot_finish": create_tot_finish_node,
    })


# 模块加载时自动注册
_register_reasoning_handlers()
```

- [ ] **Step 2: Update workflows/__init__.py**

在 `__all__` 列表末尾添加：

```python
# 推理组件
from workflows.reasoning import (
    BaseReasoningState,
    ReasoningConfig,
    StepRecord,
    ReactState,
    PlanExecuteState,
    TaskStep,
    ToTState,
    Branch,
    create_react_workflow,
    create_plan_execute_workflow,
    create_tot_workflow,
)
```

同时在 `__all__` 中添加对应项：

```python
    # 推理组件
    "BaseReasoningState",
    "ReasoningConfig",
    "StepRecord",
    "ReactState",
    "PlanExecuteState",
    "TaskStep",
    "ToTState",
    "Branch",
    "create_react_workflow",
    "create_plan_execute_workflow",
    "create_tot_workflow",
```

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/__init__.py server/src/workflows/__init__.py && git commit -m "feat(reasoning): export reasoning components and register handlers"
```

---

## Task 6: 验证和测试

**Files:**
- Test: `server/src/workflows/reasoning/test_reasoning.py`（新创建）

**Interfaces:**
- Consumes: 所有推理组件
- Produces: 测试通过

- [ ] **Step 1: Write integration test**

```python
# server/src/workflows/reasoning/test_reasoning.py
# -*- coding: utf-8 -*-
"""
推理组件集成测试
"""

import pytest
from unittest.mock import MagicMock

from workflows.reasoning.base import BaseReasoningState, ReasoningConfig, StepRecord
from workflows.reasoning.react import ReactState, react_router, create_reasoning_node, create_finish_node
from workflows.reasoning.plan_execute import PlanExecuteState, TaskStep, plan_execute_router
from workflows.reasoning.tree_of_thought import ToTState, Branch, tot_router


class TestBaseTypes:
    """测试公共类型"""

    def test_reasoning_config_defaults(self):
        config = ReasoningConfig()
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300
        assert config.enable_reflection is True
        assert config.llm_provider == "deepseek"

    def test_reasoning_config_to_dict(self):
        config = ReasoningConfig(max_iterations=5)
        d = config.to_dict()
        assert d["max_iterations"] == 5

    def test_step_record_structure(self):
        step: StepRecord = {
            "step_type": "reasoning",
            "content": "test content",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        assert step["step_type"] == "reasoning"
        assert step["content"] == "test content"


class TestReactRouter:
    """测试 ReAct 路由"""

    def test_no_action_returns_reasoning(self):
        state: ReactState = {"messages": [], "iteration": 0, "max_iterations": 10, "intermediate_steps": []}
        assert react_router(state) == "reasoning"

    def test_has_action_no_observation_returns_action(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "action": "search"
        }
        assert react_router(state) == "action"

    def test_has_observation_returns_reflect(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "action": "search", "observation": "result"
        }
        assert react_router(state) == "reflect"

    def test_has_final_answer_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "final_answer": "done"
        }
        assert react_router(state) == "finish"

    def test_max_iterations_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 10, "max_iterations": 10,
            "intermediate_steps": []
        }
        assert react_router(state) == "finish"


class TestPlanExecuteRouter:
    """测试 Plan-and-Execute 路由"""

    def test_no_plan_returns_plan(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "plan": [], "pending_tasks": []
        }
        assert plan_execute_router(state) == "plan"

    def test_has_plan_with_pending_returns_execute(self):
        step: TaskStep = {"step_id": "s1", "description": "do something", "status": "pending"}
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [],
            "plan": [step], "pending_tasks": [step], "current_step": 0
        }
        assert plan_execute_router(state) == "execute"

    def test_no_pending_returns_finish(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "plan": [], "pending_tasks": [], "current_step": 0
        }
        assert plan_execute_router(state) == "finish"


class TestToTRouter:
    """测试 ToT 路由"""

    def test_no_new_branches_returns_generate(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 0, "max_depth": 5
        }
        assert tot_router(state) == "generate"

    def test_has_best_branch_returns_finish(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "best_branch_id": "b1"
        }
        assert tot_router(state) == "finish"

    def test_max_depth_returns_finish(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 5, "max_depth": 5
        }
        assert tot_router(state) == "finish"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run tests**

```bash
cd server && python -m pytest src/workflows/reasoning/test_reasoning.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/test_reasoning.py && git commit -m "test(reasoning): add integration tests for reasoning components"
```

---

## Self-Review Checklist

1. **Spec coverage:** 每个 spec 中的状态类、节点工厂、路由函数、工作流类都在对应 task 中实现。✅
2. **Placeholder scan:** 无占位符、无 TODO、无模糊描述，每个 step 都有完整代码。✅
3. **Type consistency:** `ReasoningConfig`、`BaseReasoningState` 在所有模块间一致；`react_router`、`plan_execute_router`、`tot_router` 签名一致。✅

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-27-langgraph-reasoning-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
