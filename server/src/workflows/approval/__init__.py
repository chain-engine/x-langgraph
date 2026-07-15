# -*- coding: utf-8 -*-
"""
自动化审批工作流

展示 LangGraph 的人机交互（Human-in-the-Loop）能力：
- 自动决策
- 人工审批
- 条件路由
"""

from workflows.approval.workflow import (
    create_approval_workflow,
    run_approval,
    run_approval_with_human,
    stream_approval,
)
from workflows.approval.state import (
    ApprovalType,
    ApprovalLevel,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalResult,
)

__all__ = [
    "create_approval_workflow",
    "run_approval",
    "run_approval_with_human",
    "stream_approval",
    "ApprovalType",
    "ApprovalLevel",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalResult",
]
