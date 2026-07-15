# -*- coding: utf-8 -*-
"""
ORM 基类

定义所有 ORM 模型的公共字段和方法。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """
    ORM 基类

    提供公共字段：
    - id: 主键
    - created_at: 创建时间
    - updated_at: 更新时间
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
