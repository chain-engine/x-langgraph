# -*- coding: utf-8 -*-
"""
智能客服工作流节点定义
"""

import time
import uuid

from langgraph.types import interrupt

from workflows.customer_service.state import CustomerServiceState
from workflows.customer_service.tools import faq_search_tool, create_ticket_tool

from core.logger import logger


def intake_node(state: CustomerServiceState) -> dict:
    """
    工单接收节点：提取客户信息，生成工单 ID

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("执行工单接收")

    messages = state.get("messages", [])
    last_message = messages[-1] if messages else {}

    # 生成工单 ID
    ticket_id = f"TK{int(time.time())}_{uuid.uuid4().hex[:6]}"

    # 提取客户信息（简单模拟）
    content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
    customer_name = _extract_name(content)

    return {
        "stage": "intake",
        "ticket_id": ticket_id,
        "customer_name": customer_name,
    }


def classify_node(state: CustomerServiceState) -> dict:
    """
    工单分类节点：根据内容分类工单类型和优先级

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("执行工单分类")

    messages = state.get("messages", [])
    last_message = messages[-1] if messages else {}
    content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)

    # 分类逻辑（简单规则匹配）
    ticket_type = _classify_ticket(content)
    priority = _determine_priority(content)

    # 技术问题需要人工审批
    requires_approval = ticket_type == "technical"

    return {
        "stage": "classify",
        "ticket_type": ticket_type,
        "priority": priority,
        "requires_approval": requires_approval,
    }


def handle_inquiry_node(state: CustomerServiceState) -> dict:
    """处理咨询类工单"""
    logger.info(f"处理咨询工单: {state.get('ticket_id')}")

    messages = state.get("messages", [])
    last_message = messages[-1] if messages else {}
    content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)

    # 查询 FAQ
    faq_result = faq_search_tool.invoke(content)

    return {
        "stage": "handle",
        "output": faq_result,
    }


def handle_complaint_node(state: CustomerServiceState) -> dict:
    """处理投诉类工单"""
    logger.info(f"处理投诉工单: {state.get('ticket_id')}")

    ticket_id = state.get("ticket_id", "")
    customer_name = state.get("customer_name", "客户")

    resolution = (
        f"尊敬的 {customer_name}，非常抱歉给您带来不好的体验。\n"
        f"您的投诉已记录（工单号：{ticket_id}），我们将在 24 小时内给您答复。\n"
        f"如有紧急问题，请拨打客服热线：400-xxx-xxxx"
    )

    return {
        "stage": "handle",
        "output": resolution,
    }


def handle_technical_node(state: CustomerServiceState) -> dict:
    """
    处理技术问题工单（需要人工审批）

    展示 LangGraph 的 Human-in-the-loop 功能
    """
    logger.info(f"处理技术工单: {state.get('ticket_id')}")

    # 检查是否需要人工审批且尚未批准
    if state.get("requires_approval", False) and state.get("approved") is None:
        # 使用 interrupt 暂停执行，等待人工审批
        response = interrupt(
            {
                "type": "approval_required",
                "message": f"技术工单 {state.get('ticket_id')} 需要人工审批",
                "ticket_info": {
                    "ticket_id": state.get("ticket_id"),
                    "ticket_type": state.get("ticket_type"),
                    "priority": state.get("priority"),
                    "customer": state.get("customer_name"),
                },
            }
        )

        # 处理审批结果
        if response.get("approved"):
            return {
                "stage": "handle",
                "approved": True,
                "approval_comments": response.get("comments", ""),
                "output": "技术问题已审批通过，已分配给技术支持团队处理。",
            }
        else:
            return {
                "stage": "handle",
                "approved": False,
                "approval_comments": response.get("comments", ""),
                "output": "技术问题审批未通过，建议用户参考文档或等待后续处理。",
            }

    # 已审批或不需要审批
    return {
        "stage": "handle",
        "output": "技术问题已转交给技术支持团队，预计 4 小时内响应。",
    }


def handle_billing_node(state: CustomerServiceState) -> dict:
    """处理账单类工单"""
    logger.info(f"处理账单工单: {state.get('ticket_id')}")

    resolution = (
        "您的账单问题已受理。\n"
        "常见账单问题处理时间：\n"
        "- 费用争议：3-5 个工作日\n"
        "- 发票问题：1-2 个工作日\n"
        "- 退款处理：5-7 个工作日\n"
        "如有疑问，请回复此消息。"
    )

    return {
        "stage": "handle",
        "output": resolution,
    }


def review_node(state: CustomerServiceState) -> dict:
    """
    质量审核节点：检查处理结果是否完整

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info(f"执行质量审核: {state.get('ticket_id')}")

    output = state.get("output", "")
    error = None

    # 简单的质量检查
    if not output or len(output) < 10:
        error = "处理结果不完整，需要补充"

    return {
        "stage": "complete",
        "error": error,
    }


# 辅助函数
def _extract_name(content: str) -> str:
    """从内容中提取客户姓名（简单模拟）"""
    import re

    # 尝试匹配 "我是xxx" 或 "我叫xxx"
    match = re.search(r"(?:我是|我叫)\s*(\S+)", content)
    if match:
        return match.group(1)

    return "尊敬的客户"


def _classify_ticket(content: str) -> str:
    """分类工单类型"""
    content_lower = content.lower()

    # 优先匹配技术问题
    if any(kw in content_lower for kw in ["技术", "bug", "错误", "故障", "无法", "登录", "crash", "崩溃"]):
        return "technical"
    # 其次匹配投诉
    elif any(kw in content_lower for kw in ["投诉", "不满", "差评", "太差"]):
        return "complaint"
    # 匹配账单问题
    elif any(kw in content_lower for kw in ["账单", "支付", "退款", "发票", "费用"]):
        return "billing"
    else:
        return "inquiry"


def _determine_priority(content: str) -> str:
    """确定优先级"""
    content_lower = content.lower()

    if any(kw in content_lower for kw in ["紧急", "立即", "马上", "严重"]):
        return "urgent"
    elif any(kw in content_lower for kw in ["重要", "尽快", "急"]):
        return "high"
    elif any(kw in content_lower for kw in ["一般", "普通"]):
        return "low"
    else:
        return "medium"
