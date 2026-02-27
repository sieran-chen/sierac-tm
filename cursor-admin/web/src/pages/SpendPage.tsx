import { useEffect, useState } from 'react'
import { api, SpendRow } from '../api/client'

export default function SpendPage() {
  const [rows, setRows] = useState<SpendRow[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.spend()
      .then(setRows)
      .catch((e) => { setError((e as Error).message); setRows([]) })
      .finally(() => setLoading(false))
  }, [])

  const filtered = rows.filter(r =>
    r.email.includes(search) || (r.name ?? '').includes(search)
  )

  const total = rows.reduce((s, r) => s + r.spend_cents, 0)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">支出管理</h1>
        <span className="text-sm text-gray-500">
          本计费周期团队总支出：<strong className="text-gray-800">${(total / 100).toFixed(2)}</strong>
        </span>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中…</p>}
      {error && (
        <p className="text-sm text-red-600">
          加载失败：{error}。请检查 Cursor API 配置（CURSOR_API_TOKEN）与同步任务是否正常执行。
        </p>
      )}

      <input value={search} onChange={e => setSearch(e.target.value)}
        placeholder="搜索成员邮箱或姓名…"
        className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-72" />

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">成员</th>
              <th className="px-4 py-2 text-right">本周期支出</th>
              <th className="px-4 py-2 text-right">按量请求数</th>
              <th className="px-4 py-2 text-right">月度上限</th>
              <th className="px-4 py-2 text-right">计费周期开始</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map(r => (
              <tr key={r.email} className="hover:bg-gray-50">
                <td className="px-5 py-2.5">
                  <div className="font-medium">{r.name || r.email}</div>
                  {r.name && <div className="text-xs text-gray-400">{r.email}</div>}
                </td>
                <td className="px-4 py-2.5 text-right font-semibold">
                  ${(r.spend_cents / 100).toFixed(2)}
                </td>
                <td className="px-4 py-2.5 text-right">{r.fast_premium_requests.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right text-gray-500">
                  {r.monthly_limit_dollars != null ? `$${r.monthly_limit_dollars}` : '无限制'}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">{r.billing_cycle_start}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-6 text-center">
                  <p className="text-gray-500">暂无支出数据</p>
                  <p className="text-xs text-gray-400 mt-1">可能当前套餐未提供支出接口，或同步尚未完成。请检查 Cursor API 配置与采集服务同步任务。详见《数据可见性条件与排查》。</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
