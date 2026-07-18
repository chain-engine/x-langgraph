# -*- coding: utf-8 -*-
"""
聊天服务

处理聊天业务逻辑，包括工作流执行和响应生成
"""

import asyncio
import json
from typing import Any, Optional, AsyncGenerator

from .base import Service
from repositories.workflow_repository import WorkflowRepository
from core.logger import logger


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
                from workflows.simple_router.workflow import SimpleRouterWorkflow

                result = await SimpleRouterWorkflow().arun(message, session_id)
            elif workflow_type == "customer_service":
                from workflows.customer_service.workflow import CustomerServiceWorkflow

                result = await CustomerServiceWorkflow().arun(message, session_id)
            elif workflow_type == "rag_qa":
                from workflows.rag_qa import run_rag_qa

                result = await asyncio.to_thread(run_rag_qa, message, session_id)
            elif workflow_type == "multi_agent":
                from workflows.multi_agent import run_multi_agent

                result = await asyncio.to_thread(run_multi_agent, message, session_id)
            elif workflow_type == "approval":
                from workflows.approval.workflow import ApprovalWorkflow

                request = self._build_approval_request(message, session_id)
                result = await ApprovalWorkflow().arun(request, session_id)
            else:
                from workflows.simple_router.workflow import SimpleRouterWorkflow

                result = await SimpleRouterWorkflow().arun(message, session_id)

            return self._normalize_workflow_result(result)
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
            if workflow_type == "customer_service":
                from workflows.customer_service.workflow import CustomerServiceWorkflow

                workflow = CustomerServiceWorkflow()
                event_source = workflow.astream_run(message, session_id)
            else:
                from workflows.simple_router.workflow import SimpleRouterWorkflow

                workflow = SimpleRouterWorkflow()
                event_source = workflow.astream(
                    {"input": message, "route": "", "output": "", "error": None},
                    config={"configurable": {"thread_id": session_id}},
                )

            async for event in event_source:
                async for stream_event in self._iter_stream_events(event):
                    yield stream_event
        except Exception as e:
            logger.error(f"Stream workflow execution error: {e}")
            yield {"event": "error", "data": str(e)}

    @staticmethod
    def _build_approval_request(message: str, session_id: str) -> dict[str, Any]:
        """从聊天消息构建审批请求（支持 JSON 或纯文本）"""
        try:
            parsed = json.loads(message)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        return {
            "request_type": "expense",
            "requester_id": session_id,
            "requester_name": "用户",
            "department": "默认部门",
            "amount": 500.0,
            "description": message,
        }

    @staticmethod
    def _normalize_workflow_result(result: Any) -> dict[str, Any]:
        """将各工作流返回值统一为 ChatService 响应格式"""
        if hasattr(result, "model_dump"):
            data = result.model_dump()
            response = (
                getattr(result, "final_decision", None)
                or getattr(result, "final_output", None)
                or getattr(result, "answer", None)
                or ""
            )
            return {"response": response, "node": None, **data}

        if isinstance(result, dict):
            response = (
                result.get("response")
                or result.get("output")
                or result.get("resolution")
                or result.get("answer")
                or result.get("final_decision")
                or ""
            )
            node = result.get("node") or result.get("route") or result.get("stage")
            return {"response": response, "node": node, **result}

        return {"response": str(result), "node": None}

    @staticmethod
    async def _iter_stream_events(event: Any) -> AsyncGenerator[dict, None]:
        """将 LangGraph 流式更新转换为 SSE 事件格式"""
        if isinstance(event, dict):
            for node_name, node_output in event.items():
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "data": node_output,
                }
