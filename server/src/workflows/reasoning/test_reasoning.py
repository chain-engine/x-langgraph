# -*- coding: utf-8 -*-
"""
推理组件集成测试
"""

import pytest

from workflows.reasoning.base import BaseReasoningState, ReasoningConfig, StepRecord
from workflows.reasoning.react import ReactState, react_router, create_reasoning_node, create_finish_node
from workflows.reasoning.plan_execute import PlanExecuteState, TaskStep, plan_execute_router
from workflows.reasoning.tree_of_thought import ToTState, Branch, tot_router


class TestBaseTypes:
    """测试公共类型"""

    def test_reasoning_config_defaults(self):
        config = ReasoningConfig()
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300
        assert config.enable_reflection is True
        assert config.llm_provider == "deepseek"

    def test_reasoning_config_to_dict(self):
        config = ReasoningConfig(max_iterations=5)
        d = config.to_dict()
        assert d["max_iterations"] == 5

    def test_step_record_structure(self):
        step: StepRecord = {
            "step_type": "reasoning",
            "content": "test content",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        assert step["step_type"] == "reasoning"
        assert step["content"] == "test content"


class TestReactRouter:
    """测试 ReAct 路由"""

    def test_should_continue_true_returns_reasoning(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "should_continue": True
        }
        assert react_router(state) == "reasoning"

    def test_should_continue_false_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "should_continue": False
        }
        assert react_router(state) == "finish"

    def test_has_error_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "error": "some error"
        }
        assert react_router(state) == "finish"

    def test_max_iterations_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 10, "max_iterations": 10,
            "intermediate_steps": [], "should_continue": True
        }
        assert react_router(state) == "finish"


class TestPlanExecuteRouter:
    """测试 Plan-and-Execute 路由"""

    def test_no_pending_tasks_returns_finish(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "plan": [], "pending_tasks": []
        }
        assert plan_execute_router(state) == "finish"

    def test_has_pending_tasks_returns_executor(self):
        step: TaskStep = {"step_id": "s1", "description": "do something", "status": "pending"}
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [],
            "plan": [step], "pending_tasks": [step], "current_step": 0
        }
        assert plan_execute_router(state) == "executor"

    def test_needs_replan_returns_replan(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "pending_tasks": [], "needs_replan": True
        }
        assert plan_execute_router(state) == "replan"

    def test_has_error_returns_finish(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "pending_tasks": [], "error": "failed"
        }
        assert plan_execute_router(state) == "finish"


class TestToTRouter:
    """测试 ToT 路由"""

    def test_no_evaluation_results_returns_finish(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 0, "max_depth": 5
        }
        assert tot_router(state) == "finish"

    def test_best_branch_alone_does_not_force_finish(self):
        """tot_router 本身不检查 best_branch_id，该逻辑由 selector 节点处理"""
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "best_branch_id": "b1",
            "depth": 0, "max_depth": 5,
            "evaluation_results": [{"branch_id": "b1", "score": 0.9}]
        }
        assert tot_router(state) == "generator"

    def test_max_depth_returns_finish(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 5, "max_depth": 5,
            "evaluation_results": [{"branch_id": "b1", "score": 0.9}]
        }
        assert tot_router(state) == "finish"

    def test_has_evaluations_and_not_max_depth_returns_generator(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 0, "max_depth": 5,
            "evaluation_results": [{"branch_id": "b1", "score": 0.9}]
        }
        assert tot_router(state) == "generator"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
