# server/src/workflows/reasoning/plan_execute.py
# -*- coding: utf-8 -*-
"""
Plan-and-Execute 模式

工作流：

    [planner] → [executor] → [reflector]
       ↑           ↑           ↓
       └───────────┴─ [replan] ┘ (needs_replan?) → [planner]
                   ↓           ↓
                   └───────────┴─ [finish]
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, NotRequired, Optional, TypedDict

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


# ===== 状态类型 =====


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

输出要求（严格遵守）：

```json
{
  "steps": [
    {
      "step_id": "step-1",
      "description": "步骤的清晰描述",
      "depends_on": []
    }
  ]
}
```

规则：
1. 每个步骤必须有 `step_id`（建议 `step-<n>`）和 `description`
2. 步骤数量控制在 3-8 个之间，保持精简
3. `depends_on` 是可选的，仅当步骤有先后依赖时填写
4. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""


_EXECUTOR_SYSTEM_PROMPT = """你是一个任务执行代理。

你将收到一个执行步骤以及到目前为止已完成的所有步骤结果。
请基于已有信息产出该步骤的最终执行结果。

输出要求（严格遵守）：

```json
{
  "result": "步骤执行结果（文本形式）"
}
```

规则：
1. 充分利用已完成步骤提供的信息
2. 输出应当可被下一步直接复用
3. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""


_REFLECTOR_SYSTEM_PROMPT = """你是一个任务进度反思代理。

你将看到：
- 原始任务
- 已完成步骤及其结果
- 当前步骤的执行结果

请判断：
- 当前任务是否已经可以汇总为最终答案？
- 是否需要重规划（重新调整剩余步骤）？

输出要求（严格遵守）：

```json
{
  "is_done": true | false,
  "needs_replan": true | false,
  "summary": "简短说明当前状态",
  "next_hints": "若 needs_replan=true，对新规划的提示，可为空字符串"
}
```

规则：
1. 仅当所有原始步骤已完成且得到最终答案时，is_done=true
2. 若当前步骤失败或后续步骤不可行，将 needs_replan=true
3. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""


_REPLAN_SYSTEM_PROMPT = """你是一个任务重规划代理。

你将看到：
- 原始任务
- 已完成步骤及其结果
- 反思代理给出的提示（next_hints）

请基于以上信息重新规划剩余步骤（仅输出尚未完成的部分）。

输出要求（严格遵守）：

```json
{
  "steps": [
    {
      "step_id": "step-<n>",
      "description": "步骤的清晰描述",
      "depends_on": []
    }
  ],
  "discard_prior_pending": true
}
```

规则：
1. 保持与已完成步骤 step_id 不冲突
2. 仅生成尚未完成的步骤，不要重复已完成的工作
3. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""


_JSON_BLOCK = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


# ===== 辅助函数 =====


def _now_iso() -> str:
    """获取当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def _extract_user_query(state: PlanExecuteState) -> str:
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


def _parse_json_block(raw: str) -> Optional[Any]:
    """从 LLM 响应中解析 JSON（优先从 ```json 块提取，失败时回退到整段）"""
    if not raw:
        return None
    match = _JSON_BLOCK.search(raw)
    candidate = match.group(1).strip() if match else raw
    start = candidate.find("{")
    if start < 0:
        return None
    try:
        parsed, _ = json.JSONDecoder().raw_decode(candidate[start:])
        return parsed
    except json.JSONDecodeError:
        return None


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


def _make_step(
    description: str,
    step_id: Optional[str] = None,
    status: str = "pending",
    depends_on: Optional[list[str]] = None,
) -> TaskStep:
    """构造一个 TaskStep"""
    sid = step_id or f"step-{uuid.uuid4().hex[:8]}"
    step: TaskStep = {
        "step_id": sid,
        "description": description,
        "status": status,
    }
    if depends_on is not None:
        step["depends_on"] = depends_on
    return step


def _format_step(step: TaskStep) -> str:
    """格式化单个 TaskStep 为可读字符串"""
    sid = step.get("step_id", "?")
    desc = step.get("description", "")
    status = step.get("status", "")
    result = step.get("result")
    base = f"[{sid}] ({status}) {desc}"
    if result:
        return f"{base}\n  结果: {result}"
    return base


def _format_steps(steps: list[TaskStep]) -> str:
    """格式化任务步骤列表"""
    if not steps:
        return "（无）"
    return "\n".join(_format_step(s) for s in steps)


# ===== 节点工厂 =====


def create_planner_node(config: ReasoningConfig) -> Callable[[PlanExecuteState], dict]:
    """
    创建 planner 节点

    调用 LLM 将用户任务分解为有序步骤，写入 `plan` 与 `pending_tasks`。
    首次规划时忽略 `pending_hints`；replan 后调用时会带上 hints。
    """

    def planner_node(state: PlanExecuteState) -> dict:
        iteration = state.get("iteration", 0)
        user_query = _extract_user_query(state)
        hints = state.get("pending_hints")
        replan_count = state.get("replan_count", 0)
        history = state.get("intermediate_steps", []) or []

        logger.info(
            f"PlanExecute: 规划节点 [迭代 {iteration + 1}/{state.get('max_iterations', config.max_iterations)}, "
            f"replan={replan_count}]"
        )

        messages: list[BaseMessage] = [SystemMessage(content=config.system_prompt or _PLANNER_SYSTEM_PROMPT)]
        if user_query:
            messages.append(HumanMessage(content=f"任务：{user_query}"))

        # 重规划场景：注入已完成结果与 hints
        completed = list(state.get("completed_tasks", []) or [])
        if replan_count > 0 or hints:
            context_lines = [f"已完成步骤：\n{_format_steps(completed)}"]
            if hints:
                context_lines.append(f"重规划提示：\n{hints}")
            messages.append(HumanMessage(content="\n\n".join(context_lines)))

        try:
            provider = get_llm_provider(config.llm_provider)
            response = provider.invoke(messages)
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"PlanExecute: Planner LLM 调用失败 - {exc}")
            return {
                "error": f"Planner LLM 调用失败: {exc}",
                "needs_replan": False,
                "intermediate_steps": _append_step(
                    history,
                    "plan",
                    f"LLM 调用失败: {exc}",
                    {"error": str(exc)},
                ),
            }

        parsed = _parse_json_block(raw)
        steps_data = parsed.get("steps") if isinstance(parsed, dict) else None
        if not isinstance(steps_data, list) or not steps_data:
            logger.warning("PlanExecute: Planner 未返回有效步骤，回退为单步")
            plan_steps: list[TaskStep] = [_make_step(user_query or "完成任务")]
        else:
            plan_steps = []
            for item in steps_data:
                if not isinstance(item, dict):
                    continue
                desc = str(item.get("description", "")).strip()
                if not desc:
                    continue
                sid = item.get("step_id")
                deps = item.get("depends_on")
                plan_steps.append(
                    _make_step(
                        desc,
                        step_id=str(sid).strip() if sid else None,
                        depends_on=[str(d) for d in deps] if isinstance(deps, list) else None,
                    )
                )
            if not plan_steps:
                plan_steps = [_make_step(user_query or "完成任务")]

        return {
            "plan": plan_steps,
            "pending_tasks": list(plan_steps),
            "completed_tasks": list(state.get("completed_tasks", []) or []),
            "current_step": 0,
            "needs_replan": False,
            "pending_hints": None,
            "execution_summary": None,
            "current_result": None,
            "reflection_result": None,
            "intermediate_steps": _append_step(
                history,
                "plan",
                f"规划生成 {len(plan_steps)} 个步骤",
                {"step_count": len(plan_steps), "replan": replan_count},
            ),
        }

    return planner_node


def create_executor_node(
    tools: Optional[dict[str, Callable[..., Any] | BaseTool]] = None,
) -> Callable[[PlanExecuteState], dict]:
    """
    创建 executor 节点

    取出 `pending_tasks[0]`，尝试使用 LLM 与已注册工具完成任务，将结果写入
    `current_result` 与 `pending_tasks[0].result`，并把该步骤移入 `completed_tasks`。
    """
    registry: dict[str, Any] = dict(tools) if tools else {}

    def executor_node(state: PlanExecuteState) -> dict:
        iteration = state.get("iteration", 0)
        history = state.get("intermediate_steps", []) or []
        pending = list(state.get("pending_tasks", []) or [])

        if not pending:
            logger.warning("PlanExecute: Executor 收到空 pending_tasks")
            return {
                "error": "无可执行步骤",
                "current_result": None,
                "execution_summary": "无可执行步骤",
            }

        current = dict(pending[0])
        current["status"] = "in_progress"
        step_id = current.get("step_id", "?")
        step_desc = current.get("description", "")
        logger.info(f"PlanExecute: 执行步骤 {step_id} [迭代 {iteration + 1}] - {step_desc}")

        completed = list(state.get("completed_tasks", []) or [])
        context_lines = ["已完成步骤："]
        context_lines.append(_format_steps(completed) if completed else "（无）")

        tool_lines = ["可用工具："]
        if registry:
            tool_lines.append(", ".join(sorted(registry.keys())))
        else:
            tool_lines.append("（无）")

        user_prompt = (
            f"任务：{_extract_user_query(state)}\n\n"
            f"当前步骤：[{step_id}] {step_desc}\n\n"
            + "\n".join(context_lines + tool_lines)
        )

        # 调用 LLM 产出执行结果
        try:
            provider = get_llm_provider(config.llm_provider)
            response = provider.invoke(
                [SystemMessage(content=_EXECUTOR_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
            )
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"PlanExecute: Executor LLM 调用失败 - {exc}")
            failed = dict(current)
            failed["status"] = "failed"
            failed["result"] = f"LLM 调用失败: {exc}"
            new_pending = [dict(p) for p in pending[1:]]
            new_completed = [*completed, failed]
            return {
                "error": f"Executor LLM 调用失败: {exc}",
                "current_result": failed["result"],
                "execution_summary": failed["result"],
                "pending_tasks": new_pending,
                "completed_tasks": new_completed,
                "current_step": state.get("current_step", 0) + 1,
                "intermediate_steps": _append_step(
                    history,
                    "execute",
                    f"步骤 {step_id} 执行失败: {exc}",
                    {"step_id": step_id, "error": str(exc)},
                ),
            }

        parsed = _parse_json_block(raw)
        result_text = ""
        if isinstance(parsed, dict):
            candidate = parsed.get("result")
            if isinstance(candidate, str):
                result_text = candidate.strip()
        if not result_text:
            result_text = raw.strip() or "（执行未返回结果）"

        current["status"] = "completed"
        current["result"] = result_text
        new_pending = [dict(p) for p in pending[1:]]
        new_completed = [*completed, current]

        return {
            "current_result": result_text,
            "execution_summary": f"[{step_id}] {result_text[:200]}",
            "pending_tasks": new_pending,
            "completed_tasks": new_completed,
            "current_step": state.get("current_step", 0) + 1,
            "intermediate_steps": _append_step(
                history,
                "execute",
                f"[{step_id}] {step_desc}\n结果: {result_text}",
                {"step_id": step_id},
            ),
        }

    return executor_node


def create_reflector_node(config: ReasoningConfig) -> Callable[[PlanExecuteState], dict]:
    """
    创建 reflector 节点

    当 enable_reflection=True 时调用 LLM 评估任务完成度、是否需要重规划；
    否则仅依据 pending_tasks 是否为空做基础判断。
    """
    enable_reflection = config.enable_reflection
    llm_provider_name = config.llm_provider

    def reflector_node(state: PlanExecuteState) -> dict:
        iteration = state.get("iteration", 0) + 1
        history = state.get("intermediate_steps", []) or []
        pending = list(state.get("pending_tasks", []) or [])
        completed = list(state.get("completed_tasks", []) or [])
        last_result = state.get("current_result") or ""

        logger.info(f"PlanExecute: 反思节点 [迭代 {iteration}]")

        is_done = len(pending) == 0
        needs_replan = False
        reflection_text = ""

        if enable_reflection and last_result:
            prompt_lines = [
                f"原始任务：{_extract_user_query(state)}",
                f"已完成步骤：\n{_format_steps(completed) if completed else '（无）'}",
                f"当前步骤执行结果：\n{last_result}",
            ]
            pending_hints: Optional[str] = None
            try:
                provider = get_llm_provider(llm_provider_name)
                response = provider.invoke(
                    [
                        SystemMessage(content=_REFLECTOR_SYSTEM_PROMPT),
                        HumanMessage(content="\n\n".join(prompt_lines)),
                    ]
                )
                parsed = _parse_json_block(_extract_message_content(response))
                if isinstance(parsed, dict):
                    is_done = bool(parsed.get("is_done", is_done))
                    needs_replan = bool(parsed.get("needs_replan", False)) and not is_done
                    reflection_text = str(parsed.get("summary", "")).strip()
                    if needs_replan:
                        # 将 next_hints 暂存到 pending_hints，供下一轮 planner/replan 使用
                        hints = str(parsed.get("next_hints", "")).strip()
                        if hints:
                            pending_hints = hints
                else:
                    reflection_text = "（反思结果无法解析）"
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"PlanExecute: 反思失败 - {exc}")
                reflection_text = f"反思失败: {exc}"

        if not is_done and not needs_replan and len(pending) == 0:
            # 若 LLM 没显式判断但 pending 已空，按完成处理
            is_done = True

        return {
            "iteration": iteration,
            "needs_replan": needs_replan,
            "pending_hints": pending_hints,
            "reflection_result": reflection_text or ("全部步骤已完成" if is_done else "继续执行"),
            "intermediate_steps": _append_step(
                history,
                "reflection",
                reflection_text or ("任务完成" if is_done else "继续执行"),
                {
                    "iteration": iteration,
                    "is_done": is_done,
                    "needs_replan": needs_replan,
                },
            ),
        }

    return reflector_node


def create_replan_node(config: ReasoningConfig) -> Callable[[PlanExecuteState], dict]:
    """
    创建 replan 节点

    在 reflector 判定 needs_replan=True 时调用 LLM 重新规划剩余步骤，
    替换 `pending_tasks` 并递增 `replan_count`。
    """
    llm_provider_name = config.llm_provider

    def replan_node(state: PlanExecuteState) -> dict:
        iteration = state.get("iteration", 0)
        history = state.get("intermediate_steps", []) or []
        completed = list(state.get("completed_tasks", []) or [])
        replan_count = state.get("replan_count", 0) + 1
        hints = state.get("pending_hints") or state.get("reflection_result") or ""

        logger.info(f"PlanExecute: 重规划节点 [第 {replan_count} 次]")

        prompt_lines = [
            f"原始任务：{_extract_user_query(state)}",
            f"已完成步骤：\n{_format_steps(completed) if completed else '（无）'}",
        ]
        if hints:
            prompt_lines.append(f"重规划提示：\n{hints}")

        try:
            provider = get_llm_provider(llm_provider_name)
            response = provider.invoke(
                [
                    SystemMessage(content=_REPLAN_SYSTEM_PROMPT),
                    HumanMessage(content="\n\n".join(prompt_lines)),
                ]
            )
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"PlanExecute: Replan LLM 调用失败 - {exc}")
            return {
                "error": f"Replan LLM 调用失败: {exc}",
                "replan_count": replan_count,
                "needs_replan": False,
                "intermediate_steps": _append_step(
                    history,
                    "plan",
                    f"重规划失败: {exc}",
                    {"replan": replan_count, "error": str(exc)},
                ),
            }

        parsed = _parse_json_block(raw)
        steps_data = parsed.get("steps") if isinstance(parsed, dict) else None
        new_steps: list[TaskStep] = []
        if isinstance(steps_data, list) and steps_data:
            for item in steps_data:
                if not isinstance(item, dict):
                    continue
                desc = str(item.get("description", "")).strip()
                if not desc:
                    continue
                sid = item.get("step_id")
                deps = item.get("depends_on")
                new_steps.append(
                    _make_step(
                        desc,
                        step_id=str(sid).strip() if sid else None,
                        depends_on=[str(d) for d in deps] if isinstance(deps, list) else None,
                    )
                )

        if not new_steps:
            logger.warning("PlanExecute: Replan 未返回新步骤，保持原 pending_tasks")
            return {
                "replan_count": replan_count,
                "needs_replan": False,
                "intermediate_steps": _append_step(
                    history,
                    "plan",
                    "重规划未产生新步骤",
                    {"replan": replan_count},
                ),
            }

        return {
            "replan_count": replan_count,
            "pending_tasks": new_steps,
            "needs_replan": False,
            "pending_hints": None,
            "current_step": 0,
            "intermediate_steps": _append_step(
                history,
                "plan",
                f"重规划生成 {len(new_steps)} 个新步骤",
                {"replan": replan_count, "step_count": len(new_steps)},
            ),
        }

    return replan_node


def create_finish_node() -> Callable[[PlanExecuteState], dict]:
    """
    创建 finish 节点

    汇总已完成步骤产出最终答案，并写入 `messages`。
    """

    def finish_node(state: PlanExecuteState) -> dict:
        completed = list(state.get("completed_tasks", []) or [])
        history = state.get("intermediate_steps", []) or []

        if completed:
            lines = ["最终答案："]
            for step in completed:
                sid = step.get("step_id", "?")
                desc = step.get("description", "")
                result = step.get("result") or "（无结果）"
                lines.append(f"- [{sid}] {desc}\n  {result}")
            final_answer = "\n".join(lines)
        else:
            final_answer = state.get("final_answer") or "（无可用结果）"

        logger.info("PlanExecute: 输出最终答案")
        return {
            "final_answer": final_answer,
            "needs_replan": False,
            "messages": [AIMessage(content=final_answer)] if final_answer else [],
            "intermediate_steps": _append_step(
                history,
                "reflection",
                "输出最终答案",
                {"completed_steps": len(completed)},
            ),
        }

    return finish_node


# ===== 路由函数 =====


def plan_execute_router(state: PlanExecuteState) -> str:
    """
    Plan-and-Execute 路由函数

    - needs_replan=True → "replan"
    - 已无 pending_tasks 或 iteration >= max_iterations 或有 error → "finish"
    - 否则 → "executor"
    """
    if state.get("error"):
        return "finish"
    if state.get("needs_replan"):
        return "replan"
    if not (state.get("pending_tasks") or []):
        return "finish"
    if state.get("iteration", 0) >= state.get("max_iterations", 10):
        return "finish"
    return "executor"


# ===== 工作流工厂 =====


def create_plan_execute_workflow(
    config: Optional[ReasoningConfig] = None,
    tools: Optional[dict[str, Callable[..., Any] | BaseTool]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> BaseWorkflow:
    """
    创建 Plan-and-Execute 工作流实例

    Args:
        config: 推理配置
        tools: 工具注册表（可选，供 executor 节点使用）
        checkpointer: 状态检查点器

    Returns:
        BaseWorkflow 子类实例
    """

    class _PlanExecuteWorkflow(BaseWorkflow):
        name = "plan_execute"
        description = "Plan-and-Execute 推理工作流"

        def __init__(self) -> None:
            super().__init__(checkpointer=checkpointer)
            self.config = config or ReasoningConfig()
            self.tools = tools or {}

        def build(self) -> Any:
            logger.info(f"构建工作流: {self.name}")

            workflow: StateGraph = StateGraph(PlanExecuteState)

            workflow.add_node("planner", create_planner_node(self.config))
            workflow.add_node("executor", create_executor_node(self.tools))
            workflow.add_node("reflector", create_reflector_node(self.config))
            workflow.add_node("replan", create_replan_node(self.config))
            workflow.add_node("finish", create_finish_node())

            workflow.set_entry_point("planner")

            # planner → executor
            workflow.add_edge("planner", "executor")
            # executor → reflector
            workflow.add_edge("executor", "reflector")

            # reflector → {executor | replan | finish}
            workflow.add_conditional_edges(
                "reflector",
                plan_execute_router,
                {
                    "executor": "executor",
                    "replan": "replan",
                    "finish": "finish",
                },
            )

            # replan → planner
            workflow.add_edge("replan", "planner")
            workflow.add_edge("finish", END)

            cp = self.checkpointer or MemorySaver()
            return workflow.compile(checkpointer=cp)

    return _PlanExecuteWorkflow()


__all__ = [
    "TaskStep",
    "PlanExecuteState",
    "create_planner_node",
    "create_executor_node",
    "create_reflector_node",
    "create_replan_node",
    "create_finish_node",
    "plan_execute_router",
    "create_plan_execute_workflow",
]
