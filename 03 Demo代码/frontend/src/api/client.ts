import type { AnalysisResult, ApiResponse, Case, CaseCreatePayload, Report, User } from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEMO_USER_KEY = 'rent-safe-ai-demo-user-id'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ message: response.statusText }))
    throw new Error(payload.message ?? `请求失败 (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function ensureDemoUser(): Promise<number> {
  const cached = localStorage.getItem(DEMO_USER_KEY)
  if (cached) return Number(cached)

  const user = await request<User>('/api/v1/users', {
    method: 'POST',
    body: JSON.stringify({
      username: `demo_${Date.now()}`,
      password: 'demo123456',
    }),
  })
  localStorage.setItem(DEMO_USER_KEY, String(user.id))
  return user.id
}

export async function createCase(payload: CaseCreatePayload): Promise<Case> {
  const result = await request<ApiResponse<Case>>('/api/cases', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return result.data
}

export async function runAnalysis(caseId: number): Promise<AnalysisResult> {
  const result = await request<ApiResponse<AnalysisResult>>(`/api/cases/${caseId}/analysis`, {
    method: 'POST',
  })
  return result.data
}

export async function getReport(caseId: number): Promise<Report> {
  const result = await request<ApiResponse<Report>>(`/api/report/${caseId}`)
  return result.data
}

export const DEMO_SAMPLE = {
  title: '押金被扣 2000 元',
  amount: 3000,
  description:
    '2024年3月1日至2025年2月28日租期，押金3000元。合同已到期正常退租，房东以墙面损坏为由扣2000元，我有聊天记录和合同。',
}
