# -*- coding: utf-8 -*-
"""
工具基类模块

定义工具的基础抽象类和结果模型。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.tools import BaseTool as LangChainBaseTool
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行结果"""

    success: bool = Field(description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="元数据")


class BaseTool(ABC):
    """
    工具基类

    所有工具都需要继承此类并实现 create_tool 方法。
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def create_tool(self) -> LangChainBaseTool:
        """
        创建 LangChain 工具实例

        Returns:
            LangChain BaseTool 实例
        """
        pass

    def execute(self, *args, **kwargs) -> ToolResult:
        """
        执行工具（直接调用方式）

        Returns:
            ToolResult 执行结果
        """
        try:
            tool = self.create_tool()
            result = tool.invoke(*args, **kwargs)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
