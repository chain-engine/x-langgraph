# -*- coding: utf-8 -*-
"""
框架级底层核心能力
"""

from .logger import logger
from .config import settings
from .exceptions import (
    BaseException,
    BusinessError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    RateLimitError,
    SystemError,
    DatabaseError,
    ExternalServiceError,
    ConfigurationError,
)
from .container import container, Container
from .middleware import setup_middleware

__all__ = [
    "logger",
    "settings",
    "BaseException",
    "BusinessError",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ConflictError",
    "RateLimitError",
    "SystemError",
    "DatabaseError",
    "ExternalServiceError",
    "ConfigurationError",
    "container",
    "Container",
    "setup_middleware",
]
