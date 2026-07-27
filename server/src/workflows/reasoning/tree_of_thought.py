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
from typing import Any, Callable, NotRequired, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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


class Branch(TypedDict):
    """推理分支"""

    branch_id: str
    content: str               # 分支推理内容
    score: NotRequired[Optional[float]]   # 评估得分
    parent_id: NotRequired[Optional[str]]  # 父分支 ID
    children_ids: NotRequired[list[str]]   # 子分支 ID
    status: str               # "active" | "evaluated" | "pruned" | "selected"
    metadata: NotRequired[Optional[dict[str, Any]]]


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

_GENERATOR_SYSTEM_PROMPT = """你是一个 Tree-of-Thought 思维探索专家。

你将收到：
- 用户的原始任务
- 当前最佳分支的推理内容（若是首次生成则为占位信息）

请基于当前最佳思考，生成多个不同的思考方向/分支，以扩展推理树。

输出要求（严格遵守）：

```json
{
  "thought": "你对于为何扩展新分支的简要说明",
  "branches": [
    {
      "content": "该分支的独立推理内容（包含新视角或新方法）",
      "rationale": "为什么这条分支有价值（一句话）"
    }
  ]
}
```

规则：
1. 每个分支必须从不同角度思考问题，并保持逻辑连贯
2. 分支数量应等于 {max_branches}；不同分支应互不重叠
3. 若上轮 best_branch 提供思路，应在其基础上进行有意义的扩展
4. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""

_EVALUATOR_SYSTEM_PROMPT = """你是一个推理分支评估专家。

你将看到：
- 原始任务
- 多个待评估的推理分支内容

请为每条分支打分（0.0 ~ 1.0，分数越高表示越可能通向最终正确答案），
并简要说出一条优点或缺陷，便于后续选择。

输出要求（严格遵守）：

```json
{
  "evaluations": [
    {
      "branch_id": "branch-<id>",
      "score": 0.0,
      "comment": "一句话评价"
    }
  ]
}
```

规则：
1. 基于与原任务的相关性、逻辑性、可推进性进行评分
2. 若分支内容为空或完全离题，给 0 分
3. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""

_SELECTOR_SYSTEM_PROMPT = """你是一个分支选择专家。

你将看到：
- 原始任务
- 多个已被打分的分支

请基于分数及内容选出当前最优的分支（best_branch_id），并简要说明选择理由。

输出要求（严格遵守）：

```json
{
  "best_branch_id": "branch-<id>",
  "reason": "为什么选择这条分支（一句话）"
}
```

规则：
1. 若所有分支都不理想，可选择分数最高的那条
2. best_branch_id 必须出现在输入分支列表中
3. 严格输出 JSON，不要包含 JSON 之外的解释文字
"""

_JSON_BLOCK = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


# ===== 辅助函数 =====


def _now_iso() -> str:
    """获取当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def _extract_user_query(state: ToTState) -> str:
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


def _make_branch(
    content: str,
    branch_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    status: str = "active",
) -> Branch:
    """构造一个 Branch"""
    bid = branch_id or f"branch-{uuid.uuid4().hex[:8]}"
    branch: Branch = {
        "branch_id": bid,
        "content": content,
        "status": status,
    }
    if parent_id:
        branch["parent_id"] = parent_id
    return branch


def _format_branches(branches: list[Branch]) -> str:
    """格式化分支列表为可读字符串"""
    if not branches:
        return "（无）"
    lines: list[str] = []
    for b in branches:
        bid = b.get("branch_id", "?")
        content = b.get("content", "")
        score = b.get("score")
        parent = b.get("parent_id")
        score_text = f", score={score:.2f}" if isinstance(score, (int, float)) else ""
        parent_text = f", parent={parent}" if parent else ""
        lines.append(f"- [{bid}]{parent_text}{score_text}: {content}")
    return "\n".join(lines)


def _find_branch(branches: list[Branch], branch_id: Optional[str]) -> Optional[Branch]:
    """按 ID 查找分支（返回拷贝或 None）"""
    if not branch_id:
        return None
    for b in branches:
        if b.get("branch_id") == branch_id:
            return b
    return None


# ===== 节点工厂 =====


def create_generator_node(config: ReasoningConfig) -> Callable[[ToTState], dict]:
    """
    创建 generator 节点

    基于当前最佳分支（首次为占位），调用 LLM 生成 num_branches 个新分支，
    写入 `new_branches` 与 `branches`，并使 best_branch 成为新分支的父。
    """

    def generator_node(state: ToTState) -> dict:
        iteration = state.get("iteration", 0)
        depth = state.get("depth", 0)
        max_branches = state.get("max_branches", 3) or 3
        history = state.get("intermediate_steps", []) or []
        branches = list(state.get("branches", []) or [])
        best_id = state.get("best_branch_id")
        best_branch = _find_branch(branches, best_id)
        best_content = best_branch.get("content", "") if best_branch else ""

        logger.info(
            f"ToT: 生成节点 [迭代 {iteration + 1}/{state.get('max_iterations', config.max_iterations)}, "
            f"depth={depth + 1}, max_branches={max_branches}]"
        )

        user_query = _extract_user_query(state)
        prompt = (
            f"任务：{user_query or '（无）'}\n\n"
            f"当前最佳分支推理：\n{best_content or '（首次生成，无前置分支）'}\n\n"
            f"本轮请生成 {max_branches} 个不同的思考分支。"
        )

        # 调用 LLM 产出新分支
        try:
            system_prompt = (
                config.system_prompt
                if config.system_prompt
                else _GENERATOR_SYSTEM_PROMPT.format(max_branches=max_branches)
            )
            provider = get_llm_provider(config.llm_provider)
            response = provider.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt),
                ]
            )
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"ToT: Generator LLM 调用失败 - {exc}")
            return {
                "error": f"Generator LLM 调用失败: {exc}",
                "new_branches": [],
                "intermediate_steps": _append_step(
                    history,
                    "reasoning",
                    f"LLM 调用失败: {exc}",
                    {"error": str(exc)},
                ),
            }

        parsed = _parse_json_block(raw)
        new_branches: list[Branch] = []
        thought = ""
        if isinstance(parsed, dict):
            thought = str(parsed.get("thought", "")).strip()
            raw_branches = parsed.get("branches")
            if isinstance(raw_branches, list):
                for item in raw_branches:
                    if not isinstance(item, dict):
                        continue
                    content = str(item.get("content", "")).strip()
                    if not content:
                        continue
                    rationale = str(item.get("rationale", "")).strip()
                    branch = _make_branch(
                        content,
                        parent_id=best_id,
                        status="active",
                    )
                    meta: dict[str, Any] = {}
                    if rationale:
                        meta["rationale"] = rationale
                    if meta:
                        branch["metadata"] = meta
                    new_branches.append(branch)
                    if len(new_branches) >= max_branches:
                        break

        if not new_branches:
            logger.warning("ToT: Generator 未返回有效分支，回退为单分支")
            fallback_content = raw.strip() or (thought or "（生成失败）")
            new_branches = [
                _make_branch(
                    fallback_content,
                    parent_id=best_id,
                    status="active",
                )
            ]

        # 裁剪到 max_branches
        new_branches = new_branches[:max_branches]
        new_ids = [b["branch_id"] for b in new_branches]

        # 更新父分支的 children_ids
        updated_branches: list[Branch] = []
        for b in branches:
            if b.get("branch_id") == best_id:
                children = list(b.get("children_ids", []) or [])
                for bid in new_ids:
                    if bid not in children:
                        children.append(bid)
                new_b = dict(b)
                new_b["children_ids"] = children
                updated_branches.append(new_b)  # type: ignore[arg-type]
            else:
                updated_branches.append(dict(b))

        all_branches = [*updated_branches, *[dict(b) for b in new_branches]]

        return {
            "branches": all_branches,
            "new_branches": [dict(b) for b in new_branches],
            "current_branch_id": new_ids[0] if new_ids else None,
            "depth": depth + 1,
            "evaluation_results": [],
            "intermediate_steps": _append_step(
                history,
                "reasoning",
                thought or f"生成 {len(new_branches)} 个新分支",
                {
                    "iteration": iteration,
                    "depth": depth + 1,
                    "branch_count": len(new_branches),
                    "branch_ids": new_ids,
                },
            ),
        }

    return generator_node


def create_evaluator_node(config: ReasoningConfig) -> Callable[[ToTState], dict]:
    """
    创建 evaluator 节点

    对 `new_branches` 中的每条分支调用 LLM 打分，写入 `evaluation_results` 与
    `evaluated_branches`，并把各分支状态标记为 evaluated。
    """
    llm_provider_name = config.llm_provider

    def evaluator_node(state: ToTState) -> dict:
        iteration = state.get("iteration", 0)
        history = state.get("intermediate_steps", []) or []
        new_branches = list(state.get("new_branches", []) or [])
        branches = list(state.get("branches", []) or [])

        logger.info(f"ToT: 评估节点 [迭代 {iteration + 1}] - {len(new_branches)} 条分支")

        evaluation_results: list[dict[str, Any]] = []
        evaluated_ids: list[str] = [str(i) for i in (state.get("evaluated_branches", []) or [])]

        if not new_branches:
            logger.warning("ToT: Evaluator 收到空 new_branches")
            return {
                "evaluation_results": evaluation_results,
                "evaluated_branches": evaluated_ids,
                "intermediate_steps": _append_step(
                    history,
                    "reflection",
                    "（无可评估分支）",
                    {"iteration": iteration, "count": 0},
                ),
            }

        # 调用 LLM 一次性评估全部新分支
        branch_lines = "\n".join(
            f"- [{b['branch_id']}] {b.get('content', '')}" for b in new_branches
        )
        prompt = (
            f"任务：{_extract_user_query(state) or '（无）'}\n\n"
            f"待评估分支：\n{branch_lines}"
        )

        score_by_id: dict[str, float] = {}
        comment_by_id: dict[str, str] = {}

        try:
            provider = get_llm_provider(llm_provider_name)
            response = provider.invoke(
                [
                    SystemMessage(content=_EVALUATOR_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"ToT: Evaluator LLM 调用失败，使用本地启发式打分 - {exc}")
            raw = ""

        parsed = _parse_json_block(raw)
        raw_evals: list[dict[str, Any]] = []
        if isinstance(parsed, dict):
            candidate = parsed.get("evaluations")
            if isinstance(candidate, list):
                raw_evals = [e for e in candidate if isinstance(e, dict)]

        if raw_evals:
            for item in raw_evals:
                bid = str(item.get("branch_id", "")).strip()
                score_val = item.get("score")
                comment_val = str(item.get("comment", "")).strip()
                if not bid:
                    continue
                try:
                    score_float = float(score_val) if score_val is not None else 0.0
                except (TypeError, ValueError):
                    score_float = 0.0
                score_float = max(0.0, min(1.0, score_float))
                score_by_id[bid] = score_float
                if comment_val:
                    comment_by_id[bid] = comment_val

        # 为未被 LLM 打分的分支写入回退值（避免 review 时空缺）
        for branch in new_branches:
            bid = branch["branch_id"]
            content = branch.get("content", "")
            if bid not in score_by_id:
                # 启发式：以内容长度归一化作为分（避免极端情况）
                fallback = min(1.0, max(0.0, len(content) / 400.0))
                score_by_id[bid] = fallback
                comment_by_id.setdefault(bid, "（LLM 未打分，使用启发式分数）")

        # 把分数写回 branch，更新 status
        updated_branches: list[Branch] = []
        evaluated_set = set(evaluated_ids)
        for branch in branches:
            new_branch = dict(branch)
            if branch.get("branch_id") in {b["branch_id"] for b in new_branches}:
                bid = branch["branch_id"]
                new_branch["score"] = score_by_id.get(bid, 0.0)
                new_branch["status"] = "evaluated"
                metadata = dict(branch.get("metadata") or {})
                if bid in comment_by_id:
                    metadata["eval_comment"] = comment_by_id[bid]
                if metadata:
                    new_branch["metadata"] = metadata
            updated_branches.append(new_branch)  # type: ignore[arg-type]

        # 构造 evaluation_results
        for branch in new_branches:
            bid = branch["branch_id"]
            evaluation_results.append(
                {
                    "branch_id": bid,
                    "score": score_by_id.get(bid, 0.0),
                    "comment": comment_by_id.get(bid, ""),
                }
            )
            if bid not in evaluated_set:
                evaluated_ids.append(bid)
                evaluated_set.add(bid)

        return {
            "branches": updated_branches,
            "evaluation_results": evaluation_results,
            "evaluated_branches": evaluated_ids,
            "intermediate_steps": _append_step(
                history,
                "reflection",
                f"评估 {len(new_branches)} 个分支",
                {
                    "iteration": iteration,
                    "count": len(new_branches),
                    "scores": {r["branch_id"]: r["score"] for r in evaluation_results},
                },
            ),
        }

    return evaluator_node


def create_selector_node(config: ReasoningConfig) -> Callable[[ToTState], dict]:
    """
    创建 selector 节点

    基于 evaluation_results 调用 LLM 选出当前最优分支，写入 `best_branch_id`；
    若 LLM 不可用则退化为按分数最高的本地选择。
    """
    llm_provider_name = config.llm_provider

    def selector_node(state: ToTState) -> dict:
        iteration = state.get("iteration", 0)
        history = state.get("intermediate_steps", []) or []
        evaluations = list(state.get("evaluation_results", []) or [])
        branches = list(state.get("branches", []) or [])

        logger.info(f"ToT: 选择节点 [迭代 {iteration + 1}] - {len(evaluations)} 条候选")

        if not evaluations:
            return {
                "best_branch_id": state.get("best_branch_id"),
                "current_branch_id": state.get("current_branch_id"),
                "intermediate_steps": _append_step(
                    history,
                    "reflection",
                    "（无可选分支）",
                    {"iteration": iteration},
                ),
            }

        # 准备分支描述
        eval_map: dict[str, dict[str, Any]] = {e["branch_id"]: e for e in evaluations}
        content_by_id: dict[str, str] = {}
        for b in branches:
            if b.get("branch_id") in eval_map:
                content_by_id[b["branch_id"]] = b.get("content", "")

        eval_lines = []
        for bid, info in eval_map.items():
            score = info.get("score", 0.0)
            comment = info.get("comment", "")
            content = content_by_id.get(bid, "")
            eval_lines.append(
                f"- [{bid}] score={score:.2f} | content: {content}\n  评价: {comment}"
            )

        prompt = (
            f"任务：{_extract_user_query(state) or '（无）'}\n\n"
            f"候选分支：\n" + "\n".join(eval_lines)
        )

        chosen_id: Optional[str] = None
        reason = ""

        try:
            provider = get_llm_provider(llm_provider_name)
            response = provider.invoke(
                [
                    SystemMessage(content=_SELECTOR_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            raw = _extract_message_content(response)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"ToT: Selector LLM 调用失败，使用本地打分 - {exc}")
            raw = ""

        parsed = _parse_json_block(raw)
        if isinstance(parsed, dict):
            candidate_id = str(parsed.get("best_branch_id", "")).strip()
            if candidate_id in eval_map:
                chosen_id = candidate_id
                reason = str(parsed.get("reason", "")).strip()

        if chosen_id is None:
            chosen_id = max(
                eval_map.items(),
                key=lambda kv: kv[1].get("score", 0.0),
            )[0]
            reason = reason or "本地打分：取分数最高者"

        # 标记被选分支为 selected
        updated_branches: list[Branch] = []
        for branch in branches:
            new_branch = dict(branch)
            if branch.get("branch_id") == chosen_id:
                metadata = dict(branch.get("metadata") or {})
                metadata["selected_reason"] = reason
                new_branch["metadata"] = metadata
                new_branch["status"] = "selected"
            updated_branches.append(new_branch)  # type: ignore[arg-type]

        return {
            "branches": updated_branches,
            "best_branch_id": chosen_id,
            "current_branch_id": chosen_id,
            "iteration": iteration + 1,
            "intermediate_steps": _append_step(
                history,
                "reflection",
                f"选中分支 {chosen_id}: {reason}",
                {"iteration": iteration, "best_branch_id": chosen_id},
            ),
        }

    return selector_node


def create_finish_node() -> Callable[[ToTState], dict]:
    """
    创建 finish 节点

    汇总最优分支内容为最终答案，写入 `messages` 供下游消费。
    """

    def finish_node(state: ToTState) -> dict:
        history = state.get("intermediate_steps", []) or []
        branches = list(state.get("branches", []) or [])
        best_id = state.get("best_branch_id")
        best_branch = _find_branch(branches, best_id)

        if best_branch:
            content = best_branch.get("content", "")
            metadata = best_branch.get("metadata") or {}
            score = best_branch.get("score")
            score_text = f"（score={score:.2f}）" if isinstance(score, (int, float)) else ""
            rationale = metadata.get("selected_reason") or metadata.get("rationale") or ""
            suffix = f" {score_text}".rstrip()
            if rationale:
                suffix += f"\n选择理由：{rationale}"
            final_answer = f"{content}{suffix}" if content else (state.get("final_answer") or "")
        else:
            final_answer = state.get("final_answer") or "（无可用分支）"

        logger.info("ToT: 输出最终答案")
        return {
            "final_answer": final_answer,
            "new_branches": [],
            "messages": [AIMessage(content=final_answer)] if final_answer else [],
            "intermediate_steps": _append_step(
                history,
                "reflection",
                "输出最终答案",
                {"best_branch_id": best_id},
            ),
        }

    return finish_node


# ===== 路由函数 =====


def tot_router(state: ToTState) -> str:
    """
    ToT 路由函数

    - 有 error → "finish"
    - 当前深度达到 max_depth → "finish"
    - iteration 达到 max_iterations → "finish"
    - 没有可评估的新分支 → "finish"
    - 否则 → "generator"
    """
    if state.get("error"):
        return "finish"
    if not (state.get("evaluation_results") or []):
        return "finish"
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 5) or 5
    if depth >= max_depth:
        return "finish"
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10) or 10
    if iteration >= max_iterations:
        return "finish"
    return "generator"


# ===== 工作流工厂 =====


def create_tot_workflow(
    config: Optional[ReasoningConfig] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> BaseWorkflow:
    """
    创建 Tree-of-Thought 工作流实例

    Args:
        config: 推理配置
        checkpointer: 状态检查点器

    Returns:
        BaseWorkflow 子类实例
    """

    class _ToTWorkflow(BaseWorkflow):
        name = "tree_of_thought"
        description = "Tree-of-Thought (简化版) 推理工作流"

        def __init__(self) -> None:
            super().__init__(checkpointer=checkpointer)
            self.config = config or ReasoningConfig()

        def build(self) -> Any:
            logger.info(f"构建工作流: {self.name}")

            workflow: StateGraph = StateGraph(ToTState)

            workflow.add_node("generator", create_generator_node(self.config))
            workflow.add_node("evaluator", create_evaluator_node(self.config))
            workflow.add_node("selector", create_selector_node(self.config))
            workflow.add_node("finish", create_finish_node())

            workflow.set_entry_point("generator")

            # generator → evaluator
            workflow.add_edge("generator", "evaluator")
            # evaluator → selector
            workflow.add_edge("evaluator", "selector")

            # selector → {generator | finish}
            workflow.add_conditional_edges(
                "selector",
                tot_router,
                {
                    "generator": "generator",
                    "finish": "finish",
                },
            )

            workflow.add_edge("finish", END)

            cp = self.checkpointer or MemorySaver()
            return workflow.compile(checkpointer=cp)

    return _ToTWorkflow()


__all__ = [
    "Branch",
    "ToTState",
    "create_generator_node",
    "create_evaluator_node",
    "create_selector_node",
    "create_finish_node",
    "tot_router",
    "create_tot_workflow",
]
