# -*- coding: utf-8 -*-
"""
审批路由

提供 Human-in-the-Loop 审批接口（异步实现）
"""

from fastapi import APIRouter, HTTPException
from langgraph.types import Command

from api.schemas import ApprovalRequest, ApprovalResponse
from core.logger import logger
from workflows.customer_service import create_customer_service_workflow
from langgraph.checkpoint.memory import MemorySaver

router = APIRouter(prefix="/approval", tags=["approval"])

# 存储工作流实例（生产环境应使用 Redis 或数据库）
_workflows: dict = {}


def _get_or_create_workflow(session_id: str):
    """
    获取或创建工作流实例

    Args:
        session_id: 会话 ID

    Returns:
        工作流实例
    """
    if session_id not in _workflows:
        checkpointer = MemorySaver()
        _workflows[session_id] = create_customer_service_workflow(checkpointer)
    return _workflows[session_id]


@router.post("/resume", response_model=ApprovalResponse)
async def resume_workflow(request: ApprovalRequest) -> ApprovalResponse:
    """
    恢复等待审批的工作流

    当工作流因 interrupt 暂停时，使用此接口恢复执行。

    Args:
        request: 审批请求

    Returns:
        审批响应
    """
    logger.info(f"收到审批请求: session_id={request.session_id}, approved={request.approved}")

    try:
        graph = _get_or_create_workflow(request.session_id)
        config = {"configurable": {"thread_id": request.session_id}}

        # 使用 Command 异步恢复执行
        result = await graph.ainvoke(
            Command(
                resume={
                    "approved": request.approved,
                    "comments": request.comments or "",
                }
            ),
            config=config,
        )

        logger.info(f"工作流恢复执行完成: session_id={request.session_id}")

        return ApprovalResponse(
            status="success",
            message="工作流已恢复执行",
        )

    except Exception as e:
        logger.error(f"审批处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{session_id}")
async def get_approval_status(session_id: str) -> dict:
    """
    获取会话的审批状态

    Args:
        session_id: 会话 ID

    Returns:
        审批状态
    """
    try:
        graph = _get_or_create_workflow(session_id)
        config = {"configurable": {"thread_id": session_id}}

        # 异步获取当前状态
        state = await graph.aget_state(config)

        return {
            "session_id": session_id,
            "status": "waiting_approval" if state.next else "completed",
            "next_nodes": state.next,
            "values": state.values,
        }

    except Exception as e:
        logger.error(f"获取审批状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
