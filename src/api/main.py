# -*- coding: utf-8 -*-
"""
FastAPI 应用入口

企业级 LangGraph API 服务

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

或者:
    uv run python -m api.main
"""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.schemas import HealthResponse, ThreadInfo
from api.routes import chat, approval
from config.settings import settings
from core.logger import logger

try:
    from core.checkpointer import create_mysql_checkpointer
except ImportError:
    create_mysql_checkpointer = None


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
    
    try:
        if create_mysql_checkpointer:
            checkpointer = await create_mysql_checkpointer()
            approval.set_checkpointer(checkpointer)
            logger.info("MySQL Checkpointer 初始化成功")
        else:
            logger.warning("MySQL Checkpointer 模块未安装，使用内存存储")
    except Exception as e:
        logger.warning(f"MySQL Checkpointer 初始化失败: {e}")
        logger.info("将使用内存存储（开发模式）")
    
    logger.info("=" * 50)

    yield

    logger.info("LangGraph API 服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="x-langgraph API",
    description="企业级 LangGraph 工作流 API 服务",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    请求 ID 中间件

    为每个请求生成唯一的 request_id 并注入日志上下文
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
    
    return response


@app.middleware("http")
async def error_handler_middleware(request: Request, call_next):
    """
    全局错误处理中间件
    """
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"未处理的异常: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（带认证和速率限制）
app.include_router(
    chat.router,
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)
app.include_router(
    approval.router,
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)


@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """根路径 - 健康检查"""
    return HealthResponse()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """健康检查接口"""
    return HealthResponse()


@app.get("/health/live")
async def health_live() -> dict:
    """
    Liveness 健康检查

    检查服务是否正在运行（不检查依赖）
    """
    return {"status": "ok", "service": "x-langgraph-api"}


@app.get("/health/ready")
async def health_ready() -> dict:
    """
    Readiness 健康检查

    检查服务及其依赖是否就绪
    """
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
    
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "service": "x-langgraph-api"
    }


@app.get("/metrics")
async def metrics() -> str:
    """
    Prometheus 指标端点

    返回服务指标数据
    """
    lines = []
    lines.append("# HELP x_langgraph_requests_total Total requests")
    lines.append(f"# TYPE x_langgraph_requests_total counter")
    lines.append(f"x_langgraph_requests_total {sum(data['count'] for data in _rate_limit_store.values())}")
    
    lines.append("# HELP x_langgraph_active_clients Active clients")
    lines.append("# TYPE x_langgraph_active_clients gauge")
    lines.append(f"x_langgraph_active_clients {len(_rate_limit_store)}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
