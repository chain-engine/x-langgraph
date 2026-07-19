# -*- coding: utf-8 -*-
"""
智能客服工作流状态定义
"""

from typing import TypedDict, Optional, Annotated
from langgraph.graph import add_messages


class CustomerServiceState(TypedDict):
    """智能客服工作流状态"""

    # 消息历史（使用 add_messages reducer 自动合并）
    messages: Annotated[list, add_messages]

    # 处理阶段
    stage: str  # 'intake', 'classify', 'handle', 'review', 'complete'

    # 工单信息
    ticket_id: Optional[str]
    ticket_type: Optional[str]  # 'inquiry', 'complaint', 'technical', 'billing'
    priority: Optional[str]  # 'low', 'medium', 'high', 'urgent'

    # 客户信息
    customer_name: Optional[str]

    # 处理结果
    output: Optional[str]

    # 人机交互
    requires_approval: bool
    approved: Optional[bool]
    approval_comments: Optional[str]

    # 错误处理
    error: Optional[str]
