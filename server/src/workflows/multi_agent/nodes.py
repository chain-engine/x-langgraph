# -*- coding: utf-8 -*-
"""
多智能体协作工作流节点定义

展示 LangGraph 的多智能体协作模式：
- 协调者：任务分解和分配
- 研究员：信息收集和分析
- 撰写者：内容生成
- 编辑：内容优化
- 审核员：质量控制
"""

import uuid
import random

from workflows.multi_agent.state import (
    MultiAgentState,
    AgentRole,
    TaskStatus,
    SubTask,
)
from core.logger import logger


# ===== 协调者节点 =====


def coordinator_node(state: MultiAgentState) -> dict:
    """
    协调者节点

    职责：
    1. 分析用户请求
    2. 分解为子任务
    3. 分配给合适的智能体

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    logger.info("Multi-Agent: 协调者分析任务")

    request = state.get("original_request", "")

    # 生成子任务
    subtasks = _decompose_request(request)

    logger.info(f"Multi-Agent: 分解为 {len(subtasks)} 个子任务")

    return {
        "subtasks": [task.model_dump() for task in subtasks],
        "current_stage": "coordinator",
        "iteration_count": 0,
        "completed_tasks": [],
    }


def _decompose_request(request: str) -> list[SubTask]:
    """分解用户请求为子任务"""
    subtasks = []

    # 研究任务
    subtasks.append(
        SubTask(
            id=f"research-{uuid.uuid4().hex[:6]}",
            description=f"研究主题：{request}",
            assigned_to=AgentRole.RESEARCHER.value,
            status=TaskStatus.PENDING.value,
        )
    )

    # 撰写任务（依赖研究任务）
    research_task_id = subtasks[0].id
    subtasks.append(
        SubTask(
            id=f"write-{uuid.uuid4().hex[:6]}",
            description="基于研究结果撰写内容",
            assigned_to=AgentRole.WRITER.value,
            status=TaskStatus.PENDING.value,
            dependencies=[research_task_id],
        )
    )

    # 编辑任务（依赖撰写任务）
    write_task_id = subtasks[1].id
    subtasks.append(
        SubTask(
            id=f"edit-{uuid.uuid4().hex[:6]}",
            description="优化和完善内容",
            assigned_to=AgentRole.EDITOR.value,
            status=TaskStatus.PENDING.value,
            dependencies=[write_task_id],
        )
    )

    # 审核任务（依赖编辑任务）
    edit_task_id = subtasks[2].id
    subtasks.append(
        SubTask(
            id=f"review-{uuid.uuid4().hex[:6]}",
            description="审核内容质量",
            assigned_to=AgentRole.REVIEWER.value,
            status=TaskStatus.PENDING.value,
            dependencies=[edit_task_id],
        )
    )

    return subtasks


# ===== 研究员节点 =====


def researcher_node(state: MultiAgentState) -> dict:
    """
    研究员节点

    职责：
    1. 收集信息
    2. 分析数据
    3. 提供研究发现
    """
    logger.info("Multi-Agent: 研究员收集信息")

    request = state.get("original_request", "")

    try:
        # 模拟研究过程
        findings = _conduct_research(request)

        # 更新任务状态
        subtasks, completed_tasks = _update_task_status(
            state, AgentRole.RESEARCHER.value, findings
        )

        logger.info(f"Multi-Agent: 研究完成 - {len(findings)} 字符")

        return {
            "research_findings": findings,
            "subtasks": subtasks,
            "completed_tasks": completed_tasks,
            "current_stage": "researcher",
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 研究失败 - {e}")
        return {
            "research_findings": f"研究失败: {str(e)}",
            "error": f"研究阶段错误: {str(e)}",
        }


def _conduct_research(topic: str) -> str:
    """执行研究（模拟）"""
    return f"""关于 "{topic}" 的研究发现：

1. **背景信息**
   - 该主题涉及多个重要领域
   - 当前有许多相关研究和实践案例

2. **关键发现**
   - 发现 A: 相关技术正在快速发展
   - 发现 B: 存在多种可行的解决方案
   - 发现 C: 实际应用中需要考虑多方面因素

3. **数据支持**
   - 相关数据表明趋势良好
   - 市场反馈积极
   - 技术成熟度较高

4. **建议**
   - 可以采用渐进式实施策略
   - 需要关注风险控制
   - 建议进行小规模试点

（注：这是模拟的研究结果，实际项目中应接入真实的知识库或搜索服务）"""


# ===== 撰写者节点 =====


def writer_node(state: MultiAgentState) -> dict:
    """
    撰写者节点

    职责：
    1. 基于研究结果撰写内容
    2. 组织结构
    3. 生成初稿
    """
    logger.info("Multi-Agent: 撰写者生成内容")

    request = state.get("original_request", "")
    research = state.get("research_findings", "")

    try:
        # 生成初稿
        draft = _write_draft(request, research)

        # 更新任务状态
        subtasks, completed_tasks = _update_task_status(
            state, AgentRole.WRITER.value, draft
        )

        logger.info(f"Multi-Agent: 撰写完成 - {len(draft)} 字符")

        return {
            "draft_content": draft,
            "subtasks": subtasks,
            "completed_tasks": completed_tasks,
            "current_stage": "writer",
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 撰写失败 - {e}")
        return {
            "draft_content": f"撰写失败: {str(e)}",
            "error": f"撰写阶段错误: {str(e)}",
        }


def _write_draft(topic: str, research: str) -> str:
    """生成初稿"""
    return f"""# {topic}

## 概述

{research[:200]}...

## 详细内容

### 1. 简介

本文将详细讨论 {topic} 的各个方面，包括背景、现状和未来发展趋势。

### 2. 主要发现

基于研究分析，我们发现：

- **要点一**: 相关技术已经成熟，可以投入实际应用
- **要点二**: 需要注意实施过程中的风险控制
- **要点三**: 建议采用渐进式部署策略

### 3. 实施建议

1. 首先，进行小规模试点测试
2. 其次，收集反馈并优化方案
3. 最后，逐步扩大应用范围

### 4. 结论

综上所述，{topic} 具有良好的应用前景，但需要在实施过程中保持谨慎。

---
*（初稿，待编辑优化）*"""


# ===== 编辑节点 =====


def editor_node(state: MultiAgentState) -> dict:
    """
    编辑节点

    职责：
    1. 优化内容结构
    2. 改进语言表达
    3. 确保逻辑连贯
    """
    logger.info("Multi-Agent: 编辑优化内容")

    draft = state.get("draft_content", "")
    revision_requests = state.get("revision_requests", [])

    try:
        # 编辑内容
        edited = _edit_content(draft, revision_requests)

        # 更新任务状态
        subtasks, completed_tasks = _update_task_status(
            state, AgentRole.EDITOR.value, edited
        )

        logger.info(f"Multi-Agent: 编辑完成 - {len(edited)} 字符")

        return {
            "edited_content": edited,
            "subtasks": subtasks,
            "completed_tasks": completed_tasks,
            "current_stage": "editor",
            "revision_requests": [],
        }

    except Exception as e:
        logger.error(f"Multi-Agent: 编辑失败 - {e}")
        return {
            "edited_content": draft,
            "error": f"编辑阶段错误: {str(e)}",
        }


def _edit_content(draft: str, revision_requests: list[str]) -> str:
    """编辑内容"""
    # 简单的编辑优化
    edited = draft.replace("*（初稿，待编辑优化）*", "")

    # 添加修订说明
    if revision_requests:
        revision_note = "\n\n---\n**修订说明:**\n"
        for req in revision_requests:
            revision_note += f"- {req}\n"
        edited += revision_note

    edited += "\n\n*（已编辑优化）*"
    return edited


# ===== 审核员节点 =====


def reviewer_node(state: MultiAgentState) -> dict:
    """
    审核员节点

    职责：
    1. 质量检查
    2. 提供反馈
    3. 决定是否需要修订
    """
    logger.info("Multi-Agent: 审核员检查质量")

    edited_content = state.get("edited_content", "")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    try:
        # 审核内容
        review_result = _review_content(edited_content)

        # 更新任务状态
        subtasks, completed_tasks = _update_task_status(
            state, AgentRole.REVIEWER.value, review_result
        )

        # 判断是否需要修订
        needs_revision = "需要修订" in review_result and iteration_count < max_iterations

        # 提取修订请求
        revision_requests = []
        if needs_revision:
            revision_requests = _extract_revision_requests(review_result)

        logger.info(f"Multi-Agent: 审核完成 - {'需要修订' if needs_revision else '通过'}")

        return {
            "review_feedback": review_result,
            "subtasks": subtasks,
            "completed_tasks": completed_tasks,
            "current_stage": "reviewer",
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


def _review_content(content: str) -> str:
    """审核内容"""
    issues = []

    if len(content) < 100:
        issues.append("内容太短，需要补充更多细节")

    if "待编辑" in content:
        issues.append("发现未处理的标记")

    # 模拟随机审核结果
    if random.random() < 0.3 and not issues:
        issues.append("可以增加更多案例说明")
        issues.append("建议添加总结部分")

    if issues:
        return f"""审核反馈：

**需要修订**

发现以下问题：
{chr(10).join(f'- {issue}' for issue in issues)}

请编辑进行修改后重新提交审核。"""
    else:
        return """审核反馈：

**通过**

内容质量良好，结构清晰，逻辑连贯。

建议：可以考虑添加更多实际案例来增强说服力。"""


def _extract_revision_requests(review: str) -> list[str]:
    """从审核反馈中提取修订请求"""
    requests = []
    lines = review.split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("- ") and "发现" not in line:
            requests.append(line[2:])

    return requests


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
        (更新后的 subtasks, 更新后的 completed_tasks)
    """
    subtasks = state.get("subtasks", [])
    completed_tasks = state.get("completed_tasks", [])

    for task_dict in subtasks:
        if task_dict.get("assigned_to") == agent_role:
            task_id = task_dict.get("id")
            if task_id not in completed_tasks:
                task_dict["status"] = TaskStatus.COMPLETED.value
                task_dict["result"] = result
                completed_tasks.append(task_id)
                break

    return subtasks, completed_tasks


# ===== 条件路由函数 =====


def route_to_agent(state: MultiAgentState) -> str:
    """条件路由：决定下一个执行的智能体"""
    subtasks = state.get("subtasks", [])
    completed_tasks = state.get("completed_tasks", [])

    # 检查是否需要修订
    if state.get("needs_revision", False):
        return "editor"

    # 找到下一个可执行的任务
    for task_dict in subtasks:
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


def should_continue(state: MultiAgentState) -> str:
    """条件路由：判断是否继续迭代"""
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    needs_revision = state.get("needs_revision", False)

    if needs_revision and iteration_count < max_iterations:
        return "continue"
    else:
        return "complete"
