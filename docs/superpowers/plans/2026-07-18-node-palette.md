# Node Palette — Drag to Create Nodes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a left-side panel with draggable node type templates (processor / router / tool) that users can drag onto the canvas to create new workflow nodes.

**Architecture:** A new `NodePalette.vue` component sits in the left sidebar area of `WorkflowEditor.vue`. It uses VueFlow's `onDrop` + HTML5 Drag API to handle drag-and-drop onto the canvas. On drop, the component emits a `node-add` event upward to `WorkflowEditor.vue`, which calls `store.addNode()` then triggers `save()`. The palette is always visible in the editor, positioned above the existing node list.

**Tech Stack:** Vue 3, @vue-flow/core, TypeScript, Tailwind CSS.

---

## Global Constraints

- Existing Tailwind color tokens: `accent-cyan`, `accent-violet`, `accent-green`, `accent-red`, `accent-amber`, `accent-amber`
- Existing icon library: `lucide-vue-next`
- Existing `workflow.ts` store already has `addNode()` method
- Node type enum values: `processor` | `router` | `tool` | `unknown`

---

## File Structure

- **Create:** `web/src/components/panels/NodePalette.vue` — the draggable palette panel
- **Modify:** `web/src/views/WorkflowEditor.vue` — embed palette + handle `onDrop` + wire `addNode` call
- **Modify:** `web/src/stores/workflow.ts` — `addNode` already exists, no changes needed
- **Modify:** `web/src/api/workflows.ts` — `addNode` already exists, no changes needed

---

## Task 1: Create `NodePalette.vue`

**Files:**
- Create: `web/src/components/panels/NodePalette.vue`

**Interfaces:**
- Consumes: nothing external
- Produces: emits `dragstart` natively via HTML5 drag (no custom emit needed — parent handles `onDrop` on the VueFlow canvas)

- [ ] **Step 1: Write the component**

```vue
<script setup lang="ts">
import { GitBranch, Cog, Wrench, HelpCircle } from 'lucide-vue-next'

const nodeTypes = [
  {
    type: 'processor',
    label: 'Processor',
    description: '处理消息的节点',
    icon: Cog,
    color: 'accent-cyan',
    borderClass: 'border-accent-cyan',
    iconClass: 'text-accent-cyan',
  },
  {
    type: 'router',
    label: 'Router',
    description: '路由分发到多个分支',
    icon: GitBranch,
    color: 'accent-violet',
    borderClass: 'border-accent-violet',
    iconClass: 'text-accent-violet',
  },
  {
    type: 'tool',
    label: 'Tool',
    description: '调用外部工具',
    icon: Wrench,
    color: 'accent-green',
    borderClass: 'border-accent-green',
    iconClass: 'text-accent-green',
  },
  {
    type: 'unknown',
    label: 'Unknown',
    description: '未知类型节点',
    icon: HelpCircle,
    color: 'accent-red',
    borderClass: 'border-accent-red',
    iconClass: 'text-accent-red',
  },
]

function onDragStart(event: DragEvent, nodeType: string) {
  event.dataTransfer?.setData('application/x-workflow-node-type', nodeType)
  event.dataTransfer!.effectAllowed = 'move'
}
</script>

<template>
  <div class="p-3 border-b border-zinc-200">
    <h3 class="text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wide">添加节点</h3>
    <div class="space-y-1.5">
      <div
        v-for="t in nodeTypes"
        :key="t.type"
        draggable="true"
        @dragstart="onDragStart($event, t.type)"
        class="flex items-center gap-2.5 rounded-lg border-2 px-3 py-2 cursor-grab active:cursor-grabbing hover:shadow-sm transition-all hover:-translate-y-0.5"
        :class="t.borderClass"
      >
        <component :is="t.icon" :size="14" :class="t.iconClass" />
        <div class="flex flex-col">
          <span class="text-xs font-medium text-zinc-900">{{ t.label }}</span>
          <span class="text-[10px] text-zinc-400">{{ t.description }}</span>
        </div>
      </div>
    </div>
    <p class="text-[10px] text-zinc-400 mt-2">拖拽到画布添加节点</p>
  </div>
</template>
```

- [ ] **Step 2: Verify file created**

Run: `ls web/src/components/panels/NodePalette.vue`
Expected: file exists

- [ ] **Step 3: Commit**

```bash
git add web/src/components/panels/NodePalette.vue
git commit -m "feat(web): add NodePalette component"
```

---

## Task 2: Wire palette into WorkflowEditor + drop handling

**Files:**
- Modify: `web/src/views/WorkflowEditor.vue:13-31` (imports + setup) and `web/src/views/WorkflowEditor.vue:108-151` (left aside section)

**Interfaces:**
- Consumes: `NodePalette.vue`, `store.addNode()`, `store.saveWorkflow()`
- Produces: `WorkflowCanvas.vue` gets `ref` for `nodes`/`edges` arrays + `onDrop` handler

**Important note on Task 2:** `WorkflowCanvas.vue` is the component that owns the VueFlow instance. The cleanest way to handle drop is to expose the VueFlow instance's `onDrop` handler from inside `WorkflowCanvas.vue`. We will add a `dropZoneRef` div inside the VueFlow wrapper and handle `dragover`/`drop` at the canvas level. Alternatively, since `WorkflowCanvas` already has `addEdges` from `useVueFlow()`, we can expose an `addNode` callback. The simplest approach: add `onDrop` to `WorkflowCanvas.vue` and emit upward, so `WorkflowEditor.vue` calls `store.addNode()` then triggers `save()`. This keeps the canvas "dumb" (just rendering) and the editor handles business logic.

- [ ] **Step 1: Modify WorkflowCanvas.vue — add drop handling**

```vue
// After line 24 (const { onConnect, addEdges, applyNodeChanges, applyEdgeChanges } = useVueFlow())
// Add:
const { onConnect, addEdges, applyNodeChanges, applyEdgeChanges, onDrop } = useVueFlow()

const emit = defineEmits<{
  save: []
  selectNode: [node: NodeDefinition | null]
  selectEdge: [edge: EdgeDefinition | null]
  nodeDrop: [nodeType: string, position: { x: number; y: number }]
}>()

// After line 25 (const nodes = ref<Node[]>([]))
const vueFlowRef = ref<HTMLElement | null>(null)

// After line 106 (onConnect)
onDrop((event: DragEvent) => {
  const nodeType = event.dataTransfer?.getData('application/x-workflow-node-type')
  if (!nodeType) return
  const bounds = (event.target as HTMLElement).getBoundingClientRect()
  const position = {
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  }
  emit('nodeDrop', nodeType, position)
})
```

- [ ] **Step 2: Modify WorkflowCanvas.vue — add @dragover.prevent on VueFlow wrapper**

In the `<template>` section, wrap VueFlow in a div that handles `dragover`:

```vue
<!-- Replace <div class="relative h-full w-full"> with: -->
<div
  class="relative h-full w-full"
  @dragover.prevent
>
```

- [ ] **Step 3: Modify WorkflowEditor.vue — import NodePalette**

Add after existing imports (around line 7):
```vue
import NodePalette from '@/components/panels/NodePalette.vue'
```

- [ ] **Step 4: Modify WorkflowEditor.vue — add nodeDrop handler**

Add new function after `handleSelectEdge` (around line 73):

```ts
async function handleNodeDrop(nodeType: string, position: { x: number; y: number }) {
  if (!store.current) return
  const id = `${nodeType}_${Date.now()}`
  const node: NodeDefinition = {
    id,
    type: nodeType,
    label: nodeType === 'processor' ? 'New Processor'
      : nodeType === 'router' ? 'New Router'
      : nodeType === 'tool' ? 'New Tool'
      : 'New Unknown',
    position,
    handler: '',
    config: {},
  }
  await store.addNode(node)
  // Sync position after server assigns it
  const saved = store.current?.graph_data.nodes.find((n) => n.id === id)
  if (saved) {
    saved.position = position
  }
}
```

- [ ] **Step 5: Modify WorkflowEditor.vue — wire into WorkflowCanvas**

Update the `<WorkflowCanvas>` tag (around line 154):
```vue
<WorkflowCanvas
  :workflow="store.current"
  @select-node="handleSelectNode"
  @select-edge="handleSelectEdge"
  @save="save"
  @node-drop="handleNodeDrop"
/>
```

- [ ] **Step 6: Modify WorkflowEditor.vue — embed NodePalette in left aside**

In the left aside `<aside class="w-60 shrink-0 ...>` section, add NodePalette above the State Schema section:

```vue
<aside class="w-60 shrink-0 border-r border-zinc-200 bg-white overflow-y-auto">
  <!-- Add this -->
  <NodePalette />

  <div class="p-4">
    <h3 class="flex items-center gap-1.5 text-xs font-medium text-zinc-500 mb-3 uppercase tracking-wide">
      <Database :size="13" /> State Schema
    </h3>
    <!-- rest unchanged below -->
```

- [ ] **Step 7: Verify in browser**

Run: `cd web && npm run dev`
Expected: Editor page shows a "添加节点" palette section at top-left with 4 draggable node type cards.

- [ ] **Step 8: Commit**

```bash
git add web/src/views/WorkflowEditor.vue web/src/components/graph/WorkflowCanvas.vue
git commit -m "feat(web): wire NodePalette into editor with drag-drop node creation"
```

---

## Task 3: Set entry_point on first node

**Files:**
- Modify: `web/src/stores/workflow.ts` — `addNode` function

**Context:** When a workflow has zero nodes, the first node added should automatically become the `entry_point`.

- [ ] **Step 1: Modify addNode to auto-set entry_point**

Find the `addNode` function in `workflow.ts` (line 54-57) and update:

```ts
async function addNode(node: any) {
  if (!current.value) return
  current.value = await workflowApi.addNode(current.value.name, node)
  // Auto-set entry_point if this is the first node
  if (current.value.graph_data.nodes.length === 1) {
    current.value.graph_data.entry_point = node.id
    await workflowApi.update(current.value.name, current.value)
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/stores/workflow.ts
git commit -m "feat(web): auto-set entry_point on first node added to workflow"
```
