# Task 3 Report: plan_execute.py — Plan-and-Execute 模式

## What I implemented

Created `server/src/workflows/reasoning/plan_execute.py` implementing the Plan-and-Execute reasoning pattern with all interfaces required by the task brief:

- **`TaskStep`**: `TypedDict` describing a single planning step (step_id, description, status, optional result/depends_on/metadata).
- **`PlanExecuteState`**: `BaseReasoningState` subclass extending with `plan`, `current_step`, `pending_tasks`, `completed_tasks`, `replan_count`, `pending_hints`, `execution_summary`, `current_result`, `reflection_result`, `needs_replan`, `final_answer`.
- **`create_planner_node(config)`**: factory that calls the configured LLM to decompose the user task into ordered steps (falls back to a single-step plan on parse failure or empty result), writes `plan` + `pending_tasks`, and resets `current_step` to 0. On replan, injects completed steps and `pending_hints` into the prompt.
- **`create_executor_node(tools)`**: factory that pops `pending_tasks[0]`, invokes the LLM with the current step and a summary of completed steps, writes the result back into the step, and moves it to `completed_tasks`. Handles LLM errors by marking the step `failed` and still advancing the queue.
- **`create_reflector_node(config)`**: factory that, when `enable_reflection=True`, calls the LLM to assess `is_done` / `needs_replan`; otherwise falls back to a structural check on `pending_tasks`. Increments `iteration` and records a reflection step.
- **`create_replan_node(config)`**: factory that, when `needs_replan=True`, asks the LLM to generate replacement steps (consuming the `pending_hints` from the reflector), updates `pending_tasks`, and increments `replan_count`.
- **`create_finish_node()`**: factory that assembles a final answer from `completed_tasks`, appends an `AIMessage` to `messages`, and records a final reflection step.
- **`plan_execute_router(state)`**: routes to `"executor"` (continue), `"replan"` (when `needs_replan`), or `"finish"` (error, no pending, or max iterations reached).
- **`create_plan_execute_workflow(config, tools, checkpointer)`**: factory that builds a `BaseWorkflow` subclass wiring `planner → executor → reflector → {executor | replan | finish}` and `replan → planner`, with a `MemorySaver` checkpointer by default.

The module follows the same conventions as `react.py`: `TypedDict` states, `Annotated[list, add_messages]` messages, factory-style node creators, `_now_iso()` ISO timestamps, `_append_step()` for immutable step list updates, JSON-block parsing with `_parse_json_block()`, and `_extract_message_content()` for response normalization.

## Test results

- `cd server && python -m py_compile src/workflows/reasoning/plan_execute.py && printf "OK\n"` → `OK`.
- `python -c "from workflows.reasoning.plan_execute import (TaskStep, PlanExecuteState, create_planner_node, create_executor_node, create_reflector_node, create_replan_node, create_finish_node, plan_execute_router, create_plan_execute_workflow); ..."` → `imports OK`.
- `create_plan_execute_workflow(config=ReasoningConfig()).build()` → returns a compiled `StateGraph` (`plan_execute`).
- Router unit checks:
  - `pending_tasks=[]` → `"finish"`
  - `pending_tasks=[…]` → `"executor"`
  - `needs_replan=True` → `"replan"`
  - `error=set` → `"finish"`
  - `iteration >= max_iterations` → `"finish"`
- End-to-end smoke test (mocked LLM): a 2-step plan ran through planner → executor → reflector → executor → reflector → finish, producing `final_answer` with 2 completed steps and 6 recorded `intermediate_steps`.
- Editor lint diagnostics for the new file: no errors found.

## Files changed

- `server/src/workflows/reasoning/plan_execute.py` — added.
- `.superpowers/sdd/task-3-report.md` — this report.

## Self-review findings

- The provided task brief is truncated at line 103 inside the first prompt template. The exact prompt content for `_PLANNER_SYSTEM_PROMPT`, `_EXECUTOR_SYSTEM_PROMPT`, `_REFLECTOR_SYSTEM_PROMPT`, and `_REPLAN_SYSTEM_PROMPT` was therefore inferred from the documented interface list plus the project pattern set in `react.py` (JSON-schema prompt + rules). Prompts are best-effort and easy to swap if a downstream review reveals different expectations.
- `create_executor_node(tools)` matches the spec'd interface list exactly. It currently uses the `"deepseek"` provider name as a default; this can be lifted into a `ReasoningConfig` if a future task asks for a configurable executor.
- The reflector's "continue vs. replan" decision is made by the LLM; on parse failure the node defaults to continuing, leaving the router to bound runaway loops via `max_iterations`.
- The `replan` node consumes the same `next_hints` channel as the planner's replan path, keeping the two flows symmetric.
- `plan_execute_router` deliberately treats `error` and `iteration >= max_iterations` as terminal conditions so a failing iteration cannot loop forever, mirroring `react_router`.
- `replan_count` is only incremented by the `replan` node; the planner does not double-count replans when invoked after replan.
