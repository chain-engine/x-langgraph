# -*- coding: utf-8 -*-
"""
测试配置和 fixtures

提供共享的测试配置和测试夹具
"""

import sys
from pathlib import Path

import pytest

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# ========== 环境配置 ==========

@pytest.fixture(autouse=True)
def mock_env_settings(monkeypatch):
    """
    自动 mock 环境变量设置

    确保测试环境有默认的配置
    """
    # 设置测试用的 API Keys
    monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-deepseek-key")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("STRUCTURED", "false")
    monkeypatch.setenv("TEMPERATURE", "0.0")


# ========== 工作流 Fixtures ==========

@pytest.fixture
def simple_router_graph():
    """
    Simple Router 工作流 fixture

    Returns:
        编译后的工作流图
    """
    from workflows.simple_router import create_simple_router_workflow
    return create_simple_router_workflow()


@pytest.fixture
def customer_service_graph():
    """
    Customer Service 工作流 fixture

    Returns:
        编译后的工作流图
    """
    from workflows.customer_service import create_customer_service_workflow
    return create_customer_service_workflow()


@pytest.fixture
def approval_graph():
    """
    Approval 工作流 fixture

    Returns:
        编译后的工作流图
    """
    from workflows.approval import create_approval_workflow
    return create_approval_workflow()


# ========== Checkpointer Fixtures ==========

@pytest.fixture
def memory_checkpointer():
    """
    内存 Checkpointer fixture

    Returns:
        MemorySaver 实例
    """
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


# ========== LLM Provider Fixtures ==========

@pytest.fixture
def mock_llm_provider():
    """
    Mock LLM Provider fixture

    Returns:
        MockProvider 实例
    """
    from llm.providers import get_llm_provider
    return get_llm_provider("mock")


@pytest.fixture
def test_settings(mock_env_settings):
    """
    测试设置 fixture

    Returns:
        Settings 实例
    """
    from config.settings import Settings
    return Settings()


# ========== 测试辅助函数 ==========

def assert_valid_response(response: dict, required_keys: list = None):
    """
    断言响应有效

    Args:
        response: 响应字典
        required_keys: 必须包含的键列表
    """
    assert isinstance(response, dict)
    if required_keys:
        for key in required_keys:
            assert key in response, f"Missing required key: {key}"
