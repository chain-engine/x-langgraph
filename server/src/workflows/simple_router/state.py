# -*- coding: utf-8 -*-
"""
意图分类路由工作流状态定义
"""

from typing import TypedDict, Optional, Literal, Annotated
from langgraph.graph import add_messages


class IntentClassifierState(TypedDict):
    """意图分类工作流状态"""

    messages: Annotated[list, add_messages]

    # 意图分类结果
    intent: str  # 'product_inquiry', 'order_status', 'technical_support', 'complaint', 'billing', 'other'

    # 路由置信度
    confidence: float

    # 业务响应
    response: str

    # 人机交互（技术支持审批）
    approved: Optional[bool]
    approval_comments: Optional[str]

    # 错误信息
    error: Optional[str]


class IntentDecision(TypedDict):
    """LLM 意图分类结构"""

    intent: Literal[
        "product_inquiry",
        "order_status",
        "technical_support",
        "complaint",
        "billing",
        "other",
    ]
    reasoning: str
    confidence: float
