# -*- coding: utf-8 -*-
"""
Prometheus 指标路由
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/metrics")
async def metrics() -> str:
    """Prometheus 指标端点"""
    from main import _rate_limit_store

    lines = []
    lines.append("# HELP x_langgraph_requests_total Total requests")
    lines.append(f"# TYPE x_langgraph_requests_total counter")
    lines.append(f"x_langgraph_requests_total {sum(data['count'] for data in _rate_limit_store.values())}")

    lines.append("# HELP x_langgraph_active_clients Active clients")
    lines.append("# TYPE x_langgraph_active_clients gauge")
    lines.append(f"x_langgraph_active_clients {len(_rate_limit_store)}")

    return "\n".join(lines)
