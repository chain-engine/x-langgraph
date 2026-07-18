# -*- coding: utf-8 -*-
"""
意图分类路由工作流定义

展示 LangGraph 的核心能力：
- LLM 意图分类 + 条件路由
- 多意图分支处理
- 人机交互（interrupt）
- 继承 BaseWorkflow 基类
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from workflows.base import BaseWorkflow
from workflows.simple_router.state import IntentClassifierState
from workflows.simple_router.nodes import (
    classify_intent,
    handle_product_inquiry,
    handle_order_status,
    handle_technical_support,
    handle_complaint,
    handle_billing,
    handle_other,
)

from core.logger import logger


class IntentClassifierWorkflow(BaseWorkflow):
    """
    意图分类路由工作流

    根据用户输入自动识别意图，并路由到对应的业务处理节点：

    工作流结构:
        START → classify → [条件路由]
                                ├→ product_inquiry → END
                                ├→ order_status → END
                                ├→ technical_support → END (interrupt 等待审批)
                                ├→ complaint → END
                                ├→ billing → END
                                └→ other → END
    """

    name = "simple_router"
    description = "意图分类路由：根据用户输入自动识别意图（产品咨询/订单状态/技术支持/投诉/账单）并分发处理"

    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        super().__init__(checkpointer)

    def build(self) -> StateGraph:
        logger.info(f"构建工作流: {self.name}")

        workflow = StateGraph(IntentClassifierState)

        # 节点
        workflow.add_node("classify", classify_intent)
        workflow.add_node("product_inquiry", handle_product_inquiry)
        workflow.add_node("order_status", handle_order_status)
        workflow.add_node("technical_support", handle_technical_support)
        workflow.add_node("complaint", handle_complaint)
        workflow.add_node("billing", handle_billing)
        workflow.add_node("other", handle_other)

        # 入口
        workflow.set_entry_point("classify")

        # 条件路由
        workflow.add_conditional_edges(
            "classify",
            self._route_by_intent,
            {
                "product_inquiry": "product_inquiry",
                "order_status": "order_status",
                "technical_support": "technical_support",
                "complaint": "complaint",
                "billing": "billing",
                "other": "other",
            },
        )

        # 所有分支结束
        for node in [
            "product_inquiry",
            "order_status",
            "technical_support",
            "complaint",
            "billing",
            "other",
        ]:
            workflow.add_edge(node, END)

        checkpointer = self.checkpointer or MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    @staticmethod
    def _route_by_intent(state: IntentClassifierState) -> str:
        return state.get("intent", "other")


# ========== 向后兼容别名（保持 API 稳定）==========

create_simple_router_workflow = IntentClassifierWorkflow
run_simple_router = IntentClassifierWorkflow().invoke
arun_simple_router = IntentClassifierWorkflow().ainvoke
