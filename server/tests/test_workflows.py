# -*- coding: utf-8 -*-
"""
工作流单元测试

包含意图分类、工具测试、LLM Provider 测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ========== 意图分类路由工作流测试 ==========

class TestIntentClassifier:
    """意图分类路由工作流测试"""

    def test_product_inquiry_route(self):
        """测试产品咨询路由"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "你们的产品多少钱？",
            config={"configurable": {"thread_id": "test-product"}}
        )
        assert result is not None
        assert result.get("intent") == "product_inquiry"

    def test_order_status_route(self):
        """测试订单状态路由"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "我的订单什么时候发货？",
            config={"configurable": {"thread_id": "test-order"}}
        )
        assert result is not None
        assert result.get("intent") == "order_status"

    def test_technical_support_route(self):
        """测试技术支持路由"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "登录报错，无法正常使用",
            config={"configurable": {"thread_id": "test-tech"}}
        )
        assert result is not None
        assert result.get("intent") == "technical_support"

    def test_complaint_route(self):
        """测试投诉路由"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "服务太差了，我要投诉",
            config={"configurable": {"thread_id": "test-complaint"}}
        )
        assert result is not None
        assert result.get("intent") == "complaint"

    def test_billing_route(self):
        """测试账单路由"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "这个月的账单有问题",
            config={"configurable": {"thread_id": "test-billing"}}
        )
        assert result is not None
        assert result.get("intent") == "billing"

    def test_other_route(self):
        """测试其他/闲聊路由"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "你好啊，今天天气不错",
            config={"configurable": {"thread_id": "test-other"}}
        )
        assert result is not None
        assert result.get("intent") == "other"

    def test_workflow_creation(self):
        """测试工作流创建"""
        from workflows.intent_classifier import IntentClassifierWorkflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = IntentClassifierWorkflow(checkpointer)

        assert graph is not None

    def test_confidence_field(self):
        """测试置信度字段"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "你们有什么产品？",
            config={"configurable": {"thread_id": "test-confidence"}}
        )
        assert result is not None
        assert "confidence" in result


class TestIntentClassifierAdvanced:
    """意图分类路由高级测试"""

    def test_concurrent_sessions(self):
        """测试并发会话"""
        from workflows.intent_classifier import IntentClassifierWorkflow
        from langgraph.checkpoint.memory import MemorySaver
        import concurrent.futures

        def run_session(session_id):
            checkpointer = MemorySaver()
            graph = IntentClassifierWorkflow(checkpointer)
            return graph.invoke(
                "产品咨询",
                config={"configurable": {"thread_id": session_id}}
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_session, f"session-{i}") for i in range(3)]
            results = [f.result() for f in futures]

        assert len(results) == 3
        assert all(r is not None for r in results)

    def test_chinese_input(self):
        """测试中文输入"""
        from workflows.intent_classifier import IntentClassifierWorkflow

        wf = IntentClassifierWorkflow()
        result = wf.invoke(
            "帮我查一下订单物流",
            config={"configurable": {"thread_id": "test-chinese"}}
        )
        assert result is not None


# ========== 工具测试 ==========

class TestTools:
    """工具模块测试"""

    def test_calculator_tool_basic(self):
        """测试计算器工具 - 基本运算"""
        from tools.calculation_tools import calculator_tool

        assert "579" in calculator_tool.invoke("123 + 456")
        assert "100" in calculator_tool.invoke("150 - 50")
        assert "50" in calculator_tool.invoke("10 * 5")
        assert "20" in calculator_tool.invoke("100 / 5")

    def test_calculator_tool_complex(self):
        """测试计算器工具 - 复杂运算"""
        from tools.calculation_tools import calculator_tool

        result = calculator_tool.invoke("(10 + 5) * 2")
        assert "30" in result

    def test_weather_tool_beijing(self):
        """测试天气工具 - 北京"""
        from tools.weather_tools import weather_query_tool

        result = weather_query_tool.invoke("北京")
        assert "北京" in result

    def test_weather_tool_mock_data(self):
        """测试天气工具 - 无 API Key 时返回模拟数据"""
        from tools.weather_tools import weather_query_tool

        result = weather_query_tool.invoke("测试城市")
        assert result is not None

    def test_csv_processor_columns(self):
        """测试 CSV 处理工具 - 列操作"""
        from tools.data_tools import csv_processor_tool

        csv_data = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai"
        result = csv_processor_tool.invoke(
            {"data": csv_data, "operation": "columns"}
        )
        assert "name" in result
        assert "age" in result
        assert "city" in result

    def test_csv_processor_validate(self):
        """测试 CSV 处理工具 - 验证"""
        from tools.data_tools import csv_processor_tool

        csv_data = "name,age\nAlice,30\nBob,25"
        result = csv_processor_tool.invoke(
            {"data": csv_data, "operation": "validate"}
        )
        assert "有效" in result or "valid" in result.lower()

    def test_json_processor_validate(self):
        """测试 JSON 处理工具 - 验证"""
        from tools.data_tools import json_processor_tool

        json_data = '{"name": "Alice", "age": 30}'
        result = json_processor_tool.invoke(
            {"data": json_data, "operation": "validate"}
        )
        assert "有效" in result or "valid" in result.lower()

    def test_json_processor_keys(self):
        """测试 JSON 处理工具 - 键提取"""
        from tools.data_tools import json_processor_tool

        json_data = '{"name": "Alice", "age": 30, "city": "Beijing"}'
        result = json_processor_tool.invoke(
            {"data": json_data, "operation": "keys"}
        )
        assert "name" in result
        assert "age" in result


# ========== LLM Provider 测试 ==========

class TestLLMProvider:
    """LLM 提供者测试"""

    def test_list_providers(self):
        """测试列出提供者"""
        from llm.providers import list_providers

        providers = list_providers()
        assert "deepseek" in providers
        assert "doubao" in providers
        assert "aliyun" in providers
        assert "mock" in providers

    def test_get_mock_provider(self):
        """测试获取 Mock 提供者"""
        from llm.providers import get_llm_provider

        provider = get_llm_provider("mock")
        assert provider is not None
        assert provider.name == "mock"

    def test_mock_provider_invoke(self):
        """测试 Mock 提供者调用"""
        from llm.providers import get_llm_provider
        from langchain_core.messages import HumanMessage

        provider = get_llm_provider("mock")
        response = provider.invoke([HumanMessage(content="测试消息")])

        assert response is not None
        assert hasattr(response, "content")

    def test_invalid_provider(self):
        """测试无效提供者"""
        from llm.providers import get_llm_provider

        with pytest.raises(ValueError):
            get_llm_provider("invalid_provider")

    def test_prompt_manager(self):
        """测试提示模板管理器"""
        from llm.prompts import prompt_manager

        templates = prompt_manager.list_templates()
        assert len(templates) > 0

        template = prompt_manager.get("system_default")
        assert template is not None


# ========== 配置测试 ==========

class TestSettings:
    """配置测试"""

    def test_settings_creation(self):
        """测试配置创建"""
        from config.settings import Settings

        settings = Settings()
        assert settings is not None
        assert settings.DEBUG is not None

    def test_get_available_provider(self):
        """测试获取可用提供者"""
        from config.settings import settings

        provider = settings.get_available_provider()
        assert provider in ["deepseek", "doubao", "aliyun", "mock"]

    def test_has_valid_api_key(self):
        """测试 API Key 检查"""
        from config.settings import settings

        assert hasattr(settings, "has_valid_api_key")

    def test_validate_model_config(self):
        """测试模型配置验证"""
        from config.settings import settings

        assert settings.validate_model_config("mock") is True


# ========== 异步测试 ==========

class TestAsyncWorkflows:
    """异步工作流测试"""

    def test_intent_classifier_invoke_basic(self):
        """测试基本调用（验证工作流正常）"""
        from workflows.intent_classifier import IntentClassifierWorkflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = IntentClassifierWorkflow(checkpointer)

        result = graph.invoke(
            "产品功能介绍",
            config={"configurable": {"thread_id": "basic-test"}}
        )

        assert result is not None
        assert "intent" in result

    def test_intent_classifier_stream_basic(self):
        """测试基本流式调用"""
        from workflows.intent_classifier import IntentClassifierWorkflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = IntentClassifierWorkflow(checkpointer)

        events = list(graph.stream(
            "我想查一下账单",
            config={"configurable": {"thread_id": "stream-basic-test"}},
            stream_mode="updates"
        ))

        assert len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
