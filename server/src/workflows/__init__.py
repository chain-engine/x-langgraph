# -*- coding: utf-8 -*-
"""
工作流模块

提供各类 LangGraph 工作流定义，展示状态管理、条件路由、人机交互等核心功能。

工作流列表：
- simple_router: 意图分类路由工作流（LLM 分类 + 条件分发）
- customer_service: 智能客服工作流（状态管理 + Checkpointer）
- rag_qa: RAG 文档问答工作流（向量检索 + LLM 生成）
- multi_agent: 多智能体协作工作流（任务分解 + 迭代优化）
- approval: 自动化审批工作流（人机交互 + 条件路由）

使用示例：
    # 意图分类路由
    from workflows.simple_router import run_simple_router
    result = run_simple_router("你们的产品多少钱？")

    # RAG 问答
    from workflows.rag_qa import run_rag_qa
    result = run_rag_qa("什么是 LangGraph？")

    # 多智能体
    from workflows.multi_agent import run_multi_agent
    result = run_multi_agent("编写一份分析报告")

    # 自动化审批
    from workflows.approval import run_approval
    result = run_approval(request)
"""

# 基类
from workflows.base import BaseWorkflow

# 意图分类路由工作流
from workflows.simple_router import (
    IntentClassifierWorkflow,
    create_simple_router_workflow,
    run_simple_router,
)

# 智能客服工作流
from workflows.customer_service import (
    create_customer_service_workflow,
    run_customer_service,
    stream_customer_service,
)

# RAG 文档问答工作流
from workflows.rag_qa import (
    create_rag_qa_workflow,
    run_rag_qa,
    stream_rag_qa,
    RAGQAState,
    RAGQAResult,
)

# 多智能体协作工作流
from workflows.multi_agent import (
    create_multi_agent_workflow,
    run_multi_agent,
    stream_multi_agent,
    AgentRole,
    MultiAgentResult,
)

# 自动化审批工作流
from workflows.approval import (
    create_approval_workflow,
    run_approval,
    run_approval_with_human,
    stream_approval,
    ApprovalType,
    ApprovalLevel,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalResult,
)

__all__ = [
    # 基类
    "BaseWorkflow",
    # 意图分类
    "IntentClassifierWorkflow",
    "create_simple_router_workflow",
    "run_simple_router",
    # 智能客服
    "create_customer_service_workflow",
    "run_customer_service",
    "stream_customer_service",
    # RAG 问答
    "create_rag_qa_workflow",
    "run_rag_qa",
    "stream_rag_qa",
    "RAGQAState",
    "RAGQAResult",
    # 多智能体
    "create_multi_agent_workflow",
    "run_multi_agent",
    "stream_multi_agent",
    "AgentRole",
    "MultiAgentResult",
    # 自动化审批
    "create_approval_workflow",
    "run_approval",
    "run_approval_with_human",
    "stream_approval",
    "ApprovalType",
    "ApprovalLevel",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalResult",
]
