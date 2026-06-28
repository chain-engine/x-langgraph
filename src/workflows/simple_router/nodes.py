# -*- coding: utf-8 -*-
"""
简单路由工作流节点定义

支持两种路由模式：
1. LLM 智能路由（需要 API Key）
2. 规则路由（降级方案）
"""

import re

from workflows.simple_router.state import SimpleRouterState, RouteDecision
from tools.search_tools import web_search_tool
from tools.calculation_tools import calculator_tool
from tools.weather_tools import weather_query_tool
from config.settings import settings
from core.logger import logger


# ========== 路由提示模板 ==========

ROUTING_SYSTEM_PROMPT = """你是一个智能路由器，负责分析用户输入并决定应该由哪个处理器处理。

可用的处理器：
- search: 搜索信息、查找资料、询问概念、百科问答
- calculate: 数学计算、算术运算、数值处理
- weather: 天气查询、气温预报、天气相关咨询
- unknown: 无法识别的请求或与以上类别都不相关

请根据用户输入的语义，选择最合适的处理器。
"""

ROUTING_USER_PROMPT = """用户输入: {user_input}

请分析用户意图，返回路由决策。"""


# ========== 智能路由节点 ==========

def router_node(state: SimpleRouterState) -> dict:
    """
    路由节点：根据输入内容决定执行哪个工具

    优先使用 LLM 智能路由，失败时降级到规则路由。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    user_input = state.get("input", "")
    logger.info(f"路由分析: {user_input}")

    # 尝试 LLM 智能路由
    if _has_valid_api_key():
        try:
            decision = _llm_routing(user_input)
            logger.info(
                f"LLM 路由决策: {decision.route} "
                f"(置信度: {decision.confidence:.2f}, 理由: {decision.reasoning})"
            )
            return {
                "route": decision.route,
                "routing_reasoning": decision.reasoning,
                "routing_confidence": decision.confidence,
            }
        except Exception as e:
            logger.warning(f"LLM 路由失败，降级到规则路由: {e}")

    # 降级到规则路由
    result = _fallback_routing(user_input)
    logger.info(f"规则路由决策: {result['route']}")
    return result


def _has_valid_api_key() -> bool:
    """检查是否有可用的 API Key"""
    return settings.has_valid_api_key()


def _llm_routing(user_input: str) -> RouteDecision:
    """
    使用 LLM 进行智能路由

    Args:
        user_input: 用户输入

    Returns:
        RouteDecision 路由决策
    """
    from llm.providers import get_llm_provider

    # 获取可用的 LLM 提供者
    provider_name = settings.get_available_provider()
    provider = get_llm_provider(provider_name)

    # 配置结构化输出
    structured_llm = provider.chat_model.with_structured_output(RouteDecision)

    # 构建提示
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [
        SystemMessage(content=ROUTING_SYSTEM_PROMPT),
        HumanMessage(content=ROUTING_USER_PROMPT.format(user_input=user_input)),
    ]

    # 调用 LLM
    return structured_llm.invoke(messages)


def _fallback_routing(user_input: str) -> dict:
    """
    降级路由：基于规则的简单路由

    Args:
        user_input: 用户输入

    Returns:
        路由决策字典
    """
    # 检查是否包含数字和运算符（计算）
    if re.search(r"\d+\s*[+\-*/]\s*\d+", user_input):
        return {
            "route": "calculate",
            "routing_reasoning": "检测到数学运算表达式",
            "routing_confidence": 0.9,
        }

    # 检查是否包含天气相关关键词
    weather_keywords = ["天气", "气温", "温度", "weather", "下雨", "晴天", "阴天", "风速", "湿度"]
    if any(kw in user_input for kw in weather_keywords):
        return {
            "route": "weather",
            "routing_reasoning": "检测到天气相关关键词",
            "routing_confidence": 0.85,
        }

    # 检查是否包含搜索相关关键词
    search_keywords = ["搜索", "查找", "什么是", "什么是", "search", "查一下", "帮我找", "请问"]
    if any(kw in user_input for kw in search_keywords):
        return {
            "route": "search",
            "routing_reasoning": "检测到搜索相关关键词",
            "routing_confidence": 0.85,
        }

    # 默认使用搜索（最通用的处理方式）
    return {
        "route": "search",
        "routing_reasoning": "默认路由到搜索",
        "routing_confidence": 0.5,
    }


# ========== 处理节点 ==========

def search_node(state: SimpleRouterState) -> dict:
    """搜索节点"""
    user_input = state.get("input", "")
    logger.info(f"执行搜索: {user_input}")

    try:
        result = web_search_tool.invoke(user_input)
        return {"output": result, "error": None}
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return {"output": "", "error": str(e)}


def calculate_node(state: SimpleRouterState) -> dict:
    """计算节点"""
    user_input = state.get("input", "")
    logger.info(f"执行计算: {user_input}")

    try:
        result = calculator_tool.invoke(user_input)
        return {"output": result, "error": None}
    except Exception as e:
        logger.error(f"计算失败: {e}")
        return {"output": "", "error": str(e)}


def weather_node(state: SimpleRouterState) -> dict:
    """天气查询节点"""
    user_input = state.get("input", "")
    logger.info(f"执行天气查询: {user_input}")

    try:
        # 从输入中提取城市名
        city = _extract_city(user_input)
        result = weather_query_tool.invoke(city)
        return {"output": result, "error": None}
    except Exception as e:
        logger.error(f"天气查询失败: {e}")
        return {"output": "", "error": str(e)}


def unknown_node(state: SimpleRouterState) -> dict:
    """未知请求节点"""
    return {
        "output": "抱歉，我无法理解您的请求。请尝试以下操作：\n"
        "- 搜索信息：输入 '搜索 xxx' 或 '什么是 xxx'\n"
        "- 数学计算：输入算式如 '123 + 456'\n"
        "- 天气查询：输入 '北京天气' 或 '上海气温'",
        "error": None,
    }


# ========== 辅助函数 ==========

def _extract_city(text: str) -> str:
    """从文本中提取城市名"""
    cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "重庆"]

    for city in cities:
        if city in text:
            return city

    # 默认返回北京
    return "北京"
