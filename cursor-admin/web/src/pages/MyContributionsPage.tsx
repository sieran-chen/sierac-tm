import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getISOWeek, getISOWeekYear, subWeeks, subMonths } from 'date-fns'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api, Member, MyContributionScore } from '../api/client'

const WEIGHT_LABELS: Record<string, string> = {
  lines_added: '代码行数',
  commit_count: 'Commit 数',
  session_duration_hours: '会话时长',
  agent_requests: 'Agent 请求',
  files_changed: '修改文件数',
}

function getWeekKey(d: Date): string {
  return `${getISOWeekYear(d)}-W${String(getISOWeek(d)).padStart(2, '0')}`
}

function getMonthKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function lastNWeekKeys(n: number): string[] {
  return Array.from({ length: n }, (_, i) => getWeekKey(subWeeks(new Date(), i)))
}

function lastNMonthKeys(n: number): string[] {
  return Array.from({ length: n }, (_, i) => getMonthKey(subMonths(new Date(), i)))
}

export default function MyContributionsPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [email, setEmail] = useState('')
  const [periodType, setPeriodType] = useState<'weekly' | 'monthly'>('weekly')
  const [periodKey, setPeriodKey] = useState('')
  const [score, setScore] = useState<MyContributionScore | null>(null)
  const [history, setHistory] = useState<{ period_key: string; total_score: number }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const weekOptions = lastNWeekKeys(12)
  const monthOptions = lastNMonthKeys(12)
  const periodOptions = periodType === 'weekly' ? weekOptions : monthOptions
  const effectiveKey = periodKey || periodOptions[0] || ''

  useEffect(() => { api.members().then(setMembers) }, [])

  useEffect(() => {
    if (!email.trim() || !effectiveKey) {
      setScore(null)
      setHistory([])
      return
    }
    setLoading(true)
    setError(null)
    api.myContributions({ email: email.trim(), period_type: periodType, period_key: effectiveKey })
      .then((res) => {
        if (res && typeof res === 'object' && 'total_score' in res) {
          setScore(res as MyContributionScore)
        } else {
          setScore(null)
        }
      })
      .catch((e) => { setError(e.message); setScore(null) })
      .finally(() => setLoading(false))
  }, [email, periodType, effectiveKey])

  useEffect(() => {
    if (!email.trim()) {
      setHistory([])
      return
    }
    const keys = periodType === 'weekly' ? lastNWeekKeys(8) : lastNMonthKeys(8)
    Promise.all(
      keys.map((key) =>
        api.myContributions({ email: email.trim(), period_type: periodType, period_key: key })
          .then((res) => (res && typeof res === 'object' && 'total_score' in res ? (res as MyContributionScore).total_score : 0))
          .catch(() => 0)
      )
    ).then((scores) => setHistory(keys.map((period_key, i) => ({ period_key, total_score: scores[i] }))))
  }, [email, periodType])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">我的贡献</h1>
      <p className="text-sm text-gray-600">
        查看个人贡献得分、排名与各维度明细；未接入 Hook 时会话维度为 0，且不参与排行。
      </p>

      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">成员</label>
          <select
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm min-w-[200px]"
          >
            <option value="">请选择成员</option>
            {members.map((m) => (
              <option key={m.email} value={m.email}>{m.name || m.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">周期</label>
          <select
            value={periodType}
            onChange={(e) => { setPeriodType(e.target.value as 'weekly' | 'monthly'); setPeriodKey('') }}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="weekly">周</option>
            <option value="monthly">月</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">周期键</label>
          <select
            value={periodKey || periodOptions[0]}
            onChange={(e) => setPeriodKey(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm min-w-[100px]"
          >
            {periodOptions.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 text-red-700 px-4 py-2 text-sm">{error}</div>
      )}

      {!email && (
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-8 text-center text-gray-500">
          请选择成员查看其贡献得分
        </div>
      )}

      {email && loading && <div className="text-sm text-gray-500">加载中…</div>}

      {email && !loading && score && (
        <>
          {!score.hook_adopted && (
            <div className="rounded-lg bg-amber-50 text-amber-800 px-4 py-2 text-sm">
              本周期未检测到 Hook 上报，会话维度得分为 0，且不参与排行。在已立项项目目录下使用 Cursor 并完成 Agent 会话后，下次计算将计入。
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="text-xs text-gray-500 mb-1">总分</div>
              <div className="text-2xl font-bold text-brand-600">{Number(score.total_score).toFixed(2)}</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="text-xs text-gray-500 mb-1">排名</div>
              <div className="text-2xl font-bold">{score.rank != null ? `第 ${score.rank} 名` : '—'}</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="text-xs text-gray-500 mb-1">Hook 状态</div>
              <div className="text-lg font-medium">{score.hook_adopted ? '已接入' : '未接入'}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 text-sm font-medium text-gray-600">维度得分</div>
            <div className="px-5 py-3 flex flex-wrap gap-4">
              {Object.entries(score.score_breakdown || {}).map(([k, v]) => (
                <span key={k} className="px-3 py-1 bg-gray-100 rounded text-sm">
                  {WEIGHT_LABELS[k] ?? k}: {Number(v).toFixed(2)}
                </span>
              ))}
              {Object.keys(score.score_breakdown || {}).length === 0 && (
                <span className="text-gray-400 text-sm">暂无维度数据</span>
              )}
            </div>
          </div>

          {score.projects && score.projects.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 text-sm font-medium text-gray-600">项目分布</div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-5 py-2 text-left">项目</th>
                    <th className="px-4 py-2 text-right">得分</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {score.projects.map((p) => (
                    <tr key={p.project_id}>
                      <td className="px-5 py-2.5">
                        <Link to={`/projects/${p.project_id}`} className="text-brand-600 hover:underline">
                          {p.project_name}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 text-right font-medium">{Number(p.total_score).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {history.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 text-sm font-medium text-gray-600">近 8 期趋势</div>
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={[...history].reverse()}>
                    <XAxis dataKey="period_key" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => [Number(v).toFixed(2), '总分']} />
                    <Line type="monotone" dataKey="total_score" stroke="var(--brand-500, #6366f1)" strokeWidth={2} dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}

      {email && !loading && !score && (
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-8 text-center text-gray-500">
          该周期暂无贡献得分数据（可能尚未执行计算或该成员无数据）
        </div>
      )}
    </div>
  )
}
