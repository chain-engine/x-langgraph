# -*- coding: utf-8 -*-
"""
安全模块

提供 API Key 认证和速率限制功能
"""

import time
from typing import Optional

from fastapi import Request, HTTPException

from core.config import settings
from core.logger import logger


_rate_limit_store: dict[str, dict[str, float]] = {}


async def verify_api_key(request: Request) -> Optional[str]:
    """
    API Key 认证依赖

    检查请求头中的 X-API-Key 是否有效

    Args:
        request: FastAPI 请求对象

    Returns:
        有效的 API Key（如果配置了）

    Raises:
        HTTPException: 当 API Key 无效时返回 401
    """
    api_key = request.headers.get("X-API-Key")

    if settings.API_KEY and api_key != settings.API_KEY:
        logger.warning(f"Invalid API Key from {request.client.host}")
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )
    return api_key


async def rate_limit(request: Request) -> None:
    """
    速率限制依赖

    限制每个 IP 每分钟最多 60 次请求

    Args:
        request: FastAPI 请求对象

    Raises:
        HTTPException: 当超过速率限制时返回 429
    """
    client_ip = request.client.host

    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = {"count": 0.0, "window_start": 0.0}

    now = time.time()
    window = 60

    if now - _rate_limit_store[client_ip]["window_start"] > window:
        _rate_limit_store[client_ip] = {"count": 1.0, "window_start": now}
    else:
        _rate_limit_store[client_ip]["count"] += 1
        if _rate_limit_store[client_ip]["count"] > 60:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )