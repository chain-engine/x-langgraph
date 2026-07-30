import { http, getApiKey } from './http'
import type {
  WorkflowDefinition,
  WorkflowSummary,
  NodeDefinition,
  EdgeDefinition,
  ExecuteRequest,
  ExecuteResult,
} from '@/types/workflow'

export const workflowApi = {
  list: () => http.get<WorkflowSummary[]>('/v1/workflows'),
  get: (name: string) => http.get<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}`),
  create: (wf: WorkflowDefinition) => http.post<WorkflowDefinition>('/v1/workflows', wf),
  update: (name: string, wf: WorkflowDefinition) => http.put<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}`, wf),
  delete: (name: string) => http.delete<{ deleted: boolean }>(`/v1/workflows/${encodeURIComponent(name)}`),

  listHandlers: () => http.get<{ handlers: Array<{ id: string; name: string }> }>('/v1/workflows/handlers'),

  addNode: (name: string, node: NodeDefinition) =>
    http.post<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}/nodes`, node),
  updateNode: (name: string, nodeId: string, node: NodeDefinition) =>
    http.put<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeId)}`, node),
  deleteNode: (name: string, nodeId: string) =>
    http.delete<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeId)}`),

  addEdge: (name: string, edge: EdgeDefinition) =>
    http.post<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}/edges`, edge),
  updateEdge: (name: string, edgeId: string, edge: EdgeDefinition) =>
    http.put<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}/edges/${encodeURIComponent(edgeId)}`, edge),
  deleteEdge: (name: string, edgeId: string) =>
    http.delete<WorkflowDefinition>(`/v1/workflows/${encodeURIComponent(name)}/edges/${encodeURIComponent(edgeId)}`),

  execute: (name: string, req: ExecuteRequest) =>
    http.post<ExecuteResult>(`/v1/workflows/${encodeURIComponent(name)}/execute`, req),
}
