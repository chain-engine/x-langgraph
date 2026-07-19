# -*- coding: utf-8 -*-
"""
自动化审批工作流定义

展示 LangGraph 的人机交互（Human-in-the-Loop）能力：
- 自动决策
- 人工审批
- 条件路由
- 继承 BaseWorkflow 基类
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_core.messages import HumanMessage

from workflows.base import BaseWorkflow
from workflows.approval.state import (
    ApprovalState,
    ApprovalResult,
    ApprovalType,
)
from workflows.approval.nodes import (
    submit_node,
    evaluate_node,
    human_approval_node,
    auto_approve_node,
    notify_node,
    route_by_evaluation,
    route_by_status,
)

from core.logger import logger


class ApprovalWorkflow(BaseWorkflow):
    """
    自动化审批工作流

    处理各种审批请求，支持自动审批和人工审批：
    - leave: 请假申请
    - expense: 报销申请
    - procurement: 采购申请
    - contract: 合同审批

    工作流结构:
        START → submit → evaluate → [条件路由]
                                     ├→ auto_approve → notify → END
                                     └→ human_approval → [条件路由]
                                                         ├→ notify → END
                                                         └→ END
    """

    name = "approval"
    description = "自动化审批工作流：支持自动审批和人工审批"

    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        super().__init__(checkpointer)

    def build(self) -> StateGraph:
        """
        构建工作流图

        Returns:
            编译后的 StateGraph
        """
        logger.info(f"构建工作流: {self.name}")

        # 创建状态图
        workflow = StateGraph(ApprovalState)

        # 添加节点
        workflow.add_node("submit", submit_node)
        workflow.add_node("evaluate", evaluate_node)
        workflow.add_node("human_approval", human_approval_node)
        workflow.add_node("auto_approve", auto_approve_node)
        workflow.add_node("notify", notify_node)

        # 设置入口点
        workflow.set_entry_point("submit")

        # 普通边
        workflow.add_edge("submit", "evaluate")

        # 条件路由：根据评估结果
        workflow.add_conditional_edges(
            "evaluate",
            route_by_evaluation,
            {
                "auto_approve": "auto_approve",
                "human_approval": "human_approval",
            },
        )

        # 自动审批后发送通知
        workflow.add_edge("auto_approve", "notify")

        # 人工审批后的条件路由
        workflow.add_conditional_edges(
            "human_approval",
            route_by_status,
            {
                "notify": "notify",
                "end": END,
            },
        )

        # 通知后结束
        workflow.add_edge("notify", END)

        # 编译工作流
        checkpointer = self.checkpointer or MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    def _create_initial_state(self, request: dict) -> ApprovalState:
        """创建初始状态"""
        return {
            "messages": [],
            "request": request,
            "approval_level": "",
            "approval_status": "",
            "auto_evaluation": {},
            "risk_level": "",
            "recommended_action": "",
            "approval_history": [],
            "requires_human": False,
            "human_approved": None,
            "human_comments": None,
            "approver_id": None,
            "final_status": "",
            "output": "",
            "notification_sent": False,
            "error": None,
        }

    def run(self, request: dict, thread_id: str = "default") -> ApprovalResult:
        """
        运行审批工作流

        Args:
            request: 审批请求
            thread_id: 会话 ID

        Returns:
            ApprovalResult 结果对象
        """
        logger.info(f"Approval: 开始处理 - {request.get('request_type', '')}")

        result = self.invoke(
            self._create_initial_state(request),
            config={"configurable": {"thread_id": thread_id}},
        )

        return ApprovalResult(
            request_id=result.get("request", {}).get("request_id", ""),
            final_status=result.get("final_status", ""),
            final_decision=result.get("output", ""),
            approval_history=result.get("approval_history", []),
            auto_evaluation=result.get("auto_evaluation", {}),
            risk_level=result.get("risk_level", "unknown"),
            success=result.get("error") is None,
            error=result.get("error"),
        )

    async def arun(self, request: dict, thread_id: str = "default") -> ApprovalResult:
        """
        异步运行审批工作流

        Args:
            request: 审批请求
            thread_id: 会话 ID

        Returns:
            ApprovalResult 结果对象
        """
        logger.info(f"Approval: 异步处理 - {request.get('request_type', '')}")

        result = await self.ainvoke(
            self._create_initial_state(request),
            config={"configurable": {"thread_id": thread_id}},
        )

        return ApprovalResult(
            request_id=result.get("request", {}).get("request_id", ""),
            final_status=result.get("final_status", ""),
            final_decision=result.get("output", ""),
            approval_history=result.get("approval_history", []),
            auto_evaluation=result.get("auto_evaluation", {}),
            risk_level=result.get("risk_level", "unknown"),
            success=result.get("error") is None,
            error=result.get("error"),
        )

    def run_with_human(
        self,
        request: dict,
        approval_decision: dict,
        thread_id: str = "default",
    ) -> ApprovalResult:
        """
        运行带人工审批的审批工作流

        Args:
            request: 审批请求
            approval_decision: 人工审批决定 {"approved": bool, "comments": str}
            thread_id: 会话 ID

        Returns:
            ApprovalResult 结果对象
        """
        logger.info(f"Approval: 带人工审批 - {request.get('request_type', '')}")

        # 第一步：执行到中断点
        for event in self.stream(
            self._create_initial_state(request),
            config={"configurable": {"thread_id": thread_id}},
        ):
            for node_name, node_output in event.items():
                logger.info(f"Approval: 节点 {node_name} 执行完成")
                if node_name == "human_approval" and "__interrupt__" in str(node_output):
                    logger.info("Approval: 到达人工审批节点，等待审批...")

        # 第二步：提供审批决定，继续执行
        logger.info(f"Approval: 提供审批决定 - {'通过' if approval_decision.get('approved') else '拒绝'}")

        for event in self.stream(
            Command(resume=approval_decision),
            config={"configurable": {"thread_id": thread_id}},
        ):
            for node_name, node_output in event.items():
                logger.info(f"Approval: 节点 {node_name} 执行完成")

        # 获取最终状态
        final_state = self.get_state({"configurable": {"thread_id": thread_id}})

        return ApprovalResult(
            request_id=request.get("request_id", ""),
            final_status=final_state.values.get("final_status", ""),
            final_decision=final_state.values.get("output", ""),
            approval_history=final_state.values.get("approval_history", []),
            auto_evaluation=final_state.values.get("auto_evaluation", {}),
            risk_level=final_state.values.get("risk_level", "unknown"),
            success=final_state.values.get("error") is None,
            error=final_state.values.get("error"),
        )


# ========== 工厂函数（保持向后兼容）==========

def create_approval_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
) -> StateGraph:
    """
    创建自动化审批工作流（工厂函数）

    Args:
        checkpointer: 状态持久化器

    Returns:
        编译后的工作流图
    """
    workflow = ApprovalWorkflow(checkpointer)
    return workflow.graph


def run_approval(
    request: dict,
    thread_id: str = "default",
    checkpointer: BaseCheckpointSaver | None = None,
) -> ApprovalResult:
    """
    运行审批工作流（便捷函数）

    Args:
        request: 审批请求
        thread_id: 会话 ID
        checkpointer: 状态持久化器

    Returns:
        ApprovalResult 结果对象
    """
    workflow = ApprovalWorkflow(checkpointer)
    return workflow.run(request, thread_id)


def run_approval_with_human(
    request: dict,
    approval_decision: dict,
    thread_id: str = "default",
    checkpointer: BaseCheckpointSaver | None = None,
) -> ApprovalResult:
    """
    运行带人工审批的审批工作流

    Args:
        request: 审批请求
        approval_decision: 人工审批决定
        thread_id: 会话 ID
        checkpointer: 状态持久化器

    Returns:
        ApprovalResult 结果对象
    """
    workflow = ApprovalWorkflow(checkpointer)
    return workflow.run_with_human(request, approval_decision, thread_id)


def stream_approval(
    request: dict,
    thread_id: str = "default",
    checkpointer: BaseCheckpointSaver | None = None,
    stream_mode: str = "updates",
):
    """
    流式运行审批工作流

    Args:
        request: 审批请求
        thread_id: 会话 ID
        checkpointer: 状态持久化器
        stream_mode: 流式模式

    Yields:
        每个节点的更新
    """
    workflow = ApprovalWorkflow(checkpointer)
    yield from workflow.stream(
        workflow._create_initial_state(request),
        config={"configurable": {"thread_id": thread_id}},
        stream_mode=stream_mode,
    )
