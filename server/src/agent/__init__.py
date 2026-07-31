# -*- coding: utf-8 -*-
"""
Agent 模块

提供通用的 Agent 能力，用于嵌入工作流中：
- ReAct Agent 节点
- 工具注册和管理
- Agent 注册表
"""

from agent.base import BaseAgent, AgentConfig, AgentResult
from agent.registry import AgentRegistry, get_agent_registry
from agent.react_agent import create_react_agent_node, ReactAgentConfig
from agent.factory import create_agent_node
from agent.tools import ToolRegistry, get_tool_registry

__all__ = [
    # Base
    "BaseAgent",
    "AgentConfig",
    "AgentResult",
    # Registry
    "AgentRegistry",
    "get_agent_registry",
    # ReAct Agent
    "create_react_agent_node",
    "ReactAgentConfig",
    # Factory
    "create_agent_node",
    # Tools
    "ToolRegistry",
    "get_tool_registry",
]
