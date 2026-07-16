import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { streamWorkflow } from '@/api/sse'
import { workflowApi } from '@/api/workflows'
import type { StreamEvent, ExecutionLogEntry, NodeStatus } from '@/types/workflow'

export const useExecutionStore = defineStore('execution', () => {
  const isRunning = ref(false)
  const currentNode = ref<string | null>(null)
  const nodeStatuses = ref<Record<string, NodeStatus>>({})
  const activeEdges = ref<Set<string>>(new Set())
  const logEntries = ref<ExecutionLogEntry[]>([])
  const stateSnapshot = ref<Record<string, any>>({})
  const error = ref<string | null>(null)
  const result = ref<string | null>(null)

  let abortController: AbortController | null = null

  const sortedLog = computed(() =>
    [...logEntries.value].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    ),
  )

  function reset() {
    currentNode.value = null
    nodeStatuses.value = {}
    activeEdges.value = new Set()
    logEntries.value = []
    stateSnapshot.value = {}
    error.value = null
    result.value = null
  }

  async function execute(workflowName: string, message: string, sessionId: string) {
    reset()
    isRunning.value = true

    try {
      const res = await workflowApi.execute(workflowName, { message, session_id: sessionId })
      result.value = res.response
      if (res.error) {
        error.value = res.error
      }
      if (res.state) {
        stateSnapshot.value = res.state
      }
    } catch (e: any) {
      error.value = e.message
    } finally {
      isRunning.value = false
    }
  }

  function stream(workflowName: string, message: string, sessionId: string) {
    reset()
    isRunning.value = true

    abortController = streamWorkflow(
      workflowName,
      message,
      sessionId,
      (event: StreamEvent) => {
        const ts = new Date().toISOString()

        if (event.event === 'node_update' && event.node) {
          currentNode.value = event.node
          nodeStatuses.value[event.node] = 'completed'

          if (event.data) {
            stateSnapshot.value = { ...stateSnapshot.value, ...event.data }

            const route = event.data.route
            if (route) {
              const edgeId = `e-${event.node}-${route}`
              activeEdges.value.add(edgeId)
              activeEdges.value = new Set(activeEdges.value)
            }
          }
        }

        if (event.event === 'done') {
          isRunning.value = false
          currentNode.value = null
        }

        if (event.event === 'error') {
          error.value = typeof event.data === 'string' ? event.data : '执行失败'
          isRunning.value = false
        }

        logEntries.value.push({
          timestamp: ts,
          node: event.node || '',
          event: event.event,
          data: event.data,
        })
      },
      (err: string) => {
        error.value = err
        isRunning.value = false
      },
      () => {
        isRunning.value = false
      },
    )
  }

  function stop() {
    abortController?.abort()
    isRunning.value = false
    currentNode.value = null
  }

  return {
    isRunning,
    currentNode,
    nodeStatuses,
    activeEdges,
    logEntries,
    stateSnapshot,
    error,
    result,
    sortedLog,
    reset,
    execute,
    stream,
    stop,
  }
})
