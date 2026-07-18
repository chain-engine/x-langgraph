import { defineStore } from 'pinia'
import { ref } from 'vue'
import { workflowApi } from '@/api/workflows'
import type { WorkflowDefinition, WorkflowSummary } from '@/types/workflow'

export const useWorkflowStore = defineStore('workflow', () => {
  const list = ref<WorkflowSummary[]>([])
  const current = ref<WorkflowDefinition | null>(null)
  const loading = ref(false)
  const handlers = ref<Array<{ id: string; name: string }>>([])

  async function fetchList() {
    loading.value = true
    try {
      list.value = await workflowApi.list()
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkflow(name: string) {
    loading.value = true
    try {
      current.value = await workflowApi.get(name)
      return current.value
    } finally {
      loading.value = false
    }
  }

  async function fetchHandlers() {
    const res = await workflowApi.listHandlers()
    handlers.value = res.handlers
  }

  async function saveWorkflow(wf: WorkflowDefinition) {
    if (current.value && current.value.name === wf.name) {
      current.value = await workflowApi.update(wf.name, wf)
    } else {
      current.value = await workflowApi.create(wf)
    }
    await fetchList()
    return current.value
  }

  async function deleteWorkflow(name: string) {
    await workflowApi.delete(name)
    list.value = list.value.filter((w) => w.name !== name)
    if (current.value?.name === name) {
      current.value = null
    }
  }

  async function addNode(node: any) {
    if (!current.value) return
    current.value = await workflowApi.addNode(current.value.name, node)
    // 第一个节点自动设为入口点
    if (current.value.graph_data.nodes.length === 1) {
      current.value.graph_data.entry_point = node.id
      await workflowApi.update(current.value.name, current.value)
    }
  }

  async function updateNode(nodeId: string, node: any) {
    if (!current.value) return
    current.value = await workflowApi.updateNode(current.value.name, nodeId, node)
  }

  async function deleteNode(nodeId: string) {
    if (!current.value) return
    current.value = await workflowApi.deleteNode(current.value.name, nodeId)
  }

  async function addEdge(edge: any) {
    if (!current.value) return
    current.value = await workflowApi.addEdge(current.value.name, edge)
  }

  async function updateEdge(edgeId: string, edge: any) {
    if (!current.value) return
    current.value = await workflowApi.updateEdge(current.value.name, edgeId, edge)
  }

  async function deleteEdge(edgeId: string) {
    if (!current.value) return
    current.value = await workflowApi.deleteEdge(current.value.name, edgeId)
  }

  return {
    list,
    current,
    loading,
    handlers,
    fetchList,
    fetchWorkflow,
    fetchHandlers,
    saveWorkflow,
    deleteWorkflow,
    addNode,
    updateNode,
    deleteNode,
    addEdge,
    updateEdge,
    deleteEdge,
  }
})
