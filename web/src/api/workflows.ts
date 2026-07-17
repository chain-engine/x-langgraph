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
  list: () => http.get<WorkflowSummary[]>('/workflows'),
  get: (name: string) => http.get<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}`),
  create: (wf: WorkflowDefinition) => http.post<WorkflowDefinition>('/workflows', wf),
  update: (name: string, wf: WorkflowDefinition) => http.put<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}`, wf),
  delete: (name: string) => http.delete<{ deleted: boolean }>(`/workflows/${encodeURIComponent(name)}`),

  addNode: (name: string, node: NodeDefinition) =>
    http.post<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}/nodes`, node),
  updateNode: (name: string, nodeId: string, node: NodeDefinition) =>
    http.put<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeId)}`, node),
  deleteNode: (name: string, nodeId: string) =>
    http.delete<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeId)}`),

  addEdge: (name: string, edge: EdgeDefinition) =>
    http.post<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}/edges`, edge),
  updateEdge: (name: string, edgeId: string, edge: EdgeDefinition) =>
    http.put<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}/edges/${encodeURIComponent(edgeId)}`, edge),
  deleteEdge: (name: string, edgeId: string) =>
    http.delete<WorkflowDefinition>(`/workflows/${encodeURIComponent(name)}/edges/${encodeURIComponent(edgeId)}`),

  execute: (name: string, req: ExecuteRequest) =>
    http.post<ExecuteResult>(`/workflows/${encodeURIComponent(name)}/execute`, req),
}
