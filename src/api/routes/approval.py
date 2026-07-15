# -*- coding: utf-8 -*-
"""
审批路由

提供 Human-in-the-Loop 审批接口（异步实现）
API层只做接口注册和转发，具体业务逻辑由Service层处理
"""

from fastapi import APIRouter, HTTPException

from constants.schemas import ApprovalRequest, ApprovalResponse
from core.logger import logger
from services.approval_service import ApprovalService

router = APIRouter(prefix="/approval", tags=["approval"])

approval_service = ApprovalService()


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
        result = await approval_service.resume_workflow(
            request.session_id,
            request.approved,
            request.comments or ""
        )

        return ApprovalResponse(
            status=result.get("status", "success"),
            message=result.get("message", "工作流已恢复执行"),
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
        result = await approval_service.get_approval_status(session_id)
        return result

    except Exception as e:
        logger.error(f"获取审批状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
