import { getApiKey } from './http'
import type { StreamEvent } from '@/types/workflow'

export function streamWorkflow(
  name: string,
  message: string,
  sessionId: string,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: string) => void,
  onClose?: () => void,
): AbortController {
  const controller = new AbortController()

  const apiKey = getApiKey()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (apiKey) headers['X-API-Key'] = apiKey

  fetch(`/workflows/${name}/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, session_id: sessionId }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }))
        onError?.(detail.detail || `HTTP ${res.status}`)
        return
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: StreamEvent = JSON.parse(line.slice(6))
              onEvent(event)
            } catch {
              // skip malformed lines
            }
          }
        }
      }

      onClose?.()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError?.(err.message)
      }
    })

  return controller
}
