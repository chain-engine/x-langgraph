# -*- coding: utf-8 -*-
"""
天气查询工具模块

提供统一的天气查询接口，支持多种数据源：
- 高德地图 API（需要 API Key）
- Mock 数据（无需配置）

Usage:
    from tools.weather import get_weather_provider, weather_query_tool

    # 获取天气提供者
    provider = get_weather_provider()
    info = provider.get_weather("北京")

    # 或使用 LangChain Tool
    result = weather_query_tool.invoke("北京")
"""

from typing import Optional

from tools.weather.base import WeatherProvider, WeatherInfo
from tools.weather.mock_provider import MockWeatherProvider
from tools.weather.amap_provider import AmapWeatherProvider

from core.config import settings
from core.logger import logger


# ========== Provider 工厂 ==========

def get_weather_provider(provider_name: Optional[str] = None) -> WeatherProvider:
    """
    获取天气数据提供者

    Args:
        provider_name: 指定提供者名称（amap, mock），为空则自动选择

    Returns:
        WeatherProvider 实例

    Examples:
        # 自动选择（有 API Key 用 Amap，否则 Mock）
        provider = get_weather_provider()

        # 指定使用 Mock
        provider = get_weather_provider("mock")

        # 指定使用高德
        provider = get_weather_provider("amap")
    """
    if provider_name == "mock":
        logger.info("使用 Mock 天气提供者")
        return MockWeatherProvider()

    if provider_name == "amap" or settings.AMAP_API_KEY:
        if settings.AMAP_API_KEY:
            logger.info("使用高德地图天气提供者")
            return AmapWeatherProvider(settings.AMAP_API_KEY)
        else:
            logger.warning("未配置 AMAP_API_KEY，降级到 Mock 提供者")

    logger.info("使用 Mock 天气提供者（默认）")
    return MockWeatherProvider()


def list_weather_providers() -> list[str]:
    """列出所有可用的天气提供者"""
    providers = ["mock"]
    if settings.AMAP_API_KEY:
        providers.append("amap")
    return providers


# ========== LangChain Tool 封装 ==========

from langchain_core.tools import tool


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

    provider = get_weather_provider()

    try:
        info = provider.get_weather(city)
        return info.to_string()
    except Exception as e:
        logger.error(f"天气查询失败: {e}")
        return f"查询失败: {str(e)}"


# ========== 便捷函数 ==========

def query_weather(city: str, provider_name: Optional[str] = None) -> WeatherInfo:
    """
    查询天气（直接返回 WeatherInfo 对象）

    Args:
        city: 城市名称
        provider_name: 提供者名称（可选）

    Returns:
        WeatherInfo 天气信息对象
    """
    provider = get_weather_provider(provider_name)
    return provider.get_weather(city)


# ========== 导出 ==========

__all__ = [
    # 类型
    "WeatherProvider",
    "WeatherInfo",
    # 提供者
    "MockWeatherProvider",
    "AmapWeatherProvider",
    # 工厂
    "get_weather_provider",
    "list_weather_providers",
    # Tool
    "weather_query_tool",
    # 便捷函数
    "query_weather",
]
