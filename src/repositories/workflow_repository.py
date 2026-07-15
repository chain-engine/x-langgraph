# -*- coding: utf-8 -*-
"""
工作流数据访问层

封装工作流状态的 CRUD 操作、多表联查、分页、条件查询。
"""

from typing import Any, Dict, Optional

from sqlalchemy import select, update

from models.workflow import WorkflowInstance, WorkflowNode, WorkflowExecution
from infra.mysql import session_factory
from core.logger import logger
from core.exceptions import DatabaseError, NotFoundError


class WorkflowRepository:
    """
    工作流状态数据访问层

    封装基于 LangGraph Checkpointer 的工作流状态 CRUD 操作。
    """

    def __init__(self, checkpointer: Any = None):
        """
        初始化工作流仓库

        Args:
            checkpointer: LangGraph Checkpointer 实例
        """
        self._checkpointer = checkpointer

    async def get_checkpointer(self) -> Any:
        """
        获取 Checkpointer 实例（延迟初始化）
        """
        if self._checkpointer is None:
            from workflows.checkpointer import create_checkpointer
            self._checkpointer = await create_checkpointer()
        return self._checkpointer

    async def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流状态
        """
        try:
            checkpointer = await self.get_checkpointer()
            
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = await checkpointer.get(config)
            
            if checkpoint is None:
                return None
            
            return {
                "thread_id": thread_id,
                "status": "running",
                "checkpoint": checkpoint,
            }
        except Exception as e:
            logger.error(f"Failed to get workflow state: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def save_state(self, thread_id: str, state: Dict[str, Any]) -> None:
        """
        保存工作流状态

        Args:
            thread_id: 会话 ID
            state: 工作流状态数据
        """
        try:
            checkpointer = await self.get_checkpointer()
            
            config = {"configurable": {"thread_id": thread_id}}
            await checkpointer.put(config, state)
            
            logger.debug(f"Workflow state saved: {thread_id}")
        except Exception as e:
            logger.error(f"Failed to save workflow state: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def delete_state(self, thread_id: str) -> None:
        """
        删除工作流状态

        Args:
            thread_id: 会话 ID
        """
        try:
            checkpointer = await self.get_checkpointer()
            
            config = {"configurable": {"thread_id": thread_id}}
            await checkpointer.delete(config)
            
            logger.debug(f"Workflow state deleted: {thread_id}")
        except Exception as e:
            logger.error(f"Failed to delete workflow state: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def list_states(self, limit: int = 10, offset: int = 0) -> list[Dict[str, Any]]:
        """
        列出工作流状态列表

        Args:
            limit: 每页数量
            offset: 偏移量

        Returns:
            list[Dict[str, Any]]: 工作流状态列表
        """
        try:
            return session_factory.execute(
                lambda session: session.query(WorkflowInstance)
                .order_by(WorkflowInstance.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
        except Exception as e:
            logger.error(f"Failed to list workflow states: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def get_instance(self, thread_id: str) -> Optional[WorkflowInstance]:
        """
        获取工作流实例

        Args:
            thread_id: 会话 ID

        Returns:
            Optional[WorkflowInstance]: 工作流实例
        """
        try:
            result = session_factory.execute(
                lambda session: session.query(WorkflowInstance)
                .filter(WorkflowInstance.thread_id == thread_id)
                .first()
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get workflow instance: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def create_instance(self, workflow_name: str, thread_id: str) -> WorkflowInstance:
        """
        创建工作流实例

        Args:
            workflow_name: 工作流名称
            thread_id: 会话 ID

        Returns:
            WorkflowInstance: 创建的工作流实例
        """
        try:
            instance = WorkflowInstance(
                workflow_name=workflow_name,
                thread_id=thread_id,
                status="running",
            )
            
            result = session_factory.transaction(
                lambda session: session.add(instance) or instance
            )
            
            logger.info(f"Workflow instance created: {thread_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create workflow instance: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def update_instance(self, thread_id: str, **kwargs) -> WorkflowInstance:
        """
        更新工作流实例

        Args:
            thread_id: 会话 ID
            **kwargs: 更新字段

        Returns:
            WorkflowInstance: 更新后的工作流实例
        """
        try:
            instance = await self.get_instance(thread_id)
            if not instance:
                raise NotFoundError(message=f"Workflow instance not found: {thread_id}")
            
            for key, value in kwargs.items():
                setattr(instance, key, value)
            
            result = session_factory.transaction(
                lambda session: session.merge(instance)
            )
            
            logger.debug(f"Workflow instance updated: {thread_id}")
            return result
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update workflow instance: {e}", exc_info=True)
            raise DatabaseError(message=str(e))

    async def delete_instance(self, thread_id: str) -> None:
        """
        删除工作流实例

        Args:
            thread_id: 会话 ID
        """
        try:
            instance = await self.get_instance(thread_id)
            if not instance:
                raise NotFoundError(message=f"Workflow instance not found: {thread_id}")
            
            session_factory.transaction(
                lambda session: session.delete(instance)
            )
            
            logger.info(f"Workflow instance deleted: {thread_id}")
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete workflow instance: {e}", exc_info=True)
            raise DatabaseError(message=str(e))
