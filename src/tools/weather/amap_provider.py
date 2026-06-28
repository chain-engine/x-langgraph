# -*- coding: utf-8 -*-
"""
高德地图天气数据提供者

使用高德地图 API 获取实时天气信息。
"""

import requests

from tools.weather.base import WeatherProvider, WeatherInfo
from core.logger import logger


class AmapWeatherProvider(WeatherProvider):
    """
    高德地图天气数据提供者

    使用高德地图 Web 服务 API 获取实时天气。
    API 文档: https://lbs.amap.com/api/webservice/guide/api/weatherinfo
    """

    name = "amap"
    description = "高德地图天气 API 提供者"

    API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

    def __init__(self, api_key: str):
        """
        初始化高德地图天气提供者

        Args:
            api_key: 高德地图 API Key
        """
        self.api_key = api_key

    def get_weather(self, city: str) -> WeatherInfo:
        """
        获取实时天气信息

        Args:
            city: 城市名称

        Returns:
            WeatherInfo 天气信息
        """
        logger.info(f"[Amap] 查询天气: {city}")

        try:
            city_code = self.get_city_code(city)
            params = {
                "key": self.api_key,
                "city": city_code,
                "extensions": "base",  # base=实况天气, all=预报天气
                "output": "JSON",
            }

            response = requests.get(self.API_URL, params=params, timeout=10)
            data = response.json()

            if data.get("status") == "1" and data.get("lives"):
                live = data["lives"][0]
                return WeatherInfo(
                    city=live.get("city", city),
                    weather=live.get("weather", "未知"),
                    temperature=live.get("temperature", "未知"),
                    wind_direction=live.get("winddirection", "未知"),
                    wind_power=live.get("windpower", "未知"),
                    humidity=live.get("humidity", "未知"),
                    report_time=live.get("reporttime", "未知"),
                    is_mock=False,
                )

            logger.warning(f"[Amap] 查询失败: {data.get('info', '未知错误')}")
            # 查询失败时返回默认值
            return WeatherInfo(
                city=city,
                weather="查询失败",
                temperature="未知",
                is_mock=False,
            )

        except requests.RequestException as e:
            logger.error(f"[Amap] 网络请求失败: {e}")
            raise ConnectionError(f"网络请求失败: {e}")

        except Exception as e:
            logger.error(f"[Amap] 查询异常: {e}")
            raise RuntimeError(f"查询异常: {e}")

    def is_available(self) -> bool:
        """检查 API Key 是否配置"""
        return bool(self.api_key)

    def get_forecast(self, city: str) -> list[dict]:
        """
        获取天气预报（未来几天）

        Args:
            city: 城市名称

        Returns:
            预报数据列表
        """
        logger.info(f"[Amap] 查询天气预报: {city}")

        try:
            city_code = self.get_city_code(city)
            params = {
                "key": self.api_key,
                "city": city_code,
                "extensions": "all",  # all=预报天气
                "output": "JSON",
            }

            response = requests.get(self.API_URL, params=params, timeout=10)
            data = response.json()

            if data.get("status") == "1" and data.get("forecasts"):
                return data["forecasts"]

            return []

        except Exception as e:
            logger.error(f"[Amap] 预报查询失败: {e}")
            return []
