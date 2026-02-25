import { useEffect, useState } from 'react'
import { format } from 'date-fns'
import { api, AlertEvent } from '../api/client'

export default function EventsPage() {
  const [events, setEvents] = useState<AlertEvent[]>([])

  useEffect(() => { api.alertEvents(100).then(setEvents) }, [])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">告警历史</h1>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">触发时间</th>
              <th className="px-5 py-2 text-left">规则名称</th>
              <th className="px-4 py-2 text-left">指标</th>
              <th className="px-4 py-2 text-right">当前值</th>
              <th className="px-4 py-2 text-right">阈值</th>
              <th className="px-4 py-2 text-left">详情</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {events.map(e => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-5 py-2.5 text-gray-500">
                  {format(new Date(e.triggered_at), 'MM-dd HH:mm')}
                </td>
                <td className="px-5 py-2.5 font-medium">{e.rule_name}</td>
                <td className="px-4 py-2.5 text-gray-600">{e.metric}</td>
                <td className="px-4 py-2.5 text-right font-semibold text-red-600">
                  {e.metric_value}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">{e.threshold}</td>
                <td className="px-4 py-2.5 text-xs text-gray-400 font-mono">
                  {JSON.stringify(e.detail)}
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr><td colSpan={6} className="px-5 py-6 text-center text-gray-400">暂无告警记录</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
