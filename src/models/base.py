# -*- coding: utf-8 -*-
"""
数据模型基类
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


class BaseEntity(BaseModel):
    """实体基类"""

    id: str = Field(default_factory=lambda: str(uuid4()), description="实体ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    model_config = {
        "from_attributes": True,
    }

    def model_post_init(self, __context: Any) -> None:
        """模型初始化后处理"""
        if not self.updated_at:
            self.updated_at = datetime.utcnow()


class TimestampMixin:
    """时间戳Mixin"""

    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    def update_timestamp(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.utcnow()


class SoftDeleteMixin:
    """软删除Mixin"""

    is_deleted: bool = Field(default=False, description="是否删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")
    deleted_by: Optional[str] = Field(default=None, description="删除人ID")

    def soft_delete(self, deleted_by: Optional[str] = None) -> None:
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by

    def restore(self) -> None:
        """恢复"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None


class Repository(ABC):
    """仓库基类

    定义数据访问层的通用接口
    """

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """根据ID获取实体

        Args:
            entity_id: 实体ID

        Returns:
            Optional[Any]: 实体对象或None
        """
        pass

    @abstractmethod
    async def create(self, entity: Any) -> Any:
        """创建实体

        Args:
            entity: 实体对象

        Returns:
            Any: 创建的实体对象
        """
        pass

    @abstractmethod
    async def update(self, entity: Any) -> Any:
        """更新实体

        Args:
            entity: 实体对象

        Returns:
            Any: 更新后的实体对象
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体

        Args:
            entity_id: 实体ID

        Returns:
            bool: 是否删除成功
        """
        pass

    @abstractmethod
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None
    ) -> tuple[list[Any], int]:
        """查询所有实体

        Args:
            skip: 跳过记录数
            limit: 限制记录数
            filters: 过滤条件

        Returns:
            tuple[list[Any], int]: 实体列表和总数
        """
        pass


class Service(ABC):
    """服务基类

    定义业务逻辑层的通用接口
    """

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """根据ID获取实体

        Args:
            entity_id: 实体ID

        Returns:
            Optional[Any]: 实体对象或None
        """
        pass

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Any:
        """创建实体

        Args:
            data: 实体数据

        Returns:
            Any: 创建的实体对象
        """
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> Any:
        """更新实体

        Args:
            entity_id: 实体ID
            data: 更新数据

        Returns:
            Any: 更新后的实体对象
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体

        Args:
            entity_id: 实体ID

        Returns:
            bool: 是否删除成功
        """
        pass

    @abstractmethod
    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> dict[str, Any]:
        """查询所有实体

        Args:
            page: 页码
            page_size: 每页记录数
            filters: 过滤条件
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            dict[str, Any]: 分页数据
        """
        pass
