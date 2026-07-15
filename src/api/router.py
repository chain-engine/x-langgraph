# -*- coding: utf-8 -*-
"""
API 路由管理

统一管理所有 API 路由的注册
"""

from fastapi import APIRouter, Depends

from api.routes import chat, approval, health, metrics


def _verify_api_key_dependency(request):
    """API Key 认证依赖"""
    from main import verify_api_key
    return verify_api_key(request)


def _rate_limit_dependency(request):
    """速率限制依赖"""
    from main import rate_limit
    return rate_limit(request)


api_router = APIRouter()

api_router.include_router(
    chat.router,
    dependencies=[Depends(_verify_api_key_dependency), Depends(_rate_limit_dependency)]
)
api_router.include_router(
    approval.router,
    dependencies=[Depends(_verify_api_key_dependency), Depends(_rate_limit_dependency)]
)
api_router.include_router(health.router)
api_router.include_router(metrics.router)

__all__ = ["api_router"]
