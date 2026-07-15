# -*- coding: utf-8 -*-
"""
LangGraph Checkpointer 模块

提供 LangGraph 状态持久化功能，支持 MySQL 数据库。
"""

from contextlib import asynccontextmanager
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings
from core.logger import logger

try:
    from langgraph.checkpoint.mysql.aio import AsyncMySQLSaver
except ImportError:
    AsyncMySQLSaver = None


@asynccontextmanager
async def get_mysql_checkpointer():
    """
    获取 MySQL Checkpointer（异步上下文管理器）

    Usage:
        async with get_mysql_checkpointer() as checkpointer:
            graph = create_workflow(checkpointer)
            result = await graph.ainvoke(...)

    Yields:
        AsyncMySQLSaver 实例
    """
    if AsyncMySQLSaver is None:
        logger.warning("MySQL Checkpointer 模块未安装，使用 MemorySaver")
        yield MemorySaver()
        return

    connection_string = settings.get_checkpoint_db_url()
    logger.info(f"连接 Checkpoint 数据库: {settings.CHECKPOINT_DB_HOST}:{settings.CHECKPOINT_DB_PORT}")

    engine = create_async_engine(connection_string, echo=settings.DEBUG)

    async with AsyncMySQLSaver(engine) as checkpointer:
        await checkpointer.setup()
        logger.info("MySQL Checkpoint 表初始化完成")
        yield checkpointer


async def create_mysql_checkpointer() -> Optional[object]:
    """
    创建 MySQL Checkpointer（非上下文管理器方式）

    注意：使用此方式需要手动管理连接生命周期

    Returns:
        AsyncMySQLSaver 实例或 MemorySaver（降级）
    """
    if AsyncMySQLSaver is None:
        logger.warning("MySQL Checkpointer 模块未安装，使用 MemorySaver")
        return MemorySaver()

    connection_string = settings.get_checkpoint_db_url()
    engine = create_async_engine(connection_string, echo=settings.DEBUG)
    checkpointer = AsyncMySQLSaver(engine)
    await checkpointer.setup()
    return checkpointer


async def create_checkpointer() -> object:
    """
    创建 Checkpointer（自动选择可用的实现）

    Returns:
        Checkpointer 实例
    """
    if AsyncMySQLSaver is None:
        logger.info("使用 MemorySaver（开发模式）")
        return MemorySaver()

    try:
        return await create_mysql_checkpointer()
    except Exception as e:
        logger.warning(f"MySQL Checkpointer 创建失败，使用 MemorySaver: {e}")
        return MemorySaver()
