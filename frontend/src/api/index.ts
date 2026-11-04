import { request } from './client'
import type {
  AgentConversation,
  DashboardData,
  Health,
  InvestmentInputs,
  InvestmentResult,
  KnowledgeAnswer,
  KnowledgeResult,
  KnowledgeStats,
  Meta,
  ScenarioResponse,
  UploadResult,
  ValuationResult,
  VisionResult,
} from '@/types'

export const api = {
  meta: () => request<Meta>('/api/meta'),
  health: () => request<Health>('/api/health'),
  dashboard: () => request<DashboardData>('/api/dashboard'),
  research: () => request<Record<string, unknown>>('/api/research'),
  modelCard: () => request<Record<string, unknown>>('/api/model-card'),
  security: () => request<Record<string, unknown>>('/api/security'),
  market: (zipcode: string) => request<Record<string, unknown>>(`/api/market/${zipcode}`),
  valuation: (payload: Record<string, unknown>) =>
    request<ValuationResult>('/api/valuation/analyze', { method: 'POST', body: JSON.stringify(payload) }),
  investment: (payload: InvestmentInputs) =>
    request<InvestmentResult>('/api/investment/calculate', { method: 'POST', body: JSON.stringify(payload) }),
  scenarios: (payload: { base: InvestmentInputs; rent_change_pct?: number; interest_rate_delta?: number; price_change_pct?: number }) =>
    request<ScenarioResponse>('/api/investment/scenarios', { method: 'POST', body: JSON.stringify(payload) }),
  presets: () => request<{ presets: Record<string, unknown>[]; defaults: InvestmentInputs }>('/api/investment/presets'),
  knowledgeStats: () => request<KnowledgeStats>('/api/knowledge/stats'),
  knowledgeSearch: (payload: { question: string; top_k?: number; category?: string | null }) =>
    request<{ question: string; results: KnowledgeResult[] }>('/api/knowledge/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  knowledgeQuery: (payload: { question: string; top_k?: number; category?: string | null }) =>
    request<KnowledgeAnswer>('/api/knowledge/query', { method: 'POST', body: JSON.stringify(payload) }),
  knowledgeDocument: (docId: string) =>
    request<{ doc_id: string; meta: Record<string, string>; markdown: string }>(`/api/knowledge/documents/${docId}`),
  uploadImage: async (file: File): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    return request<UploadResult>('/api/vision/upload', { method: 'POST', body: form })
  },
  analyzeImage: (imageId: string) =>
    request<VisionResult>('/api/vision/analyze', { method: 'POST', body: JSON.stringify({ image_id: imageId }) }),
  saveReport: (payload: { kind: string; title: string; payload: Record<string, unknown> }) =>
    request<{ id: string; created_at: string }>('/api/reports', { method: 'POST', body: JSON.stringify(payload) }),
  conversations: () => request<{ items: AgentConversation[] }>('/api/agent/conversations'),
  conversation: (id: string) => request<Record<string, unknown>>(`/api/agent/conversations/${id}`),
}
