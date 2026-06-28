# -*- coding: utf-8 -*-
"""
计算工具模块

提供数学计算和单位转换功能。
"""

import re

from langchain_core.tools import tool
from core.logger import logger


@tool
def calculator_tool(expression: str) -> str:
    """
    数学计算器工具，支持基本的数学运算。

    Args:
        expression: 数学表达式，如 "123 + 456" 或 "100 * 5 / 2"

    Returns:
        计算结果
    """
    logger.info(f"执行计算: {expression}")

    try:
        # 安全处理：只保留数字、空格和常见运算符
        safe_expr = re.sub(r"[^0-9+\-*/().% ]", "", expression)

        if not safe_expr.strip():
            return "计算错误: 无效的表达式"

        result = eval(safe_expr)
        return f"计算结果: {result}"

    except ZeroDivisionError:
        return "计算错误: 除数不能为零"
    except SyntaxError:
        return "计算错误: 表达式语法错误"
    except Exception as e:
        logger.error(f"计算错误: {e}")
        return f"计算错误: {str(e)}"


@tool
def unit_converter_tool(value: float, from_unit: str, to_unit: str) -> str:
    """
    单位转换工具，支持长度、重量、温度等常见单位转换。

    Args:
        value: 要转换的数值
        from_unit: 源单位，如 'm', 'kg', 'celsius'
        to_unit: 目标单位，如 'km', 'g', 'fahrenheit'

    Returns:
        转换后的结果
    """
    logger.info(f"执行单位转换: {value} {from_unit} -> {to_unit}")

    # 单位转换表
    conversions = {
        # 长度（以米为基准）
        "length": {
            "m": 1,
            "km": 1000,
            "cm": 0.01,
            "mm": 0.001,
            "mile": 1609.344,
            "ft": 0.3048,
            "inch": 0.0254,
        },
        # 重量（以千克为基准）
        "weight": {
            "kg": 1,
            "g": 0.001,
            "mg": 0.000001,
            "lb": 0.453592,
            "oz": 0.0283495,
        },
    }

    # 温度转换（特殊处理）
    temperature_units = ["celsius", "fahrenheit", "kelvin", "c", "f", "k"]

    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()

    # 温度转换
    if from_unit_lower in temperature_units and to_unit_lower in temperature_units:
        # 先转换为摄氏度
        match from_unit_lower:
            case "fahrenheit" | "f":
                celsius = (value - 32) * 5 / 9
            case "kelvin" | "k":
                celsius = value - 273.15
            case _:
                celsius = value

        # 从摄氏度转换为目标单位
        match to_unit_lower:
            case "fahrenheit" | "f":
                result = celsius * 9 / 5 + 32
            case "kelvin" | "k":
                result = celsius + 273.15
            case _:
                result = celsius

        return f"转换结果: {value} {from_unit} = {result:.2f} {to_unit}"

    # 长度转换
    length_units = conversions["length"]
    if from_unit_lower in length_units and to_unit_lower in length_units:
        base_value = value * length_units[from_unit_lower]
        result = base_value / length_units[to_unit_lower]
        return f"转换结果: {value} {from_unit} = {result:.6f} {to_unit}"

    # 重量转换
    weight_units = conversions["weight"]
    if from_unit_lower in weight_units and to_unit_lower in weight_units:
        base_value = value * weight_units[from_unit_lower]
        result = base_value / weight_units[to_unit_lower]
        return f"转换结果: {value} {from_unit} = {result:.6f} {to_unit}"

    return f"不支持的单位转换: {from_unit} -> {to_unit}"
