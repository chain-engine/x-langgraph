# -*- coding: utf-8 -*-
"""
全局枚举定义
"""

from enum import Enum


class Environment(Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @property
    def desc(self) -> str:
        """返回环境描述"""
        return self.value
