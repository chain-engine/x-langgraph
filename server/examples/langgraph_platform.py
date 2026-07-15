# -*- coding: utf-8 -*-
"""
LangGraph Platform 部署示例

LangGraph Platform 是 LangChain 官方提供的托管服务，支持：
- 一键部署工作流
- 自动 API 生成
- 内置状态管理
- 流式输出支持

使用方法:
    1. 安装 LangGraph CLI: pip install langgraph-cli
    2. 配置 langgraph.json（项目根目录已有）
    3. 启动服务: langgraph dev
    4. 访问 API: http://localhost:8123

文档: https://langchain-ai.github.io/langgraph/cloud/
"""

from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


# 定义状态
class AgentState(TypedDict):
    """Agent 状态"""
    messages: Annotated[list[BaseMessage], add]


# 定义节点
def chatbot(state: AgentState) -> dict:
    """
    聊天机器人节点

    注意：在 LangGraph Platform 中，LLM 调用由平台管理
    这里仅作示例
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if last_message and isinstance(last_message, HumanMessage):
        # 模拟 AI 响应（实际使用时替换为真实 LLM 调用）
        response = f"收到您的消息: {last_message.content}"
        return {"messages": [AIMessage(content=response)]}

    return {"messages": [AIMessage(content="你好！有什么可以帮助你的吗？")]}


def create_graph():
    """
    创建工作流图

    LangGraph Platform 要求：
    1. 必须返回编译后的图
    2. 必须使用 checkpointer（生产环境由平台提供）
    """
    # 创建状态图
    builder = StateGraph(AgentState)

    # 添加节点
    builder.add_node("chatbot", chatbot)

    # 添加边
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)

    # 编译（LangGraph Platform 会自动注入 checkpointer）
    return builder.compile(checkpointer=MemorySaver())


# LangGraph Platform 入口点
# langgraph.json 中配置: "graphs": {"agent": "./examples/langgraph_platform.py:graph"}
graph = create_graph()


# 本地测试
if __name__ == "__main__":
    print("=" * 50)
    print("LangGraph Platform 示例")
    print("=" * 50)

    # 测试工作流
    result = graph.invoke(
        {"messages": [HumanMessage(content="你好")]},
        config={"configurable": {"thread_id": "test-123"}},
    )

    print(f"结果: {result}")

    # 流式测试
    print("\n流式输出:")
    for event in graph.stream(
        {"messages": [HumanMessage(content="LangGraph 是什么？")]},
        config={"configurable": {"thread_id": "test-456"}},
        stream_mode="updates",
    ):
        print(f"事件: {event}")

    print("\n" + "=" * 50)
    print("LangGraph Platform 部署步骤:")
    print("1. 安装 CLI: pip install langgraph-cli")
    print("2. 配置 langgraph.json（项目根目录已有）")
    print("3. 启动开发服务: langgraph dev")
    print("4. 访问 API: http://localhost:8123")
    print("5. 部署到云端: langgraph deploy")
    print("=" * 50)
