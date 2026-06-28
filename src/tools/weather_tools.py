# -*- coding: utf-8 -*-
"""
天气工具模块（兼容层）

提供天气查询功能，内部使用 Provider 模式。
保持与原有接口的向后兼容。
"""

from langchain_core.tools import tool

from tools.weather import get_weather_provider, query_weather
from core.logger import logger


@tool
def weather_query_tool(city: str) -> str:
    """
    天气查询工具，获取指定城市的实时天气信息。

    Args:
        city: 城市名称，如 "北京"、"上海"、"深圳"

    Returns:
        天气信息，包括天气状况、温度、风向等
    """
    logger.info(f"执行天气查询: {city}")

    try:
        # 使用 Provider 模式
        info = query_weather(city)
        return info.to_string()

    except Exception as e:
        logger.error(f"天气查询失败: {e}")
        return f"查询失败: {str(e)}"


# ========== 向后兼容的辅助函数 ==========

def _get_city_code(city: str) -> str:
    """
    获取城市编码（高德地图使用 adcode）

    常见城市编码映射
    """
    from tools.weather.base import WeatherProvider
    provider = get_weather_provider()
    return provider.get_city_code(city)


def _get_mock_weather(city: str) -> str:
    """模拟天气数据（向后兼容）"""
    from tools.weather.mock_provider import MockWeatherProvider
    provider = MockWeatherProvider()
    info = provider.get_weather(city)
    return info.to_string()
