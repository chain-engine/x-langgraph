# -*- coding: utf-8 -*-
"""
简单路由工作流状态定义
"""

from typing import TypedDict, Optional, Literal

from pydantic import BaseModel, Field


class SimpleRouterState(TypedDict):
    """简单路由工作流状态"""

    # 用户输入
    input: str

    # 路由决策
    route: str  # 'search', 'calculate', 'weather', 'unknown'

    # 处理结果
    output: str

    # 错误信息
    error: Optional[str]

    # 路由元信息（新增）
    routing_reasoning: Optional[str]  # 路由决策理由
    routing_confidence: Optional[float]  # 置信度 0-1


class RouteDecision(BaseModel):
    """LLM 路由决策结果（用于结构化输出）"""

    route: Literal["search", "calculate", "weather", "unknown"] = Field(
        description="路由目标节点：search(搜索信息)、calculate(数学计算)、weather(天气查询)、unknown(无法识别)"
    )
    reasoning: str = Field(
        description="路由决策的理由，解释为什么选择这个路由"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="决策置信度，0-1之间，1表示非常确定"
    )
