# -*- coding: utf-8 -*-
"""
LangGraph 工作流示例入口

运行方式:
    uv run python -m examples.agent_workflow
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langgraph.types import Command

from workflows.intent_classifier import IntentClassifierWorkflow
from workflows.customer_service import (
    create_customer_service_workflow,
    stream_customer_service,
)

from core.logger import logger


def demo_intent_classifier():
    """演示意图分类路由工作流"""
    print("\n" + "=" * 60)
    print("【示例 1】意图分类路由工作流")
    print("=" * 60)

    test_cases = [
        ("你们的产品多少钱？", "产品咨询"),
        ("我的订单什么时候发货？", "订单状态"),
        ("登录报错，无法正常使用", "技术支持"),
        ("服务太差了，我要投诉", "投诉"),
        ("这个月的账单有问题", "账单"),
        ("你好，今天天气不错", "其他"),
    ]

    wf = IntentClassifierWorkflow()
    for i, (user_input, desc) in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {desc} ---")
        result = wf.invoke(
            user_input,
            config={"configurable": {"thread_id": f"ic-{i}"}}
        )
        print(f"意图: {result.get('intent')}")
        print(f"置信度: {result.get('confidence', 'N/A')}")
        print(f"响应: {result.get('response', '')[:60]}...")


def demo_customer_service():
    """演示智能客服工作流"""
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
    """演示人机交互 (Human-in-the-loop)"""
    print("\n" + "=" * 60)
    print("【示例 3】人机交互 (Human-in-the-loop)")
    print("=" * 60)

    graph = create_customer_service_workflow()
    config = {"configurable": {"thread_id": "hitl-demo"}}

    user_input = "我的账号遇到了技术问题，无法登录"
    print(f"\n用户输入: {user_input}")
    print("\n[第一阶段] 执行到人工审批节点...")

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

    for event in graph.stream(initial_state, config=config):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                print(f"  节点 [{node_name}]: 工单ID={node_output.get('ticket_id')}, 类型={node_output.get('ticket_type')}")

    state = graph.get_state(config)
    print(f"\n[中断点] 等待人工审批...")
    print(f"  当前状态: stage={state.values.get('stage')}")

    print("\n[第二阶段] 人工审批通过，恢复执行...")

    for event in graph.stream(
        Command(resume={"approved": True, "comments": "经核实，该问题需要技术支持团队处理"}),
        config=config,
    ):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                resolution = node_output.get("resolution", "")
                print(f"  节点 [{node_name}]: {resolution[:50] if resolution else ''}...")

    final_state = graph.get_state(config)
    print(f"\n[完成] 最终状态:")
    print(f"  工单ID: {final_state.values.get('ticket_id')}")
    print(f"  审批结果: {'通过' if final_state.values.get('approved') else '未通过'}")
    print(f"  解决方案: {final_state.values.get('resolution')}")


def demo_checkpointer():
    """演示 Checkpointer 状态持久化"""
    print("\n" + "=" * 60)
    print("【示例 4】Checkpointer 状态持久化")
    print("=" * 60)

    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    thread_id = "session-123"

    print(f"\n[会话 {thread_id}] 第一次请求")
    graph1 = IntentClassifierWorkflow(checkpointer)
    result1 = graph1.invoke(
        "你们的产品有什么功能？",
        config={"configurable": {"thread_id": thread_id}},
    )
    print(f"  意图: {result1.get('intent')}")

    state = graph1.get_state({"configurable": {"thread_id": thread_id}})
    print(f"  保存的状态: {state.values}")

    print(f"\n[会话 {thread_id}] 恢复会话")
    graph2 = IntentClassifierWorkflow(checkpointer)
    previous_state = graph2.get_state({"configurable": {"thread_id": thread_id}})
    print(f"  恢复的意图: {previous_state.values.get('intent')}")


def main():
    """主函数：运行所有示例"""
    print("\n" + "=" * 60)
    print("  LangGraph 企业级工作流示例")
    print("=" * 60)

    logger.info("开始运行示例")

    demo_intent_classifier()
    demo_customer_service()
    demo_human_in_the_loop()
    demo_checkpointer()

    print("\n" + "=" * 60)
    print("  所有示例运行完成!")
    print("=" * 60)

    logger.info("示例运行完成")


if __name__ == "__main__":
    main()
