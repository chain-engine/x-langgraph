# -*- coding: utf-8 -*-
"""
自动化审批工作流状态定义

展示 LangGraph 的人机交互（Human-in-the-Loop）能力：
- 自动决策
- 人工审批
- 条件路由
"""

from enum import Enum
from typing import TypedDict, Optional, Annotated
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class ApprovalType(str, Enum):
    """审批类型"""

    LEAVE = "leave"  # 请假
    EXPENSE = "expense"  # 报销
    PROCUREMENT = "procurement"  # 采购
    CONTRACT = "contract"  # 合同
    PROJECT = "project"  # 项目


class ApprovalLevel(str, Enum):
    """审批级别"""

    AUTO_APPROVED = "auto_approved"  # 自动通过
    MANAGER = "manager"  # 部门经理
    DIRECTOR = "director"  # 总监
    VP = "vp"  # 副总裁
    CEO = "ceo"  # CEO


class ApprovalStatus(str, Enum):
    """审批状态"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    """审批请求"""

    request_id: str = Field(..., description="请求 ID")
    request_type: ApprovalType = Field(..., description="请求类型")
    requester_id: str = Field(..., description="申请人 ID")
    requester_name: str = Field(..., description="申请人姓名")
    department: str = Field(..., description="部门")
    amount: Optional[float] = Field(default=None, description="金额（报销/采购）")
    description: str = Field(..., description="申请说明")
    attachments: list[str] = Field(default_factory=list, description="附件列表")
    created_at: str = Field(..., description="创建时间")


class ApprovalState(TypedDict):
    """
    审批工作流状态

    展示 LangGraph 的状态管理：
    - 多级审批
    - 人工干预
    - 状态追踪
    """

    # 消息历史
    messages: Annotated[list, add_messages]

    # 审批请求
    request: dict  # ApprovalRequest

    # 审批流程
    approval_level: str  # 当前审批级别
    approval_status: str  # 审批状态

    # 自动评估
    auto_evaluation: dict  # 自动评估结果
    risk_level: str  # 风险等级: low, medium, high
    recommended_action: str  # 推荐动作

    # 审批历史
    approval_history: list[dict]  # 审批历史记录

    # 人工审批
    requires_human: bool  # 是否需要人工
    human_approved: Optional[bool]  # 人工审批结果
    human_comments: Optional[str]  # 审批意见
    approver_id: Optional[str]  # 审批人 ID

    # 最终结果
    final_status: str  # 最终状态
    final_decision: str  # 最终决定
    notification_sent: bool  # 是否已发送通知

    # 错误处理
    error: Optional[str]


class ApprovalResult(BaseModel):
    """审批结果"""

    request_id: str = Field(..., description="请求 ID")
    final_status: str = Field(..., description="最终状态")
    final_decision: str = Field(default="", description="最终决定")
    approval_history: list[dict] = Field(default_factory=list, description="审批历史")
    auto_evaluation: dict = Field(default_factory=dict, description="自动评估")
    risk_level: str = Field(default="unknown", description="风险等级")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
