# -*- coding: utf-8 -*-
"""
工具模块

提供各类可复用的工具定义，用于 LangGraph 工作流。

工具分类：
- 搜索工具：网络搜索、文档检索
- 计算工具：数学计算、单位转换
- 天气工具：天气查询
- 数据工具：CSV、JSON 处理
- 数据库工具：Text2SQL、SQL 执行
"""

from tools.base import BaseTool, ToolResult
from tools.search_tools import web_search_tool, document_search_tool
from tools.calculation_tools import calculator_tool, unit_converter_tool
from tools.weather_tool import weather_query_tool
from tools.data_tools import csv_processor_tool, json_processor_tool
from tools.database_tools import (
    text_to_sql_tool,
    execute_sql_tool,
    get_schema_tool,
    DATABASE_TOOLS,
)

__all__ = [
    # 基类
    "BaseTool",
    "ToolResult",
    # 搜索工具
    "web_search_tool",
    "document_search_tool",
    # 计算工具
    "calculator_tool",
    "unit_converter_tool",
    # 天气工具
    "weather_query_tool",
    # 数据工具
    "csv_processor_tool",
    "json_processor_tool",
    # 数据库工具
    "text_to_sql_tool",
    "execute_sql_tool",
    "get_schema_tool",
    "DATABASE_TOOLS",
]
