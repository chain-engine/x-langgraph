# -*- coding: utf-8 -*-
"""
审批接口数据模型
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """审批请求"""

    session_id: str = Field(description="会话 ID")
    approved: bool = Field(description="是否批准")
    comments: Optional[str] = Field(default="", description="审批意见")


class ApprovalResponse(BaseModel):
    """审批响应"""

    status: str = Field(description="处理状态")
    message: str = Field(description="处理消息")


class ApprovalStatusResponse(BaseModel):
    """审批状态响应"""

    session_id: str = Field(description="会话 ID")
    status: str = Field(description="审批状态")
    next_nodes: Optional[List[str]] = Field(default=None, description="下一步节点")
    values: Optional[dict[str, Any]] = Field(default=None, description="状态值")
    message: Optional[str] = Field(default=None, description="错误消息")
