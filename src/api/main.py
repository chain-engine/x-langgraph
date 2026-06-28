# -*- coding: utf-8 -*-
"""
FastAPI 应用入口

企业级 LangGraph API 服务

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

或者:
    uv run python -m api.main
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import HealthResponse
from api.routes import chat, approval
from config.settings import settings
from core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时
    logger.info("=" * 50)
    logger.info("LangGraph API 服务启动")
    logger.info(f"API 地址: http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info("=" * 50)

    yield

    # 关闭时
    logger.info("LangGraph API 服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="x-langgraph API",
    description="企业级 LangGraph 工作流 API 服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(approval.router)


@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """根路径 - 健康检查"""
    return HealthResponse()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """健康检查接口"""
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
