# -*- coding: utf-8 -*-
"""
MySQL 数据库基础设施层

封装 MySQL 引擎、连接池、会话工厂、连接自动释放、通用事务封装。
"""

from typing import Any, Callable, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from core.config import settings
from core.logger import logger
from core.exceptions import DatabaseError


class MySQLSessionFactory:
    """
    MySQL 会话工厂

    负责创建和管理数据库会话，提供连接池配置和事务管理。
    """

    def __init__(self):
        """初始化会话工厂"""
        self._engine = None
        self._async_engine = None
        self._session_maker = None
        self._async_session_maker = None
        self._initialized = False

    def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return

        try:
            db_url = settings.get_db_url()
            checkpoint_db_url = settings.get_checkpoint_db_url()

            self._engine = create_engine(
                db_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=settings.DEBUG,
            )

            self._async_engine = create_async_engine(
                checkpoint_db_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=settings.DEBUG,
            )

            self._session_maker = sessionmaker(
                bind=self._engine,
                class_=Session,
                autoflush=False,
                autocommit=False,
            )

            self._async_session_maker = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                autoflush=False,
                autocommit=False,
            )

            self._initialized = True
            logger.info("MySQL session factory initialized")

        except Exception as e:
            logger.error(f"Failed to initialize MySQL session factory: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    def get_session(self) -> Session:
        """
        获取同步数据库会话

        Returns:
            Session: SQLAlchemy 同步会话实例
        """
        if not self._initialized:
            self.initialize()
        return self._session_maker()

    async def get_async_session(self) -> AsyncSession:
        """
        获取异步数据库会话

        Returns:
            AsyncSession: SQLAlchemy 异步会话实例
        """
        if not self._initialized:
            self.initialize()
        return self._async_session_maker()

    def execute(self, func: Callable[[Session], Any]) -> Any:
        """
        执行同步数据库操作

        Args:
            func: 数据库操作函数，接收 Session 作为参数

        Returns:
            Any: 操作结果
        """
        session = self.get_session()
        try:
            return func(session)
        finally:
            session.close()

    async def execute_async(self, func: Callable[[AsyncSession], Any]) -> Any:
        """
        执行异步数据库操作

        Args:
            func: 数据库操作函数，接收 AsyncSession 作为参数

        Returns:
            Any: 操作结果
        """
        session = await self.get_async_session()
        try:
            return await func(session)
        finally:
            await session.close()

    def transaction(self, func: Callable[[Session], Any]) -> Any:
        """
        在事务中执行同步数据库操作

        Args:
            func: 数据库操作函数，接收 Session 作为参数

        Returns:
            Any: 操作结果
        """
        session = self.get_session()
        try:
            result = func(session)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed: {e}", exc_info=True)
            raise DatabaseError(message=str(e))
        finally:
            session.close()

    async def transaction_async(self, func: Callable[[AsyncSession], Any]) -> Any:
        """
        在事务中执行异步数据库操作

        Args:
            func: 数据库操作函数，接收 AsyncSession 作为参数

        Returns:
            Any: 操作结果
        """
        session = await self.get_async_session()
        try:
            result = await func(session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction failed: {e}", exc_info=True)
            raise DatabaseError(message=str(e))
        finally:
            await session.close()

    async def ping(self) -> bool:
        """
        检查数据库连接是否可用

        Returns:
            bool: 连接是否可用
        """
        try:
            session = await self.get_async_session()
            try:
                await session.execute(text("SELECT 1"))
                return True
            finally:
                await session.close()
        except Exception as e:
            logger.error(f"Database ping failed: {e}", exc_info=True)
            return False

    def dispose(self):
        """释放数据库连接资源"""
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            import asyncio
            asyncio.run(self._async_engine.dispose())
        self._initialized = False
        logger.info("MySQL session factory disposed")


session_factory = MySQLSessionFactory()
Base = declarative_base()
