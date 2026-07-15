# -*- coding: utf-8 -*-
"""
通用 HTTP 请求客户端

封装 httpx 客户端，提供统一的 HTTP 请求接口和错误处理。
"""

from typing import Any, Dict, Optional

import httpx

from core.config import settings
from core.logger import logger
from core.exceptions import ExternalServiceError


class HttpClient:
    """
    通用 HTTP 客户端封装

    提供同步和异步 HTTP 请求，支持超时配置和统一错误处理。
    """

    def __init__(self, base_url: str = "", timeout: int = 10):
        """
        初始化 HTTP 客户端

        Args:
            base_url: 基础 URL
            timeout: 请求超时时间（秒）
        """
        self._base_url = base_url
        self._timeout = timeout
        self._client = None
        self._async_client = None

    def get_client(self) -> httpx.Client:
        """
        获取同步 HTTP 客户端实例

        Returns:
            httpx.Client: 同步客户端实例
        """
        if not self._client:
            self._client = httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._client

    async def get_async_client(self) -> httpx.AsyncClient:
        """
        获取异步 HTTP 客户端实例

        Returns:
            httpx.AsyncClient: 异步客户端实例
        """
        if not self._async_client:
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._async_client

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 GET 请求

        Args:
            url: 请求 URL
            params: 查询参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = self.get_client()
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP GET error {e.response.status_code}: {e.response.text}")
            raise ExternalServiceError(message=str(e))
        except Exception as e:
            logger.error(f"HTTP GET failed: {e}", exc_info=True)
            raise ExternalServiceError(message=str(e))

    def post(self, url: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 POST 请求

        Args:
            url: 请求 URL
            json: 请求体

        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = self.get_client()
            response = client.post(url, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP POST error {e.response.status_code}: {e.response.text}")
            raise ExternalServiceError(message=str(e))
        except Exception as e:
            logger.error(f"HTTP POST failed: {e}", exc_info=True)
            raise ExternalServiceError(message=str(e))

    async def get_async(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送异步 GET 请求

        Args:
            url: 请求 URL
            params: 查询参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = await self.get_async_client()
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP GET error {e.response.status_code}: {e.response.text}")
            raise ExternalServiceError(message=str(e))
        except Exception as e:
            logger.error(f"HTTP GET failed: {e}", exc_info=True)
            raise ExternalServiceError(message=str(e))

    async def post_async(self, url: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送异步 POST 请求

        Args:
            url: 请求 URL
            json: 请求体

        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = await self.get_async_client()
            response = await client.post(url, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP POST error {e.response.status_code}: {e.response.text}")
            raise ExternalServiceError(message=str(e))
        except Exception as e:
            logger.error(f"HTTP POST failed: {e}", exc_info=True)
            raise ExternalServiceError(message=str(e))

    def dispose(self):
        """释放 HTTP 客户端资源"""
        if self._client:
            self._client.close()
        if self._async_client:
            import asyncio
            asyncio.run(self._async_client.aclose())
        logger.info("HTTP client disposed")


http_client = HttpClient()
