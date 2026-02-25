const API_KEY = import.meta.env.VITE_API_KEY ?? 'change-me-in-production'
const BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  members: () => request<Member[]>('/members'),

  dailyUsage: (params: { email?: string; start?: string; end?: string }) => {
    const q = new URLSearchParams()
    if (params.email) q.set('email', params.email)
    if (params.start) q.set('start', params.start)
    if (params.end)   q.set('end', params.end)
    return request<DailyUsage[]>(`/usage/daily?${q}`)
  },

  spend: () => request<SpendRow[]>('/usage/spend'),

  sessions: (params: { email?: string; workspace?: string; start?: string; end?: string; page?: number }) => {
    const q = new URLSearchParams()
    if (params.email)     q.set('email', params.email)
    if (params.workspace) q.set('workspace', params.workspace)
    if (params.start)     q.set('start', params.start)
    if (params.end)       q.set('end', params.end)
    if (params.page)      q.set('page', String(params.page))
    return request<SessionsResponse>(`/sessions?${q}`)
  },

  sessionsSummary: (params: { start?: string; end?: string }) => {
    const q = new URLSearchParams()
    if (params.start) q.set('start', params.start)
    if (params.end)   q.set('end', params.end)
    return request<SessionSummary[]>(`/sessions/summary?${q}`)
  },

  alertRules: () => request<AlertRule[]>('/alerts/rules'),
  createAlertRule: (body: Omit<AlertRule, 'id' | 'created_at'>) =>
    request<AlertRule>('/alerts/rules', { method: 'POST', body: JSON.stringify(body) }),
  updateAlertRule: (id: number, body: Omit<AlertRule, 'id' | 'created_at'>) =>
    request<AlertRule>(`/alerts/rules/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteAlertRule: (id: number) =>
    request<void>(`/alerts/rules/${id}`, { method: 'DELETE' }),

  alertEvents: (limit = 50) => request<AlertEvent[]>(`/alerts/events?limit=${limit}`),
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Member {
  id: number
  user_id: string
  email: string
  name: string
  role: string
  is_removed: boolean
}

export interface DailyUsage {
  email: string
  day: string
  agent_requests: number
  chat_requests: number
  composer_requests: number
  total_tabs_accepted: number
  total_lines_added: number
  total_lines_deleted: number
  usage_based_reqs: number
  most_used_model: string | null
  is_active: boolean
}

export interface SpendRow {
  email: string
  name: string | null
  spend_cents: number
  fast_premium_requests: number
  monthly_limit_dollars: number | null
  billing_cycle_start: string
}

export interface SessionSummary {
  user_email: string
  primary_workspace: string
  session_count: number
  total_seconds: number
  first_seen: string
  last_seen: string
}

export interface SessionsResponse {
  total: number
  page: number
  page_size: number
  data: SessionRow[]
}

export interface SessionRow {
  id: number
  conversation_id: string
  user_email: string
  primary_workspace: string | null
  workspace_roots: string[]
  started_at: string | null
  ended_at: string
  duration_seconds: number | null
}

export interface AlertRule {
  id: number
  name: string
  metric: string
  scope: string
  target_email: string | null
  threshold: number
  notify_channels: NotifyChannel[]
  enabled: boolean
  created_at: string
}

export interface NotifyChannel {
  type: 'email' | 'webhook'
  address?: string
  url?: string
}

export interface AlertEvent {
  id: number
  rule_id: number
  rule_name: string
  metric: string
  triggered_at: string
  metric_value: number
  threshold: number
  detail: Record<string, unknown>
}
