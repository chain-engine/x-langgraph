# -*- coding: utf-8 -*-
"""
工作流定义管理路由

提供工作流定义的 CRUD 和执行接口。
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.workflow import (
    WorkflowDefinition,
    WorkflowSummary,
    NodeDefinition,
    EdgeDefinition,
    ExecuteRequest,
)
from core.logger import logger
from core.container import container
from services.workflow_service import WorkflowDefinitionService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowSummary])
async def list_workflows() -> list[WorkflowSummary]:
    """列出所有工作流"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    summaries = await service.list_workflows()
    return [WorkflowSummary(**s) for s in summaries]


@router.get("/{name}", response_model=WorkflowDefinition)
async def get_workflow(name: str) -> WorkflowDefinition:
    """获取工作流详情"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    wf = await service.get_workflow(name)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return WorkflowDefinition(**wf)


@router.post("", response_model=WorkflowDefinition)
async def create_workflow(workflow: WorkflowDefinition) -> WorkflowDefinition:
    """创建工作流"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    try:
        result = await service.create_workflow(workflow.model_dump())
        return WorkflowDefinition(**result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{name}", response_model=WorkflowDefinition)
async def update_workflow(name: str, workflow: WorkflowDefinition) -> WorkflowDefinition:
    """更新工作流"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.update_workflow(name, workflow.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return WorkflowDefinition(**result)


@router.delete("/{name}")
async def delete_workflow(name: str) -> dict:
    """删除工作流"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    success = await service.delete_workflow(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return {"deleted": True, "name": name}


# ===== 节点 CRUD =====

@router.post("/{name}/nodes", response_model=WorkflowDefinition)
async def add_node(name: str, node: NodeDefinition) -> WorkflowDefinition:
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.add_node(name, node.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return WorkflowDefinition(**result)


@router.put("/{name}/nodes/{node_id}", response_model=WorkflowDefinition)
async def update_node(name: str, node_id: str, node: NodeDefinition) -> WorkflowDefinition:
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.update_node(name, node_id, node.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流或节点不存在: {name}/{node_id}")
    return WorkflowDefinition(**result)


@router.delete("/{name}/nodes/{node_id}", response_model=WorkflowDefinition)
async def delete_node(name: str, node_id: str) -> WorkflowDefinition:
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.delete_node(name, node_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return WorkflowDefinition(**result)


# ===== 边 CRUD =====

@router.post("/{name}/edges", response_model=WorkflowDefinition)
async def add_edge(name: str, edge: EdgeDefinition) -> WorkflowDefinition:
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.add_edge(name, edge.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return WorkflowDefinition(**result)


@router.put("/{name}/edges/{edge_id}", response_model=WorkflowDefinition)
async def update_edge(name: str, edge_id: str, edge: EdgeDefinition) -> WorkflowDefinition:
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.update_edge(name, edge_id, edge.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流或边不存在: {name}/{edge_id}")
    return WorkflowDefinition(**result)


@router.delete("/{name}/edges/{edge_id}", response_model=WorkflowDefinition)
async def delete_edge(name: str, edge_id: str) -> WorkflowDefinition:
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.delete_edge(name, edge_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")
    return WorkflowDefinition(**result)


# ===== 执行接口 =====

@router.post("/{name}/execute")
async def execute_workflow(name: str, request: ExecuteRequest) -> dict:
    """同步执行工作流"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)
    result = await service.execute(name, request.message, request.session_id)
    return result


@router.post("/{name}/stream")
async def stream_workflow(name: str, request: ExecuteRequest) -> StreamingResponse:
    """SSE 流式执行工作流"""
    service: WorkflowDefinitionService = container.resolve(WorkflowDefinitionService)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in service.stream_execute(name, request.message, request.session_id):
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
