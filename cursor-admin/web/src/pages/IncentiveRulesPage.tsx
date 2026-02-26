import { useEffect, useState } from 'react'
import { api, IncentiveRule, IncentiveRuleUpdate } from '../api/client'

const WEIGHT_KEYS = ['lines_added', 'commit_count', 'session_duration_hours', 'agent_requests', 'files_changed'] as const
const WEIGHT_LABELS: Record<string, string> = {
  lines_added: '代码行数',
  commit_count: 'Commit 数',
  session_duration_hours: '会话时长(h)',
  agent_requests: 'Agent 请求',
  files_changed: '修改文件数',
}

export default function IncentiveRulesPage() {
  const [rules, setRules] = useState<IncentiveRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editWeights, setEditWeights] = useState<Record<string, number>>({})
  const [editCaps, setEditCaps] = useState<Record<string, number | undefined>>({})
  const [recalculatingId, setRecalculatingId] = useState<number | null>(null)

  useEffect(() => {
    api.incentiveRules()
      .then(setRules)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const startEdit = (r: IncentiveRule) => {
    setEditingId(r.id)
    setEditWeights({ ...(r.weights || {}) })
    setEditCaps({ ...(r.caps || {}) })
  }

  const cancelEdit = () => {
    setEditingId(null)
  }

  const normalizeWeights = (w: Record<string, number>): Record<string, number> => {
    const sum = Object.values(w).reduce((a, b) => a + b, 0)
    if (sum <= 0) return w
    const out: Record<string, number> = {}
    for (const k of Object.keys(w)) {
      out[k] = Math.round((w[k] / sum) * 100) / 100
    }
    return out
  }

  const setWeight = (key: string, raw: number) => {
    const next = { ...editWeights, [key]: Math.max(0, Math.min(1, raw)) }
    setEditWeights(normalizeWeights(next))
  }

  const saveRule = async () => {
    if (editingId == null) return
    setError(null)
    try {
      const capsFiltered = Object.fromEntries(
        Object.entries(editCaps).filter(([, v]) => v != null && typeof v === 'number')
      ) as Record<string, number>
      const body: IncentiveRuleUpdate = { weights: editWeights, caps: Object.keys(capsFiltered).length ? capsFiltered : {} }
      await api.updateIncentiveRule(editingId, body)
      const list = await api.incentiveRules()
      setRules(list)
      setEditingId(null)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const recalculate = async (id: number) => {
    setRecalculatingId(id)
    setError(null)
    try {
      await api.recalculateIncentiveRule(id)
      const list = await api.incentiveRules()
      setRules(list)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRecalculatingId(null)
    }
  }

  if (loading) return <div className="p-6 text-gray-500">加载中…</div>

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">激励规则配置</h1>
      <p className="text-sm text-gray-600">
        配置贡献度权重与上限；修改后点击「重新计算」使当前周期生效。
      </p>

      {error && (
        <div className="rounded-lg bg-red-50 text-red-700 px-4 py-2 text-sm">{error}</div>
      )}

      <div className="space-y-4">
        {rules.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
              <div>
                <span className="font-medium">{r.name}</span>
                <span className="ml-2 text-xs text-gray-500">周期: {r.period_type}</span>
                {!r.enabled && <span className="ml-2 text-xs text-amber-600">已停用</span>}
              </div>
              <div className="flex gap-2">
                {editingId === r.id ? (
                  <>
                    <button
                      type="button"
                      onClick={saveRule}
                      className="px-3 py-1 rounded-lg bg-brand-500 text-white text-sm"
                    >
                      保存
                    </button>
                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="px-3 py-1 rounded-lg border border-gray-300 text-sm"
                    >
                      取消
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => startEdit(r)}
                      disabled={!r.enabled}
                      className="px-3 py-1 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50"
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      onClick={() => recalculate(r.id)}
                      disabled={!r.enabled || recalculatingId === r.id}
                      className="px-3 py-1 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50"
                    >
                      {recalculatingId === r.id ? '计算中…' : '重新计算'}
                    </button>
                  </>
                )}
              </div>
            </div>
            <div className="px-5 py-4">
              {editingId === r.id ? (
                <div className="space-y-4">
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-2">权重（总和将归一化）</div>
                    <div className="space-y-2">
                      {WEIGHT_KEYS.map((key) => (
                        <div key={key} className="flex items-center gap-3">
                          <label className="w-32 text-sm">{WEIGHT_LABELS[key] ?? key}</label>
                          <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={editWeights[key] ?? 0}
                            onChange={(e) => setWeight(key, Number(e.target.value))}
                            className="flex-1 max-w-xs"
                          />
                          <span className="text-sm w-12">{(editWeights[key] ?? 0).toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-2">上限（可选）</div>
                    <div className="flex flex-wrap gap-4">
                      <label className="flex items-center gap-2 text-sm">
                        会话时长/天(h)
                        <input
                          type="number"
                          min={0}
                          step={1}
                          value={editCaps['session_duration_hours_per_day'] ?? ''}
                          onChange={(e) =>
                            setEditCaps((c) => ({
                              ...c,
                              session_duration_hours_per_day: e.target.value ? Number(e.target.value) : undefined,
                            }))
                          }
                          className="w-20 border border-gray-300 rounded px-2 py-1"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        Agent 请求/天
                        <input
                          type="number"
                          min={0}
                          step={10}
                          value={editCaps['agent_requests_per_day'] ?? ''}
                          onChange={(e) =>
                            setEditCaps((c) => ({
                              ...c,
                              agent_requests_per_day: e.target.value ? Number(e.target.value) : undefined,
                            }))
                          }
                          className="w-24 border border-gray-300 rounded px-2 py-1"
                        />
                      </label>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-6">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">权重</div>
                    <div className="flex gap-2 flex-wrap">
                      {Object.entries(r.weights || {}).map(([k, v]) => (
                        <span key={k} className="px-2 py-0.5 bg-gray-100 rounded text-sm">
                          {WEIGHT_LABELS[k] ?? k}: {(Number(v) * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  </div>
                  {Object.keys(r.caps || {}).length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">上限</div>
                      <div className="flex gap-2 flex-wrap">
                        {Object.entries(r.caps || {}).map(([k, v]) => (
                          <span key={k} className="px-2 py-0.5 bg-gray-100 rounded text-sm">
                            {k}: {v}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {rules.length === 0 && (
          <div className="rounded-xl border border-gray-200 bg-white px-5 py-8 text-center text-gray-500">
            暂无规则；默认规则由迁移创建，若未看到请检查数据库。
          </div>
        )}
      </div>
    </div>
  )
}
