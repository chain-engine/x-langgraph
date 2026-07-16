import { http } from './http'

export interface ChatRequest {
  message: string
  session_id: string
  workflow: string
}

export interface ChatResponse {
  response: string
  session_id: string
  node: string | null
}

export interface ChatStreamEvent {
  event: string
  node?: string | null
  data?: any
}

export const chatApi = {
  chat: (request: ChatRequest): Promise<ChatResponse> =>
    http.post<ChatResponse>('/chat', request),

  stream: (request: ChatRequest): Promise<Response> =>
    fetch('/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': localStorage.getItem('x-langgraph-api-key') || '',
      },
      body: JSON.stringify(request),
    }),
}
