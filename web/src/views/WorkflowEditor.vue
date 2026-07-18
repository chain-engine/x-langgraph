<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save, Database, Settings2, Activity, ScrollText } from 'lucide-vue-next'
import { useWorkflowStore } from '@/stores/workflow'
import WorkflowCanvas from '@/components/graph/WorkflowCanvas.vue'
import NodePalette from '@/components/panels/NodePalette.vue'
import PropertyPanel from '@/components/panels/PropertyPanel.vue'
import StateInspector from '@/components/panels/StateInspector.vue'
import ExecutionLog from '@/components/panels/ExecutionLog.vue'
import ExecuteBar from '@/components/panels/ExecuteBar.vue'
import type { NodeDefinition, EdgeDefinition } from '@/types/workflow'

const route = useRoute()
const router = useRouter()
const store = useWorkflowStore()

const activeTab = ref<'property' | 'state' | 'log'>('property')
const selectedNode = ref<NodeDefinition | null>(null)
const selectedEdge = ref<EdgeDefinition | null>(null)

const workflowName = route.params.name as string

onMounted(() => {
  // 新建跳转时通过 router state 传入数据，避免重复请求
  const passed = history.state?.workflow as any
  if (passed && passed.name === workflowName) {
    store.current = passed
  } else {
    store.fetchWorkflow(workflowName)
  }
})

function goBack() {
  router.push('/')
}

async function save() {
  if (store.current) {
    await store.saveWorkflow(store.current)
  }
}

async function handleUpdateNode(node: NodeDefinition) {
  await store.updateNode(node.id, node)
}

async function handleDeleteNode(nodeId: string) {
  await store.deleteNode(nodeId)
  selectedNode.value = null
}

async function handleUpdateEdge(edge: EdgeDefinition) {
  await store.updateEdge(edge.id, edge)
}

async function handleDeleteEdge(edgeId: string) {
  await store.deleteEdge(edgeId)
  selectedEdge.value = null
}

function handleSelectNode(node: NodeDefinition | null) {
  selectedNode.value = node
  selectedEdge.value = null
  if (node) activeTab.value = 'property'
}

function handleSelectEdge(edge: EdgeDefinition | null) {
  selectedEdge.value = edge
  selectedNode.value = null
  if (edge) activeTab.value = 'property'
}

async function handleNodeDrop(nodeType: string, position: { x: number; y: number }) {
  if (!store.current) return
  const id = `${nodeType}_${Date.now()}`
  const label =
    nodeType === 'processor' ? 'New Processor'
    : nodeType === 'router' ? 'New Router'
    : nodeType === 'tool' ? 'New Tool'
    : 'New Unknown'
  const node: NodeDefinition = {
    id,
    type: nodeType,
    label,
    position,
    handler: '',
    config: {},
  }
  await store.addNode(node)
}

async function handleEdgeConnect(connection: any) {
  if (!store.current) return
  const id = `edge_${Date.now()}`
  const edge: EdgeDefinition = {
    id,
    source: connection.source,
    target: connection.target,
    type: 'normal',
  }
  await store.addEdge(edge)
}

const tabs = [
  { key: 'property' as const, label: '属性', icon: Settings2 },
  { key: 'state' as const, label: '状态', icon: Activity },
  { key: 'log' as const, label: '日志', icon: ScrollText },
]
</script>

<template>
  <div class="flex h-screen flex-col bg-zinc-50">
    <!-- 顶部栏 -->
    <header class="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-2.5">
      <div class="flex items-center gap-3">
        <button @click="goBack" class="rounded-lg p-1.5 text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition">
          <ArrowLeft :size="18" />
        </button>
        <div>
          <h1 class="text-sm font-bold text-zinc-900">{{ store.current?.name || workflowName }}</h1>
          <p class="text-xs text-zinc-500">{{ store.current?.description || '' }}</p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="save"
          class="flex items-center gap-1.5 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 px-3 py-1.5 text-sm text-accent-cyan hover:bg-accent-cyan/30 transition"
        >
          <Save :size="14" /> 保存
        </button>
      </div>
    </header>

    <!-- 主体三栏 -->
    <div class="flex flex-1 overflow-hidden">
      <!-- 左侧：节点面板 + 工作流信息 -->
      <aside class="w-60 shrink-0 border-r border-zinc-200 bg-white overflow-y-auto">
        <NodePalette />

        <div class="p-4">
          <h3 class="flex items-center gap-1.5 text-xs font-medium text-zinc-500 mb-3 uppercase tracking-wide">
            <Database :size="13" /> State Schema
          </h3>
          <div v-if="store.current?.state_schema" class="space-y-1">
            <div
              v-for="(type, field) in store.current.state_schema"
              :key="field"
              class="flex items-center justify-between rounded bg-zinc-50 px-2 py-1 border border-zinc-100"
            >
              <span class="text-xs font-mono text-accent-cyan">{{ field }}</span>
              <span class="text-xs font-mono text-zinc-500">{{ type }}</span>
            </div>
          </div>
        </div>

        <div class="border-t border-zinc-200 p-4">
          <h3 class="text-xs font-medium text-zinc-500 mb-3 uppercase tracking-wide">节点列表</h3>
          <div v-if="store.current?.graph_data.nodes" class="space-y-1">
            <div
              v-for="node in store.current.graph_data.nodes"
              :key="node.id"
              class="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-zinc-100 cursor-pointer transition"
              :class="{ 'bg-zinc-100': selectedNode?.id === node.id }"
              @click="handleSelectNode(node)"
            >
              <span
                class="w-2 h-2 rounded-full"
                :class="{
                  'bg-accent-violet': node.type === 'router',
                  'bg-accent-cyan': node.type === 'processor',
                  'bg-accent-green': node.type === 'tool',
                  'bg-accent-red': node.type === 'unknown',
                }"
              />
              <span class="text-xs text-zinc-700">{{ node.label }}</span>
              <span class="text-[10px] text-zinc-400 ml-auto font-mono">{{ node.handler }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间：画布 -->
      <main class="flex-1 relative">
        <WorkflowCanvas
          :workflow="store.current"
          @select-node="handleSelectNode"
          @select-edge="handleSelectEdge"
          @save="save"
          @node-drop="handleNodeDrop"
          @edge-connect="handleEdgeConnect"
        />
      </main>

      <!-- 右侧：面板 -->
      <aside class="w-80 shrink-0 border-l border-zinc-200 bg-white flex flex-col">
        <!-- Tab 切换 -->
        <div class="flex border-b border-zinc-200">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            @click="activeTab = tab.key"
            class="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs transition"
            :class="activeTab === tab.key ? 'text-accent-cyan border-b-2 border-accent-cyan bg-zinc-50' : 'text-zinc-500 hover:text-zinc-700'"
          >
            <component :is="tab.icon" :size="13" /> {{ tab.label }}
          </button>
        </div>

        <!-- 面板内容 -->
        <div class="flex-1 overflow-hidden">
          <PropertyPanel
            v-show="activeTab === 'property'"
            :node="selectedNode"
            :edge="selectedEdge"
            @update-node="handleUpdateNode"
            @delete-node="handleDeleteNode"
            @update-edge="handleUpdateEdge"
            @delete-edge="handleDeleteEdge"
          />
          <StateInspector v-show="activeTab === 'state'" />
          <ExecutionLog v-show="activeTab === 'log'" />
        </div>
      </aside>
    </div>

    <!-- 底部：执行控制 -->
    <ExecuteBar :workflow-name="workflowName" />
  </div>
</template>
