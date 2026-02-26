import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api, ProjectSummary } from '../api/client'

function formatDuration(seconds: number): string {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<ProjectSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.projectSummary(Number(id))
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [id])

  if (error) {
    return (
      <div className="p-6">
        <Link to="/projects" className="inline-flex items-center gap-2 text-sm text-brand-600 hover:underline mb-4">
          <ArrowLeft size={14} /> 返回项目列表
        </Link>
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-6">
        <Link to="/projects" className="inline-flex items-center gap-2 text-sm text-brand-600 hover:underline mb-4">
          <ArrowLeft size={14} /> 返回项目列表
        </Link>
        <p className="text-gray-500">加载中…</p>
      </div>
    )
  }

  const { project, session_count, total_duration_seconds, participants, contributions } = data

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 text-sm text-brand-600 hover:underline"
        >
          <ArrowLeft size={14} /> 返回项目列表
        </Link>
        <h1 className="text-xl font-semibold">{project.name}</h1>
      </div>

      {/* 基本信息 */}
      <section className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-3">基本信息</h2>
        <dl className="grid grid-cols-1 gap-2 text-sm">
          {project.description && (
            <>
              <dt className="text-gray-500">描述</dt>
              <dd className="text-gray-900">{project.description}</dd>
            </>
          )}
          {project.repo_url && (
            <>
              <dt className="text-gray-500">仓库</dt>
              <dd className="text-gray-900 font-mono text-xs break-all">{project.repo_url}</dd>
            </>
          )}
          {(project.workspace_rules?.length ?? 0) > 0 && (
            <>
              <dt className="text-gray-500">工作目录规则</dt>
              <dd className="text-gray-900 font-mono text-xs">
                {(project.workspace_rules ?? []).join(', ')}
              </dd>
            </>
          )}
          {(project.member_emails?.length ?? 0) > 0 && (
            <>
              <dt className="text-gray-500">参与成员</dt>
              <dd className="text-gray-900 text-xs">{(project.member_emails ?? []).join(', ')}</dd>
            </>
          )}
        </dl>
      </section>

      {/* 成本面板 */}
      <section className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-3">成本（本周期）</h2>
        <div className="flex gap-8">
          <div>
            <span className="text-2xl font-semibold text-gray-900">{session_count}</span>
            <span className="text-sm text-gray-500 ml-1">次会话</span>
          </div>
          <div>
            <span className="text-2xl font-semibold text-gray-900">
              {formatDuration(total_duration_seconds)}
            </span>
            <span className="text-sm text-gray-500 ml-1">总时长</span>
          </div>
        </div>
      </section>

      {/* 参与面板 */}
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <h2 className="text-sm font-medium text-gray-700 p-5 pb-2">参与成员</h2>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">成员</th>
              <th className="px-4 py-2 text-right">会话数</th>
              <th className="px-4 py-2 text-right">总时长</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {participants.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-5 py-4 text-center text-gray-400">
                  暂无参与数据
                </td>
              </tr>
            ) : (
              participants.map((p) => (
                <tr key={p.user_email} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5 font-medium">{p.user_email}</td>
                  <td className="px-4 py-2.5 text-right">{p.session_count}</td>
                  <td className="px-4 py-2.5 text-right">{formatDuration(p.total_seconds)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      {/* 贡献面板 */}
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <h2 className="text-sm font-medium text-gray-700 p-5 pb-2">Git 贡献</h2>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">作者</th>
              <th className="px-4 py-2 text-left">日期</th>
              <th className="px-4 py-2 text-right">提交数</th>
              <th className="px-4 py-2 text-right">新增行</th>
              <th className="px-4 py-2 text-right">删除行</th>
              <th className="px-4 py-2 text-right">变更文件</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {contributions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-4 text-center text-gray-400">
                  暂无贡献数据（需配置 Git 采集）
                </td>
              </tr>
            ) : (
              contributions.map((c, i) => (
                <tr key={`${c.author_email}-${c.commit_date}-${i}`} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5 font-medium">{c.author_email}</td>
                  <td className="px-4 py-2.5 text-gray-600">{c.commit_date}</td>
                  <td className="px-4 py-2.5 text-right">{c.commit_count}</td>
                  <td className="px-4 py-2.5 text-right text-green-600">+{c.lines_added}</td>
                  <td className="px-4 py-2.5 text-right text-red-600">-{c.lines_removed}</td>
                  <td className="px-4 py-2.5 text-right">{c.files_changed}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}
