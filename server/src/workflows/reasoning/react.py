# -*- coding: utf-8 -*-
"""
ReAct (Reasoning + Acting) 模式

实现经典的 ReAct 推理循环：思考（Reasoning）→ 行动（Action）→ 观察（Observation）→ 反思（Reflection），
直到满足结束条件或达到最大迭代次数。

工作流：

    [reasoning] → [acting] → [observation] → [reflection]
         ↑                                     ↓
         └────────────── (should_continue) ←───┘
                            ↓
                         [finish]

节点职责：
- reasoning: 让 LLM 分析当前状态、产生思考（thought），并决定下一步行动（action）
- acting: 根据 LLM 决策执行具体工具
- observation: 收集工具执行结果，更新到状态
- reflection: 对当前迭代进行反思，决定是否继续
- finish: 输出最终答案
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, NotRequired, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from core.logger import logger
from llms.providers import get_llm_provider
from workflows.base import BaseWorkflow
from workflows.reasoning.base import (
    BaseReasoningState,
    ReasoningConfig,
    StepRecord,
)


# ===== 状态类型别名（便于类型提示）=====

class ReactState(BaseReasoningState):
    """ReAct 推理状态"""

    thought: NotRequired[Optional[str]]
    action: NotRequired[Optional[str]]
    action_input: NotRequired[Optional[str]]
    observation: NotRequired[Optional[str]]
    should_continue: NotRequired[Optional[bool]]
    final_answer: NotRequired[Optional[str]]
    tool_results: NotRequired[Optional[dict[str, Any]]]


# ===== 提示模板 =====

_REACT_SYSTEM_PROMPT = """你是一个 ReAct (Reasoning + Acting) 推理代理。

请严格按以下 JSON 格式输出你的每一步推理：

```json
{
  "thought": "你当前对问题的思考",
  "action": "工具名称，或 FINISH（表示已得到最终答案）",
  "action_input": { ... },  // 工具参数，当 action=FINISH 时可省略
  "is_final": false          // 当 action=FINISH 时设为 true，并提供 final_answer 字段
}
```

规则：
1. 每一步都必须先输出 thought，说明你的推理逻辑
2. action 必须是已注册的工具名之一，或 FINISH
3. 当你可以直接回答用户问题时，将 action 设为 FINISH 并提供 final_answer
4. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""


_THOUGHT_PATTERN = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


# ===== 辅助函数 =====


def _now_iso() -> str:
    """获取当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def _extract_user_query(state: ReactState) -> str:
    """从状态中提取用户输入"""
    messages = state.get("messages", []) or []
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, dict):
        return last.get("content", "")
    return getattr(last, "content", str(last))


def _append_step(
    steps: list[StepRecord],
    step_type: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
) -> list[StepRecord]:
    """构造新的步骤列表（不可变更新）"""
    record: StepRecord = {
        "step_type": step_type,
        "content": content,
        "timestamp": _now_iso(),
    }
    if metadata is not None:
        record["metadata"] = metadata
    return [*steps, record]


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """
    解析 LLM 返回的 JSON 响应

    优先从 ```json 代码块提取，失败时回退到整段文本匹配。
    """
    if not raw:
        return {"thought": "", "action": "FINISH", "is_final": True, "final_answer": ""}

    match = _THOUGHT_PATTERN.search(raw)
    candidate = match.group(1).strip() if match else raw[raw.find("{") :] if "{" in raw else None

    if candidate is None:
        return {"thought": raw.strip(), "action": "FINISH", "is_final": True, "final_answer": raw.strip()}

    try:
        start = candidate.find("{")
        if start < 0:
            raise json.JSONDecodeError("JSON object not found", candidate, 0)
        parsed, _ = json.JSONDecoder().raw_decode(candidate[start:])
        return parsed
    except json.JSONDecodeError:
        return {"thought": raw.strip(), "action": "FINISH", "is_final": True, "final_answer": raw.strip()}


def _extract_message_content(response: Any) -> str:
    """兼容不同形态的 LLM 响应"""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    content = getattr(response, "content", None)
    if content is not None:
        return content
    return str(response)


# ===== 节点工厂 =====


def create_reasoning_node(config: ReasoningConfig) -> Callable[[ReactState], dict]:
    """
    创建 reasoning 节点

    调用 LLM 进行思考并产生下一步行动决策。
    """

    def reasoning_node(state: ReactState) -> dict:
        iteration = state.get("iteration", 0)
        logger.info(f"ReAct: 推理节点 [迭代 {iteration + 1}/{state.get('max_iterations', config.max_iterations)}]")

        user_query = _extract_user_query(state)
        system_prompt = config.system_prompt or _REACT_SYSTEM_PROMPT

        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        if user_query:
            messages.append(HumanMessage(content=user_query))

        # 注入历史步骤上下文
        history = state.get("intermediate_steps", []) or []
        if history:
            history_lines = [
                f"[{i + 1}] ({s.get('step_type', '')}) {s.get('content', '')}"
                for i, s in enumerate(history)
            ]
            messages.append(HumanMessage(content="历史步骤：\n" + "\n".join(history_lines)))

        try:
            provider = get_llm_provider(config.llm_provider)
            response = provider.invoke(messages)
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"ReAct: LLM 调用失败 - {exc}")
            return {
                "error": f"LLM 调用失败: {exc}",
                "final_answer": f"[推理失败] {exc}",
                "should_continue": False,
                "intermediate_steps": _append_step(
                    state.get("intermediate_steps", []) or [],
                    "reasoning",
                    f"LLM 调用失败: {exc}",
                    {"error": str(exc)},
                ),
            }

        parsed = _parse_llm_response(raw)
        thought = str(parsed.get("thought", "")).strip()
        action = str(parsed.get("action", "FINISH")).strip() or "FINISH"
        action_input = parsed.get("action_input") if isinstance(parsed.get("action_input"), dict) else {}
        is_final = bool(parsed.get("is_final", False)) or action.upper() == "FINISH"
        final_answer = parsed.get("final_answer")

        updates: dict[str, Any] = {
            "thought": thought,
            "action": None if is_final else action,
            "action_input": None if is_final else action_input,
            "should_continue": not is_final,
        }

        if is_final:
            updates["final_answer"] = str(final_answer).strip() if final_answer is not None else thought
            updates["intermediate_steps"] = _append_step(
                history,
                "reasoning",
                thought or "[reasoning] 决策结束",
                {"iteration": iteration, "action": "FINISH"},
            )
        else:
            updates["intermediate_steps"] = _append_step(
                history,
                "reasoning",
                thought or f"[reasoning] 决定执行 {action}",
                {"iteration": iteration, "action": action},
            )

        if is_final:
            updates["messages"] = [AIMessage(content=updates["final_answer"])]

        return updates

    return reasoning_node


def create_action_node(tools: Optional[dict[str, Callable[..., Any] | BaseTool]] = None) -> Callable[[ReactState], dict]:
    """
    创建 acting 节点

    执行 LLM 选择的工具。tools 是 name -> callable 或 BaseTool 的映射。
    如果 action 指定的工具未注册，则记录错误并允许反思后退出。
    """
    registry = {tool.name: tool for tool in (tools or {}).values() if isinstance(tool, BaseTool)}
    registry.update({name: tool for name, tool in (tools or {}).items() if not isinstance(tool, BaseTool)})

    def acting_node(state: ReactState) -> dict:
        action = state.get("action")
        if not action:
            logger.warning("ReAct: action 节点收到空 action，跳过执行")
            return {"observation": "无可执行工具（action 为空）", "error": "action 为空"}

        logger.info(f"ReAct: 执行工具 {action}")
        params = state.get("action_input") or {}
        iteration = state.get("iteration", 0)

        tool = registry.get(action)
        if tool is None:
            observation = f"未注册的工具: {action}"
            logger.warning(observation)
            return {
                "observation": observation,
                "error": observation,
                "intermediate_steps": _append_step(
                    state.get("intermediate_steps", []) or [],
                    "action",
                    observation,
                    {"iteration": iteration, "tool": action},
                ),
            }

        try:
            result = tool.invoke(params) if isinstance(tool, BaseTool) else (tool(**params) if isinstance(params, dict) else tool(params))
            observation = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            observation = f"工具执行失败: {exc}"
            logger.error(f"ReAct: 工具 {action} 执行失败 - {exc}")
            return {
                "observation": observation,
                "error": observation,
                "intermediate_steps": _append_step(
                    state.get("intermediate_steps", []) or [],
                    "action",
                    observation,
                    {"iteration": iteration, "tool": action},
                ),
            }

        tool_results = list(state.get("tool_results", []) or [])
        tool_results.append({"tool": action, "input": params, "output": observation})

        return {
            "observation": observation,
            "tool_results": tool_results,
            "intermediate_steps": _append_step(
                state.get("intermediate_steps", []) or [],
                "action",
                observation,
                {"iteration": iteration, "tool": action, "input": params},
            ),
        }

    return action_node


def create_observation_node() -> Callable[[ReactState], dict]:
    """
    创建 observation 节点

    将上一步的 observation 整理成结构化记录，便于后续反思使用。
    """

    def observation_node(state: ReactState) -> dict:
        observation = state.get("observation", "")
        iteration = state.get("iteration", 0)
        action = state.get("action") or "unknown"

        logger.info(f"ReAct: 记录观察 [迭代 {iteration + 1}] - {action}")

        if not observation:
            observation = "（无观察结果）"

        return {
            "intermediate_steps": _append_step(
                state.get("intermediate_steps", []) or [],
                "observation",
                str(observation),
                {"iteration": iteration, "action": action},
            ),
        }

    return observation_node


def create_reflection_node(config: ReasoningConfig) -> Callable[[ReactState], dict]:
    """
    创建 reflection 节点

    当 enable_reflection=True 时调用 LLM 评估当前观察是否足以推进任务，
    否则仅做步数累计。
    """
    enable_reflection = config.enable_reflection
    llm_provider = config.llm_provider

    def reflection_node(state: ReactState) -> dict:
        iteration = state.get("iteration", 0) + 1
        observation = state.get("observation", "")
        thought = state.get("thought", "")
        history = state.get("intermediate_steps", []) or []

        logger.info(f"ReAct: 反思节点 [迭代 {iteration}]")

        should_continue = bool(state.get("should_continue", True))

        if enable_reflection and should_continue:
            try:
                provider = get_llm_provider(llm_provider)
                prompt = (
                    "你是一个反思代理。基于以下信息判断是否可以结束推理：\n"
                    f"思考: {thought}\n观察: {observation}\n"
                    "请仅回复 JSON：{\"should_continue\": true|false, \"reason\": \"...\"}"
                )
                response = provider.invoke([HumanMessage(content=prompt)])
                parsed = _parse_llm_response(_extract_message_content(response))
                should_continue = bool(parsed.get("should_continue", should_continue))
                reason = str(parsed.get("reason", ""))
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"ReAct: 反思失败，保持原状态 - {exc}")
                reason = f"反思失败: {exc}"
        else:
            reason = "反思已禁用或主流程已结束"

        new_step = _append_step(
            history,
            "reflection",
            reason,
            {"iteration": iteration, "should_continue": should_continue},
        )

        return {
            "iteration": iteration,
            "should_continue": should_continue,
            "intermediate_steps": new_step,
        }

    return reflection_node


def create_finish_node() -> Callable[[ReactState], dict]:
    """
    创建 finish 节点

    汇总最终答案到 messages，供下游消费。
    """

    def finish_node(state: ReactState) -> dict:
        final_answer = state.get("final_answer") or state.get("observation") or ""
        logger.info("ReAct: 输出最终答案")
        return {
            "final_answer": final_answer,
            "should_continue": False,
            "messages": [AIMessage(content=final_answer)] if final_answer else [],
        }

    return finish_node


# ===== 路由函数 =====


def react_router(state: ReactState) -> str:
    """
    ReAct 路由函数

    根据 should_continue 与 iteration 决定下一步节点：
    - 反思后且 should_continue=True 且未超 max_iterations → "reasoning"
    - 否则 → "finish"
    """
    if not state.get("should_continue", False):
        return "finish"
    if state.get("error"):
        return "finish"
    if state.get("iteration", 0) >= state.get("max_iterations", 10):
        return "finish"
    return "reasoning"


# ===== 工作流类 =====


class ReactWorkflow(BaseWorkflow):
    """
    ReAct 推理工作流

    编排 reasoning → action → observation → reflection 的循环，
    通过 react_router 决定回到 reasoning 还是进入 finish。
    """

    name = "react"
    description = "ReAct (Reasoning + Acting) 推理工作流"

    def __init__(
        self,
        config: Optional[ReasoningConfig] = None,
        tools: Optional[dict[str, Callable[..., Any]]] = None,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        super().__init__(checkpointer=checkpointer)
        self.config = config or ReasoningConfig()
        self.tools = tools or {}

    def build(self) -> Any:
        """构建 ReAct 状态图"""
        logger.info(f"构建工作流: {self.name}")

        workflow: StateGraph = StateGraph(ReactState)

        reasoning_node = create_reasoning_node(self.config)
        action_node = create_action_node(self.tools)
        observation_node = create_observation_node()
        reflection_node = create_reflection_node(self.config)
        finish_node = create_finish_node()

        workflow.add_node("reasoning", reasoning_node)
        workflow.add_node("acting", action_node)
        workflow.add_node("observation", observation_node)
        workflow.add_node("reflection", reflection_node)
        workflow.add_node("finish", finish_node)

        workflow.set_entry_point("reasoning")

        # reasoning → action（除非推理阶段已经决定结束）
        workflow.add_conditional_edges(
            "reasoning",
            lambda s: "acting" if s.get("action") else "finish",
            {"acting": "acting", "finish": "finish"},
        )

        workflow.add_edge("acting", "observation")
        workflow.add_edge("observation", "reflection")

        workflow.add_conditional_edges(
            "reflection",
            react_router,
            {"reasoning": "reasoning", "finish": "finish"},
        )

        workflow.add_edge("finish", END)

        checkpointer = self.checkpointer or MemorySaver()
        return workflow.compile(checkpointer=checkpointer)


__all__ = [
    "ReactState",
    "create_reasoning_node",
    "create_action_node",
    "create_observation_node",
    "create_reflection_node",
    "create_finish_node",
    "react_router",
    "ReactWorkflow",
]
