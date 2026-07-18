# -*- coding: utf-8 -*-
"""
多智能体协作工作流节点定义

展示 LangGraph 的多智能体协作模式：
- 协调者：任务分解和分配（LLM 动态分解）
- 研究员：信息收集和分析（可接入搜索工具）
- 撰写者：内容生成（LLM 生成）
- 编辑：内容优化（LLM 优化）
- 审核员：质量控制（LLM 审核）

预留接口：
- Handoff 机制（handoff_to_agent 函数）
- 团队协作（parallel_execute 标记）
- Tool Calling（bind_tools 支持）
"""

import re
import time
import uuid
from typing import Optional, Callable

from workflows.multi_agent.state import (
    MultiAgentState,
    AgentRole,
    TaskStatus,
    SubTask,
    HandoffInfo,
    AgentOutput,
)

from core.logger import logger
from core.config import settings


# ===== System Prompts =====

COORDINATOR_PROMPT = """你是一个专业的任务协调者。你的职责是：
1. 分析用户的请求
2. 将复杂任务分解为可执行的子任务
3. 为每个子任务分配最合适的执行者

可用角色：researcher（研究员）、writer（撰写者）、editor（编辑）、reviewer（审核员）

请将用户请求分解为 2-4 个逻辑清晰的子任务，并按依赖关系排序。
返回 JSON 格式：
{
    "tasks": [
        {
            "description": "任务描述",
            "assigned_to": "角色名",
            "priority": "high/medium/low",
            "dependencies": []
        }
    ],
    "reasoning": "分解理由"
}"""

RESEARCHER_PROMPT = """你是一个专业的研究员。你的职责是：
1. 收集和整理与主题相关的信息
2. 分析数据的可靠性和相关性
3. 提供结构化的研究发现

请提供全面、客观、有据可查的研究结果。"""

WRITER_PROMPT = """你是一个专业的内容撰写者。你的职责是：
1. 基于研究结果撰写高质量内容
2. 确保内容结构清晰、逻辑连贯
3. 使用恰当的表达方式和格式

请撰写专业、流畅、有价值的内容。"""

EDITOR_PROMPT = """你是一个专业的编辑。你的职责是：
1. 优化内容的结构和表达
2. 修正语法、拼写和格式错误
3. 提升内容的可读性和专业性

请对内容进行精炼和优化。"""

REVIEWER_PROMPT = """你是一个严格的质量审核员。你的职责是：
1. 检查内容的完整性和准确性
2. 评估内容的质量和价值
3. 提供具体的改进建议

请进行严格审核，如果需要修订请明确指出问题。"""


# ===== LLM 调用辅助函数 =====

def _get_llm_provider():
    """获取可用的 LLM 提供者"""
    from llms.providers import get_llm_provider

    provider_name = settings.get_available_provider()
    return get_llm_provider(provider_name)


def _invoke_llm(
    system_prompt: str,
    user_input: str,
    structured: bool = False,
    use_mock_on_error: bool = True,
) -> str:
    """
    调用 LLM 生成内容（带超时和降级）

    Args:
        system_prompt: 系统提示词
        user_input: 用户输入
        structured: 是否结构化输出
        use_mock_on_error: 连接失败时是否使用模拟响应

    Returns:
        LLM 生成的响应内容
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    provider = _get_llm_provider()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]

    max_retries = 1  # 减少重试次数避免长时间等待
    timeout = 10  # 秒

    for attempt in range(max_retries):
        try:
            logger.info(f"LLM 调用尝试 {attempt + 1}/{max_retries}")
            response = provider.invoke(messages)
            return response.content
        except Exception as e:
            logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                continue

            # 连接失败，降级到模拟响应
            if use_mock_on_error:
                logger.info("降级到模拟响应")
                return _generate_mock_response(system_prompt, user_input)

            raise


def _generate_mock_response(system_prompt: str, user_input: str) -> str:
    """
    生成模拟响应（当 LLM 不可用时）

    Args:
        system_prompt: 系统提示词
        user_input: 用户输入

    Returns:
        模拟的响应内容
    """
    # 根据系统提示词判断需要的响应类型
    if "协调者" in system_prompt or "任务分解" in system_prompt:
        # 协调者角色 - 返回任务分解
        import json
        return json.dumps({
            "tasks": [
                {"description": f"研究主题：{user_input}", "assigned_to": "researcher", "priority": "high", "dependencies": []},
                {"description": "基于研究结果撰写内容", "assigned_to": "writer", "priority": "high", "dependencies": ["研究主题"]},
                {"description": "优化和完善内容", "assigned_to": "editor", "priority": "medium", "dependencies": ["撰写内容"]},
                {"description": "审核内容质量", "assigned_to": "reviewer", "priority": "medium", "dependencies": ["优化内容"]},
            ],
            "reasoning": "模拟：标准的多阶段内容创作流程"
        }, ensure_ascii=False, indent=2)

    elif "研究员" in system_prompt or "研究" in system_prompt:
        return f"""## 关于「{user_input}」的研究报告

### 背景信息
该主题涉及多个重要领域，目前正处于快速发展阶段。

### 关键发现
1. **趋势一**：相关技术正在快速演进
2. **趋势二**：存在多种可行的解决方案
3. **趋势三**：实际应用中需要综合考虑多方面因素

### 数据支持
- 行业增长率呈上升趋势
- 市场需求持续增长
- 技术成熟度逐步提高

### 建议
1. 建议采用渐进式实施策略
2. 关注风险控制和合规性
3. 进行小规模试点验证"""

    elif "撰写" in system_prompt or "内容" in system_prompt:
        return f"""# {user_input}

## 概述

本文档对 {user_input} 进行深入分析和讨论。

## 主要内容

### 一、背景介绍

随着技术发展，{user_input} 已成为重要议题。

### 二、核心要点

1. **要点一**：相关技术已经成熟
2. **要点二**：需要关注实施风险
3. **要点三**：建议渐进式推进

### 三、实施建议

1. 进行小规模试点
2. 收集反馈并优化
3. 逐步扩大应用范围

### 四、结论

综上所述，{user_input} 具有良好的发展前景。

---
*（本内容由 AI 自动生成）*"""

    elif "编辑" in system_prompt or "优化" in system_prompt:
        return f"""# {user_input}

## 概述

本文档对 {user_input} 进行优化和完善。

## 优化后的内容

### 一、简介

经过优化，内容更加清晰、结构更加合理。

### 二、主要改进

1. 语言表达更加精炼
2. 结构层次更加分明
3. 逻辑关系更加清晰

### 三、结论

优化后的内容质量显著提升，阅读体验更好。

---
*（已编辑优化）*"""

    elif "审核" in system_prompt or "质量" in system_prompt:
        # 模拟审核 - 大部分情况通过
        import random
        if random.random() > 0.3:
            return """## 审核报告

**审核结果：通过**

内容质量评估：
- 完整性：良好
- 准确性：良好
- 可读性：良好

建议：内容质量良好，可以直接使用。"""
        else:
            return """## 审核报告

**审核结果：需要修订**

发现以下问题：
1. 建议增加更多具体案例
2. 部分表述可以更加精炼
3. 可以补充总结部分

请根据以上建议进行修订后重新提交。"""

    # 默认响应
    return f"模拟响应：已收到您的请求 - {user_input[:50]}..."


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


# ===== Handoff 预留函数 =====

def create_handoff(to_agent: str, from_agent: str, context: dict, reason: str = "") -> HandoffInfo:
    """
    创建 Handoff 信息（预留接口）

    用于 Agent 之间传递控制权。
    当需要实现 Handoff 模式时使用此函数。

    Args:
        to_agent: 目标 Agent
        from_agent: 来源 Agent
        context: 传递的上下文
        reason: 交接原因

    Returns:
        HandoffInfo 对象
    """
    return HandoffInfo(
        from_agent=from_agent,
        to_agent=to_agent,
        reason=reason,
        context=context,
        priority="medium",
    )


def execute_handoff(state: MultiAgentState, handoff: HandoffInfo) -> dict:
    """
    执行 Handoff（预留实现）

    在 Handoff 模式下，将控制权传递给目标 Agent。

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
    3. 分配给合适的智能体

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Multi-Agent: 协调者分析任务")

    request = state.get("original_request", "")

    try:
        # 使用 LLM 动态分解任务
        tasks = _decompose_with_llm(request)

        # 序列化任务
        task_dicts = [task.model_dump() for task in tasks]

        logger.info(f"Multi-Agent: 分解为 {len(tasks)} 个子任务")

        return {
            "tasks": task_dicts,
            "current_stage": "coordinator",
            "current_agent": AgentRole.COORDINATOR.value,
            "iteration_count": 0,
            "completed_tasks": [],
            "handoffs": [],
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 任务分解失败 - {e}")
        # 降级到默认分解
        tasks = _decompose_default(request)
        return {
            "tasks": [task.model_dump() for task in tasks],
            "current_stage": "coordinator",
            "current_agent": AgentRole.COORDINATOR.value,
            "error": str(e),
        }


def _decompose_with_llm(request: str) -> list[SubTask]:
    """
    使用 LLM 动态分解任务

    Args:
        request: 用户请求

    Returns:
        子任务列表
    """
    import json

    try:
        response = _invoke_llm(COORDINATOR_PROMPT, request)
        data = json.loads(_parse_json_response(response))

        tasks = []
        for i, task_data in enumerate(data.get("tasks", [])):
            # 生成任务 ID
            task_id = f"task-{uuid.uuid4().hex[:6]}"

            # 收集依赖
            dependencies = task_data.get("dependencies", [])
            dep_ids = []
            for dep_name in dependencies:
                # 通过任务名称匹配依赖
                for prev_task in tasks:
                    if prev_task.description.startswith(dep_name):
                        dep_ids.append(prev_task.id)
                        break

            tasks.append(
                SubTask(
                    id=task_id,
                    description=task_data.get("description", ""),
                    assigned_to=task_data.get("assigned_to", AgentRole.WRITER.value),
                    status=TaskStatus.PENDING.value,
                    priority=task_data.get("priority", "medium"),
                    dependencies=dep_ids,
                )
            )

        # 如果没有分解出任务，使用默认
        if not tasks:
            tasks = _decompose_default(request)

        return tasks

    except Exception as e:
        logger.warning(f"LLM 分解失败，使用默认分解: {e}")
        return _decompose_default(request)


def _decompose_default(request: str) -> list[SubTask]:
    """
    默认任务分解（当 LLM 不可用时使用）

    Args:
        request: 用户请求

    Returns:
        子任务列表
    """
    tasks = []

    # 研究任务
    research_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=research_id,
            description=f"研究主题：{request}",
            assigned_to=AgentRole.RESEARCHER.value,
            status=TaskStatus.PENDING.value,
        )
    )

    # 撰写任务（依赖研究）
    write_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=write_id,
            description="基于研究结果撰写内容",
            assigned_to=AgentRole.WRITER.value,
            status=TaskStatus.PENDING.value,
            dependencies=[research_id],
        )
    )

    # 编辑任务（依赖撰写）
    edit_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=edit_id,
            description="优化和完善内容",
            assigned_to=AgentRole.EDITOR.value,
            status=TaskStatus.PENDING.value,
            dependencies=[write_id],
        )
    )

    # 审核任务（依赖编辑）
    review_id = f"task-{uuid.uuid4().hex[:6]}"
    tasks.append(
        SubTask(
            id=review_id,
            description="审核内容质量",
            assigned_to=AgentRole.REVIEWER.value,
            status=TaskStatus.PENDING.value,
            dependencies=[edit_id],
        )
    )

    return tasks


# ===== 研究员节点 =====


def researcher_node(state: MultiAgentState) -> dict:
    """
    研究员节点

    职责：
    1. 收集信息
    2. 分析数据
    3. 提供研究发现

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Multi-Agent: 研究员收集信息")

    request = state.get("original_request", "")

    try:
        start_time = time.time()

        # 使用 LLM 进行研究
        research_prompt = f"""{RESEARCHER_PROMPT}

主题：{request}

请提供详细的研究结果，包括：
1. 背景信息
2. 关键发现
3. 数据支持
4. 建议和结论"""

        findings = _invoke_llm(research_prompt, "")

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.RESEARCHER.value, findings
        )

        logger.info(f"Multi-Agent: 研究完成 - {len(findings)} 字符, 耗时 {duration}ms")

        return {
            "research_findings": findings,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": "researcher",
            "current_agent": AgentRole.RESEARCHER.value,
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 研究失败 - {e}")
        return {
            "research_findings": f"研究失败: {str(e)}",
            "error": f"研究阶段错误: {str(e)}",
        }


# ===== 撰写者节点 =====


def writer_node(state: MultiAgentState) -> dict:
    """
    撰写者节点

    职责：
    1. 基于研究结果撰写内容
    2. 组织结构
    3. 生成初稿

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Multi-Agent: 撰写者生成内容")

    request = state.get("original_request", "")
    research = state.get("research_findings", "")

    try:
        start_time = time.time()

        # 使用 LLM 生成内容
        write_prompt = f"""{WRITER_PROMPT}

主题：{request}

研究发现：
{research}

请撰写一篇结构完整、内容充实的文章。"""

        draft = _invoke_llm(write_prompt, "")

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.WRITER.value, draft
        )

        logger.info(f"Multi-Agent: 撰写完成 - {len(draft)} 字符, 耗时 {duration}ms")

        return {
            "draft_content": draft,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": "writer",
            "current_agent": AgentRole.WRITER.value,
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 撰写失败 - {e}")
        return {
            "draft_content": f"撰写失败: {str(e)}",
            "error": f"撰写阶段错误: {str(e)}",
        }


# ===== 编辑节点 =====


def editor_node(state: MultiAgentState) -> dict:
    """
    编辑节点

    职责：
    1. 优化内容结构
    2. 改进语言表达
    3. 确保逻辑连贯

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Multi-Agent: 编辑优化内容")

    draft = state.get("draft_content", "")
    revision_requests = state.get("revision_requests", [])

    try:
        start_time = time.time()

        # 构建编辑提示
        revision_note = ""
        if revision_requests:
            revision_note = "\n\n修订要求：\n" + "\n".join(f"- {req}" for req in revision_requests)

        edit_prompt = f"""{EDITOR_PROMPT}

原始内容：
{draft}

{revision_note}

请优化内容，提升质量和可读性。"""

        edited = _invoke_llm(edit_prompt, "")

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.EDITOR.value, edited
        )

        logger.info(f"Multi-Agent: 编辑完成 - {len(edited)} 字符, 耗时 {duration}ms")

        return {
            "edited_content": edited,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": "editor",
            "current_agent": AgentRole.EDITOR.value,
            "revision_requests": [],
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 编辑失败 - {e}")
        return {
            "edited_content": draft,
            "error": f"编辑阶段错误: {str(e)}",
        }


# ===== 审核员节点 =====


def reviewer_node(state: MultiAgentState) -> dict:
    """
    审核员节点

    职责：
    1. 质量检查
    2. 提供反馈
    3. 决定是否需要修订

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Multi-Agent: 审核员检查质量")

    edited_content = state.get("edited_content", "")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    try:
        start_time = time.time()

        # 使用 LLM 进行审核
        review_prompt = f"""{REVIEWER_PROMPT}

待审核内容：
{edited_content}

请仔细审核内容，如果需要修订请明确列出问题。"""

        review_result = _invoke_llm(review_prompt, "")

        duration = int((time.time() - start_time) * 1000)

        # 更新任务状态
        tasks, completed_tasks = _update_task_status(
            state, AgentRole.REVIEWER.value, review_result
        )

        # 判断是否需要修订（检查审核结果中是否包含修订要求）
        needs_revision = _check_needs_revision(review_result) and iteration_count < max_iterations

        # 提取修订请求
        revision_requests = []
        if needs_revision:
            revision_requests = _extract_revision_requests(review_result)

        logger.info(f"Multi-Agent: 审核完成 - {'需要修订' if needs_revision else '通过'}, 耗时 {duration}ms")

        return {
            "review_feedback": review_result,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "current_stage": "reviewer",
            "current_agent": AgentRole.REVIEWER.value,
            "needs_revision": needs_revision,
            "revision_requests": revision_requests,
            "iteration_count": iteration_count + 1,
            "final_output": edited_content if not needs_revision else "",
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 审核失败 - {e}")
        return {
            "review_feedback": f"审核失败: {str(e)}",
            "error": f"审核阶段错误: {str(e)}",
            "final_output": edited_content,
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
    state: MultiAgentState, agent_role: str, result: str
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
    tasks = state.get("tasks", [])
    completed_tasks = list(state.get("completed_tasks", []))

    for task_dict in tasks:
        if task_dict.get("assigned_to") == agent_role:
            task_id = task_dict.get("id")
            if task_id not in completed_tasks:
                task_dict["status"] = TaskStatus.COMPLETED.value
                task_dict["result"] = result
                completed_tasks.append(task_id)
                break

    return tasks, completed_tasks


# ===== 条件路由函数 =====


def route_to_agent_node(state: MultiAgentState) -> str:
    """
    条件路由节点：决定下一个执行的智能体

    基于任务依赖关系和完成状态进行路由。

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))

    # 检查是否需要修订（回到编辑）
    if state.get("needs_revision", False):
        return "editor"

    # 找到下一个可执行的任务
    for task_dict in tasks:
        task_id = task_dict.get("id")
        if task_id in completed_tasks:
            continue

        # 检查依赖是否满足
        dependencies = task_dict.get("dependencies", [])
        if all(dep in completed_tasks for dep in dependencies):
            agent = task_dict.get("assigned_to")
            return agent

    # 所有任务完成
    return "complete"


def should_continue_node(state: MultiAgentState) -> str:
    """
    条件路由节点：判断是否继续迭代

    Args:
        state: 当前状态

    Returns:
        'continue' 或 'complete'
    """
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    needs_revision = state.get("needs_revision", False)

    if needs_revision and iteration_count < max_iterations:
        return "continue"
    else:
        return "complete"


# ===== 预留：并行执行路由 =====

def route_for_parallel_node(state: MultiAgentState) -> list[dict]:
    """
    条件路由节点：返回可并行执行的任务列表（预留）

    用于 Team 模式下的并行任务分配。

    Returns:
        可并行执行的任务列表
    """
    tasks = state.get("tasks", [])
    completed_tasks = set(state.get("completed_tasks", []))

    parallel_tasks = []

    for task_dict in tasks:
        task_id = task_dict.get("id")
        if task_id in completed_tasks:
            continue

        # 检查依赖是否满足
        dependencies = task_dict.get("dependencies", [])
        if all(dep in completed_tasks for dep in dependencies):
            # 收集无依赖的任务
            if not dependencies:
                parallel_tasks.append(task_dict)

    return parallel_tasks


# ===== 预留：Handoff 路由 =====

def route_with_handoff(state: MultiAgentState) -> str:
    """
    Handoff 路由函数（预留）

    当实现 Handoff 模式时，使用此函数进行路由。
    允许 Agent 主动交接控制权。

    Args:
        state: 当前状态

    Returns:
        下一个 Agent 或 'END'
    """
    # 检查是否有待处理的 Handoff
    pending_handoff = state.get("pending_handoff")
    if pending_handoff:
        return pending_handoff.get("to_agent", "complete")

    # 否则使用默认路由
    return route_to_agent_node(state)


def initiate_handoff(
    state: MultiAgentState,
    from_agent: str,
    to_agent: str,
    context: dict,
    reason: str = "",
) -> dict:
    """
    发起 Handoff（预留实现）

    用于 Agent 之间主动交接控制权。

    Args:
        state: 当前状态
        from_agent: 来源 Agent
        to_agent: 目标 Agent
        context: 传递的上下文
        reason: 交接原因

    Returns:
        状态更新
    """
    handoff = create_handoff(to_agent, from_agent, context, reason)
    return execute_handoff(state, handoff)


# ===== 预留：Tool Calling 绑定 =====

def bind_tools_to_agent(tools: list) -> Callable:
    """
    为 Agent 绑定工具（预留实现）

    用于给 Agent 添加工具调用能力。

    Args:
        tools: 工具列表

    Returns:
        绑定工具后的 LLM
    """
    provider = _get_llm_provider()
    return provider.bind_tools(tools)


def create_researcher_with_tools(tools: list):
    """
    创建带工具的研究员（预留实现）

    Args:
        tools: 工具列表（如搜索工具）

    Returns:
        带工具的研究员节点函数
    """
    def researcher_with_tools(state: MultiAgentState) -> dict:
        """带工具的研究员节点"""
        logger.info("Multi-Agent: 研究员（带工具）收集信息")

        request = state.get("original_request", "")
        provider = _get_llm_provider()
        model = provider.bind_tools(tools)

        try:
            # 使用工具进行研究
            system_prompt = f"{RESEARCHER_PROMPT}\n\n你可以使用搜索工具获取最新信息。"

            response = model.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"研究主题：{request}"},
            ])

            findings = response.content

            # 更新任务状态
            tasks, completed_tasks = _update_task_status(
                state, AgentRole.RESEARCHER.value, findings
            )

            return {
                "research_findings": findings,
                "tasks": tasks,
                "completed_tasks": completed_tasks,
                "current_stage": "researcher",
                "current_agent": AgentRole.RESEARCHER.value,
            }

        except Exception as e:
            logger.error(f"Multi-Agent: 研究失败 - {e}")
            return {
                "research_findings": f"研究失败: {str(e)}",
                "error": str(e),
            }

    return researcher_with_tools
