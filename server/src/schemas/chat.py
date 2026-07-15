# -*- coding: utf-8 -*-
"""
聊天接口数据模型
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(..., description="用户消息", min_length=1)
    session_id: str = Field(default="default", description="会话 ID")
    workflow: str = Field(default="simple_router", description="工作流类型")


class ChatResponse(BaseModel):
    """聊天响应"""

    response: str = Field(..., description="AI 响应内容")
    session_id: str = Field(..., description="会话 ID")
    node: Optional[str] = Field(default=None, description="执行的节点")


class StreamEvent(BaseModel):
    """流式事件"""

    event: str = Field(..., description="事件类型")
    node: Optional[str] = Field(default=None, description="节点名称")
    data: Any = Field(default=None, description="事件数据")
