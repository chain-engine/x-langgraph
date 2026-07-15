# -*- coding: utf-8 -*-
"""
健康检查接口数据模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")


class HealthCheckItem(BaseModel):
    """健康检查项"""

    name: str = Field(description="检查项名称")
    status: str = Field(description="检查状态")
    provider: Optional[str] = Field(default=None, description="Provider名称")
    error: Optional[str] = Field(default=None, description="错误信息")


class HealthLiveResponse(BaseModel):
    """Liveness 健康检查响应"""

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="Success", description="响应消息")
    data: dict = Field(description="响应数据")


class HealthReadyResponse(BaseModel):
    """Readiness 健康检查响应"""

    status: str = Field(description="服务状态")
    checks: List[HealthCheckItem] = Field(description="检查项列表")
    service: str = Field(description="服务名称")
