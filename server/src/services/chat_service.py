# -*- coding: utf-8 -*-
"""
聊天服务

处理聊天业务逻辑，包括工作流执行和响应生成
"""

import asyncio
import json
from typing import Any, Optional, AsyncGenerator

from .base import Service
from constants.enums import ReasoningMode
from repositories.workflow_repository import WorkflowRepository
from repositories.workflow_definition_repository import WorkflowDefinitionRepository
from workflows.compiler import compile_workflow
from core.logger import logger


class ChatService(Service):
    """聊天服务"""

    def __init__(self, repository: Optional[WorkflowRepository] = None):
        """初始化聊天服务

        Args:
            repository: 工作流仓库实例
        """
        self._repository = repository or WorkflowRepository()
        self._definition_repo = WorkflowDefinitionRepository()
        logger.info("Chat service initialized")

    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """根据ID获取聊天记录

        Args:
            entity_id: 会话ID

        Returns:
            Optional[Any]: 聊天记录或None
        """
        logger.info(f"Get chat by id: {entity_id}")
        return await self._repository.get_state(entity_id)

    async def create(self, data: dict[str, Any]) -> Any:
        """创建聊天

        Args:
            data: 聊天数据

        Returns:
            Any: 聊天响应
        """
        message = data.get("message")
        session_id = data.get("session_id", "default")
        workflow = data.get("workflow", "intent_classifier")
        reasoning_config = data.get("reasoning")

        logger.info(f"Create chat: message={message[:50]}, session_id={session_id}, workflow={workflow}")

        result = await self._execute_workflow(workflow, message, session_id, reasoning_config)

        return {
            "response": result.get("response", ""),
            "session_id": session_id,
            "node": result.get("node"),
            "intermediate_steps": result.get("intermediate_steps"),
        }

    async def update(self, entity_id: str, data: dict[str, Any]) -> Any:
        """更新聊天

        Args:
            entity_id: 会话ID
            data: 更新数据

        Returns:
            Any: 更新后的聊天记录
        """
        data["session_id"] = entity_id
        return await self.create(data)

    async def delete(self, entity_id: str) -> bool:
        """删除聊天

        Args:
            entity_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        logger.info(f"Delete chat: {entity_id}")
        await self._repository.delete_state(entity_id)
        return True

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> dict[str, Any]:
        """查询所有聊天

        Args:
            page: 页码
            page_size: 每页记录数
            filters: 过滤条件
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            dict[str, Any]: 分页数据
        """
        offset = (page - 1) * page_size
        data = await self._repository.list_states(limit=page_size, offset=offset)
        return {"data": data, "total": len(data), "page": page, "page_size": page_size}

    async def _execute_workflow(
        self,
        workflow_name: str,
        message: str,
        session_id: str,
        reasoning_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        执行工作流

        Args:
            workflow_name: 工作流类型
            message: 用户消息
            session_id: 会话ID
            reasoning_config: 推理配置（可选）

        Returns:
            dict: 工作流执行结果
        """
        try:
            # 静态预定义工作流（硬编码路径）
            if workflow_name == "intent_classifier":
                from workflows.intent_classifier.workflow import IntentClassifierWorkflow

                result = await IntentClassifierWorkflow().arun(message, session_id)
            elif workflow_name == "customer_service":
                from workflows.customer_service.workflow import CustomerServiceWorkflow

                result = await CustomerServiceWorkflow().arun(message, session_id)
            elif workflow_name == "rag_qa":
                from workflows.rag_qa import run_rag_qa

                result = await asyncio.to_thread(run_rag_qa, message, session_id)
            elif workflow_name == "multi_agent":
                from workflows.multi_agent import run_multi_agent

                result = await asyncio.to_thread(run_multi_agent, message, session_id)
            elif workflow_name == "approval":
                from workflows.approval.workflow import ApprovalWorkflow

                request = self._build_approval_request(message, session_id)
                result = await ApprovalWorkflow().arun(request, session_id)
            elif workflow_name in ReasoningMode.get_all_marks():
                result = await self._execute_reasoning_workflow(workflow_name, message, session_id, reasoning_config)
            else:
                # 动态路径：从 DB 查询工作流定义，通过 compiler 编译执行
                definition = await self._definition_repo.get_by_name(workflow_name)
                if definition is not None:
                    result = await self._execute_dynamic_workflow(definition, message, session_id)
                else:
                    # fallback：使用默认工作流
                    logger.warning(f"Unknown workflow '{workflow_name}', falling back to intent_classifier")
                    from workflows.intent_classifier.workflow import IntentClassifierWorkflow

                    result = await IntentClassifierWorkflow().arun(message, session_id)

            return self._normalize_workflow_result(result)
        except ImportError as e:
            logger.error(f"Workflow import error: {e}")
            return {"response": "工作流加载失败", "node": None}
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {"response": "工作流执行失败", "node": None}

    async def _execute_dynamic_workflow(
        self, definition: dict[str, Any], message: str, session_id: str
    ) -> dict[str, Any]:
        """执行动态编译的工作流（来自 DB 定义）"""
        state_schema = definition.get("state_schema", {})
        state: dict[str, Any] = {}
        for field_name, field_type in state_schema.items():
            if field_name in ("input", "message"):
                state[field_name] = message
            elif field_type == "str" or field_type == "string":
                state[field_name] = ""
            elif field_type == "list":
                state[field_name] = []
            else:
                state[field_name] = None

        graph = compile_workflow(definition)
        result = await graph.ainvoke(
            state,
            config={"configurable": {"thread_id": session_id}},
        )
        return result

    async def _execute_reasoning_workflow(
        self,
        mode: str,
        message: str,
        session_id: str,
        config_dict: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        执行推理工作流（react / plan_execute / tot）

        三种推理模式的区别：
        - react: ReAct 模式，推理 → 行动 → 观察循环，适合工具调用场景
        - plan_execute: Plan-and-Execute 模式，先规划步骤再执行，适合复杂多步骤任务
        - tot: Tree-of-Thoughts 模式，多分支搜索探索最优解，适合开放式问题

        Args:
            mode: 推理模式标识（react | plan_execute | tot）
            message: 用户输入消息
            session_id: 会话 ID，用于 LLM 记忆
            config_dict: 可选配置，包含 max_iterations、timeout_seconds 等

        Returns:
            包含 final_answer 的结果字典
        """
        from workflows.reasoning.base import ReasoningConfig
        from workflows.reasoning import ReactWorkflow, create_plan_execute_workflow, create_tot_workflow

        cfg = ReasoningConfig(
            max_iterations=config_dict.get("max_iterations", 10) if config_dict else 10,
            timeout_seconds=config_dict.get("timeout_seconds", 300) if config_dict else 300,
            enable_reflection=config_dict.get("enable_reflection", True) if config_dict else True,
            llm_provider=config_dict.get("llm_provider", "deepseek") if config_dict else "deepseek",
            system_prompt=config_dict.get("system_prompt"),
        )

        # 初始化状态：包含消息历史、迭代计数器、中间步骤等
        state: dict[str, Any] = {
            "messages": [{"role": "user", "content": message}],
            "iteration": 0,
            "max_iterations": cfg.max_iterations,
            "intermediate_steps": [],
            "error": None,
            "session_id": session_id,
        }

        # 根据推理模式选择并初始化对应的工作流
        # - ReactWorkflow: ReAct 模式，内置 graph 属性，直接实例化使用
        # - create_plan_execute_workflow: 返回上下文管理器，需调用 __enter__ 获取 workflow 实例
        # - create_tot_workflow: 同上，且需要额外初始化树搜索相关状态（depth、max_depth、branches）
        if mode == "react":
            workflow = ReactWorkflow(config=cfg)
            graph = workflow.graph
        elif mode == "plan_execute":
            # Plan-and-Execute 模式：先规划再执行，支持执行过程中重规划
            wf = create_plan_execute_workflow(config=cfg)
            workflow = wf.__enter__()  # 进入上下文，初始化 planner 和 executor
            graph = workflow.graph
        elif mode == "tot":
            # Tree-of-Thoughts 模式：多分支搜索，需要初始化树的深度和分支状态
            wf = create_tot_workflow(config=cfg)
            workflow = wf.__enter__()
            graph = workflow.graph
            state["depth"] = 0  # 当前探索深度
            state["max_depth"] = config_dict.get("max_depth", 5) if config_dict else 5  # 最大探索深度
            state["branches"] = []  # 存储探索过的分支路径
            state["new_branches"] = []
            state["evaluation_results"] = []
            state["evaluated_branches"] = []
            state["best_branch_id"] = None
        else:
            return {"response": f"Unknown reasoning mode: {mode}", "node": None}

        try:
            result = await graph.ainvoke(
                state,
                config={"configurable": {"thread_id": session_id}},
            )
            # 提取最终响应
            response = (
                result.get("final_answer")
                or result.get("output")
                or result.get("best_branch_content", "")
            )
            if isinstance(result.get("messages"), list) and result.get("messages"):
                msgs = result["messages"]
                last = msgs[-1]
                if isinstance(last, dict):
                    response = response or last.get("content", "")
                elif hasattr(last, "content"):
                    response = response or last.content

            return {
                "response": response,
                "node": mode,
                "intermediate_steps": result.get("intermediate_steps", []),
                **result,
            }
        finally:
            if mode in ("plan_execute", "tot"):
                workflow.__exit__(None, None, None)

    async def stream(
        self,
        workflow_name: str,
        message: str,
        session_id: str,
        reasoning_config: Optional[Any] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        流式执行工作流

        Args:
            workflow_name: 工作流类型
            message: 用户消息
            session_id: 会话ID
            reasoning_config: 推理配置

        Yields:
            dict: 流式事件
        """
        try:
            # 推理工作流（react/plan_execute/tot）走独立流式路径，通过专门的流式处理器执行
            if workflow_name in ReasoningMode.get_all_marks():
                async for event in self._stream_reasoning_workflow(
                    workflow_name, message, session_id, reasoning_config
                ):
                    yield event
                return

            # 静态预定义工作流（硬编码路径）
            if workflow_name == "customer_service":
                from workflows.customer_service.workflow import CustomerServiceWorkflow

                workflow = CustomerServiceWorkflow()
                event_source = workflow.astream_run(message, session_id)
            else:
                # 先查 DB，看是否为自定义工作流
                definition = await self._definition_repo.get_by_name(workflow_name)
                if definition is not None:
                    async for event in self._stream_dynamic_workflow(definition, message, session_id):
                        yield event
                    return

                # fallback 到 intent_classifier
                from workflows.intent_classifier.workflow import IntentClassifierWorkflow

                workflow = IntentClassifierWorkflow()
                event_source = workflow.astream(
                    message,
                    config={"configurable": {"thread_id": session_id}},
                )

            async for event in event_source:
                async for stream_event in self._iter_stream_events(event):
                    yield stream_event

            yield {"event": "done", "data": None}
        except Exception as e:
            logger.error(f"Stream workflow execution error: {e}")
            yield {"event": "error", "data": str(e)}

    async def _stream_reasoning_workflow(
        self,
        mode: str,
        message: str,
        session_id: str,
        config_dict: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        流式执行推理工作流

        与 _execute_reasoning_workflow 类似，但通过 astream 实时 yield 每一步的中间结果，
        实现打字机效果的流式输出。ToT 模式额外维护了分支评估相关状态。

        Args:
            mode: 推理模式（react | plan_execute | tot）
            message: 用户消息
            session_id: 会话 ID
            config_dict: 可选配置，包含 max_iterations、max_depth 等

        Yields:
            流式事件字典，格式为 {"event": "xxx", "data": {...}}
        """
        from workflows.reasoning.base import ReasoningConfig
        from workflows.reasoning import ReactWorkflow, create_plan_execute_workflow, create_tot_workflow

        cfg = ReasoningConfig(
            max_iterations=config_dict.get("max_iterations", 10) if config_dict else 10,
            timeout_seconds=config_dict.get("timeout_seconds", 300) if config_dict else 300,
            enable_reflection=config_dict.get("enable_reflection", True) if config_dict else True,
            llm_provider=config_dict.get("llm_provider", "deepseek") if config_dict else "deepseek",
            system_prompt=config_dict.get("system_prompt"),
        )

        # 初始化状态（与 _execute_reasoning_workflow 相同）
        state: dict[str, Any] = {
            "messages": [{"role": "user", "content": message}],
            "iteration": 0,
            "max_iterations": cfg.max_iterations,
            "intermediate_steps": [],
            "error": None,
            "session_id": session_id,
        }

        # 根据模式选择工作流（与 _execute_reasoning_workflow 相同逻辑）
        # ToT 模式需要额外的树搜索状态用于流式输出中的分支评估展示
        if mode == "react":
            workflow = ReactWorkflow(config=cfg)
            graph = workflow.graph
        elif mode == "plan_execute":
            wf = create_plan_execute_workflow(config=cfg)
            workflow = wf.__enter__()
            graph = workflow.graph
        elif mode == "tot":
            # Tree-of-Thoughts：维护分支探索相关状态，用于流式输出展示探索进度
            wf = create_tot_workflow(config=cfg)
            workflow = wf.__enter__()
            graph = workflow.graph
            state["depth"] = 0
            state["max_depth"] = config_dict.get("max_depth", 5) if config_dict else 5
            state["branches"] = []
            state["new_branches"] = []
            state["evaluation_results"] = []
            state["evaluated_branches"] = []
            state["best_branch_id"] = None

        try:
            latest_state: dict[str, Any] = {}
            async for event in graph.astream(state, config={"configurable": {"thread_id": session_id}}, stream_mode="updates"):
                for node_name, node_output in event.items():
                    latest_state.update(node_output)
                    if isinstance(node_output, dict):
                        steps = node_output.get("intermediate_steps", [])
                        new_step = steps[-1] if steps else None
                        if new_step:
                            yield {
                                "event": "reasoning_step",
                                "node": node_name,
                                "step_type": new_step.get("step_type"),
                                "content": new_step.get("content"),
                                "metadata": new_step.get("metadata"),
                                "data": node_output,
                            }
                        else:
                            yield {
                                "event": "node_update",
                                "node": node_name,
                                "data": node_output,
                            }
                    else:
                        yield {"event": "node_update", "node": node_name, "data": node_output}

            response = latest_state.get("final_answer") or latest_state.get("output", "")
            if not response and isinstance(latest_state.get("messages"), list):
                msgs = latest_state["messages"]
                last = msgs[-1]
                response = (last.get("content") if isinstance(last, dict) else getattr(last, "content", "")) or ""

            yield {
                "event": "done",
                "node": mode,
                "data": {
                    "response": response,
                    "state": latest_state,
                    "intermediate_steps": latest_state.get("intermediate_steps", []),
                },
            }
        finally:
            if mode in ("plan_execute", "tot"):
                workflow.__exit__(None, None, None)

    async def _stream_dynamic_workflow(
        self, definition: dict[str, Any], message: str, session_id: str
    ) -> AsyncGenerator[dict, None]:
        """流式执行动态编译的工作流（来自 DB 定义）"""
        state_schema = definition.get("state_schema", {})
        state: dict[str, Any] = {}
        for field_name, field_type in state_schema.items():
            if field_name in ("input", "message"):
                state[field_name] = message
            elif field_type == "str" or field_type == "string":
                state[field_name] = ""
            elif field_type == "list":
                state[field_name] = []
            else:
                state[field_name] = None

        graph = compile_workflow(definition)

        latest_state: dict[str, Any] = {}
        async for event in graph.astream(
            state,
            config={"configurable": {"thread_id": session_id}},
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    latest_state.update(node_output)
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "data": node_output,
                }

        response = latest_state.get("output", "")
        yield {"event": "done", "data": {"response": response, "state": latest_state}}

    @staticmethod
    def _build_approval_request(message: str, session_id: str) -> dict[str, Any]:
        """从聊天消息构建审批请求（支持 JSON 或纯文本）"""
        try:
            parsed = json.loads(message)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        return {
            "request_type": "expense",
            "requester_id": session_id,
            "requester_name": "用户",
            "department": "默认部门",
            "amount": 500.0,
            "description": message,
        }

    @staticmethod
    def _normalize_workflow_result(result: Any) -> dict[str, Any]:
        """将各工作流返回值统一为 ChatService 响应格式"""
        if hasattr(result, "model_dump"):
            data = result.model_dump()
            response = getattr(result, "output", None) or ""
            return {"response": response, "node": None, **data}

        if isinstance(result, dict):
            response = (
                result.get("output")
                or result.get("response")
                or ""
            )
            node = result.get("node") or result.get("route") or result.get("stage")
            return {"response": response, "node": node, **result}

        return {"response": str(result), "node": None}

    @staticmethod
    async def _iter_stream_events(event: Any) -> AsyncGenerator[dict, None]:
        """将 LangGraph 流式更新转换为 SSE 事件格式"""
        if isinstance(event, dict):
            for node_name, node_output in event.items():
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "data": node_output,
                }
