# -*- coding: utf-8 -*-
"""
意图分类路由工作流模块

展示 LLM 意图分类 + 条件路由的典型客服场景。

使用示例：
    from workflows.simple_router import run_simple_router
    result = run_simple_router("你们的产品多少钱？")
"""

from workflows.simple_router.workflow import (
    IntentClassifierWorkflow,
    create_simple_router_workflow,
    run_simple_router,
)

__all__ = ["IntentClassifierWorkflow", "create_simple_router_workflow", "run_simple_router"]
