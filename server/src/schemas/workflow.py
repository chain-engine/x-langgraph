# -*- coding: utf-8 -*-
"""
工作流定义数据模型

用于工作流可视化编辑器的 CRUD 接口。
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class NodeDefinition(BaseModel):
    """节点定义"""
    id: str = Field(..., description="节点 ID")
    type: str = Field("processor", description="节点类型: router/processor/tool/unknown")
    label: str = Field(..., description="节点显示名称")
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0}, description="画布坐标")
    handler: str = Field(default="", description="处理函数标识，映射到后端实现")
    config: dict[str, Any] = Field(default_factory=dict, description="节点配置")


class EdgeDefinition(BaseModel):
    """边定义"""
    id: str = Field(..., description="边 ID")
    source: str = Field(..., description="起始节点 ID")
    target: str = Field(..., description="目标节点 ID")
    type: str = Field("normal", description="边类型: normal/conditional")
    condition: Optional[dict[str, str]] = Field(default=None, description="条件表达式: {field, operator, value}")


class GraphData(BaseModel):
    """图数据"""
    nodes: list[NodeDefinition] = Field(default_factory=list)
    edges: list[EdgeDefinition] = Field(default_factory=list)
    entry_point: str = Field(default="", description="入口节点 ID")


class WorkflowDefinition(BaseModel):
    """工作流定义"""
    name: str = Field(..., description="工作流名称（唯一）")
    description: str = Field(default="", description="工作流描述")
    state_schema: dict[str, str] = Field(default_factory=dict, description="状态字段: {字段名: 类型}")
    graph_data: GraphData = Field(default_factory=GraphData)
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)


class WorkflowSummary(BaseModel):
    """工作流摘要（列表用）"""
    name: str
    description: str
    node_count: int = 0
    edge_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ExecuteRequest(BaseModel):
    """执行请求"""
    message: str = Field(..., description="输入消息")
    session_id: str = Field(default="default", description="会话 ID")
