# Task 1: Task 1: base.py — 公共基类和类型

## Task 1: base.py — 公共基类和类型

**Files:**
- Create: `server/src/workflows/reasoning/base.py`

**Interfaces:**
- Consumes: 无
- Produces: `BaseReasoningState`, `ReasoningConfig`, `StepRecord`

**Dependencies:** 无

- [ ] **Step 1: Write base.py**

```python
# server/src/workflows/reasoning/base.py
# -*- coding: utf-8 -*-
"""
推理组件公共基类

定义所有推理模式共享的类型和配置。
"""

from typing import TypedDict, Optional, Any, NotRequired, Annotated
from langgraph.graph import add_messages
from dataclasses import dataclass, field


class StepRecord(TypedDict):
    """结构化的中间步骤记录"""
    step_type: str               # "reasoning" | "action" | "observation" | "reflection" | "plan" | "execute"
    content: str                # 步骤内容
    timestamp: str              # ISO 格式时间戳
    metadata: NotRequired[dict[str, Any] | None]


class BaseReasoningState(TypedDict):
    """
    所有推理状态的公共字段

    各模式应继承此类并扩展自己的字段。
    """

    # 消息历史（使用 add_messages reducer 自动合并）
    messages: Annotated[list, add_messages]

    # 迭代控制
    iteration: int               # 当前迭代次数（0-indexed）
    max_iterations: int          # 最大迭代上限

    # 中间步骤记录
    intermediate_steps: list[StepRecord]

    # 错误信息
    error: Optional[str]

    # 会话 ID（用于断点续算）
    session_id: Optional[str]


@dataclass
class ReasoningConfig:
    """推理组件通用配置"""

    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_reflection: bool = True
    llm_provider: str = "deepseek"
    system_prompt: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "enable_reflection": self.enable_reflection,
            "llm_provider": self.llm_provider,
            "system_prompt": self.system_prompt,
        }
```

- [ ] **Step 2: Create reasoning directory**

```bash
mkdir -p server/src/workflows/reasoning
touch server/src/workflows/reasoning/__init__.py
```

- [ ] **Step 3: Run linter**

```bash
cd server && python -m py_compile src/workflows/reasoning/base.py && echo "OK"
```

- [ ] **Step 4: Commit**

```bash
git add server/src/workflows/reasoning/ && git commit -m "feat(reasoning): add base classes for reasoning components"
```

---

## Global Constraints
- 所有状态类使用 `typing.TypedDict`，`messages` 字段用 `Annotated[list, add_messages]`
- 节点函数签名统一为 `def node(state: StateClass) -> dict:`
- 路由函数签名统一为 `def router(state: StateClass) -> str:`，返回节点名
- `max_iterations` 默认 `10`，防止无限循环
- 与现有 `workflows/base.py`、`workflows/compiler.py` 模式保持一致
- 所有节点函数注册到 `HANDLER_REGISTRY`，命名约定：`<prefix>_<node_name>`
