# -*- coding: utf-8 -*-
"""
数据访问层

封装业务 CRUD、多表联查、分页、条件查询。
依赖 infra 获取数据库会话，infra 永不反向依赖 repository/service/api。
"""

from .workflow_repository import WorkflowRepository

__all__ = [
    "WorkflowRepository",
]
