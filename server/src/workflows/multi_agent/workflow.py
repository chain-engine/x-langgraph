# -*- coding: utf-8 -*-
"""
多智能体协作工作流定义

展示 LangGraph 的多智能体协作能力：
- 任务分解与分配
- 顺序执行
- 结果合并
- 迭代优化
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from workflows.multi_agent.state import (
    MultiAgentState,
    MultiAgentResult,
)
from workflows.multi_agent.nodes import (
    coordinator_node,
    researcher_node,
    writer_node,
    editor_node,
    reviewer_node,
    route_to_agent,
    should_continue,
)

from core.logger import logger


def create_multi_agent_workflow(
    checkpointer: MemorySaver | None = None,
    max_iterations: int = 3,
) -> StateGraph:
    """
    创建多智能体协作工作流

    Args:
        checkpointer: 状态持久化器（可选）
        max_iterations: 最大迭代次数

    Returns:
        编译后的工作流图

    工作流结构:
        START → coordinator → [条件路由]
                                 ├→ researcher
                                 ├→ writer
                                 ├→ editor → reviewer → [判断]
                                 │                       ├→ 迭代 (→ editor)
                                 │                       └→ END
                                 └→ complete → END
    """
    logger.info("创建多智能体协作工作流")

    # 创建状态图
    workflow = StateGraph(MultiAgentState)

    # 添加节点
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("editor", editor_node)
    workflow.add_node("reviewer", reviewer_node)

    # 设置入口点
    workflow.set_entry_point("coordinator")

    # 条件路由：协调者分配任务后路由到对应智能体
    workflow.add_conditional_edges(
        "coordinator",
        route_to_agent,
        {
            "researcher": "researcher",
            "writer": "writer",
            "editor": "editor",
            "reviewer": "reviewer",
            "complete": END,
        },
    )

    # 研究员完成后路由
    workflow.add_conditional_edges(
        "researcher",
        route_to_agent,
        {
            "researcher": "researcher",
            "writer": "writer",
            "editor": "editor",
            "reviewer": "reviewer",
            "complete": END,
        },
    )

    # 撰写者完成后路由
    workflow.add_conditional_edges(
        "writer",
        route_to_agent,
        {
            "researcher": "researcher",
            "writer": "writer",
            "editor": "editor",
            "reviewer": "reviewer",
            "complete": END,
        },
    )

    # 编辑完成后路由到审核员
    workflow.add_edge("editor", "reviewer")

    # 审核员完成后判断是否继续迭代
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "continue": "editor",  # 需要修订，回到编辑
            "complete": END,  # 完成
        },
    )

    # 创建 Checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()

    # 编译工作流
    return workflow.compile(checkpointer=checkpointer)


def run_multi_agent(
    request: str,
    thread_id: str = "default",
    max_iterations: int = 3,
    checkpointer: MemorySaver | None = None,
) -> MultiAgentResult:
    """
    运行多智能体协作

    Args:
        request: 用户请求
        thread_id: 会话 ID
        max_iterations: 最大迭代次数
        checkpointer: 状态持久化器

    Returns:
        MultiAgentResult 结果对象
    """
    logger.info(f"Multi-Agent: 开始处理 - {request[:50]}...")

    graph = create_multi_agent_workflow(checkpointer, max_iterations)
    config = {"configurable": {"thread_id": thread_id}}

    # 初始状态
    initial_state: MultiAgentState = {
        "original_request": request,
        "messages": [HumanMessage(content=request)],
        "subtasks": [],
        "completed_tasks": [],
        "research_findings": "",
        "draft_content": "",
        "edited_content": "",
        "review_feedback": "",
        "final_output": "",
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "current_stage": "init",
        "needs_revision": False,
        "revision_requests": [],
        "error": None,
        "failed_agents": [],
    }

    # 执行工作流
    result = graph.invoke(initial_state, config=config)

    # 构建返回结果
    agent_outputs = {
        "research": result.get("research_findings", ""),
        "draft": result.get("draft_content", ""),
        "edited": result.get("edited_content", ""),
        "review": result.get("review_feedback", ""),
    }

    return MultiAgentResult(
        original_request=request,
        final_output=result.get("final_output", result.get("edited_content", "")),
        subtasks_completed=len(result.get("completed_tasks", [])),
        iteration_count=result.get("iteration_count", 0),
        agent_outputs=agent_outputs,
        success=result.get("error") is None,
        error=result.get("error"),
    )


def stream_multi_agent(
    request: str,
    thread_id: str = "default",
    max_iterations: int = 3,
    checkpointer: MemorySaver | None = None,
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
    logger.info(f"Multi-Agent: 流式处理 - {request[:50]}...")

    graph = create_multi_agent_workflow(checkpointer, max_iterations)
    config = {"configurable": {"thread_id": thread_id}}

    # 初始状态
    initial_state: MultiAgentState = {
        "original_request": request,
        "messages": [HumanMessage(content=request)],
        "subtasks": [],
        "completed_tasks": [],
        "research_findings": "",
        "draft_content": "",
        "edited_content": "",
        "review_feedback": "",
        "final_output": "",
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "current_stage": "init",
        "needs_revision": False,
        "revision_requests": [],
        "error": None,
        "failed_agents": [],
    }

    # 流式执行
    yield from graph.stream(initial_state, config=config, stream_mode=stream_mode)
