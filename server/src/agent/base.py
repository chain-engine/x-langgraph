# -*- coding: utf-8 -*-
"""
Agent 基类和接口定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import Field

from constants import AgentStatus, AgentType


@dataclass
class AgentConfig:
    """Agent 配置"""

    name: str
    agent_type: AgentType = AgentType.REACT
    system_prompt: str = ""
    max_iterations: int = 5
    output_field: str = "agent_result"
    llm_provider: str = "deepseek"  # 默认使用 deepseek
    llm_model: Optional[str] = None  # 可覆盖默认模型
    tools: list[str] = field(default_factory=list)  # 工具名称列表


@dataclass
class AgentResult:
    """Agent 执行结果"""

    success: bool
    output: Any = None
    error: Optional[str] = None
    iterations: int = 0
    tool_calls: list[dict] = field(default_factory=list)  # 记录工具调用历史
    status: AgentStatus = AgentStatus.IDLE


class BaseAgent(ABC):
    """
    Agent 基类

    所有 Agent 实现都需要继承此类。
    """

    def __init__(self, config: AgentConfig):
        """
        初始化 Agent

        Args:
            config: Agent 配置
        """
        self.config = config
        self._reset()

    def _reset(self):
        """重置 Agent 状态"""
        self.status = AgentStatus.IDLE
        self.iterations = 0
        self.tool_calls = []
        self.output = None

    @abstractmethod
    async def run(self, input_data: dict) -> AgentResult:
        """
        运行 Agent

        Args:
            input_data: 输入数据（包含 messages 等）

        Returns:
            AgentResult 执行结果
        """
        pass

    @abstractmethod
    async def step(self, input_data: dict) -> dict:
        """
        执行单个步骤

        Args:
            input_data: 输入数据

        Returns:
            dict 步骤输出
        """
        pass

    def should_continue(self) -> bool:
        """判断是否继续执行"""
        if self.iterations >= self.config.max_iterations:
            self.status = AgentStatus.MAX_ITERATIONS
            return False
        if self.status in [AgentStatus.FINISHED, AgentStatus.ERROR, AgentStatus.MAX_ITERATIONS]:
            return False
        return True

    @property
    def name(self) -> str:
        """获取 Agent 名称"""
        return self.config.name
