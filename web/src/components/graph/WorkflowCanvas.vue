<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection, NodeChange, EdgeChange } from '@vue-flow/core'
import WorkflowNode from './WorkflowNode.vue'
import WorkflowEdge from './WorkflowEdge.vue'
import type { WorkflowDefinition, NodeDefinition, EdgeDefinition } from '@/types/workflow'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps<{
  workflow: WorkflowDefinition | null
}>()

const emit = defineEmits<{
  save: []
  selectNode: [node: NodeDefinition | null]
  selectEdge: [edge: EdgeDefinition | null]
  nodeDrop: [nodeType: string, position: { x: number; y: number }]
  edgeConnect: [connection: Connection]
}>()

const execution = useExecutionStore()
const { onConnect, addEdges, applyNodeChanges, applyEdgeChanges } = useVueFlow()

const vueFlowRef = ref<HTMLElement | null>(null)
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])

function handleDrop(event: DragEvent) {
  const nodeType = event.dataTransfer?.getData('application/x-workflow-node-type')
  if (!nodeType) return
  const bounds = vueFlowRef.value?.getBoundingClientRect()
  if (!bounds) return
  emit('nodeDrop', nodeType, {
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  })
}

const nodeTypes = { workflow: WorkflowNode }
const edgeTypes = { workflow: WorkflowEdge }

function syncFromWorkflow(wf: WorkflowDefinition | null) {
  if (!wf) {
    nodes.value = []
    edges.value = []
    return
  }

  const graph = wf.graph_data
  const mappedNodes: Node[] = graph.nodes.map((n) => ({
    id: n.id,
    type: 'workflow',
    position: n.position,
    data: {
      label: n.label,
      nodeType: n.type,
      handler: n.handler,
      config: n.config,
      isEntryPoint: n.id === graph.entry_point,
    },
  }))

  const hasEndTarget = graph.edges.some((e) => e.target === '__end__' || e.source === '__end__')
  if (hasEndTarget) {
    const maxY = Math.max(...mappedNodes.map((n) => n.position.y))
    mappedNodes.push({
      id: '__end__',
      type: 'workflow',
      position: { x: 400, y: maxY + 200 },
      data: { label: 'END', nodeType: 'end', handler: '', config: {}, isEntryPoint: false },
    })
  }
  nodes.value = mappedNodes

  const mappedEdges: Edge[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'workflow',
    data: {
      edgeType: e.type,
      condition: e.condition,
    },
    animated: false,
  }))
  edges.value = mappedEdges
}

watch(() => props.workflow, syncFromWorkflow, { immediate: true })

watch(() => execution.currentNode, (node) => {
  nodes.value = nodes.value.map((n) => ({
    ...n,
    data: {
      ...n.data,
      status: n.id === node ? 'running' : execution.nodeStatuses[n.id] || 'idle',
    },
  }))
})

watch(() => execution.activeEdges, (active) => {
  edges.value = edges.value.map((e) => ({
    ...e,
    animated: active.has(e.id),
    data: { ...e.data, isActive: active.has(e.id) },
  }))
}, { deep: true })

onConnect((connection: Connection) => {
  addEdges([{
    ...connection,
    type: 'workflow',
    data: { edgeType: 'normal' },
  }])
  emit('edgeConnect', connection)
})

function onNodeClick({ node }: { node: Node }) {
  const wfNode = props.workflow?.graph_data.nodes.find((n) => n.id === node.id)
  emit('selectNode', wfNode || null)
}

function onEdgeClick({ edge }: { edge: Edge }) {
  const wfEdge = props.workflow?.graph_data.edges.find((e) => e.id === edge.id)
  emit('selectEdge', wfEdge || null)
}

function onNodeConnect(connection: Connection) {
  addEdges([{
    ...connection,
    type: 'workflow',
    data: { edgeType: 'normal' },
  }])
  emit('edgeConnect', connection)
}

function onNodesChange(changes: NodeChange[]) {
  applyNodeChanges(changes)
  if (changes.some((c) => c.type === 'position' && c.dragging === false)) {
    emit('save')
  }
}

function onEdgesChange(changes: EdgeChange[]) {
  applyEdgeChanges(changes)
  if (changes.some((c) => c.type === 'remove')) {
    emit('save')
  }
}

const minimapColor = (node: Node) => {
  const t = node.data?.nodeType
  if (t === 'router') return '#a855f7'
  if (t === 'tool') return '#10b981'
  if (t === 'unknown') return '#ef4444'
  return '#00d4ff'
}
</script>

<template>
  <div class="relative h-full w-full" ref="vueFlowRef" @dragover.prevent @drop="handleDrop">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :default-viewport="{ zoom: 1 }"
      fit-view-on-init
      class="h-full w-full"
      @nodes-change="onNodesChange"
      @edges-change="onEdgesChange"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @connect="onNodeConnect"
    >
      <Background :gap="20" :size="1" pattern-color="#1a1a24" />
      <Controls position="bottom-left" />
      <MiniMap position="bottom-right" :node-color="minimapColor" mask-color="rgba(10,10,15,0.8)" />
    </VueFlow>
  </div>
</template>
