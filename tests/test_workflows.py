# -*- coding: utf-8 -*-
"""
工作流单元测试

包含路由测试、工具测试、LLM Provider 测试
"""

import pytest
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ========== 简单路由工作流测试 ==========

class TestSimpleRouter:
    """简单路由工作流测试"""

    def test_search_route(self):
        """测试搜索路由"""
        from workflows.simple_router import run_simple_router

        result = run_simple_router("搜索 Python 教程", thread_id="test-search")
        assert result is not None
        assert result.get("route") == "search"

    def test_calculate_route(self):
        """测试计算路由"""
        from workflows.simple_router import run_simple_router

        result = run_simple_router("123 + 456", thread_id="test-calc")
        assert result is not None
        assert result.get("route") == "calculate"

    def test_weather_route(self):
        """测试天气路由"""
        from workflows.simple_router import run_simple_router

        result = run_simple_router("北京天气", thread_id="test-weather")
        assert result is not None
        assert result.get("route") == "weather"

    def test_unknown_route(self):
        """测试未知输入的路由"""
        from workflows.simple_router import run_simple_router

        result = run_simple_router("随机无意义文本 xyz123", thread_id="test-unknown")
        assert result is not None
        # 未知输入应该降级到搜索
        assert result.get("route") in ["search", "unknown"]

    def test_workflow_creation(self):
        """测试工作流创建"""
        from workflows.simple_router import create_simple_router_workflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = create_simple_router_workflow(checkpointer)

        assert graph is not None

    def test_routing_metadata(self):
        """测试路由元数据"""
        from workflows.simple_router import run_simple_router

        result = run_simple_router("计算 100 除以 5", thread_id="test-metadata")
        assert result is not None
        # 应该有路由元数据
        assert "routing_reasoning" in result or result.get("route") is not None


class TestSimpleRouterAdvanced:
    """简单路由高级测试"""

    def test_concurrent_sessions(self):
        """测试并发会话"""
        from workflows.simple_router import create_simple_router_workflow
        from langgraph.checkpoint.memory import MemorySaver
        import concurrent.futures

        def run_session(session_id):
            checkpointer = MemorySaver()
            graph = create_simple_router_workflow(checkpointer)
            return graph.invoke(
                {"input": "测试消息", "route": "", "output": "", "error": None},
                config={"configurable": {"thread_id": session_id}}
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_session, f"session-{i}") for i in range(3)]
            results = [f.result() for f in futures]

        assert len(results) == 3
        assert all(r is not None for r in results)

    def test_chinese_input(self):
        """测试中文输入"""
        from workflows.simple_router import run_simple_router

        result = run_simple_router("帮我查一下上海今天热不热", thread_id="test-chinese")
        assert result is not None
        assert result.get("route") in ["weather", "search"]


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
        # 应该返回模拟数据或错误信息
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

        # 列出模板
        templates = prompt_manager.list_templates()
        assert len(templates) > 0

        # 获取模板
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

        # 方法存在即可
        assert hasattr(settings, "has_valid_api_key")

    def test_validate_model_config(self):
        """测试模型配置验证"""
        from config.settings import settings

        # Mock 总是有效的
        assert settings.validate_model_config("mock") is True


# ========== 异步测试（使用同步包装）==========

class TestAsyncWorkflows:
    """异步工作流测试"""

    def test_simple_router_invoke_basic(self):
        """测试基本调用（验证工作流正常）"""
        from workflows.simple_router import create_simple_router_workflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = create_simple_router_workflow(checkpointer)

        result = graph.invoke(
            {"input": "北京天气", "route": "", "output": "", "error": None},
            config={"configurable": {"thread_id": "basic-test"}}
        )

        assert result is not None
        assert "route" in result

    def test_simple_router_stream_basic(self):
        """测试基本流式调用"""
        from workflows.simple_router import create_simple_router_workflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = create_simple_router_workflow(checkpointer)

        events = list(graph.stream(
            {"input": "123 + 456", "route": "", "output": "", "error": None},
            config={"configurable": {"thread_id": "stream-basic-test"}},
            stream_mode="updates"
        ))

        assert len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
