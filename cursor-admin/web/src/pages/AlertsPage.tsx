import { useEffect, useState } from 'react'
import { Plus, Trash2, Edit2, Check, X } from 'lucide-react'
import { api, AlertRule, NotifyChannel } from '../api/client'

const METRICS = [
  { value: 'daily_agent_requests', label: '每日 Agent 请求数' },
  { value: 'daily_spend_cents',    label: '当前周期支出（分）' },
  { value: 'monthly_spend_cents',  label: '月度支出（分）' },
]

const emptyRule = (): Omit<AlertRule, 'id' | 'created_at'> => ({
  name: '',
  metric: 'daily_agent_requests',
  scope: 'user',
  target_email: '',
  threshold: 100,
  notify_channels: [],
  enabled: true,
})

export default function AlertsPage() {
  const [rules, setRules] = useState<AlertRule[]>([])
  const [editing, setEditing] = useState<(Omit<AlertRule, 'id' | 'created_at'> & { id?: number }) | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    api.alertRules()
      .then(setRules)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const save = async () => {
    if (!editing) return
    if (editing.id) {
      await api.updateAlertRule(editing.id, editing)
    } else {
      await api.createAlertRule(editing)
    }
    setEditing(null)
    load()
  }

  const del = async (id: number) => {
    if (!confirm('确认删除此告警规则？')) return
    await api.deleteAlertRule(id)
    load()
  }

  const addChannel = () => {
    if (!editing) return
    setEditing({ ...editing, notify_channels: [...editing.notify_channels, { type: 'email', address: '' }] })
  }

  const updateChannel = (i: number, ch: NotifyChannel) => {
    if (!editing) return
    const chs = [...editing.notify_channels]
    chs[i] = ch
    setEditing({ ...editing, notify_channels: chs })
  }

  const removeChannel = (i: number) => {
    if (!editing) return
    setEditing({ ...editing, notify_channels: editing.notify_channels.filter((_, idx) => idx !== i) })
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">告警规则</h1>
        <button onClick={() => setEditing(emptyRule())}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600">
          <Plus size={15} /> 新建规则
        </button>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中…</p>}
      {error && <p className="text-sm text-red-600">加载失败：{error}</p>}

      {/* 规则列表 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">规则名称</th>
              <th className="px-4 py-2 text-left">指标</th>
              <th className="px-4 py-2 text-left">范围</th>
              <th className="px-4 py-2 text-right">阈值</th>
              <th className="px-4 py-2 text-center">状态</th>
              <th className="px-4 py-2 text-center">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-5 py-2.5 font-medium">{r.name}</td>
                <td className="px-4 py-2.5 text-gray-600">
                  {METRICS.find(m => m.value === r.metric)?.label ?? r.metric}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {r.scope === 'user' ? r.target_email : '全团队'}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">{r.threshold}</td>
                <td className="px-4 py-2.5 text-center">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    r.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {r.enabled ? '启用' : '停用'}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <button onClick={() => setEditing({ ...r })}
                      className="p-1 text-gray-400 hover:text-brand-600"><Edit2 size={14} /></button>
                    <button onClick={() => del(r.id)}
                      className="p-1 text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr><td colSpan={6} className="px-5 py-6 text-center text-gray-400">暂无告警规则</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4">
            <h2 className="text-base font-semibold">{editing.id ? '编辑告警规则' : '新建告警规则'}</h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">规则名称</label>
                <input value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">指标</label>
                <select value={editing.metric} onChange={e => setEditing({ ...editing, metric: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
                  {METRICS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">阈值</label>
                <input type="number" value={editing.threshold}
                  onChange={e => setEditing({ ...editing, threshold: Number(e.target.value) })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">范围</label>
                <select value={editing.scope} onChange={e => setEditing({ ...editing, scope: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
                  <option value="user">指定成员</option>
                  <option value="team">全团队</option>
                </select>
              </div>
              {editing.scope === 'user' && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">成员邮箱</label>
                  <input value={editing.target_email ?? ''}
                    onChange={e => setEditing({ ...editing, target_email: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
                </div>
              )}
              <div className="col-span-2 flex items-center gap-2">
                <input type="checkbox" id="enabled" checked={editing.enabled}
                  onChange={e => setEditing({ ...editing, enabled: e.target.checked })} />
                <label htmlFor="enabled" className="text-sm text-gray-600">启用此规则</label>
              </div>
            </div>

            {/* 通知渠道 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500 font-medium">通知渠道</span>
                <button onClick={addChannel} className="text-xs text-brand-600 hover:underline">+ 添加渠道</button>
              </div>
              <div className="space-y-2">
                {editing.notify_channels.map((ch, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <select value={ch.type} onChange={e => updateChannel(i, { ...ch, type: e.target.value as 'email' | 'webhook' })}
                      className="border border-gray-300 rounded-lg px-2 py-1 text-xs">
                      <option value="email">邮件</option>
                      <option value="webhook">Webhook</option>
                    </select>
                    {ch.type === 'email' ? (
                      <input value={ch.address ?? ''} placeholder="收件邮箱"
                        onChange={e => updateChannel(i, { ...ch, address: e.target.value })}
                        className="flex-1 border border-gray-300 rounded-lg px-2 py-1 text-xs" />
                    ) : (
                      <input value={ch.url ?? ''} placeholder="Webhook URL（企业微信/钉钉等）"
                        onChange={e => updateChannel(i, { ...ch, url: e.target.value })}
                        className="flex-1 border border-gray-300 rounded-lg px-2 py-1 text-xs" />
                    )}
                    <button onClick={() => removeChannel(i)} className="text-gray-400 hover:text-red-500"><X size={14} /></button>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setEditing(null)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
                取消
              </button>
              <button onClick={save}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-brand-500 text-white rounded-lg hover:bg-brand-600">
                <Check size={14} /> 保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
