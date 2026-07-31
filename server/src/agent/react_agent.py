"""
ReAct Agent 实现

基于 llms 模块的 LLM 能力，封装为可嵌入工作流的 Agent 节点
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.logger import logger


@dataclass
class ReactAgentConfig:
    """ReAct Agent 配置"""

    name: str = "react_agent"
    system_prompt: str = "你是一个有用的 AI 助手。"
    llm_provider: str = "deepseek"
    llm_model: str | None = None
    tools: list[BaseTool] = field(default_factory=list)
    max_iterations: int = 5
    output_field: str = "agent_result"
    include_history_in_response: bool = False


class ToolCall(BaseModel):
    """工具调用记录"""

    tool_name: str
    tool_input: dict
    tool_output: Any | None = None
    error: str | None = None


class ReasoningStep(BaseModel):
    """推理步骤"""

    thought: str = Field(description="思考过程")
    action: str | None = Field(default=None, description="要调用的工具名称")
    action_input: dict | None = Field(default=None, description="工具输入参数")
    observation: str | None = Field(default=None, description="观察结果")


def create_react_agent_node(
    name: str,
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str = "你是一个有用的 AI 助手。",
    max_iterations: int = 5,
    output_field: str = "agent_result",
    include_history: bool = False,
) -> Callable[[dict], dict]:
    """
    创建 ReAct Agent 节点（可嵌入工作流）

    Agent 节点内部运行 ReAct 循环：
    Thought → Action → Observation → ...

    Args:
        name: 节点名称
        llm: 聊天模型实例
        tools: 工具列表
        system_prompt: 系统提示词
        max_iterations: 最大迭代次数
        output_field: 输出字段名
        include_history: 是否在输出中包含完整推理历史

    Returns:
        Callable[[dict], dict]: 工作流节点函数
    """

    def agent_node(state: dict) -> dict:
        """
        ReAct Agent 节点

        Args:
            state: 工作流状态，包含 messages 等

        Returns:
            dict: 更新后的状态
        """
        logger.info(f"[{name}] ReAct Agent 开始执行")

        messages = state.get("messages", [])
        if messages and isinstance(messages[0], dict):
            messages = [_dict_to_message(m) for m in messages]

        full_messages = [SystemMessage(content=system_prompt)] + (messages or [])
        llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

        iterations = 0
        tool_calls: list[ToolCall] = []
        final_response = ""

        while iterations < max_iterations:
            iterations += 1
            logger.info(f"[{name}] 迭代 {iterations}/{max_iterations}")

            try:
                response = llm_with_tools.invoke(full_messages)
            except Exception as e:
                logger.error(f"[{name}] LLM 调用失败: {e}")
                return _build_error_result(output_field, f"LLM 调用失败: {str(e)}", iterations)

            full_messages.append(response)
            tool_calls_in_response = response.tool_calls or []

            if not tool_calls_in_response:
                final_response = response.content or ""
                logger.info(f"[{name}] Agent 完成，响应: {final_response[:100]}...")
                break

            for tool_call in tool_calls_in_response:
                tool_result = _execute_tool_call(tools, tool_call)
                tool_calls.append(tool_result)
                _append_tool_messages(full_messages, tool_result)

        if not final_response and tool_calls:
            final_response = _generate_summary(llm, full_messages)

        result = {
            output_field: {
                "success": True,
                "response": final_response,
                "iterations": iterations,
                "tool_calls": [_tool_call_to_dict(tc) for tc in tool_calls],
            }
        }

        if include_history:
            result[output_field]["messages"] = [_message_to_dict(m) for m in full_messages]

        logger.info(f"[{name}] ReAct Agent 完成，共 {iterations} 次迭代")
        return result

    return agent_node


def _execute_tool_call(tools: list[BaseTool], tool_call: dict) -> ToolCall:
    """执行单个工具调用"""
    tool_name = tool_call.get("name", "")
    tool_args = tool_call.get("args", {})

    logger.info(f"调用工具: {tool_name}")

    tool = next((t for t in tools if t.name == tool_name), None)
    if not tool:
        return ToolCall(
            tool_name=tool_name,
            tool_input=tool_args,
            tool_output=f"错误：未找到工具 '{tool_name}'",
            error=f"Tool not found: {tool_name}",
        )

    try:
        tool_output = _invoke_tool(tool, tool_args)
        return ToolCall(
            tool_name=tool_name,
            tool_input=tool_args,
            tool_output=tool_output,
            error=None,
        )
    except Exception as e:
        logger.error(f"工具执行错误: {e}")
        return ToolCall(
            tool_name=tool_name,
            tool_input=tool_args,
            tool_output=f"工具执行错误: {str(e)}",
            error=str(e),
        )


def _invoke_tool(tool: BaseTool, tool_args: dict) -> Any:
    """调用工具（自动处理同步/异步）"""
    if asyncio.iscoroutinefunction(tool.invoke):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(tool.invoke(tool_args))
        else:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, tool.invoke(tool_args)).result()
    return tool.invoke(tool_args)


def _append_tool_messages(full_messages: list, tool_result: ToolCall) -> None:
    """添加工具调用结果到消息历史"""
    full_messages.append(
        AIMessage(
            content="",
            additional_kwargs={
                "tool_call": {
                    "name": tool_result.tool_name,
                    "args": tool_result.tool_input,
                }
            },
        )
    )
    full_messages.append(
        HumanMessage(content=f"[TOOL_OUTPUT]{tool_result.tool_output}[/TOOL_OUTPUT]")
    )


def _generate_summary(llm: BaseChatModel, full_messages: list) -> str:
    """生成总结响应"""
    summary_prompt = (
        "请根据上述工具调用结果，给出最终回答。"
        "如果用户问题已解决，直接给出答案。"
        "如果问题未解决，说明原因并建议下一步。"
    )
    full_messages.append(HumanMessage(content=summary_prompt))
    try:
        response = llm.invoke(full_messages)
        return response.content or ""
    except Exception as e:
        return f"生成总结时出错: {str(e)}"


def _build_error_result(output_field: str, error: str, iterations: int) -> dict:
    """构建错误结果"""
    return {
        output_field: {
            "success": False,
            "error": error,
            "iterations": iterations,
        }
    }


def _tool_call_to_dict(tc: ToolCall) -> dict:
    """工具调用记录转字典"""
    return {
        "tool": tc.tool_name,
        "input": tc.tool_input,
        "output": str(tc.tool_output) if tc.tool_output else None,
        "error": tc.error,
    }


def create_react_agent_config(
    name: str,
    tools: list[str],
    system_prompt: str = "你是一个有用的 AI 助手。",
    llm_provider: str = "deepseek",
    llm_model: str | None = None,
    max_iterations: int = 5,
    output_field: str = "agent_result",
) -> ReactAgentConfig:
    """
    创建 ReAct Agent 配置

    Args:
        name: Agent 名称
        tools: 工具名称列表
        system_prompt: 系统提示词
        llm_provider: LLM 提供者
        llm_model: LLM 模型
        max_iterations: 最大迭代次数
        output_field: 输出字段名

    Returns:
        ReactAgentConfig 配置对象
    """
    return ReactAgentConfig(
        name=name,
        system_prompt=system_prompt,
        llm_provider=llm_provider,
        llm_model=llm_model,
        tools=[],  # 工具稍后通过工具注册表填充
        max_iterations=max_iterations,
        output_field=output_field,
    )


# ============ 辅助函数 ============


def _dict_to_message(d: dict) -> AIMessage | HumanMessage | SystemMessage:
    """将字典转换为消息对象"""
    msg_type = d.get("type", "ai")
    content = d.get("content", "")

    if msg_type == "system":
        return SystemMessage(content=content)
    elif msg_type in ("human", "user"):
        return HumanMessage(content=content)
    return AIMessage(content=content)


def _message_to_dict(msg: Any) -> dict:
    """将消息对象转换为字典"""
    if isinstance(msg, SystemMessage):
        return {"type": "system", "content": msg.content}
    elif isinstance(msg, HumanMessage):
        return {"type": "human", "content": msg.content}
    elif isinstance(msg, AIMessage):
        return {"type": "ai", "content": msg.content}
    else:
        return {"type": "unknown", "content": str(msg)}
