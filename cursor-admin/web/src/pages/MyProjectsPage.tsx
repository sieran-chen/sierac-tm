import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Member, MyContributionRow } from '../api/client'

type ProjectSummary = {
  project_id: number
  project_name: string
  commit_count: number
  lines_added: number
  lines_removed: number
  files_changed: number
}

function aggregateByProject(rows: MyContributionRow[]): ProjectSummary[] {
  const byId = new Map<number, ProjectSummary>()
  for (const r of rows) {
    const cur = byId.get(r.project_id)
    if (!cur) {
      byId.set(r.project_id, {
        project_id: r.project_id,
        project_name: r.project_name,
        commit_count: r.commit_count,
        lines_added: r.lines_added,
        lines_removed: r.lines_removed,
        files_changed: r.files_changed,
      })
    } else {
      cur.commit_count += r.commit_count
      cur.lines_added += r.lines_added
      cur.lines_removed += r.lines_removed
      cur.files_changed += r.files_changed
    }
  }
  return Array.from(byId.values()).sort((a, b) => b.lines_added - a.lines_added)
}

export default function MyProjectsPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [email, setEmail] = useState('')
  const [rows, setRows] = useState<MyContributionRow[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.members().then(setMembers)
  }, [])

  useEffect(() => {
    if (!email.trim()) {
      setRows([])
      return
    }
    setLoading(true)
    api.myContributions({ email: email.trim() })
      .then((res) => setRows(Array.isArray(res) ? res : []))
      .finally(() => setLoading(false))
  }, [email])

  const summary = aggregateByProject(rows)

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">我的项目</h1>
      <p className="text-sm text-gray-600">
        按成员查看其参与的项目及 Git 贡献摘要（数据来自 Git 采集，未配置时为空）。
      </p>

      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-500">成员</label>
        <select
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm min-w-[200px]"
        >
          <option value="">请选择成员</option>
          {members.map((m) => (
            <option key={m.email} value={m.email}>
              {m.name || m.email}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中…</p>}

      {!loading && email && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-5 py-2 text-left">项目</th>
                <th className="px-4 py-2 text-right">提交数</th>
                <th className="px-4 py-2 text-right">新增行</th>
                <th className="px-4 py-2 text-right">删除行</th>
                <th className="px-4 py-2 text-right">变更文件</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-6 text-center text-gray-400">
                    该成员暂无 Git 贡献记录
                  </td>
                </tr>
              ) : (
                summary.map((s) => (
                  <tr key={s.project_id} className="hover:bg-gray-50">
                    <td className="px-5 py-2.5 font-medium">
                      <Link to={`/projects/${s.project_id}`} className="text-brand-600 hover:underline">
                        {s.project_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-right">{s.commit_count}</td>
                    <td className="px-4 py-2.5 text-right text-green-600">+{s.lines_added}</td>
                    <td className="px-4 py-2.5 text-right text-red-600">-{s.lines_removed}</td>
                    <td className="px-4 py-2.5 text-right">{s.files_changed}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
