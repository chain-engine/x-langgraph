# -*- coding: utf-8 -*-
"""
Agent 注册表

管理 Agent 实例的注册和获取
"""

from typing import Optional

from agent.base import BaseAgent, AgentConfig, AgentType


class AgentRegistry:
    """
    Agent 注册表

    线程不安全，适用于单进程应用
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._factories: dict[AgentType, callable] = {}

    def register(self, name: str, agent: BaseAgent) -> None:
        """
        注册 Agent 实例

        Args:
            name: Agent 名称
            agent: Agent 实例
        """
        if name in self._agents:
            raise ValueError(f"Agent '{name}' 已存在")
        self._agents[name] = agent

    def register_factory(self, agent_type: AgentType, factory: callable) -> None:
        """
        注册 Agent 工厂函数

        Args:
            agent_type: Agent 类型
            factory: 工厂函数
        """
        self._factories[agent_type] = factory

    def get(self, name: str) -> Optional[BaseAgent]:
        """
        获取 Agent 实例

        Args:
            name: Agent 名称

        Returns:
            BaseAgent 实例或 None
        """
        return self._agents.get(name)

    def create(self, agent_type: AgentType, config: AgentConfig) -> BaseAgent:
        """
        通过工厂函数创建 Agent

        Args:
            agent_type: Agent 类型
            config: Agent 配置

        Returns:
            BaseAgent 实例
        """
        if agent_type not in self._factories:
            raise ValueError(f"未注册 Agent 类型: {agent_type}")
        factory = self._factories[agent_type]
        return factory(config)

    def list_agents(self) -> list[str]:
        """列出所有注册的 Agent"""
        return list(self._agents.keys())

    def unregister(self, name: str) -> bool:
        """
        注销 Agent

        Args:
            name: Agent 名称

        Returns:
            bool 是否成功注销
        """
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def clear(self) -> None:
        """清空所有注册"""
        self._agents.clear()


# 全局注册表实例
_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """
    获取全局 Agent 注册表

    Returns:
        AgentRegistry 实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
