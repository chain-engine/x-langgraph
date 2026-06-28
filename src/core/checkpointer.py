# -*- coding: utf-8 -*-
"""
MySQL Checkpointer 模块

提供 LangGraph 状态持久化功能，支持 MySQL 数据库。
"""

from contextlib import asynccontextmanager

from langgraph.checkpoint.mysql.aio import AsyncMySQLSaver
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import settings
from core.logger import logger


def get_mysql_connection_string() -> str:
    """
    获取 MySQL 连接字符串

    Returns:
        MySQL 连接字符串（asyncmy 驱动）
    """
    return (
        f"mysql+asyncmy://{settings.CHECKPOINT_DB_USER}:"
        f"{settings.CHECKPOINT_DB_PASSWORD}@"
        f"{settings.CHECKPOINT_DB_HOST}:"
        f"{settings.CHECKPOINT_DB_PORT}/"
        f"{settings.CHECKPOINT_DB_NAME}"
    )


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
    connection_string = get_mysql_connection_string()
    logger.info(f"连接 Checkpoint 数据库: {settings.CHECKPOINT_DB_HOST}:{settings.CHECKPOINT_DB_PORT}")

    engine = create_async_engine(connection_string, echo=settings.DEBUG)

    async with AsyncMySQLSaver(engine) as checkpointer:
        await checkpointer.setup()
        logger.info("MySQL Checkpoint 表初始化完成")
        yield checkpointer


async def create_mysql_checkpointer() -> AsyncMySQLSaver:
    """
    创建 MySQL Checkpointer（非上下文管理器方式）

    注意：使用此方式需要手动管理连接生命周期

    Returns:
        AsyncMySQLSaver 实例
    """
    connection_string = get_mysql_connection_string()
    engine = create_async_engine(connection_string, echo=settings.DEBUG)
    checkpointer = AsyncMySQLSaver(engine)
    await checkpointer.setup()
    return checkpointer
