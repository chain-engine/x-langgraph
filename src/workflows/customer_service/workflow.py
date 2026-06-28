# -*- coding: utf-8 -*-
"""
智能客服工作流定义

展示 LangGraph 的高级功能：
- 复杂状态管理 (TypedDict + Annotated)
- 多级条件路由
- Checkpointer 状态持久化
- 人机交互 (interrupt/Command)
- 流式输出
- 继承 BaseWorkflow 基类
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from workflows.base import BaseWorkflow
from workflows.customer_service.state import CustomerServiceState
from workflows.customer_service.nodes import (
    intake_node,
    classify_node,
    handle_inquiry_node,
    handle_complaint_node,
    handle_technical_node,
    handle_billing_node,
    review_node,
)

from core.logger import logger


class CustomerServiceWorkflow(BaseWorkflow):
    """
    智能客服工作流

    处理客户服务请求，支持多种工单类型：
    - inquiry: 一般咨询
    - complaint: 投诉处理
    - technical: 技术支持
    - billing: 账单问题

    工作流结构:
        START → intake → classify → [条件路由]
                                      ├→ handle_inquiry → review → END
                                      ├→ handle_complaint → review → END
                                      ├→ handle_technical → review → END
                                      └→ handle_billing → review → END
    """

    name = "customer_service"
    description = "智能客服工作流：处理咨询、投诉、技术支持和账单问题"

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
        workflow = StateGraph(CustomerServiceState)

        # 添加节点
        workflow.add_node("intake", intake_node)
        workflow.add_node("classify", classify_node)
        workflow.add_node("handle_inquiry", handle_inquiry_node)
        workflow.add_node("handle_complaint", handle_complaint_node)
        workflow.add_node("handle_technical", handle_technical_node)
        workflow.add_node("handle_billing", handle_billing_node)
        workflow.add_node("review", review_node)

        # 设置入口点
        workflow.set_entry_point("intake")

        # 添加普通边
        workflow.add_edge("intake", "classify")
        workflow.add_edge("handle_inquiry", "review")
        workflow.add_edge("handle_complaint", "review")
        workflow.add_edge("handle_technical", "review")
        workflow.add_edge("handle_billing", "review")
        workflow.add_edge("review", END)

        # 添加条件边
        workflow.add_conditional_edges(
            "classify",
            self._route_by_ticket_type,
            {
                "handle_inquiry": "handle_inquiry",
                "handle_complaint": "handle_complaint",
                "handle_technical": "handle_technical",
                "handle_billing": "handle_billing",
            },
        )

        # 编译工作流
        checkpointer = self.checkpointer or MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    @staticmethod
    def _route_by_ticket_type(state: CustomerServiceState) -> str:
        """
        条件路由：根据工单类型选择处理节点

        Args:
            state: 当前状态

        Returns:
            下一个节点名称
        """
        ticket_type = state.get("ticket_type", "inquiry")
        logger.info(f"路由到处理节点: {ticket_type}")

        routing_map = {
            "inquiry": "handle_inquiry",
            "complaint": "handle_complaint",
            "technical": "handle_technical",
            "billing": "handle_billing",
        }

        return routing_map.get(ticket_type, "handle_inquiry")

    def _create_initial_state(self, user_input: str) -> dict:
        """创建初始状态"""
        return {
            "messages": [HumanMessage(content=user_input)],
            "stage": "",
            "ticket_id": None,
            "ticket_type": None,
            "priority": None,
            "customer_name": None,
            "resolution": None,
            "requires_approval": False,
            "approved": None,
            "approval_comments": None,
            "error": None,
        }

    def run(self, user_input: str, thread_id: str = "default") -> dict:
        """
        运行工作流的便捷方法

        Args:
            user_input: 用户输入
            thread_id: 会话 ID

        Returns:
            执行结果
        """
        return self.invoke(
            self._create_initial_state(user_input),
            config={"configurable": {"thread_id": thread_id}},
        )

    async def arun(self, user_input: str, thread_id: str = "default") -> dict:
        """
        异步运行工作流的便捷方法

        Args:
            user_input: 用户输入
            thread_id: 会话 ID

        Returns:
            执行结果
        """
        return await self.ainvoke(
            self._create_initial_state(user_input),
            config={"configurable": {"thread_id": thread_id}},
        )

    def stream_run(
        self,
        user_input: str,
        thread_id: str = "default",
        stream_mode: str = "updates"
    ):
        """
        流式运行工作流

        Args:
            user_input: 用户输入
            thread_id: 会话 ID
            stream_mode: 流式模式

        Yields:
            每个节点的更新
        """
        yield from self.stream(
            self._create_initial_state(user_input),
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=stream_mode,
        )

    async def astream_run(
        self,
        user_input: str,
        thread_id: str = "default",
        stream_mode: str = "updates"
    ):
        """
        异步流式运行工作流

        Args:
            user_input: 用户输入
            thread_id: 会话 ID
            stream_mode: 流式模式

        Yields:
            每个节点的更新
        """
        async for event in self.astream(
            self._create_initial_state(user_input),
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=stream_mode,
        ):
            yield event


# ========== 工厂函数（保持向后兼容）==========

def create_customer_service_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
) -> StateGraph:
    """
    创建智能客服工作流（工厂函数）

    Args:
        checkpointer: 状态持久化器

    Returns:
        编译后的工作流图
    """
    workflow = CustomerServiceWorkflow(checkpointer)
    return workflow.graph


def run_customer_service(
    user_input: str,
    thread_id: str = "default",
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict:
    """
    运行智能客服工作流（便捷函数）

    Args:
        user_input: 用户输入
        thread_id: 会话 ID
        checkpointer: 状态持久化器

    Returns:
        执行结果
    """
    workflow = CustomerServiceWorkflow(checkpointer)
    return workflow.run(user_input, thread_id)


def stream_customer_service(
    user_input: str,
    thread_id: str = "default",
    checkpointer: BaseCheckpointSaver | None = None,
    stream_mode: str = "updates",
):
    """
    流式运行智能客服工作流

    Args:
        user_input: 用户输入
        thread_id: 会话 ID
        checkpointer: 状态持久化器
        stream_mode: 流式模式

    Yields:
        每个节点的更新
    """
    workflow = CustomerServiceWorkflow(checkpointer)
    yield from workflow.stream_run(user_input, thread_id, stream_mode)
