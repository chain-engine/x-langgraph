# -*- coding: utf-8 -*-
"""
LangGraph Checkpointer 模块

Checkpointer（检查点器）是 LangGraph 的核心组件，负责持久化工作流的执行状态。
它允许工作流在执行过程中暂停、恢复，并在不同会话间共享状态。

核心概念：
- 状态持久化：将工作流的每个节点执行状态保存到存储介质（MySQL/内存）
- 会话隔离：通过 thread_id 区分不同会话的状态
- 断点续传：工作流可以暂停后从断点继续执行（如审批流程等待人工干预）
- 状态查询：可以查询历史执行状态和结果

支持的存储方式：
- AsyncMySQLSaver：异步 MySQL 持久化（生产环境）
- MemorySaver：内存存储（开发/测试环境，服务重启后状态丢失）
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

    Checkpointer 作用：在工作流执行过程中自动保存每个节点的状态，
    使得工作流可以暂停后恢复执行，实现人机协同等复杂场景。

    Usage:
        async with get_mysql_checkpointer() as checkpointer:
            # 将 checkpointer 传入工作流，工作流执行时会自动持久化状态
            graph = create_workflow(checkpointer)
            result = await graph.ainvoke(...)

    Yields:
        AsyncMySQLSaver 实例 - 用于持久化工作流状态的检查点器
    """
    if AsyncMySQLSaver is None:
        logger.warning("MySQL Checkpointer 模块未安装，使用 MemorySaver")
        yield MemorySaver()
        return

    connection_string = settings.get_db_url(async_mode=True)
    logger.info(f"连接 Checkpoint 数据库: {settings.database.host}:{settings.database.port}")

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

    connection_string = settings.get_db_url(async_mode=True)
    engine = create_async_engine(connection_string, echo=settings.DEBUG)
    checkpointer = AsyncMySQLSaver(engine)
    await checkpointer.setup()
    return checkpointer


async def create_checkpointer() -> object:
    """
    创建 Checkpointer（自动选择可用的实现）

    Checkpointer 是工作流状态持久化的核心组件，通过 thread_id 实现会话隔离，
    支持断点续传和状态查询。

    Returns:
        Checkpointer 实例 - 优先返回 AsyncMySQLSaver，失败则降级为 MemorySaver
    """
    if AsyncMySQLSaver is None:
        logger.info("使用 MemorySaver（开发模式）")
        return MemorySaver()

    try:
        return await create_mysql_checkpointer()
    except Exception as e:
        logger.warning(f"MySQL Checkpointer 创建失败，使用 MemorySaver: {e}")
        return MemorySaver()
