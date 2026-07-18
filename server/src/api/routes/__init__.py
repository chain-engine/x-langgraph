# -*- coding: utf-8 -*-
"""
API 路由模块
"""

from .chats import router as chats_router
from .approval import router as approval_router
from .health import router as health_router
from .metrics import router as metrics_router

__all__ = [
    "chats_router",
    "approval_router",
    "health_router",
    "metrics_router",
]
