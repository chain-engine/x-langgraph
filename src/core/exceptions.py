# -*- coding: utf-8 -*-
"""
全局异常定义
"""

from typing import Any, Optional


class BaseException(Exception):
    """基础异常类"""

    def __init__(
        self,
        message: str = "Unknown error",
        code: int = 500,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail or {}


class BusinessError(BaseException):
    """业务逻辑错误"""

    def __init__(
        self,
        message: str = "Business error",
        code: int = 400,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class ValidationError(BaseException):
    """参数校验错误"""

    def __init__(
        self,
        message: str = "Validation failed",
        code: int = 400,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class NotFoundError(BaseException):
    """资源未找到"""

    def __init__(
        self,
        message: str = "Not found",
        code: int = 404,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class UnauthorizedError(BaseException):
    """未授权"""

    def __init__(
        self,
        message: str = "Unauthorized",
        code: int = 401,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class ForbiddenError(BaseException):
    """禁止访问"""

    def __init__(
        self,
        message: str = "Forbidden",
        code: int = 403,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class ConflictError(BaseException):
    """资源冲突"""

    def __init__(
        self,
        message: str = "Conflict",
        code: int = 409,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class RateLimitError(BaseException):
    """限流错误"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: int = 429,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class SystemError(BaseException):
    """系统错误"""

    def __init__(
        self,
        message: str = "System error",
        code: int = 500,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class DatabaseError(BaseException):
    """数据库错误"""

    def __init__(
        self,
        message: str = "Database error",
        code: int = 500,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class ExternalServiceError(BaseException):
    """外部服务错误"""

    def __init__(
        self,
        message: str = "External service error",
        code: int = 503,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)


class ConfigurationError(BaseException):
    """配置错误"""

    def __init__(
        self,
        message: str = "Configuration error",
        code: int = 500,
        detail: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, code, detail)
