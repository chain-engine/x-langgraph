const API_KEY_KEY = 'x-langgraph-api-key'

export function getApiKey(): string {
  return localStorage.getItem(API_KEY_KEY) || ''
}

export function setApiKey(key: string) {
  localStorage.setItem(API_KEY_KEY, key)
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>,
  }

  const apiKey = getApiKey()
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }

  const res = await fetch(url, { ...options, headers })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

export const http = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body?: any) =>
    request<T>(url, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(url: string, body?: any) =>
    request<T>(url, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}
