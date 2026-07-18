# -*- coding: utf-8 -*-
"""
意图分类路由工作流模块

展示 LLM 意图分类 + 条件路由的典型客服场景。

使用示例：
    from workflows.intent_classifier import IntentClassifierWorkflow
    result = IntentClassifierWorkflow().invoke("你们的产品多少钱？")
"""

from workflows.intent_classifier.workflow import IntentClassifierWorkflow

__all__ = ["IntentClassifierWorkflow"]
