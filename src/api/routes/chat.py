# -*- coding: utf-8 -*-
"""
聊天路由

提供同步和流式聊天接口（异步实现）
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.schemas import ChatRequest, ChatResponse, StreamEvent
from core.logger import logger
from workflows.simple_router import create_simple_router_workflow
from workflows.customer_service import create_customer_service_workflow

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_workflow(workflow_type: str, checkpointer=None):
    """
    获取工作流实例

    Args:
        workflow_type: 工作流类型
        checkpointer: 状态持久化器

    Returns:
        编译后的工作流
    """
    workflows = {
        "simple_router": lambda: create_simple_router_workflow(),
        "customer_service": lambda: create_customer_service_workflow(checkpointer),
    }

    if workflow_type not in workflows:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow: {workflow_type}. Available: {list(workflows.keys())}",
        )

    return workflows[workflow_type]()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    同步聊天接口

    Args:
        request: 聊天请求

    Returns:
        聊天响应
    """
    logger.info(f"收到聊天请求: session_id={request.session_id}, workflow={request.workflow}")

    try:
        graph = _get_workflow(request.workflow)
        config = {"configurable": {"thread_id": request.session_id}}

        # 异步执行工作流
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )

        # 提取响应
        response_content = ""
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            response_content = last_message.content if hasattr(last_message, "content") else str(last_message)

        return ChatResponse(
            response=response_content,
            session_id=request.session_id,
            node=result.get("node"),
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    流式聊天接口（SSE）

    Args:
        request: 聊天请求

    Returns:
        SSE 流式响应
    """
    logger.info(f"收到流式聊天请求: session_id={request.session_id}")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            graph = _get_workflow(request.workflow)
            config = {"configurable": {"thread_id": request.session_id}}

            # 异步流式执行工作流
            async for event in graph.astream(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    stream_event = StreamEvent(
                        event="node_update",
                        node=node_name,
                        data=node_output,
                    )
                    yield f"data: {stream_event.model_dump_json()}\n\n"

            # 发送完成事件
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"流式聊天处理失败: {e}")
            error_event = StreamEvent(event="error", data=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
