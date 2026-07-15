# -*- coding: utf-8 -*-
"""
提示模板管理模块

提供统一的提示模板管理，支持：
- 预定义模板
- 动态模板渲染
- 模板分类管理
"""

from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel

from core.logger import logger


class PromptTemplateConfig(BaseModel):
    """提示模板配置"""

    name: str
    description: str
    template: str
    input_variables: list[str] = []


class PromptTemplateManager:
    """
    提示模板管理器

    管理所有的提示模板，支持：
    - 注册新模板
    - 获取模板
    - 渲染模板
    """

    def __init__(self):
        """初始化模板管理器"""
        self._templates: dict[str, PromptTemplateConfig] = {}
        self._register_default_templates()

    def _register_default_templates(self):
        """注册默认模板"""
        # ===== 通用模板 =====
        self.register(
            "system_default",
            "默认系统提示",
            "你是一个有帮助的 AI 助手。",
        )

        self.register(
            "user_input",
            "用户输入模板",
            "{input}",
            ["input"],
        )

        # ===== 路由分类模板 =====
        self.register(
            "router_system",
            "路由系统提示",
            """你是一个智能路由器，负责分析用户输入并决定使用哪个工具处理。

可用工具：
{tools_description}

请根据用户输入，选择最合适的工具。只需要返回工具名称，不要解释。""",
            ["tools_description"],
        )

        self.register(
            "router_user",
            "路由用户提示",
            """用户输入: {input}

请选择处理该请求的工具：{tool_names}""",
            ["input", "tool_names"],
        )

        # ===== 客服系统模板 =====
        self.register(
            "customer_service_system",
            "客服系统提示",
            """你是一个专业的智能客服系统。你的职责是：
1. 友好地接待客户
2. 准确理解客户问题
3. 提供准确、有帮助的解答
4. 在无法解决时引导客户使用正确的渠道

请用专业、友好的语气回复客户。""",
        )

        self.register(
            "ticket_classifier",
            "工单分类提示",
            """请根据以下客户消息，判断工单类型和优先级。

客户消息:
{message}

请返回 JSON 格式：
{{
    "ticket_type": "inquiry|complaint|technical|billing",
    "priority": "low|medium|high|urgent",
    "reason": "分类原因"
}}""",
            ["message"],
        )

        # ===== RAG 模板 =====
        self.register(
            "rag_system",
            "RAG 系统提示",
            """你是一个专业的问答助手。请根据以下上下文回答用户问题。

规则：
1. 只使用上下文中的信息回答
2. 如果上下文中没有相关信息，请说明无法回答
3. 回答要准确、简洁

上下文：
{context}""",
            ["context"],
        )

        self.register(
            "rag_user",
            "RAG 用户提示",
            "问题：{question}",
            ["question"],
        )

        # ===== Text2SQL 模板 =====
        self.register(
            "text2sql_system",
            "Text2SQL 系统提示",
            """你是一个 SQL 专家，负责将自然语言转换为 SQL 查询。

数据库 Schema：
{schema}

规则：
1. 只生成 SELECT 查询，不要生成 INSERT/UPDATE/DELETE
2. 使用标准 SQL 语法
3. 确保查询安全，避免 SQL 注入
4. 如果无法生成，返回 "ERROR: 原因"

示例：
用户: 查询所有用户
SQL: SELECT * FROM users LIMIT 100;""",
            ["schema"],
        )

        self.register(
            "text2sql_user",
            "Text2SQL 用户提示",
            "请将以下自然语言转换为 SQL：{query}",
            ["query"],
        )

        # ===== 代码生成模板 =====
        self.register(
            "code_generator_system",
            "代码生成系统提示",
            """你是一个专业的程序员，擅长生成高质量代码。

语言：{language}
风格指南：
- 使用清晰的变量名
- 添加必要的注释
- 遵循语言的最佳实践
- 处理边界情况

请生成满足要求的代码。""",
            ["language"],
        )

        self.register(
            "code_generator_user",
            "代码生成用户提示",
            """需求：{requirement}

约束条件：{constraints}""",
            ["requirement", "constraints"],
        )

        # ===== 摘要生成模板 =====
        self.register(
            "summarize_system",
            "摘要生成系统提示",
            "你是一个文本摘要专家。请将输入文本压缩为简洁的摘要，保留关键信息。",
        )

        self.register(
            "summarize_user",
            "摘要生成用户提示",
            """请为以下文本生成摘要（不超过 {max_length} 字）：

{text}""",
            ["text", "max_length"],
        )

        # ===== 翻译模板 =====
        self.register(
            "translate_system",
            "翻译系统提示",
            """你是一个专业的翻译官。请将用户输入从 {source_language} 翻译为 {target_language}。

要求：
- 保持原文的语气和风格
- 使用地道的表达方式
- 专业术语保持准确""",
            ["source_language", "target_language"],
        )

        self.register(
            "translate_user",
            "翻译用户提示",
            "{text}",
            ["text"],
        )

        # ===== 情感分析模板 =====
        self.register(
            "sentiment_system",
            "情感分析系统提示",
            """你是一个情感分析专家。请分析用户输入的情感倾向。

返回 JSON 格式：
{
    "sentiment": "positive|negative|neutral",
    "confidence": 0.0-1.0,
    "explanation": "判断原因"
}""",
        )

        self.register(
            "sentiment_user",
            "情感分析用户提示",
            "{text}",
            ["text"],
        )

        # ===== Agent 模板 =====
        self.register(
            "agent_system",
            "Agent 系统提示",
            """你是一个智能代理，具有以下能力：
{capabilities}

请根据用户需求，制定执行计划并执行。

可用工具：
{tools}

执行规则：
1. 仔细分析任务需求
2. 选择合适的工具
3. 逐步执行并观察结果
4. 必要时调整计划""",
            ["capabilities", "tools"],
        )

        logger.info(f"已注册 {len(self._templates)} 个默认提示模板")

    def register(
        self,
        name: str,
        description: str,
        template: str,
        input_variables: Optional[list[str]] = None,
    ) -> None:
        """
        注册新模板

        Args:
            name: 模板名称
            description: 模板描述
            template: 模板内容
            input_variables: 输入变量列表
        """
        self._templates[name] = PromptTemplateConfig(
            name=name,
            description=description,
            template=template,
            input_variables=input_variables or [],
        )
        logger.debug(f"注册提示模板: {name}")

    def get(self, name: str) -> PromptTemplateConfig:
        """
        获取模板配置

        Args:
            name: 模板名称

        Returns:
            PromptTemplateConfig

        Raises:
            KeyError: 模板不存在
        """
        if name not in self._templates:
            available = ", ".join(self._templates.keys())
            raise KeyError(f"提示模板不存在: {name}。可用模板: {available}")
        return self._templates[name]

    def get_template(self, name: str) -> str:
        """获取模板内容"""
        return self.get(name).template

    def render(self, name: str, **kwargs) -> str:
        """
        渲染模板

        Args:
            name: 模板名称
            **kwargs: 模板变量

        Returns:
            渲染后的字符串
        """
        config = self.get(name)

        if config.input_variables:
            template = PromptTemplate(
                template=config.template,
                input_variables=config.input_variables,
            )
            return template.format(**kwargs)

        return config.template

    def create_chat_prompt(
        self,
        system_template: str,
        user_template: str = "user_input",
        **kwargs,
    ) -> ChatPromptTemplate:
        """
        创建聊天提示模板

        Args:
            system_template: 系统提示模板名称
            user_template: 用户提示模板名称
            **kwargs: 用于渲染系统提示的变量

        Returns:
            ChatPromptTemplate
        """
        system_content = self.render(system_template, **kwargs)
        user_content = self.get_template(user_template)

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_content),
                ("human", user_content),
            ]
        )

    def list_templates(self) -> list[dict[str, str]]:
        """列出所有模板"""
        return [
            {
                "name": config.name,
                "description": config.description,
                "variables": ", ".join(config.input_variables) or "无",
            }
            for config in self._templates.values()
        ]


# 全局模板管理器实例
prompt_manager = PromptTemplateManager()
