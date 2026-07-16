# -*- coding: utf-8 -*-
"""
工作流定义数据访问层

基于 JSON 文件存储工作流定义，零数据库依赖，开箱即用。
每个工作流定义存储为 server/data/workflows/{name}.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.logger import logger


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "workflows"


class WorkflowDefinitionRepository:
    """工作流定义仓库（JSON 文件存储）"""

    def __init__(self):
        self._ensure_dir()

    def _ensure_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _file_path(self, name: str) -> Path:
        return DATA_DIR / f"{name}.json"

    async def get_by_name(self, name: str) -> Optional[dict[str, Any]]:
        try:
            path = self._file_path(name)
            if not path.exists():
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to get workflow definition '{name}': {e}")
            return None

    async def list_all(self) -> list[dict[str, Any]]:
        try:
            result = []
            for path in DATA_DIR.glob("*.json"):
                with open(path, "r", encoding="utf-8") as f:
                    result.append(json.load(f))
            return result
        except Exception as e:
            logger.error(f"Failed to list workflow definitions: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now().isoformat()
        data["created_at"] = now
        data["updated_at"] = now
        path = self._file_path(data["name"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Workflow definition created: {data['name']}")
        return data

    async def update(self, name: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        existing = await self.get_by_name(name)
        if existing is None:
            return None
        existing.update(data)
        existing["name"] = name
        existing["updated_at"] = datetime.now().isoformat()
        path = self._file_path(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info(f"Workflow definition updated: {name}")
        return existing

    async def delete(self, name: str) -> bool:
        path = self._file_path(name)
        if not path.exists():
            return False
        path.unlink()
        logger.info(f"Workflow definition deleted: {name}")
        return True

    async def add_node(self, workflow_name: str, node_data: dict[str, Any]) -> Optional[dict[str, Any]]:
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
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        nodes = graph.get("nodes", [])
        for i, n in enumerate(nodes):
            if n.get("id") == node_id:
                n.update(node_data)
                n["id"] = node_id
                nodes[i] = n
                break
        graph["nodes"] = nodes
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def delete_node(self, workflow_name: str, node_id: str) -> Optional[dict[str, Any]]:
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        graph["nodes"] = [n for n in graph.get("nodes", []) if n.get("id") != node_id]
        graph["edges"] = [e for e in graph.get("edges", []) if e.get("source") != node_id and e.get("target") != node_id]
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def add_edge(self, workflow_name: str, edge_data: dict[str, Any]) -> Optional[dict[str, Any]]:
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
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        edges = graph.get("edges", [])
        for i, e in enumerate(edges):
            if e.get("id") == edge_id:
                e.update(edge_data)
                e["id"] = edge_id
                edges[i] = e
                break
        graph["edges"] = edges
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)

    async def delete_edge(self, workflow_name: str, edge_id: str) -> Optional[dict[str, Any]]:
        wf = await self.get_by_name(workflow_name)
        if wf is None:
            return None
        graph = wf.get("graph_data", {})
        graph["edges"] = [e for e in graph.get("edges", []) if e.get("id") != edge_id]
        wf["graph_data"] = graph
        return await self.update(workflow_name, wf)
