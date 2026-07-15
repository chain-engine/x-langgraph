# -*- coding: utf-8 -*-
"""
统一响应封装
"""

from typing import Any, Optional
from datetime import datetime, timezone


def success_response(
    data: Any = None,
    message: str = "Success",
    code: int = 200,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    构造成功响应

    Args:
        data: 响应数据
        message: 响应消息
        code: 响应码
        request_id: 请求ID

    Returns:
        dict: 标准响应格式
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
    }


def error_response(
    message: str = "Error",
    code: int = 500,
    errors: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    构造错误响应

    Args:
        message: 错误消息
        code: 错误码
        errors: 错误详情
        request_id: 请求ID

    Returns:
        dict: 标准错误响应格式
    """
    response = {
        "code": code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
    }

    if errors:
        response["errors"] = errors

    return response
