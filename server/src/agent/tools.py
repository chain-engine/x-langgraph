# -*- coding: utf-8 -*-
"""
工具注册和管理

提供工具的注册、查找和管理功能
"""

from typing import Optional

from langchain_core.tools import BaseTool, tool

from core.logger import logger


class ToolRegistry:
    """
    工具注册表

    管理所有可用的工具实例
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
            name: 工具名称（可选，默认使用工具的 name 属性）
        """
        tool_name = name or tool.name
        if tool_name in self._tools:
            logger.warning(f"工具 '{tool_name}' 已存在，将被覆盖")
        self._tools[tool_name] = tool
        logger.info(f"注册工具: {tool_name}")

    def register_many(self, tools: list[BaseTool]) -> None:
        """
        批量注册工具

        Args:
            tools: 工具列表
        """
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Optional[BaseTool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            BaseTool 实例或 None
        """
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名称"""
        return list(self._tools.keys())

    def get_all(self) -> list[BaseTool]:
        """获取所有工具实例"""
        return list(self._tools.values())

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            bool 是否成功
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"注销工具: {name}")
            return True
        return False

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        logger.info("清空所有工具注册")

    def has(self, name: str) -> bool:
        """检查工具是否已注册"""
        return name in self._tools


# 全局工具注册表实例
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    获取全局工具注册表

    Returns:
        ToolRegistry 实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _register_default_tools(_global_registry)
    return _global_registry


def _register_default_tools(registry: ToolRegistry) -> None:
    """注册默认工具"""
    try:
        # 导入并注册内置工具
        from tools.calculation_tools import calculator, unit_converter
        from tools.search_tools import web_search, file_search

        registry.register(calculator)
        registry.register(unit_converter)
        registry.register(web_search)
        registry.register(file_search)

        logger.info("已注册默认工具: calculator, unit_converter, web_search, file_search")
    except ImportError as e:
        logger.warning(f"无法导入默认工具: {e}")
    except Exception as e:
        logger.warning(f"注册默认工具时出错: {e}")


def create_tool_from_function(
    func: callable,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> BaseTool:
    """
    将普通函数转换为 LangChain 工具

    Args:
        func: 要转换的函数
        name: 工具名称（默认使用函数名）
        description: 工具描述（默认从函数文档字符串生成）

    Returns:
        BaseTool: LangChain 工具实例
    """
    tool_name = name or func.__name__
    tool_desc = description or func.__doc__ or f"执行 {tool_name} 操作"

    @tool(name=tool_name, description=tool_desc)
    def wrapped_tool(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapped_tool
