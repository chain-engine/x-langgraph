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
from workflows.intent_classifier.state import IntentClassifierState
from workflows.intent_classifier.nodes import (
    classify_intent_node,
    handle_product_inquiry_node,
    handle_order_status_node,
    handle_technical_support_node,
    handle_complaint_node,
    handle_billing_node,
    handle_other_node,
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

    name = "intent_classifier"
    description = "意图分类路由：根据用户输入自动识别意图（产品咨询/订单状态/技术支持/投诉/账单）并分发处理"

    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        super().__init__(checkpointer)

    def build(self) -> StateGraph:
        logger.info(f"构建工作流: {self.name}")

        workflow = StateGraph(IntentClassifierState)

        # 节点
        workflow.add_node("classify", classify_intent_node)
        workflow.add_node("product_inquiry", handle_product_inquiry_node)
        workflow.add_node("order_status", handle_order_status_node)
        workflow.add_node("technical_support", handle_technical_support_node)
        workflow.add_node("complaint", handle_complaint_node)
        workflow.add_node("billing", handle_billing_node)
        workflow.add_node("other", handle_other_node)

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
