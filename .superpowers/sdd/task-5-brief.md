# Task 5: Task 5: 整合 — `__init__.py` 导出 + Handler 注册

## Task 5: 整合 — `__init__.py` 导出 + Handler 注册

**Files:**
- Modify: `server/src/workflows/reasoning/__init__.py`
- Modify: `server/src/workflows/__init__.py:76-107`
- Modify: `server/src/workflows/compiler.py:66-109`

**Interfaces:**
- Consumes: `react.py`, `plan_execute.py`, `tree_of_thought.py` 的导出
- Produces: 更新 `workflows/__init__.py` 和 `compiler.py`

- [ ] **Step 1: Write reasoning/__init__.py**

```python
# server/src/workflows/reasoning/__init__.py
# -*- coding: utf-8 -*-
"""
推理组件模块

提供可复用的推理节点组件：
- ReAct (Reasoning + Acting) 模式
- Plan-and-Execute 模式
- Tree-of-Thought 模式（简化版）

使用示例：
    from workflows.reasoning import (
        ReactState,
        create_react_workflow,
        PlanExecuteState,
        create_plan_execute_workflow,
        ToTState,
        create_tot_workflow,
        ReasoningConfig,
    )

    # ReAct
    tools = [search_tool, calculator_tool]
    workflow = create_react_workflow(tools)

    # Plan-and-Execute
    workflow = create_plan_execute_workflow(tools)

    # ToT
    workflow = create_tot_workflow()
"""

from workflows.reasoning.base import (
    BaseReasoningState,
    ReasoningConfig,
    StepRecord,
)

from workflows.reasoning.react import (
    ReactState,
    create_reasoning_node,
    create_action_node,
    create_observation_node,
    create_reflection_node,
    create_finish_node,
    react_router,
    create_react_workflow,
)

from workflows.reasoning.plan_execute import (
    TaskStep,
    PlanExecuteState,
    create_planner_node,
    create_executor_node,
    create_reflector_node,
    create_replan_node,
    create_finish_node as create_plan_finish_node,
    plan_execute_router,
    create_plan_execute_workflow,
)

from workflows.reasoning.tree_of_thought import (
    Branch,
    ToTState,
    create_generator_node,
    create_evaluator_node,
    create_selector_node,
    create_finish_node as create_tot_finish_node,
    tot_router,
    create_tot_workflow,
)

__all__ = [
    # Base
    "BaseReasoningState",
    "ReasoningConfig",
    "StepRecord",
    # ReAct
    "ReactState",
    "create_reasoning_node",
    "create_action_node",
    "create_observation_node",
    "create_reflection_node",
    "create_finish_node",
    "react_router",
    "create_react_workflow",
    # Plan-and-Execute
    "TaskStep",
    "PlanExecuteState",
    "create_planner_node",
    "create_executor_node",
    "create_reflector_node",
    "create_replan_node",
    "create_plan_finish_node",
    "plan_execute_router",
    "create_plan_execute_workflow",
    # ToT
    "Branch",
    "ToTState",
    "create_generator_node",
    "create_evaluator_node",
    "create_selector_node",
    "create_tot_finish_node",
    "tot_router",
    "create_tot_workflow",
]


# ===== 注册 Handler（供 JSON 编译器使用）=====

def _register_reasoning_handlers():
    """注册推理组件 handlers"""
    from workflows.compiler import HANDLER_REGISTRY

    HANDLER_REGISTRY.update({
        # ReAct
        "react_reasoning": create_reasoning_node,
        "react_action": create_action_node,
        "react_observation": create_observation_node,
        "react_reflection": create_reflection_node,
        "react_finish": create_finish_node,

        # Plan-and-Execute
        "plan_planner": create_planner_node,
        "plan_executor": create_executor_node,
        "plan_reflector": create_reflector_node,
        "plan_replan": create_replan_node,
        "plan_finish": create_plan_finish_node,

        # ToT
        "tot_generator": create_generator_node,
        "tot_evaluator": create_evaluator_node,
        "tot_selector": create_selector_node,
        "tot_finish": create_tot_finish_node,
    })


# 模块加载时自动注册
_register_reasoning_handlers()
```

- [ ] **Step 2: Update workflows/__init__.py**

在 `__all__` 列表末尾添加：

```python
# 推理组件
from workflows.reasoning import (
    BaseReasoningState,
    ReasoningConfig,
    StepRecord,
    ReactState,
    PlanExecuteState,
    TaskStep,
    ToTState,
    Branch,
    create_react_workflow,
    create_plan_execute_workflow,
    create_tot_workflow,
)
```

同时在 `__all__` 中添加对应项：

```python
    # 推理组件
    "BaseReasoningState",
    "ReasoningConfig",
    "StepRecord",
    "ReactState",
    "PlanExecuteState",
    "TaskStep",
    "ToTState",
    "Branch",
    "create_react_workflow",
    "create_plan_execute_workflow",
    "create_tot_workflow",
```

- [ ] **Step 3: Commit**

```bash
git add server/src/workflows/reasoning/__init__.py server/src/workflows/__init__.py && git commit -m "feat(reasoning): export reasoning components and register handlers"
```

---

## Global Constraints
- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`
