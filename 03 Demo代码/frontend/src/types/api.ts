export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface User {
  id: number
  username: string
  phone: string | null
  avatar: string | null
  create_time: string
  update_time: string
}

export interface CaseCreatePayload {
  user_id: number
  case_title?: string
  case_type?: string
  description?: string
  amount?: number
}

export interface Case {
  id: number
  user_id: number
  case_title: string | null
  case_type: string
  description: string | null
  amount: string | null
  status: string
  risk_level: string | null
  ai_status: string
  create_time: string
  update_time: string
}

export interface Report {
  id: number
  case_id: number
  version: number
  summary: string | null
  risk_analysis: string | null
  legal_basis: string | null
  missing_evidence: string | null
  action_plan: string | null
  disclaimer: string | null
  provider: string | null
  ai_model: string | null
  prompt_version: string | null
  knowledge_version: string | null
  create_time: string
  update_time: string
}

export interface AgentTrace {
  task_type: string
  status: string
  latency: number
  token_usage: number
  output: Record<string, unknown> | unknown[] | string | null
}

export interface AnalysisResult {
  case_id: number
  dispute_type: string
  completeness: boolean
  completeness_score: number
  follow_up_questions: string[]
  risk_level: string
  analysis_mode: string
  provider: string
  model: string
  prompt_version: string
  knowledge_version: string
  disclaimer: string
  retrieved_knowledge: Array<Record<string, string>>
  report: Report
  workflow: AgentTrace[]
}
