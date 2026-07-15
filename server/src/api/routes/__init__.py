# -*- coding: utf-8 -*-
"""
API 路由模块
"""

from .chat import router as chat_router
from .approval import router as approval_router
from .health import router as health_router
from .metrics import router as metrics_router

__all__ = [
    "chat_router",
    "approval_router",
    "health_router",
    "metrics_router",
]
