# -*- coding: utf-8 -*-
"""
多智能体协作工作流状态定义

展示 LangGraph 的多智能体状态管理：
- 复杂状态结构
- Agent 间通信
- 任务队列
"""

from enum import Enum
from typing import TypedDict, Optional, Annotated, Any
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """智能体角色"""

    COORDINATOR = "coordinator"  # 协调者
    RESEARCHER = "researcher"  # 研究员
    WRITER = "writer"  # 撰写者
    EDITOR = "editor"  # 编辑
    REVIEWER = "reviewer"  # 审核员


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(BaseModel):
    """子任务"""

    id: str = Field(..., description="任务 ID")
    description: str = Field(..., description="任务描述")
    assigned_to: str = Field(..., description="分配给的智能体角色")
    status: str = Field(default=TaskStatus.PENDING.value, description="任务状态")
    result: Optional[str] = Field(default=None, description="任务结果")
    dependencies: list[str] = Field(default_factory=list, description="依赖的任务 ID")


class MultiAgentState(TypedDict):
    """
    多智能体协作工作流状态

    展示 LangGraph 的复杂状态管理：
    - 消息历史
    - 任务队列
    - 中间结果
    - 并行执行状态
    """

    # 原始请求
    original_request: str

    # 消息历史
    messages: Annotated[list, add_messages]

    # 任务管理
    subtasks: list[dict]  # 子任务列表
    completed_tasks: list[str]  # 已完成的任务 ID

    # 各 Agent 的输出
    research_findings: str
    draft_content: str
    edited_content: str
    review_feedback: str

    # 最终结果
    final_output: str
    iteration_count: int
    max_iterations: int

    # 流程控制
    current_stage: str
    needs_revision: bool
    revision_requests: list[str]

    # 错误处理
    error: Optional[str]
    failed_agents: list[str]


class MultiAgentResult(BaseModel):
    """多智能体协作结果"""

    original_request: str = Field(..., description="原始请求")
    final_output: str = Field(default="", description="最终输出")
    subtasks_completed: int = Field(default=0, description="完成的子任务数")
    iteration_count: int = Field(default=0, description="迭代次数")
    agent_outputs: dict[str, str] = Field(default_factory=dict, description="各智能体的输出")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
