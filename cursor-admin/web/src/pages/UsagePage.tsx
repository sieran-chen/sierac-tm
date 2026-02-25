import { useEffect, useState } from 'react'
import { format, subDays } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { api, DailyUsage, Member } from '../api/client'

function fmt(d: Date) { return format(d, 'yyyy-MM-dd') }

export default function UsagePage() {
  const [members, setMembers] = useState<Member[]>([])
  const [usage, setUsage] = useState<DailyUsage[]>([])
  const [email, setEmail] = useState('')
  const [start, setStart] = useState(fmt(subDays(new Date(), 14)))
  const [end, setEnd] = useState(fmt(new Date()))
  const [loading, setLoading] = useState(false)

  useEffect(() => { api.members().then(setMembers) }, [])

  useEffect(() => {
    setLoading(true)
    api.dailyUsage({ email: email || undefined, start, end })
      .then(setUsage)
      .finally(() => setLoading(false))
  }, [email, start, end])

  // 聚合：按 day 汇总（多用户时叠加）
  const chartData = Object.values(
    usage.reduce<Record<string, { day: string; agent: number; chat: number; tabs: number }>>((acc, r) => {
      if (!acc[r.day]) acc[r.day] = { day: r.day, agent: 0, chat: 0, tabs: 0 }
      acc[r.day].agent += r.agent_requests
      acc[r.day].chat  += r.chat_requests
      acc[r.day].tabs  += r.total_tabs_accepted
      return acc
    }, {})
  ).sort((a, b) => a.day.localeCompare(b.day))

  // 按用户汇总
  const byUser = Object.values(
    usage.reduce<Record<string, { email: string; agent: number; chat: number; lines: number; usageBased: number }>>((acc, r) => {
      if (!acc[r.email]) acc[r.email] = { email: r.email, agent: 0, chat: 0, lines: 0, usageBased: 0 }
      acc[r.email].agent     += r.agent_requests
      acc[r.email].chat      += r.chat_requests
      acc[r.email].lines     += r.total_lines_added
      acc[r.email].usageBased += r.usage_based_reqs
      return acc
    }, {})
  ).sort((a, b) => b.agent - a.agent)

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">用量总览</h1>

      {/* 筛选 */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">成员</label>
          <select
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">全部成员</option>
            {members.map(m => (
              <option key={m.email} value={m.email}>{m.name || m.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">开始日期</label>
          <input type="date" value={start} onChange={e => setStart(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">结束日期</label>
          <input type="date" value={end} onChange={e => setEnd(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
        </div>
      </div>

      {/* 趋势图 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-600 mb-4">每日请求趋势</h2>
        {loading ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">加载中…</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barSize={12}>
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="agent" name="Agent 请求" fill="#4f6ef7" radius={[3,3,0,0]} />
              <Bar dataKey="chat"  name="Chat 请求"  fill="#a5b4fc" radius={[3,3,0,0]} />
              <Bar dataKey="tabs"  name="Tab 采纳"   fill="#6ee7b7" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 按用户明细 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100">
          <h2 className="text-sm font-medium text-gray-600">按成员汇总（所选时段）</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">成员</th>
              <th className="px-4 py-2 text-right">Agent 请求</th>
              <th className="px-4 py-2 text-right">Chat 请求</th>
              <th className="px-4 py-2 text-right">新增代码行</th>
              <th className="px-4 py-2 text-right">按量计费次数</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {byUser.map(u => (
              <tr key={u.email} className="hover:bg-gray-50">
                <td className="px-5 py-2.5 font-medium">{u.email}</td>
                <td className="px-4 py-2.5 text-right">{u.agent.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right">{u.chat.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right">{u.lines.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right">{u.usageBased.toLocaleString()}</td>
              </tr>
            ))}
            {byUser.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-center text-gray-400">暂无数据</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
