# -*- coding: utf-8 -*-
"""
天气查询 Provider 基类

定义天气查询的抽象接口，支持多种数据源实现。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class WeatherInfo:
    """天气信息数据类"""

    city: str
    weather: str
    temperature: str
    wind_direction: Optional[str] = None
    wind_power: Optional[str] = None
    humidity: Optional[str] = None
    report_time: Optional[str] = None
    is_mock: bool = False

    def to_string(self) -> str:
        """转换为可读字符串"""
        lines = [f"城市: {self.city}", f"天气: {self.weather}", f"温度: {self.temperature}°C"]

        if self.wind_direction:
            lines.append(f"风向: {self.wind_direction}")
        if self.wind_power:
            lines.append(f"风力: {self.wind_power}级")
        if self.humidity:
            lines.append(f"湿度: {self.humidity}%")
        if self.report_time:
            lines.append(f"更新时间: {self.report_time}")
        if self.is_mock:
            lines.append("(模拟数据，请配置 API_KEY 获取实时天气)")

        return "\n".join(lines)

    def __str__(self) -> str:
        return self.to_string()


class WeatherProvider(ABC):
    """
    天气数据提供者抽象基类

    所有天气数据源都需要实现此接口。
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def get_weather(self, city: str) -> WeatherInfo:
        """
        获取指定城市的天气信息

        Args:
            city: 城市名称

        Returns:
            WeatherInfo 天气信息对象
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查 Provider 是否可用

        Returns:
            bool: 是否可用
        """
        pass

    def get_city_code(self, city: str) -> str:
        """
        获取城市编码（可被子类覆盖）

        Args:
            city: 城市名称

        Returns:
            城市编码
        """
        city_codes = {
            "北京": "110000",
            "上海": "310000",
            "广州": "440100",
            "深圳": "440300",
            "杭州": "330100",
            "南京": "320100",
            "成都": "510100",
            "武汉": "420100",
            "西安": "610100",
            "重庆": "500000",
            "天津": "120000",
            "苏州": "320500",
            "郑州": "410100",
            "长沙": "430100",
            "青岛": "370200",
        }
        return city_codes.get(city, city)
