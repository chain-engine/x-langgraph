# -*- coding: utf-8 -*-
"""
中间件模块
"""

import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from core.logger import logger
from core.exceptions import (
    BaseException as CoreBaseException,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    SystemError,
)


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """
    请求 ID 中间件

    为每个请求生成唯一的 request_id 并注入日志上下文
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
    
    response.headers["X-Request-ID"] = request_id
    return response


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    全局错误处理中间件
    """
    try:
        return await call_next(request)
    except CoreBaseException as e:
        request_id = getattr(request.state, "request_id", None)
        logger.error(f"Handled exception: {e.message}", exc_info=True)
        
        return JSONResponse(
            status_code=e.code,
            content={
                "success": False,
                "message": e.message,
                "code": e.code,
                "errors": e.detail,
                "request_id": request_id,
            },
        )
    except Exception as e:
        request_id = getattr(request.state, "request_id", None)
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "code": 500,
                "errors": {"detail": str(e)},
                "request_id": request_id,
            },
        )


async def cors_middleware(request: Request, call_next: Callable) -> Response:
    """
    CORS 中间件
    """
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


def setup_middleware(app):
    """
    配置中间件

    Args:
        app: FastAPI 应用实例
    """
    app.middleware("http")(request_id_middleware)
    app.middleware("http")(error_handler_middleware)
    app.middleware("http")(cors_middleware)
