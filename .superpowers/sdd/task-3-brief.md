# Task 3: Task 3: plan_execute.py — Plan-and-Execute 模式

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

## Global Constraints
- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`
