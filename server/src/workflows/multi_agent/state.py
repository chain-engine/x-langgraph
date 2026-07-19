# -*- coding: utf-8 -*-
"""
多智能体协作工作流状态定义

展示 LangGraph 的多智能体协作能力：
- 复杂状态结构
- Agent 间通信协议
- 任务队列管理
- Handoff 预留接口
- 团队协作预留接口
"""

from enum import Enum
from typing import TypedDict, Optional, Annotated, Any
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class DescribedEnum(Enum):
    """
    可描述的枚举类基建
    mark: int        唯一标识
    desc: str        描述信息
    """

    def __init__(self, mark: int | str, desc: str) -> None:
        self._mark = mark
        self._desc = desc

    @property
    def mark(self) -> int | str:
        return self._mark

    @property
    def value(self) -> str:
        """重写 value，使枚举可直接赋值给 str 类型字段（如 Pydantic BaseModel）"""
        return str(self._mark)

    @property
    def desc(self) -> str:
        return self._desc

    def __str__(self) -> str:
        return str(self._mark)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Enum):
            return super().__eq__(other)
        if isinstance(other, str):
            return self._mark == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._mark)

    @classmethod
    def get_all_marks(cls) -> list[int]:
        return [described_enum.mark for described_enum in cls]

    @classmethod
    def get_all_descs(cls) -> list[str]:
        return [described_enum.desc for described_enum in cls]

    @classmethod
    def get_choices(cls) -> tuple[tuple[int, str], ...]:
        return tuple((described_enum.mark, described_enum.desc) for described_enum in cls)



class AgentRole(DescribedEnum):
    """智能体角色枚举"""

    # 核心角色
    COORDINATOR = "coordinator", "协调者"
    RESEARCHER = "researcher", "研究员"
    WRITER = "writer", "撰写者"
    EDITOR = "editor", "编辑"
    REVIEWER = "reviewer", "审核员"
    END_NODE = "__end__", "工作流结束"


class TaskStatus(DescribedEnum):
    """任务状态枚举"""

    PENDING = "pending", "待处理"
    IN_PROGRESS = "in_progress", "进行中"
    COMPLETED = "completed", "已完成"
    FAILED = "failed", "失败"
    CANCELLED = "cancelled", "已取消"


class TaskPriority(DescribedEnum):
    """任务优先级"""

    LOW = "low", "低"
    MEDIUM = "medium", "中"
    HIGH = "high", "高"
    URGENT = "urgent", "紧急"


class AgentHandoff(BaseModel):
    """
    Agent Handoff 协议结构

    当一个 Agent 完成工作后，主动决定将控制权传递给下一个 Agent。
    """

    to_agent: str = Field(..., description="目标 Agent 名称")
    reason: str = Field(default="", description="交接原因")
    context: dict = Field(default_factory=dict, description="传递给下一个 Agent 的上下文")
    from_agent: str = Field(default="", description="来源 Agent")


class AgentConfig(BaseModel):
    """Agent 配置"""

    name: str = Field(..., description="Agent 名称")
    role: str = Field(..., description="Agent 角色")
    llm_provider: str = Field(default="auto", description="LLM 提供者")
    llm_model: str = Field(default="", description="LLM 模型")
    system_prompt: str = Field(default="", description="系统提示词")
    temperature: float = Field(default=0.7, description="温度参数")


class HandoffInfo(BaseModel):
    """
    Handoff 信息（预留）

    用于 Agent 之间传递控制权的协议结构。
    当需要实现 Handoff 模式时启用。
    """

    from_agent: str = Field(..., description="来源 Agent")
    to_agent: str = Field(..., description="目标 Agent")
    reason: str = Field(default="", description="交接原因")
    context: dict = Field(default_factory=dict, description="传递的上下文")
    priority: str = Field(default="medium", description="优先级")


class SubTask(BaseModel):
    """子任务定义"""

    id: str = Field(..., description="任务 ID")
    description: str = Field(..., description="任务描述")
    assigned_to: str = Field(..., description="分配给的智能体角色")
    status: str = Field(default=TaskStatus.PENDING.value, description="任务状态")
    result: Optional[str] = Field(default=None, description="任务结果")
    dependencies: list[str] = Field(default_factory=list, description="依赖的任务 ID")
    priority: str = Field(default=TaskPriority.MEDIUM.value, description="优先级")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    error: Optional[str] = Field(default=None, description="错误信息")


class AgentOutput(BaseModel):
    """Agent 输出记录"""

    agent_role: str = Field(..., description="Agent 角色")
    input_summary: str = Field(..., description="输入摘要")
    output: str = Field(default="", description="输出内容")
    tokens_used: int = Field(default=0, description="使用的 Token 数")
    duration_ms: int = Field(default=0, description="执行耗时（毫秒）")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")


class MultiAgentState(TypedDict):
    """
    多智能体协作工作流状态

    展示 LangGraph 的复杂状态管理能力：
    - messages: 消息历史（使用 add_messages reducer 自动合并）
    - tasks: 任务队列管理
    - agent_outputs: 各 Agent 的输出记录
    - handoff: Handoff 协议（预留）
    - team: 团队协作信息（预留）
    """

    # ===== 消息历史 =====
    messages: Annotated[list, add_messages]

    # ===== 原始请求 =====
    original_request: str
    thread_id: str  # 会话 ID

    # ===== 任务管理 =====
    tasks: list[dict]  # 任务列表（SubTask 模型序列化）
    completed_tasks: list[str]  # 已完成任务 ID 列表
    current_task_id: Optional[str]  # 当前执行的任务 ID

    # ===== Agent 输出 =====
    research_findings: str
    draft_content: str
    edited_content: str
    review_feedback: str
    output: str

    # ===== 执行控制 =====
    current_stage: str  # 当前阶段
    current_agent: Optional[str]  # 当前执行的 Agent
    iteration_count: int  # 迭代次数
    max_iterations: int  # 最大迭代次数
    needs_revision: bool  # 是否需要修订
    revision_requests: list[str]  # 修订请求列表

    # ===== Handoff 支持 =====
    handoffs: list[dict]  # Handoff 历史记录
    pending_handoff: Optional[dict]  # 待处理的 Handoff

    # Agent Handoff 协议
    active_handoff: Optional[dict]  # 当前活跃的 Handoff
    handoff_history: list[dict]  # Handoff 历史
    agent_configs: dict[str, dict]  # Agent 配置映射

    # ===== 团队协作预留 =====
    parallel_tasks: list[dict]  # 可并行执行的任务列表
    parallel_execution: bool  # 是否启用并行执行模式
    parallel_results: dict[str, str]  # 并行执行结果

    # ===== 错误处理 =====
    error: Optional[str]
    failed_agents: list[str]


class MultiAgentResult(BaseModel):
    """多智能体协作结果"""

    original_request: str = Field(..., description="原始请求")
    output: str = Field(default="", description="最终输出")
    tasks_completed: int = Field(default=0, description="完成的任务数")
    tasks_total: int = Field(default=0, description="总任务数")
    iteration_count: int = Field(default=0, description="迭代次数")
    agent_outputs: dict[str, str] = Field(default_factory=dict, description="各智能体的输出")
    handoffs: list[dict] = Field(default_factory=list, description="Handoff 记录")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    duration_ms: int = Field(default=0, description="总耗时（毫秒）")


# ===== 预留：Handoff 状态类型（未来扩展）====

# class HandoffState(TypedDict):
#     """Handoff 模式状态（预留）"""
#
#     messages: Annotated[list, add_messages]
#     current_agent: Optional[str]
#     handoff_queue: list[HandoffInfo]
#     agent_contexts: dict[str, dict]  # 各 Agent 的上下文
#
#
# class TeamState(TypedDict):
#     """团队协作状态（预留）"""
#
#     messages: Annotated[list, add_messages]
#     team_leader: str
#     team_members: list[str]
#     active_tasks: dict[str, dict]  # 活跃任务
#     completed_tasks: list[str]
#     pending_results: dict[str, Any]  # 等待合并的结果
