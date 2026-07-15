# -*- coding: utf-8 -*-
"""
审批接口数据模型
"""

from typing import Optional

from pydantic import BaseModel, Field


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
