import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi, type ChatRequest, type ChatResponse } from '@/api/chat'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  node?: string
  timestamp: Date
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const currentSessionId = ref('chat-' + Date.now().toString(36))
  const currentWorkflow = ref('')
  const lastNode = ref<string | null>(null)

  let abortController: AbortController | null = null

  async function send(message: string, workflow?: string) {
    const wf = workflow || currentWorkflow.value
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2)

    messages.value.push({
      id,
      role: 'user',
      content: message,
      timestamp: new Date(),
    })

    const request: ChatRequest = {
      message,
      session_id: currentSessionId.value,
      workflow: wf,
    }

    try {
      const response: ChatResponse = await chatApi.chat(request)
      lastNode.value = response.node

      messages.value.push({
        id: id + '-resp',
        role: 'assistant',
        content: response.response,
        node: response.node || undefined,
        timestamp: new Date(),
      })

      return response
    } catch (error) {
      messages.value.push({
        id: id + '-err',
        role: 'assistant',
        content: error instanceof Error ? error.message : '未知错误',
        timestamp: new Date(),
      })
      throw error
    }
  }

  async function sendStream(message: string, workflow?: string) {
    const wf = workflow || currentWorkflow.value
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2)

    messages.value.push({
      id,
      role: 'user',
      content: message,
      timestamp: new Date(),
    })

    isStreaming.value = true
    abortController = new AbortController()

    const request: ChatRequest = {
      message,
      session_id: currentSessionId.value,
      workflow: wf,
    }

    try {
      const response = await chatApi.stream(request)
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      let assistantMsgId = id + '-resp'
      let content = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = new TextDecoder().decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue

          try {
            const event = JSON.parse(line.slice(6))
            if (event.event === 'done') break

            if (event.node) lastNode.value = event.node

            if (event.data) {
              content += event.data
            }
          } catch {}
        }

        const existingMsg = messages.value.find((m) => m.id === assistantMsgId)
        if (existingMsg) {
          existingMsg.content = content
        } else {
          messages.value.push({
            id: assistantMsgId,
            role: 'assistant',
            content,
            node: lastNode.value || undefined,
            timestamp: new Date(),
          })
        }
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        messages.value.push({
          id: id + '-err',
          role: 'assistant',
          content: error instanceof Error ? error.message : '未知错误',
          timestamp: new Date(),
        })
      }
    } finally {
      isStreaming.value = false
      abortController = null
    }
  }

  function stop() {
    abortController?.abort()
  }

  function clear() {
    messages.value = []
    currentSessionId.value = 'chat-' + Date.now().toString(36)
    lastNode.value = null
  }

  function setWorkflow(workflow: string) {
    currentWorkflow.value = workflow
    messages.value = []
    currentSessionId.value = 'chat-' + Date.now().toString(36)
  }

  return {
    messages,
    isStreaming,
    currentSessionId,
    currentWorkflow,
    lastNode,
    send,
    sendStream,
    stop,
    clear,
    setWorkflow,
  }
})
