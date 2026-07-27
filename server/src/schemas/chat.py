# -*- coding: utf-8 -*-
"""
聊天接口数据模型
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReasoningMode(str, Enum):
    """推理模式枚举"""

    REACT = "react"
    PLAN_EXECUTE = "plan_execute"
    TOT = "tot"


class ReasoningConfigRequest(BaseModel):
    """推理配置请求（可选）"""

    mode: ReasoningMode = Field(default=ReasoningMode.REACT, description="推理模式")
    max_iterations: int = Field(default=10, ge=1, le=100, description="最大迭代次数")
    timeout_seconds: int = Field(default=300, ge=10, le=3600, description="LLM 调用超时（秒）")
    enable_reflection: bool = Field(default=True, description="是否启用反思")
    llm_provider: str = Field(default="deepseek", description="LLM 提供者")
    system_prompt: Optional[str] = Field(default=None, description="自定义系统提示词")
    max_branches: int = Field(default=3, ge=1, le=10, description="ToT 最大分支数")
    max_depth: int = Field(default=5, ge=1, le=20, description="ToT 最大深度")


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(..., description="用户消息", min_length=1)
    session_id: str = Field(default="default", description="会话 ID")
    workflow: str = Field(default="intent_classifier", description="工作流类型")
    reasoning: Optional[ReasoningConfigRequest] = Field(
        default=None,
        description="推理配置（当 workflow 为 reasoning 类工作流时生效）",
    )


class ChatResponse(BaseModel):
    """聊天响应"""

    response: str = Field(..., description="AI 响应内容")
    session_id: str = Field(..., description="会话 ID")
    node: Optional[str] = Field(default=None, description="执行的节点")
    intermediate_steps: Optional[list[dict]] = Field(
        default=None, description="推理中间步骤（仅 reasoning 模式）"
    )


class StreamEvent(BaseModel):
    """流式事件"""

    event: str = Field(..., description="事件类型: node_update | reasoning_step | done | error")
    node: Optional[str] = Field(default=None, description="节点名称")
    step_type: Optional[str] = Field(
        default=None,
        description="推理步骤类型: reasoning | action | observation | reflection | plan | execute | generate | evaluate | select（仅 reasoning_step 事件）",
    )
    content: Optional[str] = Field(default=None, description="步骤内容（仅 reasoning_step 事件）")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="步骤元数据")
    data: Optional[Any] = Field(default=None, description="原始事件数据")
