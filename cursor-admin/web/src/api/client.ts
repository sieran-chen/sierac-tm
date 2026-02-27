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
  sessionsSummaryByProject: (params: { start?: string; end?: string }) => {
    const q = new URLSearchParams()
    if (params.start) q.set('start', params.start)
    if (params.end) q.set('end', params.end)
    return request<SessionSummaryByProjectRow[]>(`/sessions/summary-by-project?${q}`)
  },

  alertRules: () => request<AlertRule[]>('/alerts/rules'),
  createAlertRule: (body: Omit<AlertRule, 'id' | 'created_at'>) =>
    request<AlertRule>('/alerts/rules', { method: 'POST', body: JSON.stringify(body) }),
  updateAlertRule: (id: number, body: Omit<AlertRule, 'id' | 'created_at'>) =>
    request<AlertRule>(`/alerts/rules/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteAlertRule: (id: number) =>
    request<void>(`/alerts/rules/${id}`, { method: 'DELETE' }),

  alertEvents: (limit = 50) => request<AlertEvent[]>(`/alerts/events?limit=${limit}`),

  projects: (params?: { status?: string }) => {
    const q = params?.status ? `?status=${encodeURIComponent(params.status)}` : ''
    return request<Project[]>(`/projects${q}`)
  },
  project: (id: number) => request<Project>(`/projects/${id}`),
  createProject: (body: ProjectCreate) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(body) }),
  updateProject: (id: number, body: ProjectUpdate) =>
    request<Project>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  archiveProject: (id: number) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),
  reinjectHook: (id: number) =>
    request<{ ok: boolean; message?: string }>(`/projects/${id}/reinject-hook`, { method: 'POST' }),
  projectSummary: (id: number) =>
    request<ProjectSummary>(`/projects/${id}/summary`),
  myContributions: (params: { email: string; start?: string; end?: string; period_type?: string; period_key?: string }) => {
    const q = new URLSearchParams()
    q.set('email', params.email)
    if (params.start) q.set('start', params.start)
    if (params.end) q.set('end', params.end)
    if (params.period_type) q.set('period_type', params.period_type)
    if (params.period_key) q.set('period_key', params.period_key)
    return request<MyContributionRow[] | MyContributionScore>(`/contributions/my?${q}`)
  },

  leaderboard: (params: { period_type: string; period_key: string; hook_only?: boolean }) => {
    const q = new URLSearchParams()
    q.set('period_type', params.period_type)
    q.set('period_key', params.period_key)
    if (params.hook_only !== undefined) q.set('hook_only', String(params.hook_only))
    return request<LeaderboardResponse>(`/contributions/leaderboard?${q}`)
  },

  /** Loop health: whether Hook has reported any sessions in the last N days. */
  loopHealth: (params?: { days?: number }) => {
    const q = new URLSearchParams()
    if (params?.days != null) q.set('days', String(params.days))
    return request<LoopHealthResponse>(`/health/loop${q.toString() ? `?${q}` : ''}`)
  },

  incentiveRules: (params?: { enabled_only?: boolean }) => {
    const q = params?.enabled_only ? '?enabled_only=true' : ''
    return request<IncentiveRule[]>(`/incentive-rules${q}`)
  },
  incentiveRule: (id: number) => request<IncentiveRule>(`/incentive-rules/${id}`),
  createIncentiveRule: (body: IncentiveRuleCreate) =>
    request<IncentiveRule>('/incentive-rules', { method: 'POST', body: JSON.stringify(body) }),
  updateIncentiveRule: (id: number, body: IncentiveRuleUpdate) =>
    request<IncentiveRule>(`/incentive-rules/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteIncentiveRule: (id: number) =>
    request<void>(`/incentive-rules/${id}`, { method: 'DELETE' }),
  recalculateIncentiveRule: (id: number) =>
    request<{ ok: boolean; message?: string }>(`/incentive-rules/${id}/recalculate`, { method: 'POST' }),
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Project {
  id: number
  name: string
  description: string
  git_repos: string[]
  workspace_rules: string[]
  member_emails: string[]
  status: string
  gitlab_project_id: number | null
  repo_provider: string | null
  github_repo_full_name: string | null
  repo_url: string
  repo_ssh_url: string
  hook_initialized: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  workspace_rules: string[]
  member_emails?: string[]
  created_by: string
  git_repos?: string[]
  auto_create_repo?: boolean
  repo_slug?: string
  repo_provider?: 'gitlab' | 'github'
}

export interface ProjectUpdate {
  name?: string
  description?: string
  git_repos?: string[]
  workspace_rules?: string[]
  member_emails?: string[]
  status?: string
}

export interface ProjectSummary {
  project: Project
  session_count: number
  total_duration_seconds: number
  participants: { user_email: string; session_count: number; total_seconds: number }[]
  contributions: {
    author_email: string
    commit_date: string
    commit_count: number
    lines_added: number
    lines_removed: number
    files_changed: number
  }[]
}

export interface MyContributionRow {
  project_id: number
  project_name: string
  commit_date: string
  commit_count: number
  lines_added: number
  lines_removed: number
  files_changed: number
}

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

export interface SessionSummaryByProjectRow {
  project_id: number | null
  project_name: string
  user_email: string
  session_count: number
  total_seconds: number
  first_seen: string | null
  last_seen: string | null
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
  project_id: number | null
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

// ─── Contributions / Incentives ───────────────────────────────────────────────

export interface MyContributionScore {
  user_email: string
  period_type: string
  period_key: string
  hook_adopted: boolean
  total_score: number
  rank: number | null
  score_breakdown: Record<string, number>
  raw: { lines_added: number; commit_count: number; session_duration_hours: number; agent_requests: number; files_changed: number }
  projects: { project_id: number; project_name: string; total_score: number }[]
}

export interface LeaderboardResponse {
  period_type: string
  period_key: string
  generated_at: string | null
  entries: LeaderboardEntry[]
}

export interface LeaderboardEntry {
  rank: number | null
  user_email: string
  total_score: number
  hook_adopted: boolean
  lines_added: number
  commit_count: number
}

/** Loop health: whether Hook has reported sessions in the last N days. */
export interface LoopHealthResponse {
  loop_ok: boolean
  days_checked: number
  last_session_at: string | null
  sessions_count_7d: number
  members_with_sessions_7d: number
}

export interface IncentiveRule {
  id: number
  name: string
  period_type: string
  weights: Record<string, number>
  caps: Record<string, number>
  enabled: boolean
  created_at: string | null
  updated_at: string | null
}

export interface IncentiveRuleCreate {
  name: string
  period_type?: string
  weights: Record<string, number>
  caps?: Record<string, number>
  enabled?: boolean
}

export interface IncentiveRuleUpdate {
  name?: string
  period_type?: string
  weights?: Record<string, number>
  caps?: Record<string, number>
  enabled?: boolean
}
