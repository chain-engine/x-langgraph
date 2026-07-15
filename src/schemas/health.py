# -*- coding: utf-8 -*-
"""
健康检查接口数据模型
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
