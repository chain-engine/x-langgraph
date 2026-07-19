# -*- coding: utf-8 -*-
"""
RAG 文档问答工作流状态定义
"""

from typing import TypedDict, Optional, Annotated, Any
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class Document(TypedDict):
    """文档对象"""

    content: str  # 文档内容
    metadata: dict[str, Any]  # 元数据（来源、页码等）
    score: Optional[float]  # 相关性分数


class RAGQAState(TypedDict):
    """
    RAG 文档问答工作流状态

    展示 LangGraph 的状态管理能力：
    - 使用 Annotated 类型自动合并消息
    - 支持多字段状态
    """

    # 消息历史（使用 add_messages reducer 自动合并）
    messages: Annotated[list, add_messages]

    # 用户问题
    question: str

    # 检索阶段
    retrieved_docs: list[Document]  # 检索到的文档
    retrieval_score: Optional[float]  # 平均检索分数

    # 生成阶段
    context: str  # 构建的上下文
    output: str  # 最终回答

    # 来源追踪
    sources: list[str]  # 引用来源

    # 流程控制
    stage: str  # 'init', 'retrieve', 'build_context', 'generate', 'complete'
    needs_clarification: bool  # 是否需要澄清
    clarification_question: Optional[str]  # 澄清问题

    # 错误处理
    error: Optional[str]


class RAGQAResult(BaseModel):
    """RAG 问答结果"""

    question: str = Field(..., description="用户问题")
    output: str = Field(default="", description="生成的回答")
    sources: list[str] = Field(default_factory=list, description="引用来源")
    retrieved_docs_count: int = Field(default=0, description="检索到的文档数量")
    retrieval_score: Optional[float] = Field(default=None, description="平均检索分数")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
