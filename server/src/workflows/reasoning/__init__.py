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
        ReactWorkflow,
        PlanExecuteState,
        PlanExecuteWorkflow,
        ToTState,
        create_tot_workflow,
        ReasoningConfig,
    )

    # ReAct
    workflow = ReactWorkflow(tools=[search_tool])

    # Plan-and-Execute
    workflow = PlanExecuteWorkflow(tools=[search_tool])

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
    ReactWorkflow,
    create_reasoning_node,
    create_action_node,
    create_observation_node,
    create_reflection_node,
    create_finish_node,
    react_router,
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
    "ReactWorkflow",
    "create_reasoning_node",
    "create_action_node",
    "create_observation_node",
    "create_reflection_node",
    "create_finish_node",
    "react_router",
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
# 存储工厂函数（未调用），compiler 在编译时传入 config 再调用

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
