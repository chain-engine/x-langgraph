# -*- coding: utf-8 -*-
"""
Mock 天气数据提供者

用于测试或无 API Key 时返回模拟天气数据。
"""

from tools.weather.base import WeatherProvider, WeatherInfo


class MockWeatherProvider(WeatherProvider):
    """
    Mock 天气数据提供者

    返回预定义的模拟数据，用于测试或降级场景。
    """

    name = "mock"
    description = "模拟天气数据提供者（用于测试）"

    # 模拟天气数据库
    MOCK_DATA = {
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

    def get_weather(self, city: str) -> WeatherInfo:
        """
        获取模拟天气数据

        Args:
            city: 城市名称

        Returns:
            WeatherInfo 模拟天气信息
        """
        data = self.MOCK_DATA.get(city, {"weather": "晴", "temp": "20", "humidity": "50"})

        return WeatherInfo(
            city=city,
            weather=data["weather"],
            temperature=data["temp"],
            humidity=data["humidity"],
            wind_direction="东北风",
            wind_power="2",
            report_time=None,
            is_mock=True,
        )

    def is_available(self) -> bool:
        """Mock Provider 始终可用"""
        return True
