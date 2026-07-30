# -*- coding: utf-8 -*-
"""
全局枚举定义
"""

from enum import Enum

from .base import BaseEnum


class Environment(Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @property
    def desc(self) -> str:
        """返回环境描述"""
        return self.value


class ReasoningMode(BaseEnum):
    """推理模式枚举"""
    REACT = ("react", "ReAct 推理模式：边推理边行动，交互式调用工具")
    PLAN_EXECUTE = ("plan_execute", "Plan-and-Execute 模式：先规划后执行，支持重规划")
    TOT = ("tot", "Tree-of-Thoughts 模式：多分支搜索，探索最优解")
