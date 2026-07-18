# -*- coding: utf-8 -*-
"""
多智能体协作工作流

展示 LangGraph 的多智能体协作能力：
- Agent 角色：协调者、研究员、撰写者、编辑、审核员
- 任务分解与分配
- LLM 驱动的动态分解
- 结果合并与迭代优化
- 流式执行
- Checkpointer 状态持久化

预留接口（方便后续扩展）：
- Handoff 模式：Agent 间控制权传递
- Team 模式：并行任务执行
- Tool Calling：工具调用能力
"""

from workflows.multi_agent.workflow import (
    MultiAgentWorkflow,
    create_multi_agent_workflow,
    run_multi_agent,
    arun_multi_agent,
    stream_multi_agent,
    astream_multi_agent,
)

from workflows.multi_agent.state import (
    AgentRole,
    TaskStatus,
    TaskPriority,
    SubTask,
    HandoffInfo,
    AgentOutput,
    MultiAgentState,
    MultiAgentResult,
)

from workflows.multi_agent.nodes import (
    # 节点函数
    coordinator_node,
    researcher_node,
    writer_node,
    editor_node,
    reviewer_node,
    # 路由函数
    route_to_agent_node,
    should_continue_node,
    # Handoff 预留函数
    create_handoff,
    execute_handoff,
    initiate_handoff,
    route_with_handoff,
    # 并行执行预留函数
    route_for_parallel_node,
    # Tool Calling 预留函数
    bind_tools_to_agent,
    create_researcher_with_tools,
)

__all__ = [
    # 工作流类
    "MultiAgentWorkflow",
    # 工厂函数
    "create_multi_agent_workflow",
    "run_multi_agent",
    "arun_multi_agent",
    "stream_multi_agent",
    "astream_multi_agent",
    # 状态类型
    "AgentRole",
    "TaskStatus",
    "TaskPriority",
    "SubTask",
    "HandoffInfo",
    "AgentOutput",
    "MultiAgentState",
    "MultiAgentResult",
    # 节点函数
    "coordinator_node",
    "researcher_node",
    "writer_node",
    "editor_node",
    "reviewer_node",
    # 路由函数
    "route_to_agent",
    "should_continue",
    # Handoff 预留
    "create_handoff",
    "execute_handoff",
    "initiate_handoff",
    "route_with_handoff",
    # 并行执行预留
    "route_for_parallel",
    # Tool Calling 预留
    "bind_tools_to_agent",
    "create_researcher_with_tools",
]
