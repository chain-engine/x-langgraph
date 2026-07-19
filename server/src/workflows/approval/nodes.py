# -*- coding: utf-8 -*-
"""
自动化审批工作流节点定义

展示 LangGraph 的人机交互（Human-in-the-Loop）能力：
- 自动评估
- 条件路由
- 人工干预点
"""

import time
import uuid
from datetime import datetime

from langgraph.types import interrupt

from workflows.approval.state import (
    ApprovalState,
    ApprovalType,
    ApprovalLevel,
    ApprovalStatus,
)
from llms.providers import get_llm_provider
from llms.prompts import prompt_manager
from core.logger import logger


# ===== 提交节点 =====


def submit_node(state: ApprovalState) -> dict:
    """
    提交节点

    职责：
    1. 验证请求完整性
    2. 生成请求 ID
    3. 初始化审批流程

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Approval: 提交审批请求")

    request = state.get("request", {})

    # 生成请求 ID
    if not request.get("request_id"):
        request["request_id"] = f"REQ-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"

    # 设置初始状态
    request["submitted_at"] = datetime.now().isoformat()

    logger.info(f"Approval: 请求已提交 - {request.get('request_id')}")

    return {
        "request": request,
        "approval_status": ApprovalStatus.SUBMITTED.value,
        "approval_history": [
            {
                "action": "submit",
                "timestamp": datetime.now().isoformat(),
                "details": f"提交{request.get('request_type', '')}申请",
            }
        ],
    }


# ===== 自动评估节点 =====


def evaluate_node(state: ApprovalState) -> dict:
    """
    自动评估节点

    职责：
    1. 基于规则自动评估
    2. 确定风险等级
    3. 推荐审批动作

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Approval: 自动评估")

    request = state.get("request", {})

    try:
        # 执行自动评估
        evaluation = _auto_evaluate(request)

        logger.info(
            f"Approval: 评估完成 - 风险等级: {evaluation['risk_level']}, "
            f"推荐: {evaluation['recommended_action']}"
        )

        # 更新审批历史
        history = state.get("approval_history", [])
        history.append(
            {
                "action": "evaluate",
                "timestamp": datetime.now().isoformat(),
                "details": f"自动评估完成，风险等级: {evaluation['risk_level']}",
                "result": evaluation,
            }
        )

        return {
            "auto_evaluation": evaluation,
            "risk_level": evaluation["risk_level"],
            "recommended_action": evaluation["recommended_action"],
            "approval_status": ApprovalStatus.PENDING.value,
            "approval_history": history,
        }

    except Exception as e:
        logger.error(f"Approval: 评估失败 - {e}")
        return {
            "auto_evaluation": {"error": str(e)},
            "risk_level": "high",
            "recommended_action": "manual_review",
            "error": f"自动评估失败: {str(e)}",
        }


def _auto_evaluate(request: dict) -> dict:
    """
    自动评估函数

    基于规则和策略评估请求

    Args:
        request: 审批请求

    Returns:
        评估结果
    """
    request_type = request.get("request_type", "")
    amount = request.get("amount", 0)

    # 评估规则
    evaluation = {
        "risk_level": "low",
        "recommended_action": "auto_approve",
        "factors": [],
        "policy_check": {},
        "recommendations": [],
    }

    # 根据类型评估
    if request_type == ApprovalType.LEAVE.value:
        # 请假评估
        evaluation["factors"].append("请假申请")
        evaluation["risk_level"] = "low"
        evaluation["recommended_action"] = "auto_approve"

    elif request_type == ApprovalType.EXPENSE.value:
        # 报销评估
        if amount <= 1000:
            evaluation["risk_level"] = "low"
            evaluation["recommended_action"] = "auto_approve"
            evaluation["factors"].append("金额较小，可自动审批")
        elif amount <= 10000:
            evaluation["risk_level"] = "medium"
            evaluation["recommended_action"] = "manager_approval"
            evaluation["factors"].append("金额适中，需要经理审批")
        else:
            evaluation["risk_level"] = "high"
            evaluation["recommended_action"] = "director_approval"
            evaluation["factors"].append("金额较大，需要总监审批")

    elif request_type == ApprovalType.PROCUREMENT.value:
        # 采购评估
        if amount <= 5000:
            evaluation["risk_level"] = "low"
            evaluation["recommended_action"] = "auto_approve"
        elif amount <= 50000:
            evaluation["risk_level"] = "medium"
            evaluation["recommended_action"] = "manager_approval"
        else:
            evaluation["risk_level"] = "high"
            evaluation["recommended_action"] = "director_approval"

    elif request_type == ApprovalType.CONTRACT.value:
        # 合同评估
        evaluation["risk_level"] = "high"
        evaluation["recommended_action"] = "legal_review"
        evaluation["factors"].append("合同需要法务审核")

    else:
        # 默认需要人工审批
        evaluation["risk_level"] = "medium"
        evaluation["recommended_action"] = "manager_approval"

    # 添加策略检查
    evaluation["policy_check"] = {
        "budget_available": True,
        "compliant": True,
        "duplicate_check": "passed",
    }

    return evaluation


# ===== 人工审批节点 =====


def human_approval_node(state: ApprovalState) -> dict:
    """
    人工审批节点

    职责：
    1. 等待人工审批
    2. 使用 interrupt 暂停执行
    3. 处理审批结果

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Approval: 等待人工审批")

    request = state.get("request", {})
    evaluation = state.get("auto_evaluation", {})

    # 检查是否已有审批结果
    if state.get("human_approved") is not None:
        logger.info("Approval: 已有人工审批结果")
        return _process_human_decision(state)

    # 使用 interrupt 暂停，等待人工审批
    approval_response = interrupt(
        {
            "type": "approval_required",
            "request_id": request.get("request_id"),
            "request_type": request.get("request_type"),
            "requester": request.get("requester_name"),
            "department": request.get("department"),
            "amount": request.get("amount"),
            "description": request.get("description"),
            "risk_level": state.get("risk_level"),
            "recommendation": state.get("recommended_action"),
            "evaluation_summary": evaluation.get("factors", []),
        }
    )

    # 处理审批响应
    if approval_response:
        approved = approval_response.get("approved", False)
        comments = approval_response.get("comments", "")
        approver_id = approval_response.get("approver_id", "unknown")

        logger.info(f"Approval: 人工审批结果 - {'通过' if approved else '拒绝'}")

        # 更新审批历史
        history = state.get("approval_history", [])
        history.append(
            {
                "action": "human_approval",
                "timestamp": datetime.now().isoformat(),
                "approver_id": approver_id,
                "approved": approved,
                "comments": comments,
            }
        )

        return {
            "human_approved": approved,
            "human_comments": comments,
            "approver_id": approver_id,
            "approval_history": history,
            **_process_human_decision(
                {
                    **state,
                    "human_approved": approved,
                    "human_comments": comments,
                }
            ),
        }

    return {"error": "未收到审批响应"}


def _process_human_decision(state: ApprovalState) -> dict:
    """处理人工决定"""
    approved = state.get("human_approved", False)
    comments = state.get("human_comments", "")

    if approved:
        return {
            "final_status": ApprovalStatus.APPROVED.value,
            "output": f"审批通过: {comments}",
            "approval_status": ApprovalStatus.APPROVED.value,
        }
    else:
        return {
            "final_status": ApprovalStatus.REJECTED.value,
            "output": f"审批拒绝: {comments}",
            "approval_status": ApprovalStatus.REJECTED.value,
        }


# ===== 自动审批节点 =====


def auto_approve_node(state: ApprovalState) -> dict:
    """
    自动审批节点

    职责：
    1. 执行自动审批
    2. 记录审批结果

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Approval: 执行自动审批")

    request = state.get("request", {})

    # 更新审批历史
    history = state.get("approval_history", [])
    history.append(
        {
            "action": "auto_approve",
            "timestamp": datetime.now().isoformat(),
            "details": "系统自动审批通过",
        }
    )

    logger.info(f"Approval: 自动审批通过 - {request.get('request_id')}")

    return {
        "final_status": ApprovalStatus.APPROVED.value,
        "output": "系统自动审批通过",
        "approval_status": ApprovalStatus.APPROVED.value,
        "requires_human": False,
        "approval_history": history,
    }


# ===== 通知节点 =====


def notify_node(state: ApprovalState) -> dict:
    """
    通知节点

    职责：
    1. 发送审批结果通知
    2. 记录通知状态

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Approval: 发送通知")

    request = state.get("request", {})
    final_status = state.get("final_status", "")

    # 模拟发送通知
    notification_result = _send_notification(
        request.get("requester_id"),
        f"您的申请 {request.get('request_id')} 已{final_status}",
    )

    # 更新审批历史
    history = state.get("approval_history", [])
    history.append(
        {
            "action": "notify",
            "timestamp": datetime.now().isoformat(),
            "details": f"通知已发送 - {notification_result}",
        }
    )

    logger.info(f"Approval: 通知已发送 - {request.get('request_id')}")

    return {
        "notification_sent": True,
        "approval_history": history,
    }


def _send_notification(user_id: str, message: str) -> str:
    """
    发送通知（模拟）

    Args:
        user_id: 用户 ID
        message: 通知内容

    Returns:
        发送结果
    """
    # 模拟通知发送
    return f"已发送通知给用户 {user_id}: {message[:50]}..."


# ===== 条件路由函数 =====


def route_by_evaluation(state: ApprovalState) -> str:
    """
    条件路由：根据评估结果决定下一步

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    recommended_action = state.get("recommended_action", "")

    # 根据推荐动作路由
    if recommended_action == "auto_approve":
        return "auto_approve"
    else:
        return "human_approval"


def route_by_status(state: ApprovalState) -> str:
    """
    条件路由：根据状态决定下一步

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    final_status = state.get("final_status", "")

    if final_status in [ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value]:
        return "notify"
    else:
        return "end"
