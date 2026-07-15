# -*- coding: utf-8 -*-
"""
Redis 基础设施层

封装 Redis 客户端初始化、序列化、连接复用管理。
"""

import json
from typing import Any, Optional, TYPE_CHECKING

from core.config import settings
from core.logger import logger
from core.exceptions import ConfigurationError

if TYPE_CHECKING:
    from redis import Redis

try:
    import redis
except ImportError:
    redis = None


class RedisClient:
    """
    Redis 客户端封装

    提供 Redis 连接管理、序列化和常用操作。
    """

    def __init__(self):
        """初始化 Redis 客户端"""
        self._client = None
        self._initialized = False

    def initialize(self):
        """初始化 Redis 连接"""
        if self._initialized:
            return

        if redis is None:
            logger.warning("Redis 模块未安装，跳过初始化")
            return

        try:
            redis_url = settings.get_redis_url()
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=20,
            )

            self._initialized = True
            logger.info("Redis client initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}")

    def get_client(self) -> "Redis":
        """
        获取 Redis 客户端实例

        Returns:
            redis.Redis: Redis 客户端实例
        """
        if not self._initialized:
            self.initialize()
        if not self._client:
            raise ConfigurationError(message="Redis client not initialized")
        return self._client

    def get(self, key: str) -> Optional[str]:
        """
        获取键值

        Args:
            key: 键名

        Returns:
            Optional[str]: 值，如果键不存在返回 None
        """
        if redis is None:
            return None
        try:
            return self.get_client().get(key)
        except Exception as e:
            logger.error(f"Redis get failed: {e}", exc_info=True)
            return None

    def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """
        设置键值

        Args:
            key: 键名
            value: 值
            expire: 过期时间（秒）

        Returns:
            bool: 是否成功
        """
        if redis is None:
            return False
        try:
            client = self.get_client()
            if expire:
                return client.set(key, value, ex=expire)
            return client.set(key, value)
        except Exception as e:
            logger.error(f"Redis set failed: {e}", exc_info=True)
            return False

    def get_json(self, key: str) -> Optional[dict]:
        """
        获取 JSON 格式的键值

        Args:
            key: 键名

        Returns:
            Optional[dict]: JSON 对象，如果键不存在返回 None
        """
        if redis is None:
            return None
        try:
            value = self.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get_json failed: {e}", exc_info=True)
            return None

    def set_json(self, key: str, value: dict, expire: Optional[int] = None) -> bool:
        """
        设置 JSON 格式的键值

        Args:
            key: 键名
            value: JSON 对象
            expire: 过期时间（秒）

        Returns:
            bool: 是否成功
        """
        if redis is None:
            return False
        try:
            json_value = json.dumps(value)
            return self.set(key, json_value, expire)
        except Exception as e:
            logger.error(f"Redis set_json failed: {e}", exc_info=True)
            return False

    def delete(self, key: str) -> bool:
        """
        删除键

        Args:
            key: 键名

        Returns:
            bool: 是否成功
        """
        if redis is None:
            return False
        try:
            return self.get_client().delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete failed: {e}", exc_info=True)
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            bool: 是否存在
        """
        if redis is None:
            return False
        try:
            return self.get_client().exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists failed: {e}", exc_info=True)
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        递增键值

        Args:
            key: 键名
            amount: 增量

        Returns:
            Optional[int]: 递增后的值
        """
        if redis is None:
            return None
        try:
            return self.get_client().incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment failed: {e}", exc_info=True)
            return None

    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        递减键值

        Args:
            key: 键名
            amount: 减量

        Returns:
            Optional[int]: 递减后的值
        """
        if redis is None:
            return None
        try:
            return self.get_client().decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis decrement failed: {e}", exc_info=True)
            return None

    def ping(self) -> bool:
        """
        检查 Redis 连接是否可用

        Returns:
            bool: 连接是否可用
        """
        if redis is None:
            return False
        try:
            return self.get_client().ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}", exc_info=True)
            return False

    def dispose(self):
        """释放 Redis 连接资源"""
        if self._client:
            self._client.close()
        self._initialized = False
        logger.info("Redis client disposed")


redis_client = RedisClient()
