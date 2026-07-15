# -*- coding: utf-8 -*-
"""
工作流基类模块

定义工作流的基础抽象类，提供通用的同步/异步方法。
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from langgraph.graph import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from core.logger import logger


class BaseWorkflow(ABC):
    """
    工作流基类

    所有工作流都需要继承此类并实现 build 方法。

    Features:
    - 懒加载图编译
    - 同步/异步执行支持
    - 流式执行支持
    - 状态管理
    """

    name: str = ""
    description: str = ""

    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        """
        初始化工作流

        Args:
            checkpointer: Checkpointer（检查点器），用于持久化工作流状态
        """
        self.checkpointer = checkpointer
        self._graph = None

    @abstractmethod
    def build(self) -> Any:
        """
        构建工作流图（子类必须实现）

        Returns:
            编译后的 StateGraph
        """
        pass

    @property
    def graph(self) -> Any:
        """获取编译后的工作流图（懒加载）"""
        if self._graph is None:
            self._graph = self.build()
            logger.info(f"工作流 [{self.name}] 编译完成")
        return self._graph

    # ========== 同步方法 ==========

    def invoke(self, inputs: dict, config: dict | None = None) -> dict:
        """
        同步执行工作流

        Args:
            inputs: 输入数据
            config: 配置（如 thread_id）

        Returns:
            执行结果
        """
        logger.info(f"[{self.name}] 同步执行")
        return self.graph.invoke(inputs, config=config or {})

    def stream(
        self,
        inputs: dict,
        config: dict | None = None,
        stream_mode: str = "updates"
    ) -> Any:
        """
        同步流式执行工作流

        Args:
            inputs: 输入数据
            config: 配置（如 thread_id）
            stream_mode: 流式模式，'updates' 或 'values'

        Yields:
            每个步骤的更新
        """
        logger.info(f"[{self.name}] 同步流式执行")
        yield from self.graph.stream(
            inputs,
            config=config or {},
            stream_mode=stream_mode
        )

    def get_state(self, config: dict) -> Any:
        """获取当前状态"""
        return self.graph.get_state(config)

    def update_state(self, config: dict, values: dict) -> Any:
        """更新状态"""
        logger.info(f"[{self.name}] 更新状态")
        return self.graph.update_state(config, values)

    # ========== 异步方法 ==========

    async def ainvoke(self, inputs: dict, config: dict | None = None) -> dict:
        """
        异步执行工作流

        Args:
            inputs: 输入数据
            config: 配置（如 thread_id）

        Returns:
            执行结果
        """
        logger.info(f"[{self.name}] 异步执行")
        return await self.graph.ainvoke(inputs, config=config or {})

    async def astream(
        self,
        inputs: dict,
        config: dict | None = None,
        stream_mode: str = "updates"
    ) -> AsyncGenerator[Any, None]:
        """
        异步流式执行工作流

        Args:
            inputs: 输入数据
            config: 配置（如 thread_id）
            stream_mode: 流式模式

        Yields:
            每个步骤的更新
        """
        logger.info(f"[{self.name}] 异步流式执行")
        async for event in self.graph.astream(
            inputs,
            config=config or {},
            stream_mode=stream_mode
        ):
            yield event

    async def aget_state(self, config: dict) -> Any:
        """异步获取当前状态"""
        return await self.graph.aget_state(config)

    async def aupdate_state(self, config: dict, values: dict) -> Any:
        """异步更新状态"""
        logger.info(f"[{self.name}] 异步更新状态")
        return await self.graph.aupdate_state(config, values)

    # ========== 辅助方法 ==========

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"

    def to_dict(self) -> dict:
        """导出工作流信息"""
        return {
            "name": self.name,
            "description": self.description,
            "has_checkpointer": self.checkpointer is not None,
        }
