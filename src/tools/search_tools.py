# -*- coding: utf-8 -*-
"""
搜索工具模块

提供网络搜索和文档检索功能。
支持真实搜索 API 和模拟数据降级。
"""

import httpx
from typing import Optional

from langchain_core.tools import tool
from core.logger import logger
from config.settings import settings


@tool
def web_search_tool(query: str) -> str:
    """
    网络搜索工具，用于搜索互联网上的信息。

    Args:
        query: 搜索关键词或问题

    Returns:
        搜索结果摘要
    """
    logger.info(f"执行网络搜索: {query}")

    try:
        result = _real_web_search(query)
        if result:
            return result
    except Exception as e:
        logger.warning(f"真实搜索失败，使用模拟数据: {e}")

    return _mock_web_search(query)


def _real_web_search(query: str) -> str:
    """
    使用真实搜索 API

    Args:
        query: 搜索关键词

    Returns:
        搜索结果摘要，失败返回空字符串
    """
    search_api_key = getattr(settings, "SEARCH_API_KEY", "")
    search_api_url = getattr(settings, "SEARCH_API_URL", "")

    if not search_api_key or not search_api_url:
        return ""

    try:
        with httpx.Client() as client:
            response = client.get(
                search_api_url,
                params={"q": query, "key": search_api_key},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("results"):
                results = []
                for item in data["results"][:3]:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    results.append(f"- {title}: {snippet}")
                return "\n".join(results)
            return ""

    except Exception as e:
        logger.error(f"真实搜索 API 调用失败: {e}")
        return ""


def _mock_web_search(query: str) -> str:
    """
    模拟搜索（降级方案）

    Args:
        query: 搜索关键词

    Returns:
        模拟搜索结果
    """
    results = {
        "langgraph": "LangGraph 是用于构建有状态、多参与者应用程序的库，基于 LangChain 构建。",
        "python": "Python 是一种高级编程语言，以其简洁的语法和强大的生态系统著称。",
        "人工智能": "人工智能(AI)是计算机科学的一个分支，致力于创建能够执行需要人类智能的任务的系统。",
        "langchain": "LangChain 是一个用于开发由语言模型驱动的应用程序的框架。",
        "fastapi": "FastAPI 是一个现代、快速的 Web 框架，用于构建 API。",
        "mysql": "MySQL 是一个开源的关系型数据库管理系统。",
    }

    for keyword, result in results.items():
        if keyword.lower() in query.lower():
            return f"搜索结果: {result}"

    return f"搜索结果: 未找到与 '{query}' 相关的信息，请尝试其他关键词。\n\n提示：配置 SEARCH_API_KEY 和 SEARCH_API_URL 可获取实时搜索结果。"


@tool
def document_search_tool(query: str, doc_type: Optional[str] = None) -> str:
    """
    文档检索工具，用于在文档库中搜索相关内容。

    Args:
        query: 搜索查询
        doc_type: 文档类型过滤（可选），如 'pdf', 'doc', 'txt'

    Returns:
        匹配的文档内容摘要
    """
    logger.info(f"执行文档搜索: query={query}, doc_type={doc_type}")

    # 模拟文档库
    documents = [
        {
            "title": "LangGraph 入门指南",
            "content": "LangGraph 是构建有状态 AI 应用的框架，支持循环、分支和持久化。",
            "type": "pdf",
        },
        {
            "title": "Python 最佳实践",
            "content": "使用类型注解、编写文档字符串、遵循 PEP 8 规范。",
            "type": "doc",
        },
        {
            "title": "API 设计规范",
            "content": "RESTful API 应遵循统一接口、无状态、可缓存等原则。",
            "type": "txt",
        },
    ]

    # 过滤并搜索
    matched = []
    for doc in documents:
        if doc_type and doc["type"] != doc_type:
            continue
        if query.lower() in doc["content"].lower() or query.lower() in doc["title"].lower():
            matched.append(doc)

    if matched:
        result = "找到以下相关文档:\n"
        for doc in matched:
            result += f"- {doc['title']}: {doc['content'][:50]}...\n"
        return result

    return f"未找到与 '{query}' 相关的文档。"
