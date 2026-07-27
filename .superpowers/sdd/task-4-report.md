# Task 4 Report: tree_of_thought.py — Tree-of-Thought 模式（简化版）

## What I implemented

Created `server/src/workflows/reasoning/tree_of_thought.py` with the simplified Tree-of-Thought workflow. All required interfaces are exported:

- **State types** (both `TypedDict`):
  - `Branch` — branch record with `branch_id`, `content`, `score`, `parent_id`, `children_ids`, `status`, `metadata`.
  - `ToTState(BaseReasoningState)` — extends the shared reasoning state with `branches`, `current_branch_id`, `evaluated_branches`, `best_branch_id`, `max_branches`, `max_depth`, `depth`, `new_branches`, `final_answer`, `evaluation_results`.
- **Node factories** (each follows `def node(state: StateClass) -> dict:` and returns immutable updates):
  - `create_generator_node(config)` — prompts LLM for `num_branches` new branches, parents them under `best_branch_id`, updates `children_ids`, increments `depth`.
  - `create_evaluator_node(config)` — single LLM call scores every new branch, writes `evaluation_results`, marks branches as `evaluated`, adds heuristic fallback score if LLM skipped an id.
  - `create_selector_node(config)` — asks LLM to pick `best_branch_id`; falls back to highest local score; marks branch `selected` and bumps `iteration`.
  - `create_finish_node()` — synthesizes `final_answer` from the selected branch content + score + selected reason, emits `AIMessage` to `messages`.
- **Routing**:
  - `tot_router(state) -> str` — exits to `finish` on error, missing evaluations, `depth >= max_depth`, or `iteration >= max_iterations`; otherwise loops back to `generator`.
- **Workflow**:
  - `create_tot_workflow(config, checkpointer=None)` — returns a `BaseWorkflow` subclass that compiles `generator → evaluator → selector → {generator | finish}`.
- **Helpers** mirrored from `react.py`/`plan_execute.py`: `_now_iso`, `_extract_user_query`, `_append_step`, `_parse_json_block` (using `json.JSONDecoder().raw_decode`), `_extract_message_content`, plus ToT-specific `_make_branch`, `_format_branches`, `_find_branch`.
- **Limits**: `max_branches` default 3, `max_depth` default 5 (overridable via state values written before invocation).
- **Step logging**: every node appends a `StepRecord` via `_append_step` with metadata (depth, branch_ids, scores, chosen id, etc.).
- **Same surface contract** as the other reasoning modules: imports from `core.logger`, `llms.providers.get_llm_provider`, and `workflows.reasoning.base`.

## Test results

- `cd server && python -m py_compile src/workflows/reasoning/tree_of_thought.py && printf "OK\n"` → **OK**
- Smoke import via `from workflows.reasoning.tree_of_thought import (...)` works for all eight required names.
- End-to-end simulation with a stub LLM:
  - `generator` produced two branches with stable ids (`branch-<8hex>`) under the configured `best_branch_id`.
  - `evaluator` ran a single LLM call and produced `evaluation_results` with per-branch scores; heuristic fallback engaged when the LLM response used placeholder ids.
  - `selector` returned the highest-scoring branch (`branch-2cb43582`) after the LLM `best_branch_id` placeholder failed validation.
  - `tot_router` returned `generator` while `depth=1, iteration=1` and `finish` when `depth=5` (>= `max_depth`).
- Lint check (`ReadLints`): **No linter errors found**.

## Files changed

- `server/src/workflows/reasoning/tree_of_thought.py` — added (~650 lines).
- `.superpowers/sdd/task-4-report.md` — added as the task report.

## Self-review findings

- **Routing semantics**: selector → generator loop checks `depth` and `iteration`, so the same `iteration < max_iterations` invariant from ReAct still holds while adding a second dimension (`depth < max_depth`). This means a workflow can saturate `max_depth` (5) but still have iteration headroom — appropriate for ToT where deepening is the primary cutoff.
- **LLM resilience**: if any individual LLM call fails, `evaluator`/`selector` fall back to local heuristics (heuristic length-based score; pick highest scored branch). `generator` falls back to a single branch containing the raw LLM text so the workflow does not stall. `error` is only set on `generator` failure so the router can short-circuit to `finish`.
- **Idempotent updates**: every node returns fresh dicts (e.g. `dict(b)` for branches) rather than mutating in place, matching the immutable update style used elsewhere in the reasoning package and compatible with LangGraph reducers.
- **Public surface**: `__all__` lists exactly the eight names required by the brief. Module-level imports use only what is actually referenced (removed the unused `BaseMessage` import after lint feedback).
- **Considerations worth flagging downstream**:
  - The workflow does not currently implement `HANDLER_REGISTRY` registration. If the parent SDD contracts (`workflows/compiler.py`) require registration, follow-up tasks should expose the `create_*_node` factories via that registry (the constants `<prefix>_<node_name>` would map naturally: `tot_generator`, `tot_evaluator`, `tot_selector`, `tot_finish`).
  - `max_branches` and `max_depth` are read from state rather than from `ReasoningConfig`. This is intentional (matches the brief's "default 3 / default 5" wording) but means callers must set them in the initial state or default before invoking.
