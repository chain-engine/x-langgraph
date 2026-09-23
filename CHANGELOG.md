# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

## [Unreleased]

### Changed
- 重构 README.md 和 README.en.md 文档，按照生产级开源项目规范重新组织章节结构
- 新增 CHANGELOG.md 版本变更记录

## [0.1.0] - 2026-07-31

### Added
- 项目初始化，搭建基础框架
- FastAPI 后端 API 服务，支持 RESTful 接口
- LangGraph 工作流编排引擎，支持 5 种内置工作流
  - 意图分类路由（Intent Classifier）
  - 智能客服（Customer Service）
  - RAG 文档问答（RAG Q&A）
  - 多智能体协作（Multi-Agent）
  - 自动化审批（Approval）
- ReAct、Tree-of-Thought、Plan-and-Execute 三种推理模式
- MySQL Checkpointer 状态持久化，支持自动降级到 MemorySaver
- Human-in-the-Loop 人机协作机制（interrupt/resume）
- 多 LLM 提供者支持：DeepSeek、豆包、阿里云百炼、Mimo
- IOC 依赖注入容器
- SSE 流式响应支持
- Vue 3 前端可视化工作流编辑器（Vue Flow）
- Docker 容器化部署方案（Dockerfile + docker-compose.yml）
- 完整的 API 文档（Swagger UI + ReDoc）
- 双语文档（README.md 中文、README.en.md 英文）

### Changed
- 重构 API 路由为 v1 版本（/v1/chat、/v1/workflows、/v1/approval）
- 重命名 simple_router 为 intent_classifier
- 重命名 infra 为 infras

### Fixed
- 修复 ReAct 模式规范偏差
- 修复 Plan-and-Execute 执行器 LLM 提供者配置
- 修复 Tree-of-Thought 分支数量传递问题
- 修复所有推理模式的超时配置

## [0.0.1] - 2026-06-28

### Added
- 项目首次提交
- MIT 开源许可证
- 基础项目结构搭建

---

## 版本说明

- **Added**：新增功能
- **Changed**：已有功能的变更
- **Deprecated**：即将移除的功能
- **Removed**：已移除的功能
- **Fixed**：Bug 修复
- **Security**：安全相关的变更
