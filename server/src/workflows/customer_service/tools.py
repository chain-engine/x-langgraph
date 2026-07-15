# -*- coding: utf-8 -*-
"""
智能客服专用工具
"""

from langchain_core.tools import tool
from core.logger import logger


@tool
def faq_search_tool(question: str) -> str:
    """
    FAQ 搜索工具，用于查询常见问题答案。

    Args:
        question: 用户问题

    Returns:
        相关的 FAQ 答案
    """
    logger.info(f"FAQ 搜索: {question}")

    faq_database = {
        "退款": "退款政策：购买后 7 天内可申请全额退款，请联系客服处理。",
        "退货": "退货流程：请在订单页面提交退货申请，我们将在 3 个工作日内处理。",
        "发货": "发货时间：普通订单 1-2 天发货，加急订单当天发货。",
        "物流": "物流查询：可在订单详情页查看实时物流信息，或联系快递公司。",
        "账号": "账号问题：如忘记密码，请使用手机号验证重置；如账号异常，请联系客服。",
        "支付": "支付方式：支持支付宝、微信、银行卡等多种支付方式。",
        "优惠券": "优惠券使用：结算时选择使用优惠券，每位用户限用一张。",
    }

    for keyword, answer in faq_database.items():
        if keyword in question:
            return f"【FAQ 匹配】{answer}"

    return "抱歉，未找到相关 FAQ，请转人工客服处理。"


@tool
def create_ticket_tool(
    customer_name: str, ticket_type: str, priority: str, description: str
) -> str:
    """
    创建工单工具，用于记录客户问题。

    Args:
        customer_name: 客户姓名
        ticket_type: 工单类型
        priority: 优先级
        description: 问题描述

    Returns:
        工单 ID
    """
    import time

    logger.info(f"创建工单: {customer_name}, {ticket_type}, {priority}")

    # 生成工单 ID
    ticket_id = f"TK{int(time.time())}"

    return f"工单已创建\n- 工单ID: {ticket_id}\n- 客户: {customer_name}\n- 类型: {ticket_type}\n- 优先级: {priority}"


@tool
def escalate_tool(ticket_id: str, reason: str) -> str:
    """
    工单升级工具，用于将工单转交给高级客服处理。

    Args:
        ticket_id: 工单 ID
        reason: 升级原因

    Returns:
        升级结果
    """
    logger.info(f"工单升级: {ticket_id}, 原因: {reason}")

    return f"工单 {ticket_id} 已升级至高级客服，预计 2 小时内响应。升级原因: {reason}"
