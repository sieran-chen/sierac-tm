import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { format, subDays } from 'date-fns'
import { api, Member, SessionSummaryByProjectRow, SessionRow, SessionsResponse, Project } from '../api/client'

function fmt(d: Date) { return format(d, 'yyyy-MM-dd') }
function fmtDuration(sec: number | null) {
  if (!sec) return '—'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function WorkspacePage() {
  const [members, setMembers] = useState<Member[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [summaryByProject, setSummaryByProject] = useState<SessionSummaryByProjectRow[]>([])
  const [sessions, setSessions] = useState<SessionsResponse | null>(null)
  const [email, setEmail] = useState('')
  const [projectFilter, setProjectFilter] = useState<string>('')
  const [start, setStart] = useState(fmt(subDays(new Date(), 14)))
  const [end, setEnd] = useState(fmt(new Date()))
  const [page, setPage] = useState(1)
  const [tab, setTab] = useState<'summary' | 'detail'>('summary')

  useEffect(() => { api.members().then(setMembers) }, [])
  useEffect(() => { api.projects({ status: 'active' }).then(setProjects) }, [])

  useEffect(() => {
    api.sessionsSummaryByProject({ start, end }).then(setSummaryByProject)
  }, [start, end])

  useEffect(() => {
    if (tab !== 'detail') return
    api.sessions({ email: email || undefined, workspace: undefined, start, end, page })
      .then(setSessions)
  }, [tab, email, start, end, page])

  const projectNameById = new Map(projects.map((p) => [p.id, p.name]))
  const filteredSummary = summaryByProject.filter(
    (s) =>
      (!email || s.user_email === email) &&
      (!projectFilter || s.project_name === projectFilter)
  )

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">项目参与（按项目聚合）</h1>
      <p className="text-sm text-gray-600">
        按项目与成员汇总 Agent 会话；未关联项目的会话显示为「未归属」。
      </p>

      {/* 筛选 */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">成员</label>
          <select
            value={email}
            onChange={(e) => { setEmail(e.target.value); setPage(1) }}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">全部</option>
            {members.map((m) => (
              <option key={m.email} value={m.email}>{m.name || m.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">项目</label>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm min-w-[140px]"
          >
            <option value="">全部</option>
            {Array.from(new Set(summaryByProject.map((s) => s.project_name))).sort().map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">开始</label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">结束</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      <div className="flex gap-2">
        {(['summary', 'detail'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? 'bg-brand-500 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t === 'summary' ? '汇总视图' : '会话明细'}
          </button>
        ))}
      </div>

      {tab === 'summary' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 text-sm font-medium text-gray-600">
            按项目 + 成员汇总
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-5 py-2 text-left">项目</th>
                <th className="px-5 py-2 text-left">成员</th>
                <th className="px-4 py-2 text-right">会话数</th>
                <th className="px-4 py-2 text-right">累计时长</th>
                <th className="px-4 py-2 text-right">最近活跃</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredSummary.map((s, i) => (
                <tr key={`${s.project_id}-${s.user_email}-${i}`} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5 font-medium text-gray-800">
                    {s.project_id != null ? (
                      <Link to={`/projects/${s.project_id}`} className="text-brand-600 hover:underline">
                        {s.project_name}
                      </Link>
                    ) : (
                      <span className="text-gray-500">{s.project_name}</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-gray-600">{s.user_email}</td>
                  <td className="px-4 py-2.5 text-right">{s.session_count}</td>
                  <td className="px-4 py-2.5 text-right font-medium">{fmtDuration(s.total_seconds)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">
                    {s.last_seen ? format(new Date(s.last_seen), 'MM-dd HH:mm') : '—'}
                  </td>
                </tr>
              ))}
              {filteredSummary.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center">
                    <p className="text-gray-500 mb-1">暂无参与数据</p>
                    <p className="text-xs text-gray-400 max-w-md mx-auto">
                      数据来自 Hook 上报的 agent_sessions（含 project_id）。未关联项目的会话会显示为「未归属」。
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'detail' && sessions && sessions.data.length === 0 && sessions.total === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-gray-500 mb-1">暂无会话明细</p>
          <p className="text-xs text-gray-400 max-w-md mx-auto">
            请先在成员电脑安装 Hook 并触发一次 Agent 会话。
          </p>
        </div>
      )}

      {tab === 'detail' && sessions && (sessions.data.length > 0 || sessions.total > 0) && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-600">会话明细（共 {sessions.total} 条）</span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 text-xs border border-gray-300 rounded disabled:opacity-40"
              >
                上一页
              </button>
              <span className="px-2 py-1 text-xs text-gray-500">第 {page} 页</span>
              <button
                disabled={sessions.data.length < sessions.page_size}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 text-xs border border-gray-300 rounded disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-5 py-2 text-left">项目</th>
                <th className="px-5 py-2 text-left">成员</th>
                <th className="px-5 py-2 text-left">工作目录</th>
                <th className="px-4 py-2 text-right">时长</th>
                <th className="px-4 py-2 text-right">结束时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.data.map((s: SessionRow) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5">
                    {s.project_id != null ? (
                      <Link to={`/projects/${s.project_id}`} className="text-brand-600 hover:underline">
                        {projectNameById.get(s.project_id) ?? `#${s.project_id}`}
                      </Link>
                    ) : (
                      <span className="text-gray-500">未归属</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5">{s.user_email}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-gray-600 max-w-xs truncate">
                    {s.primary_workspace ?? s.workspace_roots?.[0] ?? '—'}
                  </td>
                  <td className="px-4 py-2.5 text-right">{fmtDuration(s.duration_seconds)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">
                    {format(new Date(s.ended_at), 'MM-dd HH:mm')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
