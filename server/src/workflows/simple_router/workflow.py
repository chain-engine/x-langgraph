# -*- coding: utf-8 -*-
"""
简单路由工作流定义

展示 LangGraph 的基本功能：
- StateGraph 状态管理
- 条件边路由
- 多节点协作
- 继承 BaseWorkflow 基类
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from workflows.base import BaseWorkflow
from workflows.simple_router.state import SimpleRouterState
from workflows.simple_router.nodes import (
    router_node,
    search_node,
    calculate_node,
    weather_node,
    unknown_node,
)

from core.logger import logger


class SimpleRouterWorkflow(BaseWorkflow):
    """
    简单路由工作流

    根据用户输入自动路由到不同的处理节点：
    - search: 搜索信息
    - calculate: 数学计算
    - weather: 天气查询
    - unknown: 未知请求

    工作流结构:
        START → router → [条件路由]
                          ├→ search → END
                          ├→ calculate → END
                          ├→ weather → END
                          └→ unknown → END
    """

    name = "simple_router"
    description = "简单路由工作流：根据输入自动路由到搜索、计算或天气节点"

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
        workflow = StateGraph(SimpleRouterState)

        # 添加节点
        workflow.add_node("router", router_node)
        workflow.add_node("search", search_node)
        workflow.add_node("calculate", calculate_node)
        workflow.add_node("weather", weather_node)
        workflow.add_node("unknown", unknown_node)

        # 设置入口点
        workflow.set_entry_point("router")

        # 添加条件边
        workflow.add_conditional_edges(
            "router",
            self._route_by_type,
            {
                "search": "search",
                "calculate": "calculate",
                "weather": "weather",
                "unknown": "unknown",
            },
        )

        # 添加结束边
        workflow.add_edge("search", END)
        workflow.add_edge("calculate", END)
        workflow.add_edge("weather", END)
        workflow.add_edge("unknown", END)

        # 编译工作流
        checkpointer = self.checkpointer or MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    @staticmethod
    def _route_by_type(state: SimpleRouterState) -> str:
        """
        条件路由函数：根据 route 字段决定下一个节点

        Args:
            state: 当前状态

        Returns:
            下一个节点名称
        """
        route = state.get("route", "unknown")
        logger.info(f"路由决策: {route}")
        return route

    def run(self, input_text: str, thread_id: str = "default") -> dict:
        """
        运行工作流的便捷方法

        Args:
            input_text: 用户输入
            thread_id: 会话 ID

        Returns:
            执行结果
        """
        return self.invoke(
            {"input": input_text, "route": "", "output": "", "error": None},
            config={"configurable": {"thread_id": thread_id}},
        )

    async def arun(self, input_text: str, thread_id: str = "default") -> dict:
        """
        异步运行工作流的便捷方法

        Args:
            input_text: 用户输入
            thread_id: 会话 ID

        Returns:
            执行结果
        """
        return await self.ainvoke(
            {"input": input_text, "route": "", "output": "", "error": None},
            config={"configurable": {"thread_id": thread_id}},
        )


# ========== 工厂函数（保持向后兼容）==========

def create_simple_router_workflow(checkpointer: BaseCheckpointSaver | None = None) -> StateGraph:
    """
    创建简单路由工作流（工厂函数）

    Args:
        checkpointer: 状态持久化器（可选）

    Returns:
        编译后的工作流图
    """
    workflow = SimpleRouterWorkflow(checkpointer)
    return workflow.graph


def run_simple_router(input_text: str, thread_id: str = "default") -> dict:
    """
    运行简单路由工作流（便捷函数）

    Args:
        input_text: 用户输入
        thread_id: 会话 ID

    Returns:
        执行结果
    """
    workflow = SimpleRouterWorkflow()
    return workflow.run(input_text, thread_id)


async def arun_simple_router(input_text: str, thread_id: str = "default") -> dict:
    """
    异步运行简单路由工作流

    Args:
        input_text: 用户输入
        thread_id: 会话 ID

    Returns:
        执行结果
    """
    workflow = SimpleRouterWorkflow()
    return await workflow.arun(input_text, thread_id)
