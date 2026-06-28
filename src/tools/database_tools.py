# -*- coding: utf-8 -*-
"""
数据库工具模块

提供 Text2SQL 功能：
- 自然语言转 SQL
- SQL 执行
- 结果格式化
- Schema 查询
"""

import re
import time
from typing import Optional, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from config.settings import settings
from core.logger import logger


class SQLQueryResult(BaseModel):
    """SQL 查询结果"""

    success: bool = Field(..., description="执行是否成功")
    sql: str = Field(default="", description="生成的 SQL")
    data: list[dict] = Field(default_factory=list, description="查询结果")
    row_count: int = Field(default=0, description="返回行数")
    columns: list[str] = Field(default_factory=list, description="列名")
    error: Optional[str] = Field(default=None, description="错误信息")
    execution_time: Optional[float] = Field(default=None, description="执行时间（秒）")


# ===== Text2SQL 工具 =====


@tool
def text_to_sql_tool(
    query: str,
    table_name: Optional[str] = None,
    dialect: str = "mysql",
) -> str:
    """
    自然语言转 SQL 工具。

    将自然语言问题转换为 SQL 查询语句。

    Args:
        query: 自然语言查询描述，如 "查询所有用户" 或 "统计每个部门的员工数量"
        table_name: 目标表名（可选）
        dialect: SQL 方言，支持 mysql, postgresql, sqlite

    Returns:
        SQL 查询语句或错误信息
    """
    logger.info(f"Text2SQL: {query[:50]}...")

    try:
        # 简单的规则转换（实际项目中使用 LLM）
        sql = _convert_to_sql(query, table_name, dialect)
        return f"生成的 SQL:\n```sql\n{sql}\n```"

    except Exception as e:
        logger.error(f"Text2SQL: 转换失败 - {e}")
        return f"转换失败: {str(e)}"


def _convert_to_sql(query: str, table_name: Optional[str], dialect: str) -> str:
    """
    将自然语言转换为 SQL（简单规则实现）

    实际项目中应使用 LLM 进行智能转换

    Args:
        query: 自然语言查询
        table_name: 表名
        dialect: SQL 方言

    Returns:
        SQL 语句
    """
    query_lower = query.lower()

    # 默认表名
    if not table_name:
        table_name = "data_table"

    # 统计类查询
    if any(kw in query_lower for kw in ["统计", "数量", "count", "多少"]):
        if "每个" in query_lower or "各组" in query_lower:
            # 分组统计
            group_match = re.search(r"每个(\w+)", query_lower)
            group_field = group_match.group(1) if group_match else "category"
            return f"SELECT {group_field}, COUNT(*) as count FROM {table_name} GROUP BY {group_field} ORDER BY count DESC"
        else:
            return f"SELECT COUNT(*) as total FROM {table_name}"

    # 求和类查询
    if any(kw in query_lower for kw in ["总计", "总和", "sum", "合计"]):
        sum_match = re.search(r"(\w+)的?总(?:和|计)", query_lower)
        sum_field = sum_match.group(1) if sum_match else "amount"
        return f"SELECT SUM({sum_field}) as total FROM {table_name}"

    # 平均值查询
    if any(kw in query_lower for kw in ["平均", "avg", "均值"]):
        avg_match = re.search(r"(\w+)的?平均", query_lower)
        avg_field = avg_match.group(1) if avg_match else "value"
        return f"SELECT AVG({avg_field}) as average FROM {table_name}"

    # 最大/最小值
    if "最大" in query_lower or "max" in query_lower:
        max_match = re.search(r"(\w+)的?最大", query_lower)
        max_field = max_match.group(1) if max_match else "value"
        return f"SELECT MAX({max_field}) as max_value FROM {table_name}"

    if "最小" in query_lower or "min" in query_lower:
        min_match = re.search(r"(\w+)的?最小", query_lower)
        min_field = min_match.group(1) if min_match else "value"
        return f"SELECT MIN({min_field}) as min_value FROM {table_name}"

    # 排序查询
    if any(kw in query_lower for kw in ["排序", "order", "前几"]):
        order_match = re.search(r"按(\w+)", query_lower)
        order_field = order_match.group(1) if order_match else "id"
        limit_match = re.search(r"前(\d+)", query_lower)
        limit = limit_match.group(1) if limit_match else "10"
        return f"SELECT * FROM {table_name} ORDER BY {order_field} DESC LIMIT {limit}"

    # 条件查询
    if "where" in query_lower or "条件" in query_lower or "筛选" in query_lower:
        return f"SELECT * FROM {table_name} WHERE 1=1 -- 请补充具体条件"

    # 默认：查询所有
    return f"SELECT * FROM {table_name} LIMIT 100"


# ===== SQL 执行工具 =====


@tool
def execute_sql_tool(
    sql: str,
    limit: int = 100,
) -> str:
    """
    执行 SQL 查询工具。

    执行 SELECT 查询并返回结果（仅支持查询，不支持修改）。

    Args:
        sql: SQL 查询语句
        limit: 最大返回行数

    Returns:
        查询结果或错误信息
    """
    logger.info(f"ExecuteSQL: 执行查询 - {sql[:50]}...")

    try:
        # 验证 SQL 安全性
        _validate_sql(sql)

        # 执行查询
        result = _execute_sql(sql, limit)

        return _format_result(result)

    except Exception as e:
        logger.error(f"ExecuteSQL: 执行失败 - {e}")
        return f"执行失败: {str(e)}"


def _validate_sql(sql: str) -> None:
    """
    验证 SQL 安全性

    只允许 SELECT 查询

    Args:
        sql: SQL 语句

    Raises:
        ValueError: SQL 不安全
    """
    sql_upper = sql.upper().strip()

    # 禁止的关键词
    forbidden = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
    ]

    for keyword in forbidden:
        if keyword in sql_upper:
            raise ValueError(f"安全限制: 不允许执行 {keyword} 操作")

    # 必须是 SELECT
    if not sql_upper.startswith("SELECT"):
        raise ValueError("安全限制: 只允许执行 SELECT 查询")


def _execute_sql(sql: str, limit: int) -> SQLQueryResult:
    """
    执行 SQL 查询（模拟）

    实际项目中应连接真实数据库

    Args:
        sql: SQL 语句
        limit: 最大行数

    Returns:
        SQLQueryResult
    """
    start_time = time.time()

    # 模拟数据库连接和查询
    # 实际项目中使用：
    # from sqlalchemy import create_engine, text
    # engine = create_engine(settings.DB_URL)
    # with engine.connect() as conn:
    #     result = conn.execute(text(sql))

    # 模拟数据
    mock_data = [
        {"id": 1, "name": "张三", "department": "技术部", "salary": 15000},
        {"id": 2, "name": "李四", "department": "产品部", "salary": 12000},
        {"id": 3, "name": "王五", "department": "技术部", "salary": 18000},
        {"id": 4, "name": "赵六", "department": "市场部", "salary": 10000},
        {"id": 5, "name": "钱七", "department": "产品部", "salary": 14000},
    ]

    # 模拟查询处理
    columns = list(mock_data[0].keys()) if mock_data else []
    data = mock_data[:limit]

    execution_time = time.time() - start_time

    return SQLQueryResult(
        success=True,
        sql=sql,
        data=data,
        row_count=len(data),
        columns=columns,
        execution_time=execution_time,
    )


def _format_result(result: SQLQueryResult) -> str:
    """
    格式化查询结果

    Args:
        result: 查询结果

    Returns:
        格式化的字符串
    """
    if not result.success:
        return f"查询失败: {result.error}"

    output = []
    output.append(f"执行成功，返回 {result.row_count} 行数据")
    output.append(f"执行时间: {result.execution_time:.3f} 秒")
    output.append("")
    output.append(f"SQL: {result.sql}")
    output.append("")

    if result.data:
        # 格式化表格
        columns = result.columns
        header = " | ".join(columns)
        separator = "-+-".join("-" * len(col) for col in columns)

        output.append(header)
        output.append(separator)

        for row in result.data[:20]:  # 最多显示 20 行
            row_str = " | ".join(str(row.get(col, "")) for col in columns)
            output.append(row_str)

        if result.row_count > 20:
            output.append(f"... 还有 {result.row_count - 20} 行")

    return "\n".join(output)


# ===== Schema 查询工具 =====


@tool
def get_schema_tool(table_name: Optional[str] = None) -> str:
    """
    获取数据库 Schema 工具。

    查询数据库表结构和字段信息。

    Args:
        table_name: 表名（可选，不指定则返回所有表）

    Returns:
        Schema 信息
    """
    logger.info(f"GetSchema: 查询 - {table_name or '所有表'}")

    # 模拟 Schema 数据
    mock_schema = {
        "users": {
            "columns": {
                "id": "INT PRIMARY KEY",
                "name": "VARCHAR(100)",
                "email": "VARCHAR(255)",
                "department": "VARCHAR(50)",
                "created_at": "DATETIME",
            },
            "description": "用户表",
        },
        "orders": {
            "columns": {
                "id": "INT PRIMARY KEY",
                "user_id": "INT",
                "amount": "DECIMAL(10,2)",
                "status": "VARCHAR(20)",
                "created_at": "DATETIME",
            },
            "description": "订单表",
        },
        "products": {
            "columns": {
                "id": "INT PRIMARY KEY",
                "name": "VARCHAR(200)",
                "price": "DECIMAL(10,2)",
                "category": "VARCHAR(50)",
                "stock": "INT",
            },
            "description": "产品表",
        },
    }

    if table_name:
        if table_name in mock_schema:
            table_info = mock_schema[table_name]
            output = [f"表: {table_name}"]
            output.append(f"描述: {table_info['description']}")
            output.append("\n字段:")
            for col, dtype in table_info["columns"].items():
                output.append(f"  - {col}: {dtype}")
            return "\n".join(output)
        else:
            return f"表 {table_name} 不存在"

    else:
        output = ["数据库表列表:"]
        for tname, tinfo in mock_schema.items():
            output.append(f"\n## {tname}")
            output.append(f"描述: {tinfo['description']}")
            output.append(f"字段数: {len(tinfo['columns'])}")
        return "\n".join(output)


# ===== 导出工具列表 =====

DATABASE_TOOLS = [
    text_to_sql_tool,
    execute_sql_tool,
    get_schema_tool,
]
