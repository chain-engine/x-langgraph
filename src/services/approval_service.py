# -*- coding: utf-8 -*-
"""
审批服务

处理 Human-in-the-Loop 审批业务逻辑
"""

from typing import Any, Optional

from models.base import Service
from core.logger import logger


class ApprovalService(Service):
    """审批服务"""

    def __init__(self):
        """初始化审批服务"""
        logger.info("Approval service initialized")

    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """根据ID获取审批状态

        Args:
            entity_id: 会话ID

        Returns:
            Optional[Any]: 审批状态或None
        """
        logger.info(f"Get approval status: {entity_id}")
        return await self.get_approval_status(entity_id)

    async def create(self, data: dict[str, Any]) -> Any:
        """创建审批请求

        Args:
            data: 审批数据

        Returns:
            Any: 审批结果
        """
        session_id = data.get("session_id")
        approved = data.get("approved", False)
        comments = data.get("comments", "")

        logger.info(f"Create approval: session_id={session_id}, approved={approved}")

        return await self.resume_workflow(session_id, approved, comments)

    async def update(self, entity_id: str, data: dict[str, Any]) -> Any:
        """更新审批状态

        Args:
            entity_id: 会话ID
            data: 更新数据

        Returns:
            Any: 更新后的审批状态
        """
        data["session_id"] = entity_id
        return await self.create(data)

    async def delete(self, entity_id: str) -> bool:
        """删除审批记录

        Args:
            entity_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        logger.info(f"Delete approval: {entity_id}")
        return True

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> dict[str, Any]:
        """查询所有审批记录

        Args:
            page: 页码
            page_size: 每页记录数
            filters: 过滤条件
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            dict[str, Any]: 分页数据
        """
        return {"data": [], "total": 0, "page": page, "page_size": page_size}

    async def resume_workflow(self, session_id: str, approved: bool, comments: str = "") -> dict[str, Any]:
        """
        恢复等待审批的工作流

        Args:
            session_id: 会话ID
            approved: 是否批准
            comments: 审批意见

        Returns:
            dict: 恢复结果
        """
        from langgraph.types import Command
        from workflows.customer_service import create_customer_service_workflow
        from core.checkpointer import create_checkpointer

        try:
            checkpointer = await create_checkpointer()
            graph = create_customer_service_workflow(checkpointer)
            config = {"configurable": {"thread_id": session_id}}

            await graph.ainvoke(
                Command(
                    resume={
                        "approved": approved,
                        "comments": comments or "",
                    }
                ),
                config=config,
            )

            logger.info(f"Workflow resumed: session_id={session_id}, approved={approved}")

            return {
                "status": "success",
                "message": "工作流已恢复执行",
            }

        except Exception as e:
            logger.error(f"Failed to resume workflow: {e}")
            return {
                "status": "error",
                "message": f"审批处理失败: {str(e)}",
            }

    async def get_approval_status(self, session_id: str) -> dict[str, Any]:
        """
        获取会话的审批状态

        Args:
            session_id: 会话ID

        Returns:
            dict: 审批状态
        """
        from workflows.customer_service import create_customer_service_workflow
        from core.checkpointer import create_checkpointer

        try:
            checkpointer = await create_checkpointer()
            graph = create_customer_service_workflow(checkpointer)
            config = {"configurable": {"thread_id": session_id}}

            state = await graph.aget_state(config)

            return {
                "session_id": session_id,
                "status": "waiting_approval" if state.next else "completed",
                "next_nodes": state.next,
                "values": state.values,
            }

        except Exception as e:
            logger.error(f"Failed to get approval status: {e}")
            return {
                "session_id": session_id,
                "status": "error",
                "message": str(e),
            }
