# -*- coding: utf-8 -*-
"""
聊天服务

处理聊天业务逻辑，包括工作流执行和响应生成
"""

from typing import Any, Optional, AsyncGenerator

from .base import Service
from repositories.workflow_repository import WorkflowRepository
from core.logger import logger
from core.config import settings


class ChatService(Service):
    """聊天服务"""

    def __init__(self, repository: Optional[WorkflowRepository] = None):
        """初始化聊天服务

        Args:
            repository: 工作流仓库实例
        """
        self._repository = repository or WorkflowRepository()
        logger.info("Chat service initialized")

    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """根据ID获取聊天记录

        Args:
            entity_id: 会话ID

        Returns:
            Optional[Any]: 聊天记录或None
        """
        logger.info(f"Get chat by id: {entity_id}")
        return await self._repository.get_state(entity_id)

    async def create(self, data: dict[str, Any]) -> Any:
        """创建聊天

        Args:
            data: 聊天数据

        Returns:
            Any: 聊天响应
        """
        message = data.get("message")
        session_id = data.get("session_id", "default")
        workflow_type = data.get("workflow", "simple_router")

        logger.info(f"Create chat: message={message[:50]}, session_id={session_id}, workflow={workflow_type}")

        result = await self._execute_workflow(workflow_type, message, session_id)

        return {
            "response": result.get("response", ""),
            "session_id": session_id,
            "node": result.get("node"),
        }

    async def update(self, entity_id: str, data: dict[str, Any]) -> Any:
        """更新聊天

        Args:
            entity_id: 会话ID
            data: 更新数据

        Returns:
            Any: 更新后的聊天记录
        """
        data["session_id"] = entity_id
        return await self.create(data)

    async def delete(self, entity_id: str) -> bool:
        """删除聊天

        Args:
            entity_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        logger.info(f"Delete chat: {entity_id}")
        await self._repository.delete_state(entity_id)
        return True

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> dict[str, Any]:
        """查询所有聊天

        Args:
            page: 页码
            page_size: 每页记录数
            filters: 过滤条件
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            dict[str, Any]: 分页数据
        """
        offset = (page - 1) * page_size
        data = await self._repository.list_states(limit=page_size, offset=offset)
        return {"data": data, "total": len(data), "page": page, "page_size": page_size}

    async def _execute_workflow(self, workflow_type: str, message: str, session_id: str) -> dict[str, Any]:
        """
        执行工作流

        Args:
            workflow_type: 工作流类型
            message: 用户消息
            session_id: 会话ID

        Returns:
            dict: 工作流执行结果
        """
        try:
            if workflow_type == "simple_router":
                from workflows.simple_router import run_simple_router
                result = await run_simple_router(message)
            elif workflow_type == "customer_service":
                from workflows.customer_service import run_customer_service
                result = await run_customer_service(message, session_id)
            elif workflow_type == "rag_qa":
                from workflows.rag_qa import run_rag_qa
                result = await run_rag_qa(message)
            elif workflow_type == "multi_agent":
                from workflows.multi_agent import run_multi_agent
                result = await run_multi_agent(message)
            elif workflow_type == "approval":
                from workflows.approval import run_approval_workflow
                result = await run_approval_workflow(message, session_id)
            else:
                from workflows.simple_router import run_simple_router
                result = await run_simple_router(message)

            return result
        except ImportError as e:
            logger.error(f"Workflow import error: {e}")
            return {"response": "工作流加载失败", "node": None}
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {"response": "工作流执行失败", "node": None}

    async def stream(self, workflow_type: str, message: str, session_id: str) -> AsyncGenerator[dict, None]:
        """
        流式执行工作流

        Args:
            workflow_type: 工作流类型
            message: 用户消息
            session_id: 会话ID

        Yields:
            dict: 流式事件
        """
        try:
            if workflow_type == "simple_router":
                from workflows.simple_router.base import SimpleRouterWorkflow
                workflow = SimpleRouterWorkflow()
                async for event in workflow.astream(message, session_id):
                    yield event
            elif workflow_type == "customer_service":
                from workflows.customer_service.base import CustomerServiceWorkflow
                workflow = CustomerServiceWorkflow()
                async for event in workflow.astream(message, session_id):
                    yield event
            else:
                from workflows.simple_router.base import SimpleRouterWorkflow
                workflow = SimpleRouterWorkflow()
                async for event in workflow.astream(message, session_id):
                    yield event
        except Exception as e:
            logger.error(f"Stream workflow execution error: {e}")
            yield {"event": "error", "data": str(e)}
