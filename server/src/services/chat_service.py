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
from repositories.workflow_definition_repository import WorkflowDefinitionRepository
from workflows.compiler import compile_workflow
from core.logger import logger


class ChatService(Service):
    """聊天服务"""

    def __init__(self, repository: Optional[WorkflowRepository] = None):
        """初始化聊天服务

        Args:
            repository: 工作流仓库实例
        """
        self._repository = repository or WorkflowRepository()
        self._definition_repo = WorkflowDefinitionRepository()
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
        workflow = data.get("workflow", "simple_router")

        logger.info(f"Create chat: message={message[:50]}, session_id={session_id}, workflow={workflow}")

        result = await self._execute_workflow(workflow, message, session_id)

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

    async def _execute_workflow(self, workflow_name: str, message: str, session_id: str) -> dict[str, Any]:
        """
        执行工作流

        Args:
            workflow_name: 工作流类型
            message: 用户消息
            session_id: 会话ID

        Returns:
            dict: 工作流执行结果
        """
        try:
            # 静态预定义工作流（硬编码路径）
            if workflow_name == "simple_router":
                from workflows.simple_router.workflow import IntentClassifierWorkflow

                result = await IntentClassifierWorkflow().arun(message, session_id)
            elif workflow_name == "customer_service":
                from workflows.customer_service.workflow import CustomerServiceWorkflow

                result = await CustomerServiceWorkflow().arun(message, session_id)
            elif workflow_name == "rag_qa":
                from workflows.rag_qa import run_rag_qa

                result = await asyncio.to_thread(run_rag_qa, message, session_id)
            elif workflow_name == "multi_agent":
                from workflows.multi_agent import run_multi_agent

                result = await asyncio.to_thread(run_multi_agent, message, session_id)
            elif workflow_name == "approval":
                from workflows.approval.workflow import ApprovalWorkflow

                request = self._build_approval_request(message, session_id)
                result = await ApprovalWorkflow().arun(request, session_id)
            else:
                # 动态路径：从 DB 查询工作流定义，通过 compiler 编译执行
                definition = await self._definition_repo.get_by_name(workflow_name)
                if definition is not None:
                    result = await self._execute_dynamic_workflow(definition, message, session_id)
                else:
                    # fallback：使用默认工作流
                    logger.warning(f"Unknown workflow '{workflow_name}', falling back to simple_router")
                    from workflows.simple_router.workflow import SimpleRouterWorkflow

                    result = await SimpleRouterWorkflow().arun(message, session_id)

            return self._normalize_workflow_result(result)
        except ImportError as e:
            logger.error(f"Workflow import error: {e}")
            return {"response": "工作流加载失败", "node": None}
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {"response": "工作流执行失败", "node": None}

    async def _execute_dynamic_workflow(
        self, definition: dict[str, Any], message: str, session_id: str
    ) -> dict[str, Any]:
        """执行动态编译的工作流（来自 DB 定义）"""
        state_schema = definition.get("state_schema", {})
        state: dict[str, Any] = {}
        for field_name, field_type in state_schema.items():
            if field_name in ("input", "message"):
                state[field_name] = message
            elif field_type == "str" or field_type == "string":
                state[field_name] = ""
            elif field_type == "list":
                state[field_name] = []
            else:
                state[field_name] = None

        graph = compile_workflow(definition)
        result = await graph.ainvoke(
            state,
            config={"configurable": {"thread_id": session_id}},
        )
        return result

    async def stream(self, workflow_name: str, message: str, session_id: str) -> AsyncGenerator[dict, None]:
        """
        流式执行工作流

        Args:
            workflow_name: 工作流类型
            message: 用户消息
            session_id: 会话ID

        Yields:
            dict: 流式事件
        """
        try:
            # 静态预定义工作流（硬编码路径）
            if workflow_name == "customer_service":
                from workflows.customer_service.workflow import CustomerServiceWorkflow

                workflow = CustomerServiceWorkflow()
                event_source = workflow.astream_run(message, session_id)
            else:
                # 先查 DB，看是否为自定义工作流
                definition = await self._definition_repo.get_by_name(workflow_name)
                if definition is not None:
                    async for event in self._stream_dynamic_workflow(definition, message, session_id):
                        yield event
                    return

                # fallback 到 simple_router
                from workflows.simple_router.workflow import IntentClassifierWorkflow

                workflow = IntentClassifierWorkflow()
                event_source = workflow.astream(
                    message,
                    config={"configurable": {"thread_id": session_id}},
                )

            async for event in event_source:
                async for stream_event in self._iter_stream_events(event):
                    yield stream_event

            yield {"event": "done", "data": None}
        except Exception as e:
            logger.error(f"Stream workflow execution error: {e}")
            yield {"event": "error", "data": str(e)}

    async def _stream_dynamic_workflow(
        self, definition: dict[str, Any], message: str, session_id: str
    ) -> AsyncGenerator[dict, None]:
        """流式执行动态编译的工作流（来自 DB 定义）"""
        state_schema = definition.get("state_schema", {})
        state: dict[str, Any] = {}
        for field_name, field_type in state_schema.items():
            if field_name in ("input", "message"):
                state[field_name] = message
            elif field_type == "str" or field_type == "string":
                state[field_name] = ""
            elif field_type == "list":
                state[field_name] = []
            else:
                state[field_name] = None

        graph = compile_workflow(definition)

        latest_state: dict[str, Any] = {}
        async for event in graph.astream(
            state,
            config={"configurable": {"thread_id": session_id}},
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    latest_state.update(node_output)
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "data": node_output,
                }

        response = latest_state.get("output", latest_state.get("final_decision", ""))
        yield {"event": "done", "data": {"response": response, "state": latest_state}}

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
