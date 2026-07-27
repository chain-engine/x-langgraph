# -*- coding: utf-8 -*-
"""
聊天路由

提供同步和流式聊天接口（异步实现）
API层只做接口注册和转发，具体业务逻辑由Service层处理
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.chat import ChatRequest, ChatResponse, StreamEvent
from core.logger import logger
from core.container import container
from services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/execute", response_model=ChatResponse)
async def chat_execute(request: ChatRequest) -> ChatResponse:
    """
    同步聊天

    Args:
        request: 聊天请求

    Returns:
        聊天响应
    """
    chat_service: ChatService = container.resolve(ChatService)
    logger.info(f"收到聊天请求: session_id={request.session_id}, workflow={request.workflow}")

    try:
        result = await chat_service.create(request.model_dump())

        return ChatResponse(
            response=result.get("response", ""),
            session_id=result.get("session_id", request.session_id),
            node=result.get("node"),
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    流式聊天（SSE）

    Args:
        request: 聊天请求

    Returns:
        SSE 流式响应
    """
    chat_service: ChatService = container.resolve(ChatService)
    logger.info(f"收到流式聊天请求: session_id={request.session_id}")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in chat_service.stream(
                request.workflow,
                request.message,
                request.session_id
            ):
                stream_event = StreamEvent(
                    event=event.get("event", "node_update"),
                    node=event.get("node"),
                    data=event.get("data"),
                )
                yield f"data: {stream_event.model_dump_json()}\n\n"

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
