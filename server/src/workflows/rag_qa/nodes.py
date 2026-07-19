# -*- coding: utf-8 -*-
"""
RAG 文档问答工作流节点定义

展示 LangGraph 的节点设计：
- 纯函数节点
- 状态转换
- 错误处理
"""

from typing import Any

from langchain_core.messages import HumanMessage, AIMessage

from workflows.rag_qa.state import RAGQAState, Document
from llms.providers import get_llm_provider
from llms.prompts import prompt_manager
from core.logger import logger


# ===== 模拟向量数据库（实际项目中替换为真实的向量数据库）=====
_MOCK_VECTOR_STORE: list[dict[str, Any]] = [
    {
        "content": "LangGraph 是一个用于构建有状态、多参与者应用程序的库。它基于 LangChain 构建，提供了图结构的工作流编排能力。",
        "metadata": {"source": "langgraph_docs.md", "section": "introduction"},
        "embedding": [0.1, 0.2, 0.3],
    },
    {
        "content": "StateGraph 是 LangGraph 的核心概念，它允许你定义状态机，其中每个节点可以更新状态，边定义了节点之间的流转。",
        "metadata": {"source": "langgraph_docs.md", "section": "state_graph"},
        "embedding": [0.2, 0.3, 0.4],
    },
    {
        "content": "Checkpointer 用于持久化工作流状态，支持暂停和恢复执行。常用的有 MemorySaver 和 SqliteSaver。",
        "metadata": {"source": "langgraph_docs.md", "section": "checkpointer"},
        "embedding": [0.3, 0.4, 0.5],
    },
    {
        "content": "Human-in-the-loop 模式允许工作流在关键节点暂停，等待人工审批或输入后继续执行。使用 interrupt() 函数实现。",
        "metadata": {"source": "langgraph_docs.md", "section": "human_in_loop"},
        "embedding": [0.4, 0.5, 0.6],
    },
    {
        "content": "LangChain 是一个用于开发由语言模型驱动的应用程序的框架。它提供了模型 I/O、数据连接、链式调用等核心功能。",
        "metadata": {"source": "langchain_docs.md", "section": "overview"},
        "embedding": [0.5, 0.6, 0.7],
    },
]


def init_node(state: RAGQAState) -> dict:
    """
    初始化节点

    解析用户问题，设置初始状态

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("RAG: 初始化")

    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            question = last_message.get("content", "")
        elif isinstance(last_message, HumanMessage):
            question = last_message.content
        else:
            question = str(last_message)
    else:
        question = state.get("question", "")

    logger.info(f"RAG: 问题 - {question[:50]}...")

    return {
        "question": question,
        "stage": "init",
        "retrieved_docs": [],
        "retrieval_score": None,
        "context": "",
        "output": "",
        "sources": [],
        "needs_clarification": False,
        "clarification_question": None,
        "error": None,
    }


def retrieve_node(state: RAGQAState) -> dict:
    """
    检索节点

    从向量数据库检索相关文档

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    question = state.get("question", "")
    logger.info(f"RAG: 检索文档 - {question[:50]}...")

    try:
        # 模拟向量检索（实际项目中使用真实的向量数据库）
        retrieved_docs = _mock_retrieve(question)

        # 计算平均检索分数
        scores = [doc.get("score", 0) for doc in retrieved_docs]
        avg_score = sum(scores) / len(scores) if scores else 0

        logger.info(f"RAG: 检索到 {len(retrieved_docs)} 个文档，平均分数: {avg_score:.2f}")

        return {
            "retrieved_docs": retrieved_docs,
            "retrieval_score": avg_score,
            "stage": "retrieve",
        }

    except Exception as e:
        logger.error(f"RAG: 检索失败 - {e}")
        return {
            "retrieved_docs": [],
            "retrieval_score": 0,
            "stage": "retrieve",
            "error": f"检索失败: {str(e)}",
        }


def build_context_node(state: RAGQAState) -> dict:
    """
    构建上下文节点

    将检索到的文档构建为上下文字符串

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("RAG: 构建上下文")

    docs = state.get("retrieved_docs", [])

    if not docs:
        return {
            "context": "未找到相关文档。",
            "stage": "build_context",
        }

    # 构建上下文
    context_parts = []
    sources = []

    for i, doc in enumerate(docs, 1):
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        source = metadata.get("source", "未知来源")

        context_parts.append(f"[文档 {i}] (来源: {source})\n{content}")
        sources.append(source)

    context = "\n\n".join(context_parts)

    return {
        "context": context,
        "sources": list(set(sources)),  # 去重
        "stage": "build_context",
    }


def generate_node(state: RAGQAState) -> dict:
    """
    生成回答节点

    使用 LLM 基于上下文生成回答

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("RAG: 生成回答")

    question = state.get("question", "")
    context = state.get("context", "")

    try:
        # 获取 LLM 提供者
        provider = get_llm_provider("deepseek")

        # 创建聊天提示
        prompt = prompt_manager.create_chat_prompt(
            system_template="rag_system",
            user_template="rag_user",
            context=context,
        )

        # 构建消息
        messages = prompt.format_messages(question=question)

        # 调用 LLM
        response = provider.invoke(messages)

        answer = response.content if hasattr(response, "content") else str(response)

        logger.info(f"RAG: 生成完成 - {len(answer)} 字符")

        return {
            "output": answer,
            "stage": "complete",
        }

    except Exception as e:
        logger.error(f"RAG: 生成失败 - {e}")

        # 降级处理：使用模拟回答
        fallback_answer = _generate_fallback_answer(question, context)

        return {
            "output": fallback_answer,
            "stage": "complete",
            "error": f"LLM 调用失败，使用降级回答: {str(e)}",
        }


def clarify_node(state: RAGQAState) -> dict:
    """
    澄清节点

    当问题不明确时，生成澄清问题

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("RAG: 生成澄清问题")

    question = state.get("question", "")

    # 简单规则判断是否需要澄清
    if len(question) < 5:
        clarification = "您的问题太简短，能否提供更多上下文？"
        return {
            "needs_clarification": True,
            "clarification_question": clarification,
            "stage": "complete",
        }

    # 不需要澄清
    return {
        "needs_clarification": False,
        "clarification_question": None,
    }


def should_retrieve(state: RAGQAState) -> str:
    """
    条件路由：判断是否需要检索

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    question = state.get("question", "")

    # 如果问题太短，先澄清
    if len(question) < 5:
        return "clarify"

    return "retrieve"


def should_generate(state: RAGQAState) -> str:
    """
    条件路由：判断是否有足够上下文生成

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    docs = state.get("retrieved_docs", [])
    score = state.get("retrieval_score", 0)

    # 如果没有找到文档或分数太低，直接使用 LLM 知识
    if not docs or score < 0.3:
        logger.info("RAG: 检索结果不足，使用 LLM 知识库")
        return "generate"

    return "build_context"


# ===== 辅助函数 =====


def _mock_retrieve(query: str, top_k: int = 3) -> list[Document]:
    """
    模拟向量检索

    实际项目中应替换为真实的向量数据库检索

    Args:
        query: 查询文本
        top_k: 返回的文档数量

    Returns:
        检索到的文档列表
    """
    # 简单的关键词匹配模拟
    query_lower = query.lower()

    results = []
    for doc in _MOCK_VECTOR_STORE:
        content = doc["content"].lower()

        # 计算简单的相似度分数
        score = 0
        for word in query_lower.split():
            if word in content:
                score += 0.2

        if score > 0:
            results.append(
                {
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": min(score, 1.0),
                }
            )

    # 按分数排序并返回 top_k
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:top_k]


def _generate_fallback_answer(question: str, context: str) -> str:
    """
    生成降级回答

    当 LLM 不可用时使用

    Args:
        question: 用户问题
        context: 上下文

    Returns:
        降级回答
    """
    if context and context != "未找到相关文档。":
        return f"""基于检索到的文档，以下是我找到的相关信息：

{context}

---
注意：由于 LLM 服务暂时不可用，以上是原始检索结果。如需更精确的回答，请稍后重试。"""

    return f"""抱歉，未能找到与 "{question}" 相关的文档。

建议：
1. 尝试使用不同的关键词
2. 检查问题是否清晰明确
3. 联系管理员添加相关文档

（注：LLM 服务暂时不可用，使用降级模式响应）"""
