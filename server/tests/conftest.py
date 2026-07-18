# -*- coding: utf-8 -*-
"""
测试配置和 fixtures

提供共享的测试配置和测试夹具
"""

import sys
from pathlib import Path

import pytest

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# ========== 环境配置 ==========

@pytest.fixture(autouse=True)
def mock_env_settings(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-deepseek-key")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("STRUCTURED", "false")
    monkeypatch.setenv("TEMPERATURE", "0.0")


# ========== 工作流 Fixtures ==========

@pytest.fixture
def intent_classifier_graph():
    """意图分类路由工作流 fixture"""
    from workflows.intent_classifier import IntentClassifierWorkflow
    return IntentClassifierWorkflow()


@pytest.fixture
def customer_service_graph():
    """智能客服工作流 fixture"""
    from workflows.customer_service import create_customer_service_workflow
    return create_customer_service_workflow()


@pytest.fixture
def approval_graph():
    """自动化审批工作流 fixture"""
    from workflows.approval import create_approval_workflow
    return create_approval_workflow()


# ========== Checkpointer Fixtures ==========

@pytest.fixture
def memory_checkpointer():
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


# ========== LLM Provider Fixtures ==========

@pytest.fixture
def mock_llm_provider():
    from llm.providers import get_llm_provider
    return get_llm_provider("mock")


@pytest.fixture
def test_settings(mock_env_settings):
    from config.settings import Settings
    return Settings()


# ========== 测试辅助函数 ==========

def assert_valid_response(response: dict, required_keys: list = None):
    assert isinstance(response, dict)
    if required_keys:
        for key in required_keys:
            assert key in response, f"Missing required key: {key}"
