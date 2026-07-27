# Task 4: Task 4: tree_of_thought.py — ToT 模式（简化版）

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

## Global Constraints
- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`
