# -*- coding: utf-8 -*-
"""
API 路由管理

统一管理所有 API 路由的注册
"""

from fastapi import APIRouter, Depends

from api.routes import chats, approval, health, metrics, workflows
from core.security import verify_api_key, rate_limit


api_router = APIRouter()

api_router.include_router(
    chats.router,
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)
api_router.include_router(
    approval.router,
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)
api_router.include_router(
    workflows.router,
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)
api_router.include_router(health.router)
api_router.include_router(metrics.router)

__all__ = ["api_router"]