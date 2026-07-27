# Task 2: Task 2: react.py — ReAct 模式

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

## Global Constraints
- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`
