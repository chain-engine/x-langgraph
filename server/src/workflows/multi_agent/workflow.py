# -*- coding: utf-8 -*-
"""
多智能体协作工作流定义

展示 LangGraph 的多智能体协作能力：
- LLM 动态任务分解
- 顺序执行与依赖管理
- 结果合并与迭代优化
- 流式输出
- Checkpointer 状态持久化
- 继承 BaseWorkflow 基类

预留接口：
- Handoff 模式（handoff_to_agent）
- Team 模式（parallel_execute）
- Tool Calling（bind_tools）

工作流结构:
    START → coordinator → [条件路由]
                             ├→ researcher
                             ├→ writer
                             ├→ editor → reviewer → [判断]
                             │                     ├→ 迭代 (→ editor)
                             │                     └→ END
                             └→ complete → END
"""

from typing import Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from workflows.base import BaseWorkflow
from workflows.multi_agent.state import (
    MultiAgentState,
    MultiAgentResult,
    AgentRole,
)

from workflows.multi_agent.nodes import (
    coordinator_node,
    researcher_node,
    writer_node,
    editor_node,
    reviewer_node,
    route_to_agent_node,
    should_continue_node,
)

from core.logger import logger


class MultiAgentWorkflow(BaseWorkflow):
    """
    多智能体协作工作流

    基于 LangGraph 的多 Agent 协作系统，包含：
    - 协调者（Coordinator）：任务分解
    - 研究员（Researcher）：信息收集
    - 撰写者（Writer）：内容生成
    - 编辑（Editor）：内容优化
    - 审核员（Reviewer）：质量控制

    Features:
    - LLM 驱动的动态任务分解
    - 迭代优化（最多 3 轮）
    - 流式执行支持
    - 状态持久化

    预留扩展点：
    - Handoff 模式：Agent 间控制权传递
    - Team 模式：并行任务执行
    - Tool Calling：工具调用能力
    """

    name = "multi_agent"
    description = "多智能体协作工作流：协调者分解任务，研究员收集信息，撰写者生成内容，编辑优化，审核员审核质量"

    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        """
        初始化工作流

        Args:
            checkpointer: 状态持久化器（可选）
        """
        super().__init__(checkpointer)

    def build(self) -> StateGraph:
        """
        构建工作流图

        Returns:
            编译后的 StateGraph
        """
        logger.info(f"构建工作流: {self.name}")

        # 创建状态图
        workflow = StateGraph(MultiAgentState)

        # ===== 添加节点 =====
        workflow.add_node("coordinator", coordinator_node)
        workflow.add_node("researcher", researcher_node)
        workflow.add_node("writer", writer_node)
        workflow.add_node("editor", editor_node)
        workflow.add_node("reviewer", reviewer_node)

        # ===== 设置入口点 =====
        workflow.set_entry_point("coordinator")

        # ===== 条件路由：协调者分配任务后路由到对应智能体 =====
        workflow.add_conditional_edges(
            "coordinator",
            route_to_agent_node,
            {
                "researcher": "researcher",
                "writer": "writer",
                "editor": "editor",
                "reviewer": "reviewer",
                "complete": END,
            },
        )

        # ===== 研究员完成后路由 =====
        workflow.add_conditional_edges(
            "researcher",
            route_to_agent_node,
            {
                "researcher": "researcher",
                "writer": "writer",
                "editor": "editor",
                "reviewer": "reviewer",
                "complete": END,
            },
        )

        # ===== 撰写者完成后路由 =====
        workflow.add_conditional_edges(
            "writer",
            route_to_agent_node,
            {
                "researcher": "researcher",
                "writer": "writer",
                "editor": "editor",
                "reviewer": "reviewer",
                "complete": END,
            },
        )

        # ===== 编辑完成后路由到审核员 =====
        workflow.add_edge("editor", "reviewer")

        # ===== 审核员完成后判断是否继续迭代 =====
        workflow.add_conditional_edges(
            "reviewer",
            should_continue_node,
            {
                "continue": "editor",  # 需要修订，回到编辑
                "complete": END,  # 完成
            },
        )

        # ===== 编译工作流 =====
        checkpointer = self.checkpointer or MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    def _create_initial_state(
        self,
        request: str,
        thread_id: str = "default",
        max_iterations: int = 3,
    ) -> MultiAgentState:
        """
        创建初始状态

        Args:
            request: 用户请求
            thread_id: 会话 ID
            max_iterations: 最大迭代次数

        Returns:
            初始状态字典
        """
        return {
            "messages": [HumanMessage(content=request)],
            "original_request": request,
            "thread_id": thread_id,
            "tasks": [],
            "completed_tasks": [],
            "current_task_id": None,
            "research_findings": "",
            "draft_content": "",
            "edited_content": "",
            "review_feedback": "",
            "final_output": "",
            "current_stage": "init",
            "current_agent": None,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "needs_revision": False,
            "revision_requests": [],
            "handoffs": [],
            "pending_handoff": None,
            "error": None,
            "failed_agents": [],
        }

    def run(
        self,
        request: str,
        thread_id: str = "default",
        max_iterations: int = 3,
    ) -> MultiAgentResult:
        """
        运行工作流的便捷方法

        Args:
            request: 用户请求
            thread_id: 会话 ID
            max_iterations: 最大迭代次数

        Returns:
            MultiAgentResult 结果对象
        """
        import time

        start_time = time.time()

        result = self.invoke(
            self._create_initial_state(request, thread_id, max_iterations),
            config={"configurable": {"thread_id": thread_id}},
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return self._build_result(result, request, duration_ms)

    async def arun(
        self,
        request: str,
        thread_id: str = "default",
        max_iterations: int = 3,
    ) -> MultiAgentResult:
        """
        异步运行工作流的便捷方法

        Args:
            request: 用户请求
            thread_id: 会话 ID
            max_iterations: 最大迭代次数

        Returns:
            MultiAgentResult 结果对象
        """
        import time
        import asyncio

        start_time = time.time()

        result = await self.ainvoke(
            self._create_initial_state(request, thread_id, max_iterations),
            config={"configurable": {"thread_id": thread_id}},
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return self._build_result(result, request, duration_ms)

    def stream_run(
        self,
        request: str,
        thread_id: str = "default",
        max_iterations: int = 3,
        stream_mode: str = "updates",
    ):
        """
        流式运行工作流

        Args:
            request: 用户请求
            thread_id: 会话 ID
            max_iterations: 最大迭代次数
            stream_mode: 流式模式

        Yields:
            每个节点的更新
        """
        yield from self.stream(
            self._create_initial_state(request, thread_id, max_iterations),
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=stream_mode,
        )

    async def astream_run(
        self,
        request: str,
        thread_id: str = "default",
        max_iterations: int = 3,
        stream_mode: str = "updates",
    ):
        """
        异步流式运行工作流

        Args:
            request: 用户请求
            thread_id: 会话 ID
            max_iterations: 最大迭代次数
            stream_mode: 流式模式

        Yields:
            每个节点的更新
        """
        async for event in self.astream(
            self._create_initial_state(request, thread_id, max_iterations),
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=stream_mode,
        ):
            yield event

    def _build_result(
        self,
        result: dict,
        request: str,
        duration_ms: int,
    ) -> MultiAgentResult:
        """
        构建结果对象

        Args:
            result: 工作流执行结果
            request: 原始请求
            duration_ms: 执行耗时

        Returns:
            MultiAgentResult 对象
        """
        tasks = result.get("tasks", [])
        completed_tasks = result.get("completed_tasks", [])

        # 构建 Agent 输出字典
        agent_outputs = {
            "research": result.get("research_findings", ""),
            "draft": result.get("draft_content", ""),
            "edited": result.get("edited_content", ""),
            "review": result.get("review_feedback", ""),
        }

        # 获取最终输出
        final_output = result.get("final_output", "")
        if not final_output:
            final_output = result.get("edited_content", "")

        # 获取 Handoff 记录
        handoffs = result.get("handoffs", [])

        return MultiAgentResult(
            original_request=request,
            final_output=final_output,
            tasks_completed=len(completed_tasks),
            tasks_total=len(tasks),
            iteration_count=result.get("iteration_count", 0),
            agent_outputs=agent_outputs,
            handoffs=handoffs,
            success=result.get("error") is None,
            error=result.get("error"),
            duration_ms=duration_ms,
        )


# ========== 工厂函数（保持向后兼容）==========

def create_multi_agent_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
    max_iterations: int = 3,
) -> StateGraph:
    """
    创建多智能体协作工作流（工厂函数）

    Args:
        checkpointer: 状态持久化器
        max_iterations: 最大迭代次数（预留参数）

    Returns:
        编译后的工作流图
    """
    workflow = MultiAgentWorkflow(checkpointer)
    return workflow.graph


def run_multi_agent(
    request: str,
    thread_id: str = "default",
    max_iterations: int = 3,
    checkpointer: BaseCheckpointSaver | None = None,
) -> MultiAgentResult:
    """
    运行多智能体协作（便捷函数）

    Args:
        request: 用户请求
        thread_id: 会话 ID
        max_iterations: 最大迭代次数
        checkpointer: 状态持久化器

    Returns:
        MultiAgentResult 结果对象
    """
    workflow = MultiAgentWorkflow(checkpointer)
    return workflow.run(request, thread_id, max_iterations)


async def arun_multi_agent(
    request: str,
    thread_id: str = "default",
    max_iterations: int = 3,
    checkpointer: BaseCheckpointSaver | None = None,
) -> MultiAgentResult:
    """
    异步运行多智能体协作（便捷函数）

    Args:
        request: 用户请求
        thread_id: 会话 ID
        max_iterations: 最大迭代次数
        checkpointer: 状态持久化器

    Returns:
        MultiAgentResult 结果对象
    """
    workflow = MultiAgentWorkflow(checkpointer)
    return await workflow.arun(request, thread_id, max_iterations)


def stream_multi_agent(
    request: str,
    thread_id: str = "default",
    max_iterations: int = 3,
    checkpointer: BaseCheckpointSaver | None = None,
    stream_mode: str = "updates",
):
    """
    流式运行多智能体协作

    Args:
        request: 用户请求
        thread_id: 会话 ID
        max_iterations: 最大迭代次数
        checkpointer: 状态持久化器
        stream_mode: 流式模式

    Yields:
        每个节点的更新
    """
    workflow = MultiAgentWorkflow(checkpointer)
    yield from workflow.stream_run(request, thread_id, max_iterations, stream_mode)


async def astream_multi_agent(
    request: str,
    thread_id: str = "default",
    max_iterations: int = 3,
    checkpointer: BaseCheckpointSaver | None = None,
    stream_mode: str = "updates",
):
    """
    异步流式运行多智能体协作

    Args:
        request: user_input: 用户请求
        thread_id: 会话 ID
        max_iterations: 最大迭代次数
        checkpointer: 状态持久化器
        stream_mode: 流式模式

    Yields:
        每个节点的更新
    """
    workflow = MultiAgentWorkflow(checkpointer)
    async for event in workflow.astream_run(request, thread_id, max_iterations, stream_mode):
        yield event
