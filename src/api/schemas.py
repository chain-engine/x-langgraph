# -*- coding: utf-8 -*-
"""
API 数据模型定义
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


class ApprovalRequest(BaseModel):
    """审批请求（Human-in-the-Loop）"""

    session_id: str = Field(..., description="会话 ID")
    approved: bool = Field(..., description="是否批准")
    comments: Optional[str] = Field(default="", description="审批意见")


class ApprovalResponse(BaseModel):
    """审批响应"""

    status: str = Field(..., description="状态")
    message: str = Field(..., description="消息")


class ThreadInfo(BaseModel):
    """会话信息"""

    thread_id: str = Field(..., description="会话 ID")
    status: str = Field(..., description="状态")
    checkpoint: Optional[dict] = Field(default=None, description="检查点数据")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
