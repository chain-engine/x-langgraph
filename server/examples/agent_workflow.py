# -*- coding: utf-8 -*-
"""
LangGraph 工作流示例入口

本文件演示如何使用 workflows 模块中的各种工作流。

运行方式:
    uv run python -m examples.agent_workflow
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langgraph.types import Command

from workflows.simple_router import create_simple_router_workflow, run_simple_router
from workflows.customer_service import (
    create_customer_service_workflow,
    run_customer_service,
    stream_customer_service,
)

from core.logger import logger


def demo_simple_router():
    """
    演示简单路由工作流

    展示功能：
    - StateGraph 状态管理
    - 条件边路由
    - 工具调用
    """
    print("\n" + "=" * 60)
    print("【示例 1】简单路由工作流")
    print("=" * 60)

    test_cases = [
        "搜索 Python 教程",
        "123 + 456 等于多少?",
        "北京今天天气怎么样?",
    ]

    for i, user_input in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {user_input} ---")
        result = run_simple_router(user_input, thread_id=f"test-{i}")
        print(f"路由: {result.get('route')}")
        print(f"结果: {result.get('output')[:100]}...")


def demo_customer_service():
    """
    演示智能客服工作流

    展示功能：
    - 复杂状态管理
    - 多级条件路由
    - Checkpointer 状态持久化
    - 流式输出
    """
    print("\n" + "=" * 60)
    print("【示例 2】智能客服工作流")
    print("=" * 60)

    test_cases = [
        ("我想咨询退款政策", "咨询类"),
        ("我要投诉你们的服务太差了", "投诉类"),
        ("我遇到了技术问题，无法登录", "技术类"),
    ]

    for i, (user_input, desc) in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {desc} ---")
        print(f"用户输入: {user_input}")

        # 使用流式输出
        print("\n[流式输出]")
        for event in stream_customer_service(user_input, thread_id=f"cs-{i}"):
            for node_name, node_output in event.items():
                print(f"  节点 [{node_name}]: ", end="")
                if isinstance(node_output, dict):
                    if "ticket_id" in node_output:
                        print(f"工单ID={node_output.get('ticket_id')}", end=", ")
                    if "ticket_type" in node_output:
                        print(f"类型={node_output.get('ticket_type')}", end="")
                print()


def demo_human_in_the_loop():
    """
    演示人机交互 (Human-in-the-loop)

    展示功能：
    - interrupt() 暂停执行
    - Command(resume=...) 恢复执行
    - Checkpointer 状态持久化
    """
    print("\n" + "=" * 60)
    print("【示例 3】人机交互 (Human-in-the-loop)")
    print("=" * 60)

    # 创建工作流
    graph = create_customer_service_workflow()
    config = {"configurable": {"thread_id": "hitl-demo"}}

    # 用户输入技术问题
    user_input = "我的账号遇到了技术问题，无法登录"
    print(f"\n用户输入: {user_input}")
    print("\n[第一阶段] 执行到人工审批节点...")

    # 初始状态
    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "stage": "",
        "ticket_id": None,
        "ticket_type": None,
        "priority": None,
        "customer_name": None,
        "resolution": None,
        "requires_approval": False,
        "approved": None,
        "approval_comments": None,
        "error": None,
    }

    # 流式执行直到中断
    for event in graph.stream(initial_state, config=config):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                print(f"  节点 [{node_name}]: 工单ID={node_output.get('ticket_id')}, 类型={node_output.get('ticket_type')}")

    # 检查当前状态
    state = graph.get_state(config)
    print(f"\n[中断点] 等待人工审批...")
    print(f"  当前状态: stage={state.values.get('stage')}")
    print(f"  工单信息: {state.values.get('ticket_id')}, 类型={state.values.get('ticket_type')}")

    # 模拟人工审批（审批通过）
    print("\n[第二阶段] 人工审批通过，恢复执行...")

    for event in graph.stream(
        Command(resume={"approved": True, "comments": "经核实，该问题需要技术支持团队处理"}),
        config=config,
    ):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                resolution = node_output.get("resolution", "")
                print(f"  节点 [{node_name}]: {resolution[:50] if resolution else ''}...")

    # 获取最终状态
    final_state = graph.get_state(config)
    print(f"\n[完成] 最终状态:")
    print(f"  工单ID: {final_state.values.get('ticket_id')}")
    print(f"  审批结果: {'通过' if final_state.values.get('approved') else '未通过'}")
    print(f"  解决方案: {final_state.values.get('resolution')}")


def demo_checkpointer():
    """
    演示 Checkpointer 状态持久化

    展示功能：
    - 会话状态保存
    - 会话恢复
    """
    print("\n" + "=" * 60)
    print("【示例 4】Checkpointer 状态持久化")
    print("=" * 60)

    from langgraph.checkpoint.memory import MemorySaver

    # 创建共享的 checkpointer
    checkpointer = MemorySaver()
    thread_id = "session-123"

    # 第一次请求
    print(f"\n[会话 {thread_id}] 第一次请求")
    graph1 = create_simple_router_workflow(checkpointer)
    result1 = graph1.invoke(
        {"input": "北京天气", "route": "", "output": "", "error": None},
        config={"configurable": {"thread_id": thread_id}},
    )
    print(f"  结果: {result1.get('output')[:100]}...")

    # 获取当前状态
    state = graph1.get_state({"configurable": {"thread_id": thread_id}})
    print(f"  保存的状态: input={state.values.get('input')}")

    # 第二次请求（使用同一个 thread_id，可以恢复之前的会话）
    print(f"\n[会话 {thread_id}] 恢复会话")
    graph2 = create_simple_router_workflow(checkpointer)
    previous_state = graph2.get_state({"configurable": {"thread_id": thread_id}})
    print(f"  恢复的状态: input={previous_state.values.get('input')}, route={previous_state.values.get('route')}")


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 60)
    print("  LangGraph 企业级工作流示例")
    print("=" * 60)

    logger.info("开始运行示例")

    # 运行各示例
    demo_simple_router()
    demo_customer_service()
    demo_human_in_the_loop()
    demo_checkpointer()

    print("\n" + "=" * 60)
    print("  所有示例运行完成!")
    print("=" * 60)

    logger.info("示例运行完成")


if __name__ == "__main__":
    main()
