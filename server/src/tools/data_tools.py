# -*- coding: utf-8 -*-
"""
数据处理工具模块

提供 CSV 和 JSON 数据处理功能。
"""

import json
from io import StringIO
from typing import Any, Optional

from langchain_core.tools import tool
from core.logger import logger


@tool
def csv_processor_tool(
    data: str,
    operation: str,
    column: Optional[str] = None,
    value: Optional[str] = None,
) -> str:
    """
    CSV 数据处理工具，支持读取、过滤、统计等操作。

    Args:
        data: CSV 格式的数据字符串
        operation: 操作类型，支持 'read', 'filter', 'stats', 'columns'
        column: 列名（用于 filter 和 stats 操作）
        value: 过滤值（用于 filter 操作）

    Returns:
        处理结果
    """
    logger.info(f"执行 CSV 处理: operation={operation}")

    try:
        import csv

        # 解析 CSV
        reader = csv.DictReader(StringIO(data))
        rows = list(reader)

        if not rows:
            return "CSV 数据为空或格式错误"

        match operation:
            case "read":
                # 读取并格式化输出
                result = f"共 {len(rows)} 行数据:\n"
                for i, row in enumerate(rows[:10]):  # 最多显示 10 行
                    result += f"{i + 1}. {row}\n"
                if len(rows) > 10:
                    result += f"... 还有 {len(rows) - 10} 行"
                return result

            case "columns":
                # 列出所有列名
                return f"列名: {list(rows[0].keys())}"

            case "filter":
                # 按列值过滤
                if not column or not value:
                    return "filter 操作需要指定 column 和 value 参数"

                filtered = [r for r in rows if r.get(column) == value]
                return f"找到 {len(filtered)} 条匹配记录:\n" + "\n".join(
                    str(r) for r in filtered[:5]
                )

            case "stats":
                # 统计信息
                if not column:
                    return "stats 操作需要指定 column 参数"

                values = [r.get(column) for r in rows if r.get(column)]
                if not values:
                    return f"列 '{column}' 没有数据"

                # 尝试数值统计
                try:
                    num_values = [float(v) for v in values]
                    return (
                        f"列 '{column}' 统计:\n"
                        f"- 数量: {len(num_values)}\n"
                        f"- 总和: {sum(num_values):.2f}\n"
                        f"- 平均: {sum(num_values) / len(num_values):.2f}\n"
                        f"- 最大: {max(num_values):.2f}\n"
                        f"- 最小: {min(num_values):.2f}"
                    )
                except ValueError:
                    # 非数值，统计唯一值
                    unique = set(values)
                    return f"列 '{column}' 统计:\n- 唯一值数量: {len(unique)}\n- 唯一值: {list(unique)[:10]}"

            case _:
                return f"不支持的操作: {operation}。支持的操作: read, filter, stats, columns"

    except Exception as e:
        logger.error(f"CSV 处理错误: {e}")
        return f"处理错误: {str(e)}"


@tool
def json_processor_tool(
    data: str,
    operation: str,
    path: Optional[str] = None,
    new_value: Optional[str] = None,
) -> str:
    """
    JSON 数据处理工具，支持解析、查询、修改等操作。

    Args:
        data: JSON 格式的数据字符串
        operation: 操作类型，支持 'parse', 'get', 'set', 'keys', 'validate'
        path: JSON 路径（如 'user.name' 或 'items[0].id'）
        new_value: 新值（用于 set 操作）

    Returns:
        处理结果
    """
    logger.info(f"执行 JSON 处理: operation={operation}")

    try:
        match operation:
            case "validate":
                # 验证 JSON 格式
                try:
                    json.loads(data)
                    return "JSON 格式有效"
                except json.JSONDecodeError as e:
                    return f"JSON 格式无效: {str(e)}"

            case "parse":
                # 解析并格式化输出
                parsed = json.loads(data)
                return json.dumps(parsed, indent=2, ensure_ascii=False)

            case "get":
                # 获取指定路径的值
                if not path:
                    return "get 操作需要指定 path 参数"

                parsed = json.loads(data)
                value = _get_json_path(parsed, path)

                if value is None:
                    return f"路径 '{path}' 不存在或值为 null"
                return f"值: {json.dumps(value, ensure_ascii=False)}"

            case "set":
                # 设置指定路径的值
                if not path or new_value is None:
                    return "set 操作需要指定 path 和 new_value 参数"

                parsed = json.loads(data)
                _set_json_path(parsed, path, json.loads(new_value))
                return f"更新后的 JSON:\n{json.dumps(parsed, indent=2, ensure_ascii=False)}"

            case "keys":
                # 列出所有键
                parsed = json.loads(data)

                if path:
                    parsed = _get_json_path(parsed, path)

                if isinstance(parsed, dict):
                    return f"键列表: {list(parsed.keys())}"
                elif isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                    return f"数组元素键: {list(parsed[0].keys())}"
                else:
                    return "该路径不是对象或对象数组"

            case _:
                return f"不支持的操作: {operation}。支持的操作: parse, get, set, keys, validate"

    except json.JSONDecodeError as e:
        return f"JSON 解析错误: {str(e)}"
    except Exception as e:
        logger.error(f"JSON 处理错误: {e}")
        return f"处理错误: {str(e)}"


def _get_json_path(data: Any, path: str) -> Any:
    """根据路径获取 JSON 值"""
    keys = path.replace("]", "").replace("[", ".").split(".")
    result = data

    for key in keys:
        if not key:
            continue
        if isinstance(result, dict):
            result = result.get(key)
        elif isinstance(result, list):
            try:
                result = result[int(key)]
            except (IndexError, ValueError):
                return None
        else:
            return None

    return result


def _set_json_path(data: Any, path: str, value: Any) -> None:
    """根据路径设置 JSON 值"""
    keys = path.replace("]", "").replace("[", ".").split(".")
    keys = [k for k in keys if k]
    result = data

    for i, key in enumerate(keys[:-1]):
        if isinstance(result, dict):
            result = result.setdefault(key, {})
        elif isinstance(result, list):
            result = result[int(key)]

    last_key = keys[-1]
    if isinstance(result, dict):
        result[last_key] = value
    elif isinstance(result, list):
        result[int(last_key)] = value
