# -*- coding: utf-8 -*-
"""
Service基类

提供Service层的通用接口定义。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class Service(ABC):
    """
    服务基类

    定义服务层的通用接口。
    """

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """根据ID获取实体"""
        pass

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Any:
        """创建实体"""
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> Any:
        """更新实体"""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> dict[str, Any]:
        """分页查询所有实体"""
        pass
