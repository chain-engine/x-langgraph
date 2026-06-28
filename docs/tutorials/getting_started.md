# 快速入门指南

本教程将帮助您快速上手 LangGraph 框架，并通过本项目的示例代码来学习核心概念。

## 1. 环境准备

### 安装 Python

确保您的系统已安装 Python 3.10 或更高版本：

```bash
python --version
```

### 安装 uv 包管理器

uv 是一个快速的 Python 包管理器，推荐使用它来管理项目依赖：

```bash
# 使用 pip 安装 uv
pip install uv

# 验证安装
uv --version
```

## 2. 项目设置

### 克隆仓库

```bash
git clone https://gitee.com/chain-engine/x-langgraph.git
cd x-langgraph
```

### 安装依赖

```bash
# 使用 uv 安装依赖
uv install
```

## 3. 运行示例

### 基础示例

运行 Hello World 示例：

```bash
uv run python examples/basic/hello_world.py
```

### 高级示例

运行智能体工作流示例：

```bash
uv run python examples/advanced/agent_workflow.py
```

## 4. 核心概念

### 4.1 图（Graph）

LangGraph 的核心概念是图，它由节点和边组成：

- **节点**：表示工作流中的一个步骤或操作
- **边**：表示节点之间的连接和流转关系

### 4.2 智能体（Agent）

智能体是能够执行特定任务的组件，可以：

- 使用工具来完成任务
- 做出决策
- 与其他智能体交互

### 4.3 工具（Tool）

工具是智能体可以使用的功能模块，例如：

- 搜索工具
- 计算工具
- 文件操作工具
- API 调用工具

## 5. 下一步学习

- 查看 `examples` 目录中的更多示例
- 阅读 LangGraph 官方文档
- 尝试创建自己的工作流和智能体

## 6. 常见问题

### Q: 运行示例时出现依赖错误

**A:** 确保已正确安装所有依赖：

```bash
uv install
```

### Q: 如何添加自定义工具

**A:** 参考 `examples/advanced/agent_workflow.py` 中的示例，创建函数并注册到智能体中。

### Q: 如何调试工作流

**A:** 可以在节点函数中添加打印语句，或者使用 Python 的调试器。

---

祝您学习愉快！
