# -*- coding: utf-8 -*-
"""
RAG 文档问答工作流

展示 LangGraph 与 RAG (Retrieval-Augmented Generation) 的集成：
- 向量检索
- 文档分块
- 上下文构建
- LLM 生成回答
"""

from workflows.rag_qa.workflow import (
    create_rag_qa_workflow,
    run_rag_qa,
    stream_rag_qa,
)
from workflows.rag_qa.state import RAGQAState, RAGQAResult, Document

__all__ = [
    "create_rag_qa_workflow",
    "run_rag_qa",
    "stream_rag_qa",
    "RAGQAState",
    "RAGQAResult",
    "Document",
]
