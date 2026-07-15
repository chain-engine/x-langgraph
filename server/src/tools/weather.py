# -*- coding: utf-8 -*-
"""
天气查询工具

直接使用高德地图 API 获取实时天气信息。
"""

import requests
from langchain_core.tools import tool

from core.config import settings
from core.logger import logger


API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

CITY_CODES = {
    "北京": "110000", "上海": "310000", "广州": "440100", "深圳": "440300",
    "杭州": "330100", "南京": "320100", "成都": "510100", "武汉": "420100",
    "西安": "610100", "重庆": "500000", "天津": "120000", "苏州": "320500",
    "郑州": "410100", "长沙": "430100", "青岛": "370200",
}


def _get_city_code(city: str) -> str:
    return CITY_CODES.get(city, city)


def query_weather(city: str) -> str:
    """
    查询天气

    Args:
        city: 城市名称

    Returns:
        天气信息字符串
    """
    if not settings.AMAP_API_KEY:
        return _get_mock_weather(city)

    try:
        city_code = _get_city_code(city)
        params = {
            "key": settings.AMAP_API_KEY,
            "city": city_code,
            "extensions": "base",
            "output": "JSON",
        }

        response = requests.get(API_URL, params=params, timeout=10)
        data = response.json()

        if data.get("status") == "1" and data.get("lives"):
            live = data["lives"][0]
            lines = [
                f"城市: {live.get('city', city)}",
                f"天气: {live.get('weather', '未知')}",
                f"温度: {live.get('temperature', '未知')}°C",
                f"风向: {live.get('winddirection', '未知')}",
                f"风力: {live.get('windpower', '未知')}级",
                f"湿度: {live.get('humidity', '未知')}%",
                f"更新时间: {live.get('reporttime', '未知')}",
            ]
            return "\n".join(lines)

        logger.warning(f"天气查询失败: {data.get('info', '未知错误')}")
        return _get_mock_weather(city)

    except Exception as e:
        logger.error(f"天气查询异常: {e}")
        return _get_mock_weather(city)


def _get_mock_weather(city: str) -> str:
    """获取模拟天气数据（无 API Key 时使用）"""
    mock_data = {
        "北京": {"weather": "晴", "temp": "18", "humidity": "45"},
        "上海": {"weather": "多云", "temp": "22", "humidity": "65"},
        "广州": {"weather": "阴", "temp": "26", "humidity": "78"},
        "深圳": {"weather": "晴", "temp": "27", "humidity": "70"},
        "杭州": {"weather": "小雨", "temp": "20", "humidity": "85"},
        "南京": {"weather": "多云", "temp": "21", "humidity": "60"},
        "成都": {"weather": "阴", "temp": "19", "humidity": "72"},
        "武汉": {"weather": "晴", "temp": "23", "humidity": "55"},
        "西安": {"weather": "晴", "temp": "17", "humidity": "40"},
        "重庆": {"weather": "多云", "temp": "24", "humidity": "68"},
    }
    data = mock_data.get(city, {"weather": "晴", "temp": "20", "humidity": "50"})
    return (
        f"城市: {city}\n"
        f"天气: {data['weather']}\n"
        f"温度: {data['temp']}°C\n"
        f"湿度: {data['humidity']}%\n"
        "(模拟数据，请配置 AMAP_API_KEY 获取实时天气)"
    )


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
    return query_weather(city)