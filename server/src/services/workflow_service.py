# -*- coding: utf-8 -*-
"""
工作流定义服务

处理工作流定义的 CRUD 业务逻辑和执行调度。
"""

from typing import Any, AsyncGenerator, Optional

from workflows.compiler import compile_workflow
from core.logger import logger
from repositories.workflow_definition_repository import WorkflowDefinitionRepository


class WorkflowDefinitionService:
    """工作流定义服务"""

    def __init__(self, repository: Optional[WorkflowDefinitionRepository] = None):
        self._repository = repository or WorkflowDefinitionRepository()

    async def list_workflows(self) -> list[dict[str, Any]]:
        """列出所有工作流摘要"""
        all_wf = await self._repository.list_all()
        summaries = []
        for wf in all_wf:
            graph = wf.get("graph_data", {})
            summaries.append({
                "name": wf.get("name", ""),
                "description": wf.get("description", ""),
                "node_count": len(graph.get("nodes", [])),
                "edge_count": len(graph.get("edges", [])),
                "created_at": wf.get("created_at"),
                "updated_at": wf.get("updated_at"),
            })
        return summaries

    async def get_workflow(self, name: str) -> Optional[dict[str, Any]]:
        """获取工作流完整定义"""
        return await self._repository.get_by_name(name)

    async def create_workflow(self, data: dict[str, Any]) -> dict[str, Any]:
        """创建工作流"""
        existing = await self._repository.get_by_name(data["name"])
        if existing is not None:
            raise ValueError(f"工作流已存在: {data['name']}")
        return await self._repository.create(data)

    async def update_workflow(self, name: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新工作流"""
        return await self._repository.update(name, data)

    async def delete_workflow(self, name: str) -> bool:
        """删除工作流"""
        return await self._repository.delete(name)

    async def add_node(self, workflow_name: str, node_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self._repository.add_node(workflow_name, node_data)

    async def update_node(self, workflow_name: str, node_id: str, node_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self._repository.update_node(workflow_name, node_id, node_data)

    async def delete_node(self, workflow_name: str, node_id: str) -> Optional[dict[str, Any]]:
        return await self._repository.delete_node(workflow_name, node_id)

    async def add_edge(self, workflow_name: str, edge_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self._repository.add_edge(workflow_name, edge_data)

    async def update_edge(self, workflow_name: str, edge_id: str, edge_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self._repository.update_edge(workflow_name, edge_id, edge_data)

    async def delete_edge(self, workflow_name: str, edge_id: str) -> Optional[dict[str, Any]]:
        return await self._repository.delete_edge(workflow_name, edge_id)

    async def execute(self, workflow_name: str, message: str, session_id: str = "default") -> dict[str, Any]:
        """同步执行工作流"""
        definition = await self._repository.get_by_name(workflow_name)
        if definition is None:
            return {"error": f"工作流不存在: {workflow_name}", "response": "", "session_id": session_id}

        try:
            # 将工作流定义编译为 LangGraph StateGraph 执行图
            graph = compile_workflow(definition)
            # 构建初始状态：将用户消息注入到 state_schema 定义的字段中
            initial_state = self._build_initial_state(definition, message)
            # 异步执行工作流图，thread_id 用于 LangGraph 的持久化和检查点机制
            result = await graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": session_id}},
            )
            return {
                "response": result.get("output", result.get("final_decision", "")),
                "session_id": session_id,
                "node": None,
                "state": result,
            }
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return {"error": str(e), "response": "", "session_id": session_id}

    async def stream_execute(self, workflow_name: str, message: str, session_id: str = "default") -> AsyncGenerator[dict, None]:
        """流式执行工作流（SSE）"""
        definition = await self._repository.get_by_name(workflow_name)
        if definition is None:
            yield {"event": "error", "data": f"工作流不存在: {workflow_name}"}
            return

        try:
            graph = compile_workflow(definition)
            initial_state = self._build_initial_state(definition, message)

            async for event in graph.astream(
                initial_state,
                config={"configurable": {"thread_id": session_id}},
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    yield {
                        "event": "node_update",
                        "node": node_name,
                        "data": node_output,
                    }

            yield {"event": "done", "data": None}
        except Exception as e:
            logger.error(f"Workflow stream failed: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}

    def _build_initial_state(self, definition: dict[str, Any], message: str) -> dict[str, Any]:
        """根据 state_schema 构建初始状态"""
        state_schema = definition.get("state_schema", {})
        state = {}
        for field_name, field_type in state_schema.items():
            if field_name == "input" or field_name == "message":
                state[field_name] = message
            elif field_name == "messages":
                state[field_name] = []
            elif field_type in ("str", "string"):
                state[field_name] = ""
            elif field_type in ("int", "integer"):
                state[field_name] = 0
            elif field_type in ("float",):
                state[field_name] = 0.0
            elif field_type in ("bool", "boolean"):
                state[field_name] = False
            elif field_type in ("list",):
                state[field_name] = []
            elif field_type in ("dict",):
                state[field_name] = {}
            elif field_type.startswith("Optional"):
                state[field_name] = None
            else:
                state[field_name] = None
        if "messages" not in state:
            state["messages"] = []
        return state

    async def seed_builtin_workflows(self):
        """生成内置工作流种子数据"""
        from workflows.seed_data import SIMPLE_ROUTER_DEF, APPROVAL_DEF
        for definition in [SIMPLE_ROUTER_DEF, APPROVAL_DEF]:
            existing = await self._repository.get_by_name(definition["name"])
            if existing is None:
                await self._repository.create(definition)
                logger.info(f"Seeded workflow: {definition['name']}")
            else:
                logger.info(f"Workflow already exists, skipping: {definition['name']}")
