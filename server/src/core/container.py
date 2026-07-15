# -*- coding: utf-8 -*-
"""
IOC 依赖注入容器
"""

from typing import Any, Dict, Type, get_type_hints


class Container:
    """
    依赖注入容器

    支持自动解析构造函数依赖
    """

    def __init__(self):
        """初始化容器"""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Type[Any]] = {}

    def register(self, service_class: Type[Any], instance: Any = None):
        """
        注册服务

        Args:
            service_class: 服务类
            instance: 服务实例（可选）
        """
        key = service_class.__name__

        if instance is not None:
            self._services[key] = instance
        else:
            self._factories[key] = service_class

        logger.info(f"Registered service: {key}")

    def resolve(self, service_class: Type[Any]) -> Any:
        """
        解析服务

        Args:
            service_class: 服务类

        Returns:
            服务实例
        """
        key = service_class.__name__

        if key in self._services:
            return self._services[key]

        if key in self._factories:
            instance = self._create_instance(self._factories[key])
            self._services[key] = instance
            return instance

        raise ValueError(f"Service not registered: {key}")

    def _create_instance(self, service_class: Type[Any]) -> Any:
        """
        创建服务实例，自动解析构造函数依赖

        Args:
            service_class: 服务类

        Returns:
            服务实例
        """
        try:
            hints = get_type_hints(service_class.__init__)
            dependencies = {}

            for param_name, param_type in hints.items():
                if param_name == "self":
                    continue
                if param_type in (type(None),):
                    continue

                try:
                    dependencies[param_name] = self.resolve(param_type)
                except ValueError:
                    pass

            return service_class(**dependencies)
        except Exception as e:
            logger.error(f"Failed to create instance for {service_class.__name__}: {e}")
            return service_class()

    def get(self, service_class: Type[Any]) -> Any:
        """
        获取服务（别名）

        Args:
            service_class: 服务类

        Returns:
            服务实例
        """
        return self.resolve(service_class)


from core.logger import logger

container = Container()
