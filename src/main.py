# -*- coding: utf-8 -*-
"""
应用主入口

企业级 LangGraph 工作流编排框架
"""

import uuid
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logger import logger
from core.middleware import setup_middleware
from core.container import container
from api.router import api_router
from services.chat_service import ChatService
from services.approval_service import ApprovalService
from repositories.workflow_repository import WorkflowRepository


async def verify_api_key(request: Request):
    """
    API Key 认证依赖

    检查请求头中的 X-API-Key 是否有效
    """
    api_key = request.headers.get("X-API-Key")

    if settings.API_KEY and api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )
    return api_key


_rate_limit_store = {}


async def rate_limit(request: Request):
    """
    速率限制依赖

    限制每个 IP 每分钟最多 60 次请求
    """
    client_ip = request.client.host

    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = {"count": 0, "window_start": 0}

    import time
    now = time.time()
    window = 60

    if now - _rate_limit_store[client_ip]["window_start"] > window:
        _rate_limit_store[client_ip] = {"count": 1, "window_start": now}
    else:
        _rate_limit_store[client_ip]["count"] += 1
        if _rate_limit_store[client_ip]["count"] > 60:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )


def register_services():
    """
    注册所有服务到 IOC 容器
    """
    logger.info("Registering services to container...")

    container.register(WorkflowRepository)
    container.register(ChatService)
    container.register(ApprovalService)

    logger.info("Services registered successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    logger.info("=" * 50)
    logger.info("LangGraph API 服务启动")
    logger.info(f"API 地址: http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"API Key 认证: {'启用' if settings.API_KEY else '未启用'}")
    logger.info("=" * 50)

    register_services()

    yield

    logger.info("LangGraph API 服务关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    """
    app = FastAPI(
        title="x-langgraph API",
        description="企业级 LangGraph 工作流 API 服务",
        version="1.0.0",
        lifespan=lifespan,
    )

    setup_middleware(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()


def main() -> None:
    """
    主函数
    """
    logger.info(f"Starting x-langgraph API v1.0.0")
    logger.info(f"Environment: {'development' if settings.DEBUG else 'production'}")
    logger.info(f"Server: {settings.API_HOST}:{settings.API_PORT}")

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD if settings.DEBUG else False,
        log_level="debug" if settings.DEBUG else "info"
    )


if __name__ == "__main__":
    main()
