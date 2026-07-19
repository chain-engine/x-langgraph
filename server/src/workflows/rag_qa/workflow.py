# -*- coding: utf-8 -*-
"""
RAG 文档问答工作流定义

展示 LangGraph 与 RAG (Retrieval-Augmented Generation) 的集成：
- 向量检索
- 文档分块
- 上下文构建
- LLM 生成回答
- 条件路由
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from workflows.rag_qa.state import RAGQAState, RAGQAResult
from workflows.rag_qa.nodes import (
    init_node,
    retrieve_node,
    build_context_node,
    generate_node,
    clarify_node,
    should_retrieve,
    should_generate,
)

from core.logger import logger


def create_rag_qa_workflow(checkpointer: MemorySaver | None = None) -> StateGraph:
    """
    创建 RAG 文档问答工作流

    Args:
        checkpointer: 状态持久化器（可选）

    Returns:
        编译后的工作流图

    工作流结构:
        START → init → [条件路由]
                         ├→ clarify → END
                         └→ retrieve → [条件路由]
                                        ├→ build_context → generate → END
                                        └→ generate → END
    """
    logger.info("创建 RAG 文档问答工作流")

    # 创建状态图
    workflow = StateGraph(RAGQAState)

    # 添加节点
    workflow.add_node("init", init_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("build_context", build_context_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("clarify", clarify_node)

    # 设置入口点
    workflow.set_entry_point("init")

    # 条件路由：初始化后判断是否需要澄清
    workflow.add_conditional_edges(
        "init",
        should_retrieve,
        {
            "retrieve": "retrieve",
            "clarify": "clarify",
        },
    )

    # 条件路由：检索后判断是否有足够上下文
    workflow.add_conditional_edges(
        "retrieve",
        should_generate,
        {
            "build_context": "build_context",
            "generate": "generate",
        },
    )

    # 普通边
    workflow.add_edge("build_context", "generate")
    workflow.add_edge("clarify", END)
    workflow.add_edge("generate", END)

    # 创建 Checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()

    # 编译工作流
    return workflow.compile(checkpointer=checkpointer)


def run_rag_qa(
    question: str,
    thread_id: str = "default",
    checkpointer: MemorySaver | None = None,
) -> RAGQAResult:
    """
    运行 RAG 文档问答

    Args:
        question: 用户问题
        thread_id: 会话 ID（用于状态持久化）
        checkpointer: 状态持久化器

    Returns:
        RAGQAResult 结果对象
    """
    logger.info(f"RAG QA: 开始处理 - {question[:50]}...")

    graph = create_rag_qa_workflow(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    # 初始状态
    initial_state: RAGQAState = {
        "messages": [HumanMessage(content=question)],
        "question": "",
        "retrieved_docs": [],
        "retrieval_score": None,
        "context": "",
        "output": "",
        "sources": [],
        "stage": "",
        "needs_clarification": False,
        "clarification_question": None,
        "error": None,
    }

    # 执行工作流
    result = graph.invoke(initial_state, config=config)

    # 构建返回结果
    return RAGQAResult(
        question=result.get("question", question),
        answer=result.get("output", ""),
        sources=result.get("sources", []),
        retrieved_docs_count=len(result.get("retrieved_docs", [])),
        retrieval_score=result.get("retrieval_score"),
        success=result.get("error") is None,
        error=result.get("error"),
    )


def stream_rag_qa(
    question: str,
    thread_id: str = "default",
    checkpointer: MemorySaver | None = None,
    stream_mode: str = "updates",
):
    """
    流式运行 RAG 文档问答

    Args:
        question: 用户问题
        thread_id: 会话 ID
        checkpointer: 状态持久化器
        stream_mode: 流式模式

    Yields:
        每个节点的更新
    """
    logger.info(f"RAG QA: 流式处理 - {question[:50]}...")

    graph = create_rag_qa_workflow(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    # 初始状态
    initial_state: RAGQAState = {
        "messages": [HumanMessage(content=question)],
        "question": "",
        "retrieved_docs": [],
        "retrieval_score": None,
        "context": "",
        "output": "",
        "sources": [],
        "stage": "",
        "needs_clarification": False,
        "clarification_question": None,
        "error": None,
    }

    # 流式执行
    yield from graph.stream(initial_state, config=config, stream_mode=stream_mode)
