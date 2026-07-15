# -*- coding: utf-8 -*-
"""
健康检查路由
"""

from fastapi import APIRouter

from core.config import settings
from schemas.health import HealthResponse, HealthLiveResponse, HealthReadyResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """根路径 - 健康检查"""
    return HealthResponse()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """健康检查接口"""
    return HealthResponse()


@router.get("/health/live", response_model=HealthLiveResponse)
async def health_live() -> HealthLiveResponse:
    """Liveness 健康检查"""
    return HealthLiveResponse(
        data={"service": "x-langgraph-api"}
    )


@router.get("/health/ready", response_model=HealthReadyResponse)
async def health_ready() -> HealthReadyResponse:
    """Readiness 健康检查"""
    checks = []

    try:
        from core.checkpointer import get_mysql_connection_string
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        connection_string = get_mysql_connection_string()
        engine = create_async_engine(connection_string)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks.append({"name": "mysql", "status": "ok"})
    except Exception as e:
        checks.append({"name": "mysql", "status": "failed", "error": str(e)})

    try:
        from llm.providers import get_llm_provider

        provider = get_llm_provider(settings.get_available_provider())
        checks.append({"name": "llm_provider", "status": "ok", "provider": provider.name})
    except Exception as e:
        checks.append({"name": "llm_provider", "status": "failed", "error": str(e)})

    all_ok = all(check["status"] == "ok" for check in checks)

    return HealthReadyResponse(
        status="ok" if all_ok else "degraded",
        checks=checks,
        service="x-langgraph-api"
    )
