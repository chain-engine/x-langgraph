# -*- coding: utf-8 -*-
"""
多智能体协作工作流

展示 LangGraph 的多智能体协作能力：
- Agent 角色：研究员、撰写者、编辑、审核员
- 任务分解与分配
- 结果合并与迭代优化
- 并行执行
"""

from workflows.multi_agent.workflow import (
    create_multi_agent_workflow,
    run_multi_agent,
    stream_multi_agent,
)
from workflows.multi_agent.state import AgentRole, MultiAgentResult

__all__ = [
    "create_multi_agent_workflow",
    "run_multi_agent",
    "stream_multi_agent",
    "AgentRole",
    "MultiAgentResult",
]
