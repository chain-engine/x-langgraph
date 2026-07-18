# -*- coding: utf-8 -*-
"""
工作流定义数据访问层

基于 MySQL 数据库存储工作流定义。
"""

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.workflow import (
    WorkflowDefinition,
    WorkflowDefinitionNode,
    WorkflowDefinitionEdge,
    WorkflowStateField,
)
from infras.mysql import session_factory
from core.logger import logger
from core.exceptions import DatabaseError


class WorkflowDefinitionRepository:
    """工作流定义仓库"""

    def _model_to_dict(self, model: WorkflowDefinition) -> dict[str, Any]:
        """将 ORM 模型转换为字典"""
        graph_data = {
            "nodes": [],
            "edges": [],
            "entry_point": model.entry_point,
        }

        for node in model.nodes:
            node_dict = {
                "id": node.node_id,
                "type": node.node_type,
                "label": node.label,
                "handler": node.handler,
                "config": node.config or {},
            }
            if node.position_x is not None and node.position_y is not None:
                node_dict["position"] = {"x": node.position_x, "y": node.position_y}
            graph_data["nodes"].append(node_dict)

        for edge in model.edges:
            edge_dict = {
                "id": edge.edge_id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
            }
            if edge.condition_field:
                edge_dict["condition"] = {
                    "field": edge.condition_field,
                    "operator": edge.condition_operator,
                    "value": edge.condition_value,
                }
            graph_data["edges"].append(edge_dict)

        state_schema = {}
        for field in sorted(model.state_fields, key=lambda f: f.field_index):
            state_schema[field.field_name] = field.field_type

        return {
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "graph_data": graph_data,
            "state_schema": state_schema,
            "entry_point": model.entry_point,
            "human_in_the_loop": model.human_in_the_loop,
            "config": model.config,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        }

    async def get_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """根据名称获取工作流定义"""
        try:
            async def query(session):
                result = await session.execute(
                    select(WorkflowDefinition)
                    .filter_by(name=name)
                    .options(selectinload(WorkflowDefinition.nodes))
                    .options(selectinload(WorkflowDefinition.edges))
                    .options(selectinload(WorkflowDefinition.state_fields))
                )
                return result.scalar_one_or_none()

            result = await session_factory.execute_async(query)
            if result is None:
                return None
            return self._model_to_dict(result)
        except Exception as e:
            logger.error(f"Failed to get workflow definition '{name}': {e}")
            raise DatabaseError(message=str(e))

    async def list_all(self) -> list[dict[str, Any]]:
        """列出所有工作流定义"""
        try:
            async def query(session):
                result = await session.execute(
                    select(WorkflowDefinition)
                    .options(selectinload(WorkflowDefinition.nodes))
                    .options(selectinload(WorkflowDefinition.edges))
                    .options(selectinload(WorkflowDefinition.state_fields))
                )
                return result.scalars().all()

            results = await session_factory.execute_async(query)
            return [self._model_to_dict(r) for r in results]
        except Exception as e:
            logger.error(f"Failed to list workflow definitions: {e}")
            raise DatabaseError(message=str(e))

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """创建工作流定义"""
        try:
            graph_data = data.get("graph_data", {})

            instance = WorkflowDefinition(
                name=data["name"],
                description=data.get("description"),
                entry_point=data.get("entry_point") or graph_data.get("entry_point"),
                human_in_the_loop=data.get("human_in_the_loop"),
                config=data.get("config"),
            )
            for node_data in graph_data.get("nodes", []):
                pos = node_data.get("position", {})
                node = WorkflowDefinitionNode(
                    node_id=node_data["id"],
                    node_type=node_data.get("type", "processor"),
                    label=node_data.get("label", node_data["id"]),
                    handler=node_data.get("handler", ""),
                    position_x=pos.get("x"),
                    position_y=pos.get("y"),
                    config=node_data.get("config"),
                )
                instance.nodes.append(node)

            for edge_data in graph_data.get("edges", []):
                condition = edge_data.get("condition", {})
                edge = WorkflowDefinitionEdge(
                    edge_id=edge_data.get("id", f"{edge_data['source']}-{edge_data['target']}"),
                    source=edge_data["source"],
                    target=edge_data["target"],
                    edge_type=edge_data.get("type", "default"),
                    condition_field=condition.get("field"),
                    condition_operator=condition.get("operator"),
                    condition_value=condition.get("value"),
                )
                instance.edges.append(edge)

            state_schema = data.get("state_schema", {})
            for idx, (field_name, field_type) in enumerate(state_schema.items()):
                field = WorkflowStateField(
                    field_name=field_name,
                    field_type=field_type,
                    field_index=idx,
                )
                instance.state_fields.append(field)

            async def create_func(session):
                session.add(instance)
                await session.flush()
                await session.refresh(instance)
                return instance.id

            workflow_id = await session_factory.transaction_async(create_func)
            logger.info(f"Workflow definition created: {data['name']} (id={workflow_id})")
            # 从新 session 重新查询（带 eager load），避免 detached instance 问题
            return await self.get_by_name(data["name"])
        except Exception as e:
            logger.error(f"Failed to create workflow definition: {e}")
            raise DatabaseError(message=str(e))

    async def update(self, name: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新工作流定义"""
        try:
            async def update_func(session):
                result = await session.execute(
                    select(WorkflowDefinition)
                    .filter_by(name=name)
                    .options(selectinload(WorkflowDefinition.nodes))
                    .options(selectinload(WorkflowDefinition.edges))
                    .options(selectinload(WorkflowDefinition.state_fields))
                )
                instance: WorkflowDefinition | None = result.scalar_one_or_none()
                if instance is None:
                    return None

                if "name" in data:
                    instance.name = data["name"]
                if "description" in data:
                    instance.description = data["description"]
                if "human_in_the_loop" in data:
                    instance.human_in_the_loop = data["human_in_the_loop"]
                if "config" in data:
                    instance.config = data["config"]

                if "entry_point" in data:
                    instance.entry_point = data["entry_point"]

                if "graph_data" in data:
                    instance.nodes.clear()
                    instance.edges.clear()
                    graph_data = data["graph_data"]
                    if "entry_point" not in data and "entry_point" in graph_data:
                        instance.entry_point = graph_data["entry_point"]

                    for node_data in graph_data.get("nodes", []):
                        pos = node_data.get("position", {})
                        node = WorkflowDefinitionNode(
                            node_id=node_data["id"],
                            node_type=node_data.get("type", "processor"),
                            label=node_data.get("label", node_data["id"]),
                            handler=node_data.get("handler", ""),
                            position_x=pos.get("x"),
                            position_y=pos.get("y"),
                            config=node_data.get("config"),
                        )
                        instance.nodes.append(node)

                    for edge_data in graph_data.get("edges", []):
                        condition = edge_data.get("condition", {})
                        edge = WorkflowDefinitionEdge(
                            edge_id=edge_data.get("id", f"{edge_data['source']}-{edge_data['target']}"),
                            source=edge_data["source"],
                            target=edge_data["target"],
                            edge_type=edge_data.get("type", "default"),
                            condition_field=condition.get("field"),
                            condition_operator=condition.get("operator"),
                            condition_value=condition.get("value"),
                        )
                        instance.edges.append(edge)

                if "state_schema" in data:
                    instance.state_fields.clear()
                    state_schema = data["state_schema"]
                    for idx, (field_name, field_type) in enumerate(state_schema.items()):
                        field = WorkflowStateField(
                            field_name=field_name,
                            field_type=field_type,
                            field_index=idx,
                        )
                        instance.state_fields.append(field)

                await session.flush()
                await session.refresh(instance)
                return self._model_to_dict(instance)

            result = await session_factory.transaction_async(update_func)
            if result is None:
                return None

            logger.info(f"Workflow definition updated: {name}")
            return result
        except Exception as e:
            logger.error(f"Failed to update workflow definition: {e}")
            raise DatabaseError(message=str(e))

    async def delete(self, name: str) -> bool:
        """删除工作流定义"""
        try:
            async def delete_func(session):
                result = await session.execute(
                    select(WorkflowDefinition).filter_by(name=name)
                )
                instance = result.scalar_one_or_none()
                if instance is None:
                    return False
                await session.delete(instance)
                return True

            result = await session_factory.transaction_async(delete_func)
            if result:
                logger.info(f"Workflow definition deleted: {name}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete workflow definition: {e}")
            raise DatabaseError(message=str(e))

    async def add_node(self, workflow_name: str, node_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """添加节点"""
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        nodes = graph.get("nodes", [])
        nodes.append(node_data)
        graph["nodes"] = nodes
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def update_node(self, workflow_name: str, node_id: str, node_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新节点"""
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        nodes = graph.get("nodes", [])
        updated = False
        for i, n in enumerate(nodes):
            if n.get("id") == node_id:
                nodes[i] = {**n, **node_data, "id": node_id}
                updated = True
                break
        if not updated:
            nodes.append({**node_data, "id": node_id})
        graph["nodes"] = nodes
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def delete_node(self, workflow_name: str, node_id: str) -> Optional[dict[str, Any]]:
        """删除节点"""
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        graph["nodes"] = [n for n in graph.get("nodes", []) if n.get("id") != node_id]
        graph["edges"] = [e for e in graph.get("edges", []) if e.get("source") != node_id and e.get("target") != node_id]
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def add_edge(self, workflow_name: str, edge_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """添加边"""
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        edges = graph.get("edges", [])
        edges.append(edge_data)
        graph["edges"] = edges
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def update_edge(self, workflow_name: str, edge_id: str, edge_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新边"""
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        edges = graph.get("edges", [])
        updated = False
        for i, e in enumerate(edges):
            if e.get("id") == edge_id:
                edges[i] = {**e, **edge_data, "id": edge_id}
                updated = True
                break
        if not updated:
            edges.append({**edge_data, "id": edge_id})
        graph["edges"] = edges
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def delete_edge(self, workflow_name: str, edge_id: str) -> Optional[dict[str, Any]]:
        """删除边"""
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        graph["edges"] = [e for e in graph.get("edges", []) if e.get("id") != edge_id]
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)