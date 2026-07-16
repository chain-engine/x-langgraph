export interface NodePosition {
  x: number
  y: number
}

export interface NodeDefinition {
  id: string
  type: string
  label: string
  position: NodePosition
  handler: string
  config: Record<string, any>
}

export interface EdgeCondition {
  field: string
  operator: string
  value: string
}

export interface EdgeDefinition {
  id: string
  source: string
  target: string
  type: 'normal' | 'conditional'
  condition?: EdgeCondition | null
}

export interface GraphData {
  nodes: NodeDefinition[]
  edges: EdgeDefinition[]
  entry_point: string
}

export interface WorkflowDefinition {
  name: string
  description: string
  state_schema: Record<string, string>
  graph_data: GraphData
  created_at?: string
  updated_at?: string
}

export interface WorkflowSummary {
  name: string
  description: string
  node_count: number
  edge_count: number
  created_at?: string
  updated_at?: string
}

export interface ExecuteRequest {
  message: string
  session_id: string
}

export interface ExecuteResult {
  response: string
  session_id: string
  node: string | null
  error?: string
  state?: Record<string, any>
}

export interface StreamEvent {
  event: string
  node?: string | null
  data?: any
}

export type NodeStatus = 'idle' | 'running' | 'completed' | 'error'

export interface ExecutionLogEntry {
  timestamp: string
  node: string
  event: string
  data?: any
}
