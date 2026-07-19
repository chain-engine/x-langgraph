# -*- coding: utf-8 -*-
"""
多智能体协作工作流节点定义

展示 LangGraph 的多智能体协作模式：
- 协调者：任务分解和分配（LLM 动态分解）
- 研究员：信息收集和分析（可接入搜索工具）
- 撰写者：内容生成（LLM 生成）
- 编辑：内容优化（LLM 优化）
- 审核员：质量控制（LLM 审核）

已实现：
- Handoff 机制（Agent 自主决定下一步）
- Tool Calling（bind_tools 支持）

预留接口：
- 团队协作（parallel_execute 标记）
"""

import re
import time
import uuid
from typing import Optional, Callable, Any

from workflows.multi_agent.state import (
    MultiAgentState,
    TaskStatus,
    SubTask,
    AgentOutput,
    AgentHandoff,
    AgentConfig,
    AgentRole,
)
from tools.search_tools import web_search_tool, document_search_tool
from tools.data_tools import csv_processor_tool, json_processor_tool
from tools.calculation_tools import calculator_tool
from tools.database_tools import text_to_sql_tool, execute_sql_tool, get_schema_tool

from core.logger import logger
from core.config import settings


# ===== Agent 配置 =====

DEFAULT_AGENT_CONFIGS = {
    AgentRole.COORDINATOR: AgentConfig(
        name=AgentRole.COORDINATOR,
        role="协调者",
        llm_provider="auto",
        llm_model="",
        system_prompt="你是一个专业的任务协调者。你的职责是：1. 分析用户的请求 2. 将复杂任务分解为可执行的子任务 3. 为每个子任务分配最合适的执行者",
        temperature=0.7,
    ),
    AgentRole.RESEARCHER: AgentConfig(
        name=AgentRole.RESEARCHER,
        role="研究员",
        llm_provider="auto",
        llm_model="",
        system_prompt="你是一个专业的研究员。你的职责是：1. 收集和整理与主题相关的信息 2. 分析数据的可靠性和相关性 3. 提供结构化的研究发现",
        temperature=0.7,
    ),
    AgentRole.WRITER: AgentConfig(
        name=AgentRole.WRITER,
        role="撰写者",
        llm_provider="auto",
        llm_model="",
        system_prompt="你是一个专业的内容撰写者。你的职责是：1. 基于研究结果撰写高质量内容 2. 确保内容结构清晰、逻辑连贯 3. 使用恰当的表达方式和格式",
        temperature=0.7,
    ),
    AgentRole.EDITOR: AgentConfig(
        name=AgentRole.EDITOR,
        role="编辑",
        llm_provider="auto",
        llm_model="",
        system_prompt="你是一个专业的编辑。你的职责是：1. 优化内容的结构和表达 2. 修正语法、拼写和格式错误 3. 提升内容的可读性和专业性",
        temperature=0.5,
    ),
    AgentRole.REVIEWER: AgentConfig(
        name=AgentRole.REVIEWER,
        role="审核员",
        llm_provider="auto",
        llm_model="",
        system_prompt="你是一个严格的质量审核员。你的职责是：1. 检查内容的完整性和准确性 2. 评估内容的质量和价值 3. 提供具体的改进建议",
        temperature=0.3,
    ),
}


# ===== Agent LLM 缓存 =====

_agent_llms: dict[str, any] = {}


def get_agent_llm(config: AgentConfig):
    """获取 Agent 的 LLM 实例（带缓存）"""
    cache_key = f"{config.name}_{config.llm_provider}_{config.llm_model}"

    if cache_key not in _agent_llms:
        from llms.providers import get_llm_provider

        provider_name = config.llm_provider if config.llm_provider != "auto" else settings.get_available_provider()
        _agent_llms[cache_key] = get_llm_provider(provider_name)
        logger.info(f"Agent [{config.name}] 使用 LLM: {provider_name}")

    return _agent_llms[cache_key]


def clear_agent_llm_cache():
    """清除 LLM 缓存"""
    global _agent_llms
    _agent_llms = {}


# ===== 任务分解（协调者）=====

def _parse_json_response(text: str, default: str = "") -> str:
    """从 LLM 响应中提取 JSON"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        import json
        try:
            return json.dumps(json.loads(match.group()), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return default or text


# ===== Handoff 工具函数 =====

def create_handoff(to_agent: str, from_agent: str, context: dict, reason: str = "") -> AgentHandoff:
    """
    创建 Handoff

    Args:
        to_agent: 目标 Agent
        from_agent: 来源 Agent
        context: 传递的上下文
        reason: 交接原因

    Returns:
        AgentHandoff 对象
    """
    return AgentHandoff(
        from_agent=from_agent,
        to_agent=to_agent,
        reason=reason,
        context=context,
    )


def execute_handoff(state: MultiAgentState, handoff: AgentHandoff) -> dict:
    """
    执行 Handoff

    将控制权传递给目标 Agent。

    Args:
        state: 当前状态
        handoff: Handoff 信息

    Returns:
        状态更新
    """
    handoffs = state.get("handoffs", [])
    handoffs.append(handoff.model_dump())

    return {
        "handoffs": handoffs,
        "pending_handoff": handoff.model_dump(),
        "current_agent": handoff.to_agent,
    }


# ===== 任务分解（协调者）=====


def coordinator_node(state: MultiAgentState) -> dict:
    """
    协调者节点

    职责：
    1. 分析用户请求
    2. 使用 LLM 动态分解为子任务
    3. 决定第一个执行者（通过 Handoff）

    Args:
        state: 当前状态

    Returns:
        状态更新，包含 Handoff 指令
    """
    logger.info("Handoff: Coordinator 开始分析任务")

    request = state.get("original_request", "")

    try:
        # 使用 LLM 动态分解任务
        tasks = _decompose_with_llm(request)

        # 序列化任务
        task_dicts = [task.model_dump() for task in tasks]

        logger.info(f"Handoff: Coordinator 分解为 {len(tasks)} 个子任务")

        # 确定第一个 Handoff 目标
        next_agent = AgentRole.END_NODE
        handoff_reason = "所有任务已完成"
        if task_dicts:
            first_task = task_dicts[0]
            next_agent = first_task.get("assigned_to", AgentRole.END_NODE)
            handoff_reason = f"任务分配：{first_task.get('description', '')}"

        # 构建 Handoff
        handoff = AgentHandoff(
            to_agent=next_agent,
            reason=handoff_reason,
            context={"tasks": task_dicts},
            from_agent=AgentRole.COORDINATOR,
        )

        return {
            "tasks": task_dicts,
            "current_stage": AgentRole.COORDINATOR,
            "current_agent": AgentRole.COORDINATOR,
            "iteration_count": 0,
            "completed_tasks": [],
            "handoffs": [],
            "active_handoff": handoff.model_dump(),
            "handoff_history": [handoff.model_dump()],
            "route": next_agent,
        }

    except Exception as e:
        logger.error(f"Handoff: Coordinator 任务分解失败 - {e}")
        tasks = _decompose_default(request)
        task_dicts = [task.model_dump() for task in tasks]
        next_agent = task_dicts[0].get("assigned_to", AgentRole.END_NODE) if task_dicts else AgentRole.END_NODE

        handoff = AgentHandoff(
            to_agent=next_agent,
            reason="默认任务分配",
            context={"tasks": task_dicts},
            from_agent=AgentRole.COORDINATOR,
        )

        return {
            "tasks": task_dicts,
            "current_stage": AgentRole.COORDINATOR,
            "current_agent": AgentRole.COORDINATOR,
            "active_handoff": handoff.model_dump(),
            "handoff_history": [handoff.model_dump()],
            "route": next_agent,
            "error": str(e),
        }


def _decompose_with_llm(request: str) -> list[SubTask]:
    """
    使用 LLM 动态分解任务

    Args:
        request: 用户请求

    Returns:
        子任务列表

    Raises:
        Exception: LLM 调用失败时抛出异常
    """
    import json

    config = DEFAULT_AGENT_CONFIGS.get(AgentRole.COORDINATOR)
    llm = get_agent_llm(config)

    prompt = f"""{config.system_prompt}

用户请求：{request}

可用角色：researcher（研究员）、writer（撰写者）、editor（编辑）、reviewer（审核员）

请将用户请求分解为 2-4 个逻辑清晰的子任务，并按依赖关系排序。
返回 JSON 格式：
{{
    "tasks": [
        {{
            "description": "任务描述",
            "assigned_to": "角色名",
            "priority": "high/medium/low",
            "dependencies": []
        }}
    ],
    "reasoning": "分解理由"
}}"""

    response = llm.invoke([
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": prompt},
    ])
    result = response.content if hasattr(response, "content") else str(response)

    data = json.loads(_parse_json_response(result))

    tasks = []
    for task_data in data.get("tasks", []):
        task_id = f"task-{uuid.uuid4().hex[:6]}"

        dependencies = task_data.get("dependencies", [])
        dep_ids = []
        for dep_name in dependencies:
            dep_str = str(dep_name) if not isinstance(dep_name, str) else dep_name
            for prev_task in tasks:
                if prev_task.description.startswith(dep_str):
                    dep_ids.append(prev_task.id)
                    break

        tasks.append(
            SubTask(
                id=task_id,
                description=task_data.get("description", ""),
                assigned_to=task_data.get("assigned_to", AgentRole.WRITER),
                status=TaskStatus.PENDING.value,
                priority=task_data.get("priority", "medium"),
                dependencies=dep_ids,
            )
        )

    return tasks


def _decompose_default(request: str) -> list[SubTask]:
    """
    默认任务分解（LLM 不可用时的备选方案）

    Args:
        request: 用户请求

    Returns:
        子任务列表
    """
    tasks = []

    research_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=research_id,
            description=f"研究主题：{request}",
            assigned_to=AgentRole.RESEARCHER,
            status=TaskStatus.PENDING.value,
        )
    )

    write_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=write_id,
            description="基于研究结果撰写内容",
            assigned_to=AgentRole.WRITER,
            status=TaskStatus.PENDING.value,
            dependencies=[research_id],
        )
    )

    edit_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=edit_id,
            description="优化和完善内容",
            assigned_to=AgentRole.EDITOR,
            status=TaskStatus.PENDING.value,
            dependencies=[write_id],
        )
    )

    review_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=review_id,
            description="审核内容质量",
            assigned_to=AgentRole.REVIEWER,
            status=TaskStatus.PENDING.value,
            dependencies=[edit_id],
        )
    )

    return tasks


# ===== 研究员节点 =====


def researcher_node(state: MultiAgentState) -> dict:
    """
    研究员节点（独立 LLM + Handoff）

    职责：
    1. 收集信息
    2. 分析数据
    3. 决定下一步（通过 Handoff）

    Args:
        state: 当前状态

    Returns:
        状态更新，包含 Handoff 指令
    """
    logger.info("Handoff: Researcher 开始工作")

    request = state.get("original_request", "")

    # 获取 Researcher 的独立 LLM
    config = DEFAULT_AGENT_CONFIGS.get(AgentRole.RESEARCHER)
    llm = get_agent_llm(config)

    try:
        start_time = time.time()

        # 构建 prompt
        prompt = f"""{config.system_prompt}

主题：{request}

请提供详细的研究结果，包括：
1. 背景信息
2. 关键发现
3. 数据支持
4. 建议和结论

完成研究后，明确告诉我要交接给哪个 Agent（writer 或 editor）。"""

        # 调用 LLM
        response = llm.invoke([
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": prompt},
        ])
        findings = response.content if hasattr(response, "content") else str(response)

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.RESEARCHER, findings
        )

        # 决定下一步 Handoff
        next_agent = _get_next_agent(state, AgentRole.RESEARCHER, [AgentRole.WRITER, AgentRole.EDITOR, AgentRole.REVIEWER])

        handoff = AgentHandoff(
            to_agent=next_agent,
            reason="研究完成，需要进入下一个阶段",
            context={"research_findings": findings},
            from_agent=AgentRole.RESEARCHER,
        )

        logger.info(f"Handoff: Researcher 完成，耗时 {duration}ms，下一步 → {next_agent}")

        return {
            "research_findings": findings,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": AgentRole.RESEARCHER,
            "current_agent": AgentRole.RESEARCHER,
            "active_handoff": handoff.model_dump(),
            "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
            "route": next_agent,
        }

    except Exception as e:
        logger.error(f"Handoff: Researcher 失败 - {e}")
        return {
            "research_findings": f"研究失败: {str(e)}",
            "error": f"研究阶段错误: {str(e)}",
            "active_handoff": None,
            "route": AgentRole.END_NODE,
        }


# ===== 撰写者节点 =====


def writer_node(state: MultiAgentState) -> dict:
    """
    撰写者节点（独立 LLM + Handoff）

    职责：
    1. 基于研究结果撰写内容
    2. 组织结构
    3. 决定下一步（通过 Handoff）

    Args:
        state: 当前状态

    Returns:
        状态更新，包含 Handoff 指令
    """
    logger.info("Handoff: Writer 开始工作")

    request = state.get("original_request", "")
    research = state.get("research_findings", "")

    # 获取 Writer 的独立 LLM
    config = DEFAULT_AGENT_CONFIGS.get(AgentRole.WRITER)
    llm = get_agent_llm(config)

    try:
        start_time = time.time()

        # 构建 prompt
        prompt = f"""主题：{request}

研究发现：
{research}

请撰写一篇结构完整、内容充实的文章。

完成后，明确告诉我要交接给哪个 Agent（editor 或 reviewer）。"""

        # 调用 LLM
        response = llm.invoke([
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": prompt},
        ])
        draft = response.content if hasattr(response, "content") else str(response)

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.WRITER, draft
        )

        # 决定下一步 Handoff
        next_agent = _get_next_agent(state, AgentRole.WRITER, [AgentRole.EDITOR, AgentRole.REVIEWER])

        handoff = AgentHandoff(
            to_agent=next_agent,
            reason="撰写完成，需要进入编辑阶段",
            context={"draft_content": draft},
            from_agent=AgentRole.WRITER,
        )

        logger.info(f"Handoff: Writer 完成，耗时 {duration}ms，下一步 → {next_agent}")

        return {
            "draft_content": draft,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": AgentRole.WRITER,
            "current_agent": AgentRole.WRITER,
            "active_handoff": handoff.model_dump(),
            "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
            "route": next_agent,
        }

    except Exception as e:
        logger.error(f"Handoff: Writer 失败 - {e}")
        return {
            "draft_content": f"撰写失败: {str(e)}",
            "error": f"撰写阶段错误: {str(e)}",
            "active_handoff": None,
            "route": AgentRole.END_NODE,
        }


# ===== 编辑节点 =====


def editor_node(state: MultiAgentState) -> dict:
    """
    编辑节点（独立 LLM + Handoff）

    职责：
    1. 优化内容结构
    2. 改进语言表达
    3. 决定下一步（通过 Handoff）

    Args:
        state: 当前状态

    Returns:
        状态更新，包含 Handoff 指令
    """
    logger.info("Handoff: Editor 开始工作")

    draft = state.get("draft_content", "")
    revision_requests = state.get("revision_requests", [])

    # 获取 Editor 的独立 LLM
    config = DEFAULT_AGENT_CONFIGS.get(AgentRole.EDITOR)
    llm = get_agent_llm(config)

    try:
        start_time = time.time()

        # 构建编辑提示
        revision_note = ""
        if revision_requests:
            revision_note = "\n\n修订要求：\n" + "\n".join(f"- {req}" for req in revision_requests)

        prompt = f"""原始内容：
{draft}

{revision_note}

请优化内容，提升质量和可读性。

完成后，明确告诉我要交接给哪个 Agent（reviewer 或继续给自己进行更多修改）。"""

        # 调用 LLM
        response = llm.invoke([
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": prompt},
        ])
        edited = response.content if hasattr(response, "content") else str(response)

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.EDITOR, edited
        )

        # 编辑完成后总是进入审核
        next_agent = AgentRole.REVIEWER

        handoff = AgentHandoff(
            to_agent=next_agent,
            reason="编辑优化完成，进入审核阶段",
            context={"edited_content": edited},
            from_agent=AgentRole.EDITOR,
        )

        logger.info(f"Handoff: Editor 完成，耗时 {duration}ms，下一步 → {next_agent}")

        return {
            "edited_content": edited,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": AgentRole.EDITOR,
            "current_agent": AgentRole.EDITOR,
            "revision_requests": [],
            "active_handoff": handoff.model_dump(),
            "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
            "route": next_agent,
        }

    except Exception as e:
        logger.error(f"Handoff: Editor 失败 - {e}")
        return {
            "edited_content": draft,
            "error": f"编辑阶段错误: {str(e)}",
            "active_handoff": None,
            "route": AgentRole.END_NODE,
        }


# ===== 审核员节点 =====


def reviewer_node(state: MultiAgentState) -> dict:
    """
    审核员节点（独立 LLM + Handoff）

    职责：
    1. 质量检查
    2. 提供反馈
    3. 决定是否需要修订（通过 Handoff）

    Args:
        state: 当前状态

    Returns:
        状态更新，包含 Handoff 指令
    """
    logger.info("Handoff: Reviewer 开始工作")

    edited_content = state.get("edited_content", "")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    # 获取 Reviewer 的独立 LLM
    config = DEFAULT_AGENT_CONFIGS.get(AgentRole.REVIEWER)
    llm = get_agent_llm(config)

    try:
        start_time = time.time()

        # 构建审核提示
        prompt = f"""待审核内容：
{edited_content}

请仔细审核内容，如果需要修订请明确列出问题。

如果内容质量达标，明确告诉我要交接给 'END' 结束流程。
如果需要修订，告诉我要交接给 'editor' 进行修订。"""

        # 调用 LLM
        response = llm.invoke([
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": prompt},
        ])
        review_result = response.content if hasattr(response, "content") else str(response)

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.REVIEWER, review_result
        )

        # 判断是否需要修订
        needs_revision = _check_needs_revision(review_result) and iteration_count < max_iterations

        # 提取修订请求
        revision_requests = []
        if needs_revision:
            revision_requests = _extract_revision_requests(review_result)

        # 决定下一步 Handoff
        next_agent = AgentRole.EDITOR if needs_revision else AgentRole.END_NODE
        handoff_reason = "内容需要修订" if needs_revision else "内容审核通过，流程结束"

        handoff = AgentHandoff(
            to_agent=next_agent,
            reason=handoff_reason,
            context={"review_feedback": review_result, "needs_revision": needs_revision},
            from_agent=AgentRole.REVIEWER,
        )

        logger.info(f"Handoff: Reviewer 完成，{'需要修订' if needs_revision else '通过'}，下一步 → {next_agent}")

        return {
            "review_feedback": review_result,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": AgentRole.REVIEWER,
            "current_agent": AgentRole.REVIEWER,
            "needs_revision": needs_revision,
            "revision_requests": revision_requests,
            "iteration_count": iteration_count + 1,
            "output": edited_content if not needs_revision else "",
            "active_handoff": handoff.model_dump(),
            "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
            "route": next_agent,
        }

    except Exception as e:
        logger.error(f"Handoff: Reviewer 失败 - {e}")
        return {
            "review_feedback": f"审核失败: {str(e)}",
            "error": f"审核阶段错误: {str(e)}",
            "output": edited_content,
            "active_handoff": None,
            "route": AgentRole.END_NODE,
        }


def _check_needs_revision(review: str) -> bool:
    """检查审核结果是否表示需要修订"""
    revision_keywords = ["修订", "修改", "改进", "建议", "问题", "不足", "需要调整"]
    review_lower = review.lower()

    # 检查是否包含修订关键词
    for keyword in revision_keywords:
        if keyword in review_lower:
            return True

    # 检查是否有明确的问题列表
    if re.search(r"(问题|建议|修订)\s*[:：]", review, re.IGNORECASE):
        return True

    return False


def _extract_revision_requests(review: str) -> list[str]:
    """从审核反馈中提取修订请求"""
    requests = []
    lines = review.split("\n")

    in_revision_section = False
    for line in lines:
        line = line.strip()

        # 检测修订区域
        if any(kw in line for kw in ["修订", "修改", "建议", "问题"]):
            if ":" in line or "：" in line:
                in_revision_section = True
                continue

        if in_revision_section and line.startswith(("1.", "2.", "3.", "4.", "5.", "-", "*", "•")):
            # 清理标记
            cleaned = re.sub(r"^[\d\.\-\*\•]+\s*", "", line)
            if cleaned and len(cleaned) > 3:
                requests.append(cleaned)

    return requests[:5]  # 限制最多 5 条修订请求


# ===== 辅助函数 =====


def _update_task_status(
    state: MultiAgentState, agent_role: AgentRole | str, result: str
) -> tuple[list[dict], list[str]]:
    """
    更新任务状态

    Args:
        state: 当前状态
        agent_role: 智能体角色
        result: 任务结果

    Returns:
        (更新后的 tasks, 更新后的 completed_tasks)
    """
    role_str = agent_role.value if isinstance(agent_role, AgentRole) else agent_role
    tasks = state.get("tasks", [])
    completed_tasks = list(state.get("completed_tasks", []))

    for task_dict in tasks:
        if task_dict.get("assigned_to") == role_str:
            task_id = task_dict.get("id")
            if task_id not in completed_tasks:
                task_dict["status"] = TaskStatus.COMPLETED.value
                task_dict["result"] = result
                completed_tasks.append(task_id)
                break

    return tasks, completed_tasks

    return tasks, completed_tasks


def _get_next_agent(state: MultiAgentState, completed_agent: AgentRole | str, candidates: list[AgentRole | str]) -> str:
    """
    根据已完成的任务确定下一个 Handoff 目标

    Args:
        state: 当前状态
        completed_agent: 已完成的 Agent
        candidates: 候选的下一个 Agent 列表

    Returns:
        下一个 Agent 名称或 AgentRole.END_NODE
    """
    completed_str = completed_agent.value if isinstance(completed_agent, AgentRole) else completed_agent
    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))
    completed_tasks.add(completed_str)

    # 按顺序查找下一个未完成的任务
    for agent in candidates:
        agent_str = agent.value if isinstance(agent, AgentRole) else agent
        if agent_str == completed_str:
            continue
        for task in tasks:
            if task.get("assigned_to") == agent_str and task.get("id") not in completed_tasks:
                return agent_str

    return AgentRole.END_NODE


def _get_next_route(state: MultiAgentState, completed_role: AgentRole | str) -> str:
    """
    根据已完成的任务确定下一个路由目标（兼容旧代码）

    Args:
        state: 当前状态
        completed_role: 已完成任务的角色

    Returns:
        下一个路由目标（agent 名称或 AgentRole.END_NODE）
    """
    return _get_next_agent(
        state, completed_role,
        [AgentRole.RESEARCHER, AgentRole.WRITER, AgentRole.EDITOR, AgentRole.REVIEWER]
    )


# ===== 条件路由函数 =====


def handoff_router(state: MultiAgentState) -> str:
    """
    Handoff 路由节点：基于 Agent 的 Handoff 决定下一个节点

    这是 Handoff 模式的核心：
    - 每个 Agent 执行完后会设置 active_handoff
    - 这个路由函数读取 active_handoff 并决定下一步

    Args:
        state: 当前状态

    Returns:
        下一个节点名称（agent 名称或 END）
    """
    handoff = state.get("active_handoff")

    if handoff:
        next_agent = handoff.get("to_agent", AgentRole.END_NODE)
        logger.info(f"Handoff Router: {handoff.get('from_agent', 'unknown')} → {next_agent} ({handoff.get('reason', '')})")
        return next_agent

    # 如果没有 Handoff，检查是否有待处理的任务
    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))

    for task_dict in tasks:
        task_id = task_dict.get("id")
        if task_id in completed_tasks:
            continue

        dependencies = task_dict.get("dependencies", [])
        if all(dep in completed_tasks for dep in dependencies):
            agent = task_dict.get("assigned_to")
            return agent

    return AgentRole.END_NODE


def route_to_agent_node(state: MultiAgentState) -> str:
    """
    条件路由节点：决定下一个执行的智能体（兼容旧代码）

    基于任务依赖关系和完成状态进行路由。

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    # 优先使用 Handoff 协议
    if state.get("active_handoff"):
        return handoff_router(state)

    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))

    # 检查是否需要修订（回到编辑）
    if state.get("needs_revision", False):
        return AgentRole.EDITOR

    # 找到下一个可执行的任务
    for task_dict in tasks:
        task_id = task_dict.get("id")
        if task_id in completed_tasks:
            continue

        dependencies = task_dict.get("dependencies", [])
        if all(dep in completed_tasks for dep in dependencies):
            agent = task_dict.get("assigned_to")
            return agent

    return AgentRole.END_NODE


# ===== 已实现：并行执行路由 =====

def route_for_parallel_node(state: MultiAgentState) -> list[str]:
    """
    条件路由节点：返回可并行执行的任务列表

    查找所有依赖已满足且相互之间无依赖的任务。
    这些任务可以被并行执行。

    Args:
        state: 当前状态

    Returns:
        可并行执行的任务 ID 列表
    """
    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))

    ready_tasks = []

    for task_dict in tasks:
        task_id = task_dict.get("id")
        if task_id in completed_tasks:
            continue

        dependencies = task_dict.get("dependencies", [])
        if all(dep in completed_tasks for dep in dependencies):
            ready_tasks.append(task_id)

    logger.info(f"并行执行路由：{len(ready_tasks)} 个任务就绪")
    return ready_tasks


def get_parallel_tasks(state: MultiAgentState) -> list[dict]:
    """
    获取可并行执行的任务详情列表

    与 route_for_parallel_node 不同，此函数返回完整任务信息，
    用于并行节点执行。

    Args:
        state: 当前状态

    Returns:
        可并行执行的任务详情列表
    """
    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))
    parallel_task_ids = set()

    for task_dict in tasks:
        task_id = task_dict.get("id")
        if task_id in completed_tasks:
            continue

        dependencies = task_dict.get("dependencies", [])
        if all(dep in completed_tasks for dep in dependencies):
            parallel_task_ids.add(task_id)

    parallel_task_list = []
    for task_id in parallel_task_ids:
        for task_dict in tasks:
            if task_dict.get("id") == task_id:
                parallel_task_list.append(task_dict)
                break

    return parallel_task_list


# ===== 已实现：Handoff 路由 =====

def route_with_handoff(state: MultiAgentState) -> str:
    """
    Handoff 路由函数

    优先使用 active_handoff（Agent 主动发起的 Handoff），
    其次检查 pending_handoff，最后降级到基于任务依赖的路由。

    Args:
        state: 当前状态

    Returns:
        下一个 Agent 或 'END'
    """
    # 1. 优先使用 active_handoff（每个 Agent 执行后设置的）
    active_handoff = state.get("active_handoff")
    if active_handoff:
        to_agent = active_handoff.get("to_agent", AgentRole.END_NODE)
        logger.info(f"Handoff: {active_handoff.get('from_agent', 'unknown')} → {to_agent} ({active_handoff.get('reason', '')})")
        return to_agent

    # 2. 检查 pending_handoff
    pending_handoff = state.get("pending_handoff")
    if pending_handoff:
        return pending_handoff.get("to_agent", AgentRole.END_NODE)

    # 3. 降级到基于任务依赖的路由
    return route_to_agent_node(state)


def initiate_handoff(
    to_agent: str,
    from_agent: str,
    context: dict,
    reason: str = "",
) -> AgentHandoff:
    """
    发起 Handoff

    创建一个 Handoff 对象，由调用方设置到 state 中。

    Args:
        to_agent: 目标 Agent
        from_agent: 来源 Agent
        context: 传递的上下文
        reason: 交接原因

    Returns:
        AgentHandoff 对象
    """
    handoff = AgentHandoff(
        to_agent=to_agent,
        from_agent=from_agent,
        reason=reason,
        context=context,
    )
    logger.info(f"Handoff 创建: {from_agent} → {to_agent} ({reason})")
    return handoff


def should_parallel_execute(state: MultiAgentState) -> bool:
    """
    判断是否应该并行执行

    当存在多个就绪且无相互依赖的任务时，返回 True。

    Args:
        state: 当前状态

    Returns:
        是否应该并行执行
    """
    parallel_ids = route_for_parallel_node(state)
    return len(parallel_ids) >= 2


# ===== Tool Calling 实现 =====


def create_researcher_with_tools():
    """
    创建带工具的研究员节点。

    使用 create_react_agent 实现完整的 ReAct 推理循环，
    支持 web_search / document_search / calculator / get_schema / execute_sql 工具。

    Returns:
        带工具的研究员节点函数
    """
    from langgraph.prebuilt import create_react_agent

    tools = [web_search_tool, document_search_tool, calculator_tool, get_schema_tool]
    model = get_agent_llm(DEFAULT_AGENT_CONFIGS[AgentRole.RESEARCHER])
    agent = create_react_agent(model, tools)

    def researcher_with_tools(state: MultiAgentState) -> dict:
        """带工具的研究员节点"""
        logger.info("Researcher（带工具）开始工作")

        request = state.get("original_request", "")
        messages = [{"role": "user", "content": f"研究主题：{request}"}]

        try:
            response = agent.invoke({"messages": messages})
            findings = _extract_agent_response(response)

            tasks, completed_tasks = _update_task_status(state, AgentRole.RESEARCHER, findings)
            next_agent = _get_next_agent(state, AgentRole.RESEARCHER, [AgentRole.WRITER, AgentRole.EDITOR, AgentRole.REVIEWER])

            handoff = AgentHandoff(
                to_agent=next_agent,
                reason="研究完成，需要进入下一个阶段",
                context={"research_findings": findings},
                from_agent=AgentRole.RESEARCHER,
            )

            return {
                "research_findings": findings,
                "tasks": tasks,
                "completed_tasks": completed_tasks,
                "current_stage": AgentRole.RESEARCHER,
                "current_agent": AgentRole.RESEARCHER,
                "active_handoff": handoff.model_dump(),
                "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
                "route": next_agent,
            }

        except Exception as e:
            logger.error(f"Researcher（带工具）失败 - {e}")
            return {
                "research_findings": f"研究失败: {str(e)}",
                "error": str(e),
                "active_handoff": None,
                "route": AgentRole.END_NODE,
            }

    return researcher_with_tools


def create_writer_with_tools():
    """
    创建带工具的撰写者节点。

    支持 calculator / csv_processor / json_processor 工具，
    让撰写者在内容中加入实时计算结果和数据引用。

    Returns:
        带工具的撰写者节点函数
    """
    from langgraph.prebuilt import create_react_agent

    tools = [calculator_tool, csv_processor_tool, json_processor_tool]
    model = get_agent_llm(DEFAULT_AGENT_CONFIGS[AgentRole.WRITER])
    agent = create_react_agent(model, tools)

    def writer_with_tools(state: MultiAgentState) -> dict:
        """带工具的撰写者节点"""
        logger.info("Writer（带工具）开始工作")

        request = state.get("original_request", "")
        findings = state.get("research_findings", "")
        prompt = f"""原始请求：{request}

已有研究发现：
{findings}

请基于以上信息撰写高质量的内容。"""
        messages = [{"role": "user", "content": prompt}]

        try:
            response = agent.invoke({"messages": messages})
            draft = _extract_agent_response(response)

            tasks, completed_tasks = _update_task_status(state, AgentRole.WRITER, draft)
            next_agent = _get_next_agent(state, AgentRole.WRITER, [AgentRole.EDITOR, AgentRole.REVIEWER])

            handoff = AgentHandoff(
                to_agent=next_agent,
                reason="撰写完成，需要进入编辑阶段",
                context={"draft_content": draft},
                from_agent=AgentRole.WRITER,
            )

            return {
                "draft_content": draft,
                "tasks": tasks,
                "completed_tasks": completed_tasks,
                "current_stage": AgentRole.WRITER,
                "current_agent": AgentRole.WRITER,
                "active_handoff": handoff.model_dump(),
                "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
                "route": next_agent,
            }

        except Exception as e:
            logger.error(f"Writer（带工具）失败 - {e}")
            return {
                "draft_content": f"撰写失败: {str(e)}",
                "error": str(e),
                "active_handoff": None,
                "route": AgentRole.END_NODE,
            }

    return writer_with_tools


def create_database_query_node():
    """
    创建数据库查询节点。

    使用 text2sql 工具将自然语言转换为 SQL，
    然后执行查询并返回结构化结果。

    Returns:
        数据库查询节点函数
    """
    from langgraph.prebuilt import create_react_agent

    tools = [text_to_sql_tool, execute_sql_tool, get_schema_tool]
    model = get_agent_llm(DEFAULT_AGENT_CONFIGS[AgentRole.RESEARCHER])
    agent = create_react_agent(model, tools)

    def database_query_node(state: MultiAgentState) -> dict:
        """数据库查询节点"""
        logger.info("Database Query 开始工作")

        request = state.get("original_request", "")
        messages = [{"role": "user", "content": f"请帮我查询数据库：{request}"}]

        try:
            response = agent.invoke({"messages": messages})
            query_result = _extract_agent_response(response)

            next_agent = _get_next_agent(state, AgentRole.RESEARCHER, [AgentRole.WRITER, AgentRole.EDITOR, AgentRole.REVIEWER])

            handoff = AgentHandoff(
                to_agent=next_agent,
                reason="数据库查询完成",
                context={"db_query_result": query_result},
                from_agent=AgentRole.RESEARCHER,
            )

            return {
                "research_findings": state.get("research_findings", "") + f"\n\n[数据库查询结果]\n{query_result}",
                "tasks": state.get("tasks", []),
                "completed_tasks": state.get("completed_tasks", []),
                "current_stage": AgentRole.RESEARCHER,
                "current_agent": AgentRole.RESEARCHER,
                "active_handoff": handoff.model_dump(),
                "handoff_history": state.get("handoff_history", []) + [handoff.model_dump()],
                "route": next_agent,
            }

        except Exception as e:
            logger.error(f"Database Query 失败 - {e}")
            return {
                "error": f"数据库查询失败: {str(e)}",
                "route": AgentRole.END_NODE,
            }

    return database_query_node


def _extract_agent_response(response: Any) -> str:
    """从 ReAct agent 响应中提取文本内容"""
    if hasattr(response, "messages"):
        messages = list(response.messages)
        if messages:
            last = messages[-1]
            if hasattr(last, "content"):
                return last.content
            return str(last)
    if hasattr(response, "content"):
        return response.content
    return str(response)
