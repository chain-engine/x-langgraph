# -*- coding: utf-8 -*-
"""
Agent 工厂函数

提供便捷的 Agent 节点创建方法
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from agent.base import AgentConfig, AgentType
from agent.react_agent import create_react_agent_node, ReactAgentConfig
from agent.registry import get_agent_registry
from agent.tools import get_tool_registry
from llms import create_chat_model


def create_agent_node(
    name: str,
    tools: list[BaseTool],
    system_prompt: str = "你是一个有用的 AI 助手。",
    llm_provider: str = "deepseek",
    llm_model: Optional[str] = None,
    max_iterations: int = 5,
    output_field: str = "agent_result",
    include_history: bool = False,
) -> dict:
    """
    创建可嵌入工作流的 Agent 节点

    这是创建 Agent 节点的主要入口函数。

    Args:
        name: 节点名称（工作流中唯一）
        tools: 工具列表
        system_prompt: 系统提示词
        llm_provider: LLM 提供者名称（deepseek/doubao/aliyun/mimo/mock）
        llm_model: LLM 模型名称（可选，覆盖默认）
        max_iterations: 最大迭代次数
        output_field: 输出字段名
        include_history: 是否在输出中包含完整推理历史

    Returns:
        dict: 包含节点函数和配置的字典
    """
    # 创建 LLM 实例
    llm = create_chat_model(
        provider_name=llm_provider,
        model_name=llm_model,
    )

    # 创建 ReAct Agent 节点
    node_func = create_react_agent_node(
        name=name,
        llm=llm,
        tools=tools,
        system_prompt=system_prompt,
        max_iterations=max_iterations,
        output_field=output_field,
        include_history=include_history,
    )

    # 注册到全局注册表
    registry = get_agent_registry()

    return {
        "node": node_func,
        "config": AgentConfig(
            name=name,
            agent_type=AgentType.REACT,
            system_prompt=system_prompt,
            llm_provider=llm_provider,
            llm_model=llm_model,
            tools=[t.name for t in tools],
            max_iterations=max_iterations,
            output_field=output_field,
        ),
    }


def create_agent_node_from_config(config: dict) -> dict:
    """
    从配置字典创建 Agent 节点

    适用于从数据库或配置文件中加载 Agent 配置。

    Args:
        config: Agent 配置字典
        {
            "name": "my_agent",
            "system_prompt": "你是一个有帮助的助手",
            "llm_provider": "deepseek",
            "llm_model": "deepseek-chat",
            "tools": ["calculator", "web_search"],
            "max_iterations": 5,
            "output_field": "agent_result",
        }

    Returns:
        dict: 包含节点函数和配置的字典
    """
    tool_registry = get_tool_registry()

    # 解析工具列表
    tool_names = config.get("tools", [])
    if isinstance(tool_names, str):
        # 支持逗号分隔的字符串
        tool_names = [t.strip() for t in tool_names.split(",")]

    # 获取工具实例
    tools = []
    for tool_name in tool_names:
        tool = tool_registry.get(tool_name)
        if tool:
            tools.append(tool)
        else:
            from core.logger import logger

            logger.warning(f"工具 '{tool_name}' 未注册，将被忽略")

    return create_agent_node(
        name=config["name"],
        tools=tools,
        system_prompt=config.get("system_prompt", "你是一个有帮助的助手。"),
        llm_provider=config.get("llm_provider", "deepseek"),
        llm_model=config.get("llm_model"),
        max_iterations=config.get("max_iterations", 5),
        output_field=config.get("output_field", "agent_result"),
        include_history=config.get("include_history", False),
    )


def get_or_create_agent(name: str, config: dict) -> dict:
    """
    获取或创建 Agent 节点

    如果同名 Agent 已存在，直接返回；否则创建并注册。

    Args:
        name: Agent 名称
        config: Agent 配置

    Returns:
        dict: Agent 节点信息
    """
    registry = get_agent_registry()

    # 尝试获取已注册的 Agent
    existing = registry.get(name)
    if existing:
        return {"agent": existing, "created": False}

    # 创建新 Agent
    result = create_agent_node_from_config(config | {"name": name})
    return {**result, "created": True}
