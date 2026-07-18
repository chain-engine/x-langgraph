# -*- coding: utf-8 -*-
"""
意图分类路由工作流节点定义

展示 LLM 意图分类 + 条件路由的典型客服场景。

支持两种模式：
1. LLM 智能分类（需要 API Key）
2. 规则分类（降级方案）
"""

import re

from langgraph.types import interrupt

from workflows.intent_classifier.state import IntentClassifierState
from core.config import settings
from core.logger import logger


# ========== 意图分类节点 ==========

INTENT_SYSTEM_PROMPT = """你是一个智能客服意图分类器。根据用户输入判断客户意图，只返回最匹配的一个类别。

可选意图：
- product_inquiry: 产品咨询（功能、规格、使用方法、价格等）
- order_status: 订单状态（订单查询、物流进度、退换货等）
- technical_support: 技术支持（功能异常、bug、配置问题等）
- complaint: 投诉（服务不满、体验问题、建议反馈等）
- billing: 账单问题（费用疑问、发票、付款方式等）
- other: 其他（闲聊、寒暄、无法归类等）

请仔细分析用户输入的语义，选择最准确的意图。"""


def classify_intent_node(state: IntentClassifierState) -> dict:
    """
    意图分类节点：根据用户输入判断意图

    优先使用 LLM 智能分类，失败时降级到规则分类。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    messages = state.get("messages", [])
    last = messages[-1] if messages else {}
    user_input = last.get("content", "") if isinstance(last, dict) else str(last)
    logger.info(f"意图分类: {user_input}")

    if _has_valid_api_key():
        try:
            intent, reasoning, confidence = _llm_classification(user_input)
            logger.info(
                f"LLM 分类: {intent} (置信度: {confidence:.2f}, 理由: {reasoning})"
            )
        except Exception as e:
            logger.warning(f"LLM 分类失败，降级到规则: {e}")
            intent, reasoning, confidence = _fallback_classification(user_input)
    else:
        intent, reasoning, confidence = _fallback_classification(user_input)

    return {
        "intent": intent,
        "confidence": confidence,
    }


# ========== 业务处理节点 ==========

def handle_product_inquiry_node(state: IntentClassifierState) -> dict:
    """产品咨询处理节点"""
    messages = state.get("messages", [])
    user_input = messages[-1].get("content", "") if messages else ""
    return {
        "response": (
            "感谢您的产品咨询！我们的产品具有以下核心优势：\n"
            "1. 高性能：采用最新算法优化，响应速度快\n"
            "2. 易用性：提供 SDK 和 REST API，接入简单\n"
            "3. 可扩展：支持水平扩展，满足大规模并发需求\n"
            f"针对您的问题「{user_input}」，建议您查阅我们的官方文档或联系技术支持获取详细解答。"
        )
    }


def handle_order_status_node(state: IntentClassifierState) -> dict:
    """订单状态查询处理节点"""
    messages = state.get("messages", [])
    user_input = messages[-1].get("content", "") if messages else ""
    return {
        "response": (
            "正在为您查询订单状态...\n\n"
            "请提供您的订单号，我将为您查询详细的物流进度。"
            f"\n\n您刚才提到「{user_input}」，我会尽快帮您处理。"
        )
    }


def handle_technical_support_node(state: IntentClassifierState) -> dict:
    """技术支持处理节点（需要人工审批）"""
    messages = state.get("messages", [])
    user_input = messages[-1].get("content", "") if messages else ""
    state_approved = state.get("approved")

    if state_approved is None:
        response = interrupt(
            {
                "type": "approval_required",
                "message": "技术问题需要人工处理",
                "intent": "technical_support",
                "user_input": user_input,
            }
        )
        if response.get("approved"):
            return {
                "approved": True,
                "approval_comments": response.get("comments", ""),
                "response": (
                    "【人工处理中】您的技术问题已转交给技术支持工程师，"
                    "预计 24 小时内给您回复。也可拨打客服热线：400-xxx-xxxx"
                ),
            }
        else:
            return {
                "approved": False,
                "approval_comments": response.get("comments", ""),
                "response": (
                    "根据您的问题「" + user_input + "」，"
                    "建议您先查阅我们的常见问题解答或操作手册。"
                    "如仍有问题，欢迎随时联系我们。"
                ),
            }

    return {
        "response": (
            "【AI 处理】针对您的技术问题，请尝试以下步骤：\n"
            "1. 确认网络连接正常\n"
            "2. 清除浏览器缓存后重试\n"
            "3. 确认是否使用了最新版本的客户端\n"
            "如果问题仍然存在，请联系技术支持。"
        )
    }


def handle_complaint_node(state: IntentClassifierState) -> dict:
    """投诉处理节点"""
    messages = state.get("messages", [])
    user_input = messages[-1].get("content", "") if messages else ""
    return {
        "response": (
            "非常抱歉给您带来了不好的体验。\n\n"
            f"您反馈的问题「{user_input}」我们已记录，"
            "我们的客服团队将在 24 小时内与您联系解决。\n"
            "感谢您的宝贵意见，我们会持续改进服务质量。"
        )
    }


def handle_billing_node(state: IntentClassifierState) -> dict:
    """账单问题处理节点"""
    messages = state.get("messages", [])
    user_input = messages[-1].get("content", "") if messages else ""
    return {
        "response": (
            "关于您的账单疑问，以下是常见处理方式：\n"
            "- 费用明细：可登录控制台查看详细账单\n"
            "- 发票申请：联系客服或通过管理后台自助申请\n"
            "- 退款问题：退款将在 3-7 个工作日内原路返回\n\n"
            f"针对「{user_input}」，我们的账单团队会尽快为您核实。"
        )
    }


def handle_other_node(state: IntentClassifierState) -> dict:
    """其他/闲聊处理节点"""
    messages = state.get("messages", [])
    user_input = messages[-1].get("content", "") if messages else ""
    return {
        "response": (
            f"感谢您的来信！关于「{user_input}」，"
            "请告诉我具体的需求，我可以帮您：\n"
            "- 查询产品信息和价格\n"
            "- 追踪订单状态\n"
            "- 解决技术问题\n"
            "- 处理账单和发票\n"
            "- 反馈投诉建议\n\n"
            "请详细描述您的问题，我会尽力帮助您。"
        )
    }


# ========== 内部方法 ==========

def _has_valid_api_key() -> bool:
    return settings.has_valid_api_key()


def _llm_classification(user_input: str) -> tuple[str, str, float]:
    """
    LLM 意图分类。

    Returns:
        (intent, reasoning, confidence)
    """
    from llms.providers import get_llm_provider
    from langchain_core.messages import HumanMessage, SystemMessage
    import json
    import re

    provider_name = settings.get_available_provider()
    provider = get_llm_provider(provider_name)

    prompt = f"""{INTENT_SYSTEM_PROMPT}

用户输入: {user_input}

请严格只返回一个 JSON 对象，不要添加任何解释文字：
{{"intent": "意图类别", "reasoning": "决策理由", "confidence": 0.0-1.0的数字}}"""

    response = provider.chat_model.invoke(
        [SystemMessage(content=prompt), HumanMessage(content="")]
    )

    # 提取 JSON
    match = re.search(r"\{.*?\}", response.content, re.DOTALL)
    if not match:
        return "other", "无法解析 LLM 响应", 0.1

    data = json.loads(match.group())
    valid_intents = {
        "product_inquiry",
        "order_status",
        "technical_support",
        "complaint",
        "billing",
        "other",
    }
    intent = data.get("intent", "other")
    if intent not in valid_intents:
        intent = "other"
    reasoning = data.get("reasoning", "")
    confidence = min(max(float(data.get("confidence", 0.5)), 0.0), 1.0)
    return intent, reasoning, confidence


def _fallback_classification(user_input: str) -> tuple[str, str, float]:
    """
    基于规则的意图分类。

    Returns:
        (intent, reasoning, confidence)
    """
    text = user_input.lower()

    # 技术支持
    tech_keywords = ["错误", "bug", "故障", "无法", "登录", "崩溃", "crash", "error", "技术", "配置"]
    if any(kw in text for kw in tech_keywords):
        return "technical_support", "检测到技术问题关键词", 0.85

    # 投诉
    complaint_keywords = ["投诉", "不满", "太差", "垃圾", "差评", "退款退货"]
    if any(kw in text for kw in complaint_keywords):
        return "complaint", "检测到投诉类关键词", 0.85

    # 账单
    billing_keywords = ["账单", "发票", "费用", "价格", "收费", "付款", "退款"]
    if any(kw in text for kw in billing_keywords):
        return "billing", "检测到账单类关键词", 0.85

    # 订单状态
    order_keywords = ["订单", "物流", "发货", "收货", "快递", "追踪", "什么时候到"]
    if any(kw in text for kw in order_keywords):
        return "order_status", "检测到订单类关键词", 0.80

    # 产品咨询
    product_keywords = ["功能", "怎么用", "如何使用", "多少钱", "价格", "规格", "介绍", "优势", "product"]
    if any(kw in text for kw in product_keywords):
        return "product_inquiry", "检测到产品咨询类关键词", 0.80

    return "other", "无法识别意图，使用默认处理", 0.5
