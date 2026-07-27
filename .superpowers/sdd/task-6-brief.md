# Task 6: Task 6: 验证和测试

## Task 6: 验证和测试

**Files:**
- Test: `server/src/workflows/reasoning/test_reasoning.py`（新创建）

**Interfaces:**
- Consumes: 所有推理组件
- Produces: 测试通过

- [ ] **Step 1: Write integration test**

```python
# server/src/workflows/reasoning/test_reasoning.py
# -*- coding: utf-8 -*-
"""
推理组件集成测试
"""

import pytest
from unittest.mock import MagicMock

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

    def test_no_action_returns_reasoning(self):
        state: ReactState = {"messages": [], "iteration": 0, "max_iterations": 10, "intermediate_steps": []}
        assert react_router(state) == "reasoning"

    def test_has_action_no_observation_returns_action(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "action": "search"
        }
        assert react_router(state) == "action"

    def test_has_observation_returns_reflect(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "action": "search", "observation": "result"
        }
        assert react_router(state) == "reflect"

    def test_has_final_answer_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "final_answer": "done"
        }
        assert react_router(state) == "finish"

    def test_max_iterations_returns_finish(self):
        state: ReactState = {
            "messages": [], "iteration": 10, "max_iterations": 10,
            "intermediate_steps": []
        }
        assert react_router(state) == "finish"


class TestPlanExecuteRouter:
    """测试 Plan-and-Execute 路由"""

    def test_no_plan_returns_plan(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "plan": [], "pending_tasks": []
        }
        assert plan_execute_router(state) == "plan"

    def test_has_plan_with_pending_returns_execute(self):
        step: TaskStep = {"step_id": "s1", "description": "do something", "status": "pending"}
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [],
            "plan": [step], "pending_tasks": [step], "current_step": 0
        }
        assert plan_execute_router(state) == "execute"

    def test_no_pending_returns_finish(self):
        state: PlanExecuteState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "plan": [], "pending_tasks": [], "current_step": 0
        }
        assert plan_execute_router(state) == "finish"


class TestToTRouter:
    """测试 ToT 路由"""

    def test_no_new_branches_returns_generate(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 0, "max_depth": 5
        }
        assert tot_router(state) == "generate"

    def test_has_best_branch_returns_finish(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "best_branch_id": "b1"
        }
        assert tot_router(state) == "finish"

    def test_max_depth_returns_finish(self):
        state: ToTState = {
            "messages": [], "iteration": 0, "max_iterations": 10,
            "intermediate_steps": [], "depth": 5, "max_depth": 5
        }
        assert tot_router(state) == "finish"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run tests**

```bash
cd server && python -m pytest src/workflows/reasoning/test_reasoning.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/test_reasoning.py && git commit -m "test(reasoning): add integration tests for reasoning components"
```

---

## Global Constraints
- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`
