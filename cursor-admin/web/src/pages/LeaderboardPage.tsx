import { useEffect, useState } from 'react'
import { getISOWeek, getISOWeekYear, subWeeks, subMonths } from 'date-fns'
import { api, LeaderboardResponse } from '../api/client'

function getWeekKey(d: Date): string {
  return `${getISOWeekYear(d)}-W${String(getISOWeek(d)).padStart(2, '0')}`
}

function getMonthKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function lastNWeekKeys(n: number): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = []
  for (let i = 0; i < n; i++) {
    const d = subWeeks(new Date(), i)
    const key = getWeekKey(d)
    out.push({ value: key, label: key })
  }
  return out
}

function lastNMonthKeys(n: number): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = []
  for (let i = 0; i < n; i++) {
    const d = subMonths(new Date(), i)
    const key = getMonthKey(d)
    out.push({ value: key, label: key })
  }
  return out
}

export default function LeaderboardPage() {
  const [periodType, setPeriodType] = useState<'weekly' | 'monthly'>('weekly')
  const [periodKey, setPeriodKey] = useState('')
  const [hookOnly, setHookOnly] = useState(true)
  const [data, setData] = useState<LeaderboardResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const weekOptions = lastNWeekKeys(12)
  const monthOptions = lastNMonthKeys(12)
  const options = periodType === 'weekly' ? weekOptions : monthOptions
  const effectiveKey = periodKey || options[0]?.value || ''

  useEffect(() => {
    if (!effectiveKey) return
    setLoading(true)
    setError(null)
    api.leaderboard({ period_type: periodType, period_key: effectiveKey, hook_only: hookOnly })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [periodType, effectiveKey, hookOnly])

  useEffect(() => {
    if (!periodKey && options[0]) setPeriodKey(options[0].value)
  }, [periodType, options])

  const exportCsv = () => {
    if (!data?.entries.length) return
    const headers = ['排名', '成员', '总分', '已接入 Hook', '代码行数', 'Commit 数']
    const rows = data.entries.map((e) => [
      e.rank ?? '',
      e.user_email,
      e.total_score.toFixed(2),
      e.hook_adopted ? '是' : '否',
      e.lines_added,
      e.commit_count,
    ])
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `leaderboard-${data.period_type}-${data.period_key}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">贡献排行榜</h1>
      <p className="text-sm text-gray-600">
        按周期展示成员贡献得分排名；仅已接入 Hook 的成员参与排行（可切换显示全部）。
      </p>

      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">周期类型</label>
          <select
            value={periodType}
            onChange={(e) => {
              setPeriodType(e.target.value as 'weekly' | 'monthly')
              setPeriodKey('')
            }}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="weekly">周</option>
            <option value="monthly">月</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">周期</label>
          <select
            value={periodKey}
            onChange={(e) => setPeriodKey(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm min-w-[120px]"
          >
            {options.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={hookOnly}
            onChange={(e) => setHookOnly(e.target.checked)}
            className="rounded border-gray-300"
          />
          仅已接入 Hook
        </label>
        <button
          type="button"
          onClick={exportCsv}
          disabled={!data?.entries?.length}
          className="px-4 py-1.5 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          导出 CSV
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 text-red-700 px-4 py-2 text-sm">{error}</div>
      )}

      {loading && <div className="text-sm text-gray-500">加载中…</div>}

      {!loading && data && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-600">
              {data.period_type === 'weekly' ? '周' : '月'} {data.period_key}
              {data.generated_at && (
                <span className="ml-2 text-gray-400 text-xs">生成于 {data.generated_at.slice(0, 19).replace('T', ' ')}</span>
              )}
            </span>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-5 py-2 text-left">排名</th>
                <th className="px-5 py-2 text-left">成员</th>
                <th className="px-4 py-2 text-right">总分</th>
                <th className="px-4 py-2 text-right">代码行数</th>
                <th className="px-4 py-2 text-right">Commit 数</th>
                <th className="px-4 py-2 text-center">Hook</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.entries.map((e, i) => (
                <tr key={e.user_email} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5 font-medium">{e.rank ?? '—'}</td>
                  <td className="px-5 py-2.5">{e.user_email}</td>
                  <td className="px-4 py-2.5 text-right font-semibold">{Number(e.total_score).toFixed(2)}</td>
                  <td className="px-4 py-2.5 text-right">{e.lines_added.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right">{e.commit_count}</td>
                  <td className="px-4 py-2.5 text-center">
                    {e.hook_adopted ? <span className="text-green-600">已接入</span> : <span className="text-gray-400">未接入</span>}
                  </td>
                </tr>
              ))}
              {data.entries.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-500">
                    暂无排行数据。请确认该周期已执行过贡献度计算，且成员已接入 Hook。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
