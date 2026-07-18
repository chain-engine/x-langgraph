# -*- coding: utf-8 -*-
"""
图编译器

将 JSON 工作流定义编译为 LangGraph StateGraph。
"""

from typing import Any, Callable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.logger import logger


# Handler 映射表：handler 标识 → Python 处理函数
HANDLER_REGISTRY: dict[str, Callable] = {}


def _register_handlers():
    """注册内置 handler"""
    from workflows.intent_classifier.nodes import (
        classify_intent,
        handle_product_inquiry,
        handle_order_status,
        handle_technical_support,
        handle_complaint,
        handle_billing,
        handle_other,
    )
    from workflows.approval.nodes import (
        submit_node, evaluate_node, human_approval_node, auto_approve_node, notify_node,
    )

    HANDLER_REGISTRY.update({
        "classify": classify_intent,
        "product_inquiry": handle_product_inquiry,
        "order_status": handle_order_status,
        "technical_support": handle_technical_support,
        "complaint": handle_complaint,
        "billing": handle_billing,
        "other": handle_other,

        "submit": submit_node,
        "evaluate": evaluate_node,
        "human_approval": human_approval_node,
        "auto_approve": auto_approve_node,
        "notify": notify_node,
    })


def _get_state_class(state_schema: dict[str, str]):
    """根据 state_schema 动态构建 TypedDict"""
    from typing import TypedDict, Optional, Annotated
    from langgraph.graph import add_messages
    fields = {}
    for field_name, field_type in state_schema.items():
        py_type = {
            "str": str, "string": str,
            "int": int, "integer": int,
            "float": float,
            "bool": bool, "boolean": bool,
            "list": list, "dict": dict,
        }.get(field_type, Any)
        if field_type.startswith("Optional"):
            py_type = Optional[py_type]
        fields[field_name] = py_type
    if "messages" not in fields:
        fields["messages"] = Annotated[list, add_messages]
    return TypedDict("DynamicState", fields)  # type: ignore


def compile_workflow(definition: dict[str, Any], checkpointer=None):
    """
    将 JSON 工作流定义编译为 LangGraph StateGraph

    Args:
        definition: 工作流定义字典
        checkpointer: 检查点存储器

    Returns:
        编译后的 StateGraph
    """
    if not HANDLER_REGISTRY:
        _register_handlers()

    graph_data = definition.get("graph_data", {})
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    entry_point = graph_data.get("entry_point", "")

    state_schema = definition.get("state_schema", {})
    if not state_schema:
        state_schema = {"input": "str", "output": "str", "error": "Optional[str]"}

    StateClass = _get_state_class(state_schema)
    workflow = StateGraph(StateClass)

    # 添加节点
    for node_def in nodes:
        node_id = node_def["id"]
        handler_name = node_def.get("handler", node_id)
        handler = HANDLER_REGISTRY.get(handler_name)
        if handler is None:
            logger.warning(f"Handler not found for node '{node_id}': '{handler_name}', using passthrough")
            handler = _passthrough_handler
        workflow.add_node(node_id, handler)
        logger.debug(f"Added node: {node_id} (handler: {handler_name})")

    # 设置入口点
    if entry_point:
        workflow.set_entry_point(entry_point)
    elif nodes:
        workflow.set_entry_point(nodes[0]["id"])

    # 添加边
    conditional_map: dict[str, dict[str, str]] = {}
    conditional_default: dict[str, str] = {}
    conditional_field: dict[str, str] = {}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        edge_type = edge.get("type", "normal")

        if edge_type == "conditional":
            condition = edge.get("condition", {})
            field_name = condition.get("field", "route")
            operator = condition.get("operator", "==")
            expected_value = condition.get("value", "")

            if source not in conditional_map:
                conditional_map[source] = {}
                conditional_field[source] = field_name

            if operator == "!=":
                conditional_default[source] = target
            else:
                conditional_map[source][expected_value] = target
        else:
            if target == "__end__":
                workflow.add_edge(source, END)
            else:
                workflow.add_edge(source, target)
            logger.debug(f"Added edge: {source} -> {target}")

    # 添加条件边
    for source, mapping in conditional_map.items():
        if "__end__" in mapping:
            mapping["__end__"] = END

        default_target = conditional_default.get(source)
        if default_target:
            if default_target == "__end__":
                default_target = END
            if str(default_target) not in mapping:
                mapping[str(default_target)] = default_target

        field_name = conditional_field.get(source, "route")
        route_fn = _make_route_fn(field_name, list(mapping.keys()), default_target)
        workflow.add_conditional_edges(source, route_fn, mapping)
        logger.debug(f"Added conditional edges from {source}: {mapping}, default: {default_target}")

    cp = checkpointer or MemorySaver()
    compiled = workflow.compile(checkpointer=cp)
    logger.info(f"Workflow compiled: {definition.get('name', 'unknown')}")
    return compiled


def _passthrough_handler(state: dict) -> dict:
    """透传 handler（当找不到对应处理函数时使用）"""
    return {"output": state.get("input", ""), "error": None}


def _make_route_fn(field_name: str, allowed_values=None, default_target=None):
    """创建条件路由函数"""
    allowed_values = allowed_values or []
    expanded_values = []
    for val in allowed_values:
        if ',' in val:
            expanded_values.extend([v.strip() for v in val.split(',')])
        else:
            expanded_values.append(val)
    def route_fn(state: dict) -> str:
        value = state.get(field_name, state.get("route", "unknown"))
        value_str = str(value)
        if value_str not in expanded_values and default_target:
            logger.info(f"Conditional routing [{field_name}]: {value_str}, using default: {default_target}")
            return default_target
        logger.info(f"Conditional routing [{field_name}]: {value_str}")
        return value_str
    return route_fn
