# -*- coding: utf-8 -*-
"""
高级工作流示例

本文件演示 RAG 问答、多智能体协作、自动化审批等高级工作流。

运行方式:
    uv run python -m examples.demo_workflows
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.logger import logger


def demo_rag_qa():
    """
    演示 RAG 文档问答工作流

    展示功能：
    - 向量检索
    - 上下文构建
    - LLM 生成回答
    - 条件路由
    """
    print("\n" + "=" * 60)
    print("【示例 1】RAG 文档问答工作流")
    print("=" * 60)

    try:
        from workflows.rag_qa import create_rag_qa_workflow, run_rag_qa

        test_questions = [
            "什么是 LangGraph？",
            "LangGraph 的核心概念有哪些？",
            "如何使用 Checkpointer？",
        ]

        for i, question in enumerate(test_questions, 1):
            print(f"\n--- 问题 {i}: {question} ---")

            result = run_rag_qa(question, thread_id=f"rag-{i}")

            print(f"\n回答: {result.answer[:200]}...")
            print(f"来源: {', '.join(result.sources[:3])}")
            print(f"检索文档数: {result.retrieved_docs_count}")
            print(f"检索分数: {result.retrieval_score:.2f}" if result.retrieval_score else "")

    except ImportError as e:
        print(f"RAG 模块未完成加载: {e}")


def demo_multi_agent():
    """
    演示多智能体协作工作流

    展示功能：
    - 任务分解
    - 多智能体协作
    - 迭代优化
    - 流式输出
    """
    print("\n" + "=" * 60)
    print("【示例 2】多智能体协作工作流")
    print("=" * 60)

    try:
        from workflows.multi_agent import create_multi_agent_workflow, stream_multi_agent

        request = "编写一份关于人工智能在企业中应用的分析报告"

        print(f"\n任务: {request}")
        print("\n[智能体协作中...]")

        # 流式执行
        for event in stream_multi_agent(request, thread_id="multi-agent-demo"):
            for agent_name, agent_output in event.items():
                print(f"\n>>> [{agent_name}] 执行完成")

                if isinstance(agent_output, dict):
                    # 显示关键输出
                    if "research_findings" in agent_output:
                        findings = agent_output["research_findings"]
                        print(f"    研究发现: {findings[:100]}...")

                    if "draft_content" in agent_output:
                        draft = agent_output["draft_content"]
                        print(f"    初稿长度: {len(draft)} 字符")

                    if "edited_content" in agent_output:
                        edited = agent_output["edited_content"]
                        print(f"    编辑后长度: {len(edited)} 字符")

                    if "review_feedback" in agent_output:
                        feedback = agent_output["review_feedback"]
                        print(f"    审核反馈: {feedback[:100]}...")

                    if "final_output" in agent_output and agent_output["final_output"]:
                        print("\n[最终输出]")
                        print(agent_output["final_output"][:500] + "...")

    except ImportError as e:
        print(f"多智能体模块未完成加载: {e}")


def demo_approval():
    """
    演示自动化审批工作流

    展示功能：
    - 自动评估
    - 人机交互
    - 条件路由
    - 状态持久化
    """
    print("\n" + "=" * 60)
    print("【示例 3】自动化审批工作流")
    print("=" * 60)

    try:
        from workflows.approval import (
            create_approval_workflow,
            run_approval,
            run_approval_with_human,
            ApprovalType,
        )

        # 测试自动审批（小额报销）
        print("\n--- 测试 1: 小额报销（自动审批）---")
        request1 = {
            "request_type": ApprovalType.EXPENSE.value,
            "requester_id": "user-001",
            "requester_name": "张三",
            "department": "技术部",
            "amount": 500.00,
            "description": "办公用品采购报销",
        }

        result1 = run_approval(request1, thread_id="approval-1")
        print(f"  请求ID: {result1.request_id}")
        print(f"  最终状态: {result1.final_status}")
        print(f"  决定: {result1.final_decision}")
        print(f"  风险等级: {result1.risk_level}")

        # 测试人工审批（大额报销）
        print("\n--- 测试 2: 大额报销（人工审批）---")
        request2 = {
            "request_type": ApprovalType.EXPENSE.value,
            "requester_id": "user-002",
            "requester_name": "李四",
            "department": "市场部",
            "amount": 15000.00,
            "description": "市场活动费用报销",
        }

        # 先执行到中断点
        print("\n[第一阶段] 提交审批...")
        result2 = run_approval_with_human(
            request2,
            {"approved": True, "comments": "金额合理，审批通过", "approver_id": "manager-001"},
            thread_id="approval-2",
        )

        print(f"  请求ID: {result2.request_id}")
        print(f"  最终状态: {result2.final_status}")
        print(f"  决定: {result2.final_decision}")
        print(f"  审批历史: {len(result2.approval_history)} 步")

    except ImportError as e:
        print(f"审批模块未完成加载: {e}")


def demo_database_tools():
    """
    演示数据库工具

    展示功能：
    - Text2SQL
    - SQL 执行
    - Schema 查询
    """
    print("\n" + "=" * 60)
    print("【示例 4】数据库工具 (Text2SQL)")
    print("=" * 60)

    try:
        from tools.database_tools import (
            text_to_sql_tool,
            execute_sql_tool,
            get_schema_tool,
        )

        # 获取 Schema
        print("\n--- 查询数据库 Schema ---")
        schema_result = get_schema_tool.invoke({})
        print(schema_result[:500])

        # Text2SQL
        print("\n--- Text2SQL 转换 ---")
        queries = [
            "查询所有用户",
            "统计每个部门的员工数量",
            "查询薪资最高的前3名员工",
        ]

        for query in queries:
            print(f"\n自然语言: {query}")
            sql_result = text_to_sql_tool.invoke({"query": query, "table_name": "users"})
            print(f"SQL: {sql_result}")

        # 执行 SQL
        print("\n--- 执行 SQL 查询 ---")
        sql = "SELECT * FROM users LIMIT 5"
        print(f"SQL: {sql}")
        result = execute_sql_tool.invoke({"sql": sql})
        print(f"结果:\n{result}")

    except ImportError as e:
        print(f"数据库工具模块未完成加载: {e}")


def demo_llm_provider():
    """
    演示 LLM 提供者

    展示功能：
    - 多模型支持
    - 统一接口
    - 流式输出
    """
    print("\n" + "=" * 60)
    print("【示例 5】LLM 提供者")
    print("=" * 60)

    try:
        from llm.providers import (
            get_llm_provider,
            list_providers,
            create_chat_model,
        )
        from llm.prompts import prompt_manager

        # 列出可用的提供者
        print("\n--- 可用的 LLM 提供者 ---")
        providers = list_providers()
        for p in providers:
            print(f"  - {p}")

        # 使用提示模板
        print("\n--- 可用的提示模板 ---")
        templates = prompt_manager.list_templates()
        for t in templates[:5]:  # 只显示前5个
            print(f"  - {t['name']}: {t['description']}")

        # 创建聊天模型
        print("\n--- 创建聊天模型 ---")
        try:
            # 尝试创建 DeepSeek 模型
            model = create_chat_model("deepseek")
            print(f"  模型创建成功: {model}")

            # 测试调用（需要有效的 API Key）
            print("\n--- 测试 LLM 调用 ---")
            print("  (注: 需要 API Key 才能实际调用)")

        except Exception as e:
            print(f"  模型创建失败: {e}")

    except ImportError as e:
        print(f"LLM 模块未完成加载: {e}")


def main():
    """主函数：运行所有高级示例"""
    print("\n" + "=" * 60)
    print("  LangGraph 高级工作流示例")
    print("=" * 60)

    logger.info("开始运行高级示例")

    # 运行各示例
    demo_rag_qa()
    demo_multi_agent()
    demo_approval()
    demo_database_tools()
    demo_llm_provider()

    print("\n" + "=" * 60)
    print("  所有高级示例运行完成!")
    print("=" * 60)

    logger.info("高级示例运行完成")


if __name__ == "__main__":
    main()
