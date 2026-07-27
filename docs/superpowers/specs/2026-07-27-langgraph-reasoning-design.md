# LangGraph 推理能力组件设计

**项目定位**: 生产级 LangGraph 工作流编排框架  
**本文档目标**: 抽取通用推理/决策/规划节点组件，供所有工作流复用  
**日期**: 2026-07-27

---

## 1. 背景与目标

当前 `x-langgraph` 框架已有 5 个业务工作流（意图分类、客服、RAG问答、多Agent、审批），每个工作流内部都有相似的推理/循环/分支逻辑，但这些能力分散在各工作流内部，未被抽象为通用组件。

本文档定义一套可复用的推理节点组件，覆盖三种核心模式：

1. **ReAct** (Reasoning + Acting) — 思考→工具调用→观察→循环
2. **Plan-and-Execute** — 先规划步骤，再按序执行
3. **Tree-of-Thought (ToT)** — 多分支探索→评估→选择最优（简化版）

---

## 2. 设计原则

- **组合优于继承** — 各模式独立实现，通过工厂函数和配置对象注入行为
- **TypedDict + Annotated** — 所有状态类使用 `typing.TypedDict`，`messages` 字段使用 `add_messages`
- **工厂函数生成节点** — 不直接暴露节点类，而是提供 `create_xxx_node(config)` 工厂函数
- **与现有系统无缝整合** — 节点函数注册到 `HANDLER_REGISTRY`，可通过 JSON 编译器加载
- **最大迭代保护** — 所有循环模式内置 `max_iterations` 保护，防止无限循环

---

## 3. 目录结构

```
server/src/workflows/reasoning/
├── __init__.py
├── base.py              # 公共基类和类型
├── react.py             # ReAct 模式
├── plan_execute.py      # Plan-and-Execute 模式
└── tree_of_thought.py   # ToT 模式（简化版）
```

---

## 4. 公共基类 — `base.py`

### 4.1 `BaseReasoningState(TypedDict)`

所有推理状态的公共字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | `Annotated[list, add_messages]` | 对话/推理历史 |
| `iteration` | `int` | 当前迭代次数 |
| `max_iterations` | `int` | 最大迭代上限 |
| `intermediate_steps` | `list[StepRecord]` | 结构化的中间步骤记录 |
| `error` | `str \| None` | 错误信息 |
| `session_id` | `str \| None` | 会话 ID（用于断点续算） |

其中 `StepRecord` 为：

```python
class StepRecord(TypedDict):
    step_type: str          # "reasoning" | "action" | "observation" | "reflection" | "plan" | "execute"
    content: str           # 步骤内容
    timestamp: str         # ISO 格式时间戳
    metadata: dict | None  # 额外元数据
```

### 4.2 `ReasoningConfig(TypedDict)`

通用配置：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_iterations` | `int` | `10` | 最大迭代次数 |
| `timeout_seconds` | `int` | `300` | 超时时间（秒） |
| `enable_reflection` | `bool` | `True` | 是否启用反思/评估 |
| `tools` | `list[BaseTool]` | `[]` | 可用工具列表 |
| `llm_config` | `dict` | `{}` | LLM 配置 |

---

## 5. ReAct 模式 — `react.py`

### 5.1 状态类 `ReactState(BaseReasoningState)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `thought` | `str \| None` | 当前思考内容 |
| `action` | `str \| None` | 当前要执行的工具名 |
| `action_input` | `dict \| None` | 工具调用参数 |
| `observation` | `str \| None` | 工具执行结果 |
| `should_continue` | `bool \| None` | 是否继续循环 |

### 5.2 节点工厂

| 函数 | 说明 |
|------|------|
| `create_reasoning_node(config: ReasoningConfig)` | 思考节点：LLM 生成推理 + 下一步 action |
| `create_action_node(tools: list)` | 动作节点：调用工具，执行 `action` |
| `create_observation_node()` | 观察节点：处理工具返回，更新 `observation` |
| `create_reflection_node(config: ReasoningConfig)` | 反思节点：评估结果，决定是否继续 |
| `create_finish_node()` | 结束节点：汇总结果，输出最终答案 |

### 5.3 路由函数

```python
def react_router(state: ReactState) -> str:
    # 迭代超限 → finish
    if state.get("iteration", 0) >= state.get("max_iterations", 10):
        return "finish"
    # 无 action → reasoning
    if not state.get("action"):
        return "reasoning"
    # 有 action 且无 observation → action
    if state.get("action") and not state.get("observation"):
        return "action"
    # 有 observation → reflect
    return "reflect"
```

### 5.4 流程图

```
[reasoning] → [action] → [observation] → [reflect]
     ↑                                     ↓
     └────────────── (should_continue) ←───┘
                        ↓
                     [finish]
```

### 5.5 工作流类 `ReactWorkflow(BaseWorkflow)`

```python
class ReactWorkflow(BaseWorkflow):
    name = "react"
    description = "ReAct: Reasoning + Acting pattern"

    def build(self, config: ReasoningConfig) -> CompiledStateGraph:
        # 构建 StateGraph(ReactState)
        # 添加所有节点和边
        # 返回编译后的图
```

---

## 6. Plan-and-Execute 模式 — `plan_execute.py`

### 6.1 状态类 `PlanExecuteState(BaseReasoningState)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `plan` | `list[TaskStep]` | 完整任务步骤列表 |
| `current_step` | `int` | 当前执行到第几步（0-indexed） |
| `pending_tasks` | `list[TaskStep]` | 待执行任务（副本） |
| `completed_tasks` | `list[TaskStep]` | 已完成任务（带结果） |
| `replan_count` | `int` | 重规划次数 |
| `pending_hints` | `str \| None` | 对 Planner 的额外上下文 |
| `execution_summary` | `str \| None` | 当前步骤执行摘要 |

其中 `TaskStep`：

```python
class TaskStep(TypedDict):
    step_id: str
    description: str
    status: str           # "pending" | "in_progress" | "completed" | "failed" | "skipped"
    result: str | None
    depends_on: list[str]  # 依赖的 step_id 列表
    metadata: dict | None
```

### 6.2 节点工厂

| 函数 | 说明 |
|------|------|
| `create_planner_node(config: ReasoningConfig)` | 规划节点：生成/修改步骤列表 |
| `create_executor_node(tools: list)` | 执行节点：执行当前步骤 |
| `create_reflector_node(config: ReasoningConfig)` | 反思节点：评估结果，决定下一步 |
| `create_replan_node(config: ReasoningConfig)` | 重规划节点：动态调整计划 |
| `create_finish_node()` | 结束节点：汇总所有步骤结果 |

### 6.3 路由函数

```python
def plan_execute_router(state: PlanExecuteState) -> str:
    if state.get("pending_tasks") and state.get("execution_summary") is None:
        return "plan"        # 无计划 → 规划
    if state.get("pending_tasks") and state.get("current_step") < len(state.get("plan", [])):
        return "execute"      # 有计划有待执行 → 执行
    if state.get("execution_summary") is not None and state.get("pending_tasks"):
        return "reflect"     # 执行完一步 → 反思
    if state.get("replan_count", 0) > 0 and state.get("execution_summary") == "replan":
        return "replan"      # 需要重规划
    if not state.get("pending_tasks"):
        return "finish"      # 无待执行 → 结束
    return "reflect"
```

### 6.4 流程图

```
[plan] → [execute] → [reflect]
              ↑          ↓
              ↓    (needs_replan?) → [replan] → [plan]
              ↓          ↓
              └──────────┴─ [finish]
```

### 6.5 工作流类 `PlanExecuteWorkflow(BaseWorkflow)`

```python
class PlanExecuteWorkflow(BaseWorkflow):
    name = "plan_execute"
    description = "Plan-and-Execute: plan first, then execute step by step"

    def build(self, config: ReasoningConfig) -> CompiledStateGraph:
        # 构建 StateGraph(PlanExecuteState)
        # 添加所有节点和边
        # 返回编译后的图
```

---

## 7. Tree-of-Thought 模式（简化版）— `tree_of_thought.py`

### 7.1 状态类 `ToTState(BaseReasoningState)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `branches` | `list[Branch]` | 所有推理分支 |
| `current_branch_id` | `str \| None` | 活跃分支 ID |
| `evaluated_branches` | `list[str]` | 已评估分支 ID 列表 |
| `best_branch_id` | `str \| None` | 当前最优分支 |
| `max_branches` | `int` | 最大分支数（默认 3） |
| `max_depth` | `int` | 最大深度（默认 5） |
| `depth` | `int` | 当前深度 |

其中 `Branch`：

```python
class Branch(TypedDict):
    branch_id: str
    content: str           # 分支推理内容
    score: float | None    # 评估得分
    parent_id: str | None # 父分支 ID（用于回溯）
    children_ids: list[str]
    status: str           # "active" | "evaluated" | "pruned" | "selected"
    metadata: dict | None
```

### 7.2 节点工厂

| 函数 | 说明 |
|------|------|
| `create_generator_node(config: ReasoningConfig)` | 分支生成节点：为当前分支生成多个子分支 |
| `create_evaluator_node(config: ReasoningConfig)` | 分支评估节点：为每个分支打分 |
| `create_selector_node()` | 选择节点：从评估后的分支中选最优 |
| `create_finish_node()` | 结束节点：输出最优分支内容 |

### 7.3 路由函数

```python
def tot_router(state: ToTState) -> str:
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 5)
    best_id = state.get("best_branch_id")

    if depth >= max_depth or best_id:
        return "finish"    # 达到深度或已选最优 → 结束
    if not state.get("evaluated_branches"):
        return "generate"  # 无评估 → 生成
    return "evaluate"     # 有评估 → 评估
```

### 7.4 流程图

```
[generate] → [evaluate] → [select] → [generate] ...
                                           ↓
                                       [finish]
```

### 7.5 工作流类 `ToTWorkflow(BaseWorkflow)`

```python
class ToTWorkflow(BaseWorkflow):
    name = "tree_of_thought"
    description = "Tree-of-Thought: explore multiple reasoning branches"

    def build(self, config: ReasoningConfig) -> CompiledStateGraph:
        # 构建 StateGraph(ToTState)
        # 添加所有节点和边
        # 返回编译后的图
```

---

## 8. 与现有系统的整合

### 8.1 导出

`workflows/__init__.py` 新增导出：

```python
from .reasoning import (
    # Base
    BaseReasoningState,
    ReasoningConfig,
    StepRecord,
    # ReAct
    ReactState,
    ReactWorkflow,
    create_reasoning_node,
    create_action_node,
    create_observation_node,
    create_reflection_node,
    # Plan-and-Execute
    PlanExecuteState,
    TaskStep,
    PlanExecuteWorkflow,
    create_planner_node,
    create_executor_node,
    create_reflector_node,
    create_replan_node,
    # ToT
    Branch,
    ToTState,
    ToTWorkflow,
    create_generator_node,
    create_evaluator_node,
    create_selector_node,
)
```

### 8.2 Handler 注册

所有节点函数在 `workflows/reasoning/__init__.py` 导入时注册到 `compiler.HANDLER_REGISTRY`，供 JSON 编译器使用。Handler 名称约定：

- ReAct: `react_reasoning`, `react_action`, `react_observation`, `react_reflection`, `react_finish`
- Plan-and-Execute: `plan_planner`, `plan_executor`, `plan_reflector`, `plan_replan`, `plan_finish`
- ToT: `tot_generator`, `tot_evaluator`, `tot_selector`, `tot_finish`

### 8.3 与现有工作流的组合

现有工作流可通过继承或组合方式使用这些组件：

```python
# 示例：客服工作流使用 ReAct
from workflows.reasoning import create_reasoning_node, ReactState

class CustomerServiceWorkflow(BaseWorkflow):
    def build(self):
        workflow = StateGraph(CustomerServiceState)
        workflow.add_node("intake", intake_node)
        workflow.add_node("reasoning", create_reasoning_node(config))
        workflow.add_node("resolve", resolve_node)
        # ...
```

---

## 9. 实现优先级

| 阶段 | 内容 | 说明 |
|------|------|------|
| Phase 1 | `base.py` + `react.py` | 公共基类 + ReAct 完整实现 |
| Phase 2 | `plan_execute.py` | Plan-and-Execute 完整实现 |
| Phase 3 | `tree_of_thought.py` | ToT 简化版实现 |
| Phase 4 | 整合 + 测试 | Handler 注册、导出、集成测试 |

---

## 10. 风险与约束

- **LLM 依赖** — 所有推理节点依赖 LLM 生成内容，质量取决于 LLM 配置
- **工具定义** — ReAct 和 Plan-and-Execute 需要外部提供 `tools` 参数，框架本身不提供工具实现
- **断点续算** — 所有工作流支持 `checkpointer`，但需要外部配置持久化存储
- **并发安全** — 节点函数设计为无状态，状态通过 `TypedDict` 传递，无并发问题
