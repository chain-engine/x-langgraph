# -*- coding: utf-8 -*-
"""
审批路由

提供 Human-in-the-Loop 审批接口（异步实现）
"""

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from api.schemas import ApprovalRequest, ApprovalResponse
from core.logger import logger
from workflows.customer_service import create_customer_service_workflow

router = APIRouter(prefix="/approval", tags=["approval"])

_checkpointer = None


def set_checkpointer(checkpointer):
    """
    设置全局 Checkpointer

    Args:
        checkpointer: AsyncMySQLSaver 实例
    """
    global _checkpointer
    _checkpointer = checkpointer
    logger.info("审批路由 Checkpointer 已设置")


def _create_workflow():
    """
    创建工作流实例（使用全局 Checkpointer）

    Returns:
        工作流实例
    """
    if _checkpointer is None:
        logger.warning("Checkpointer 未初始化，使用 MemorySaver（开发模式）")
        return create_customer_service_workflow(MemorySaver())
    return create_customer_service_workflow(_checkpointer)


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
        graph = _create_workflow()
        config = {"configurable": {"thread_id": request.session_id}}

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
        graph = _create_workflow()
        config = {"configurable": {"thread_id": session_id}}

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
