import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Archive, Edit2, Check, X, Copy, RefreshCw } from 'lucide-react'
import { api, Project, ProjectCreate, ProjectUpdate } from '../api/client'

function repoStatus(p: Project): 'created' | 'failed' | 'none' {
  const hasRepo = !!(p.gitlab_project_id || (p.repo_provider === 'github' && p.github_repo_full_name))
  if (hasRepo && p.hook_initialized) return 'created'
  if (hasRepo && !p.hook_initialized) return 'failed'
  return 'none'
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(() => {}, () => {})
}

function textToLines(s: string): string[] {
  return s.split(/\r?\n/).map((x) => x.trim()).filter(Boolean)
}
function linesToText(arr: string[]): string {
  return (arr ?? []).join('\n')
}

type FormState = (ProjectCreate & { id?: number }) | null

export default function ProjectsPage() {
  const [list, setList] = useState<Project[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('active')
  const [form, setForm] = useState<FormState>(null)
  const [createdProject, setCreatedProject] = useState<Project | null>(null)
  const [reinjecting, setReinjecting] = useState<number | null>(null)

  const load = () =>
    api.projects(statusFilter ? { status: statusFilter } : undefined).then(setList)
  useEffect(() => {
    load()
  }, [statusFilter])

  const save = async () => {
    if (!form) return
    const _wr = (form as FormState & { _wr?: string })._wr ?? linesToText(form.workspace_rules)
    const _me = (form as FormState & { _me?: string })._me ?? linesToText(form.member_emails ?? [])
    if (form.id) {
      const payload: ProjectUpdate = {
        name: form.name,
        description: form.description ?? '',
        workspace_rules: textToLines(_wr),
        member_emails: textToLines(_me),
      }
      const status = (form as Project).status
      if (status) payload.status = status
      await api.updateProject(form.id, payload)
    } else {
      const createMode = (form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual'
      const slug = (form as FormState & { _repoSlug?: string })._repoSlug ?? ''
      const isAuto = createMode === 'auto_gitlab' || createMode === 'auto_github'
      const res = await api.createProject({
        name: form.name,
        description: form.description ?? '',
        workspace_rules: textToLines(_wr),
        member_emails: textToLines(_me),
        created_by: form.created_by,
        auto_create_repo: isAuto,
        repo_slug: isAuto ? slug || undefined : undefined,
        repo_provider: createMode === 'auto_github' ? 'github' : createMode === 'auto_gitlab' ? 'gitlab' : undefined,
      })
      if (res.repo_url || res.repo_ssh_url) {
        setCreatedProject(res)
        return
      }
    }
    setForm(null)
    setCreatedProject(null)
    load()
  }

  const archive = async (id: number) => {
    if (!confirm('确认归档该项目？归档后将从白名单中移除，Hook 将不再放行该目录。')) return
    await api.archiveProject(id)
    load()
  }

  const openCreate = () => {
    setCreatedProject(null)
    setForm({
      name: '',
      description: '',
      workspace_rules: [],
      member_emails: [],
      created_by: '',
      _wr: '',
      _me: '',
      _createRepoMode: 'manual',
      _repoSlug: '',
    } as FormState & { _wr: string; _me: string; _createRepoMode: string; _repoSlug: string })
  }

  const closeModal = () => {
    setForm(null)
    setCreatedProject(null)
    load()
  }

  const onReinject = async (id: number) => {
    setReinjecting(id)
    try {
      await api.reinjectHook(id)
      load()
    } finally {
      setReinjecting(null)
    }
  }
  const openEdit = (p: Project) => {
    setForm({
      ...p,
      _wr: linesToText(p.workspace_rules),
      _me: linesToText(p.member_emails ?? []),
    } as FormState & { _wr: string; _me: string })
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">项目管理</h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600"
        >
          <Plus size={15} /> 新建项目
        </button>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-500">状态</span>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">全部</option>
          <option value="active">启用</option>
          <option value="archived">已归档</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-5 py-2 text-left">项目名称</th>
              <th className="px-4 py-2 text-left">描述</th>
              <th className="px-4 py-2 text-left">工作目录规则</th>
              <th className="px-4 py-2 text-center">仓库状态</th>
              <th className="px-4 py-2 text-center">状态</th>
              <th className="px-4 py-2 text-left">创建时间</th>
              <th className="px-4 py-2 text-center">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {list.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-5 py-2.5 font-medium">
                  <Link to={`/projects/${p.id}`} className="text-brand-600 hover:underline">
                    {p.name}
                  </Link>
                </td>
                <td className="px-4 py-2.5 text-gray-600 max-w-[200px] truncate" title={p.description}>
                  {p.description || '—'}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {(p.workspace_rules?.length ?? 0)} 条
                </td>
                <td className="px-4 py-2.5 text-center">
                  {repoStatus(p) === 'created' && (
                    <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                      已创建
                    </span>
                  )}
                  {repoStatus(p) === 'failed' && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                      创建失败
                      <button
                        type="button"
                        onClick={() => onReinject(p.id)}
                        disabled={reinjecting === p.id}
                        className="p-0.5 rounded hover:bg-amber-200"
                        title="重新注入 Hook"
                      >
                        <RefreshCw size={12} className={reinjecting === p.id ? 'animate-spin' : ''} />
                      </button>
                    </span>
                  )}
                  {repoStatus(p) === 'none' && (
                    <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                      未创建
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-center">
                  <span
                    className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      p.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {p.status === 'active' ? '启用' : '已归档'}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-500">{p.created_at?.slice(0, 10) ?? '—'}</td>
                <td className="px-4 py-2.5 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => openEdit(p)}
                      className="p-1 text-gray-400 hover:text-brand-600"
                      title="编辑"
                    >
                      <Edit2 size={14} />
                    </button>
                    {p.status === 'active' && (
                      <button
                        onClick={() => archive(p.id)}
                        className="p-1 text-gray-400 hover:text-amber-600"
                        title="归档"
                      >
                        <Archive size={14} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-6 text-center text-gray-400">
                  {statusFilter ? '暂无项目' : '暂无项目，点击「新建项目」立项'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-base font-semibold">
              {createdProject ? '创建成功' : form.id ? '编辑项目' : '新建项目'}
            </h2>

            {createdProject ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-600">项目已创建，可复制以下地址供成员 clone：</p>
                {createdProject.repo_url && (
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={createdProject.repo_url}
                      className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-xs font-mono bg-gray-50"
                    />
                    <button
                      type="button"
                      onClick={() => copyToClipboard(createdProject.repo_url)}
                      className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                      title="复制"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                )}
                {createdProject.repo_ssh_url && (
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={createdProject.repo_ssh_url}
                      className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-xs font-mono bg-gray-50"
                    />
                    <button
                      type="button"
                      onClick={() => copyToClipboard(createdProject.repo_ssh_url)}
                      className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                      title="复制"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                )}
                <div className="flex justify-end pt-2">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-sm bg-brand-500 text-white rounded-lg hover:bg-brand-600"
                  >
                    关闭
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">项目名称 *</label>
                    <input
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                      placeholder="如 Sierac-tm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">描述</label>
                    <input
                      value={form.description ?? ''}
                      onChange={(e) => setForm({ ...form, description: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                      placeholder="简要说明"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">工作目录规则 *（一行一条路径前缀）</label>
                    <textarea
                      value={(form as FormState & { _wr?: string })._wr ?? linesToText(form.workspace_rules)}
                      onChange={(e) => setForm({ ...form, _wr: e.target.value } as FormState)}
                      rows={3}
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono"
                      placeholder={'D:\\AI\\Sierac-tm\n/home/dev/sierac-tm'}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">参与成员邮箱（一行一个，留空表示全员）</label>
                    <textarea
                      value={(form as FormState & { _me?: string })._me ?? linesToText(form.member_emails ?? [])}
                      onChange={(e) => setForm({ ...form, _me: e.target.value } as FormState)}
                      rows={2}
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                      placeholder="可选"
                    />
                  </div>
                  {!form.id && (
                <>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">仓库创建方式</label>
                    <div className="flex flex-wrap gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="createRepoMode"
                          checked={((form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual') === 'manual'}
                          onChange={() => setForm({ ...form, _createRepoMode: 'manual' } as FormState)}
                        />
                        <span className="text-sm">关联已有仓库</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="createRepoMode"
                          checked={((form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual') === 'auto_gitlab'}
                          onChange={() => setForm({ ...form, _createRepoMode: 'auto_gitlab' } as FormState)}
                        />
                        <span className="text-sm">自动创建（GitLab）</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="createRepoMode"
                          checked={((form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual') === 'auto_github'}
                          onChange={() => setForm({ ...form, _createRepoMode: 'auto_github' } as FormState)}
                        />
                        <span className="text-sm">自动创建（GitHub）</span>
                      </label>
                    </div>
                  </div>
                  {(((form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual') === 'auto_gitlab' || ((form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual') === 'auto_github') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">仓库路径（slug）*</label>
                      <input
                        value={(form as FormState & { _repoSlug?: string })._repoSlug ?? ''}
                        onChange={(e) => setForm({ ...form, _repoSlug: e.target.value } as FormState)}
                        className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono"
                        placeholder="如 sierac-tm"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">创建人邮箱 *</label>
                    <input
                      value={form.created_by}
                      onChange={(e) => setForm({ ...form, created_by: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                      placeholder="admin@company.com"
                    />
                  </div>
                </>
              )}
              {form.id && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">状态</label>
                  <select
                    value={(form as Project).status ?? 'active'}
                    onChange={(e) => setForm({ ...form, status: e.target.value } as FormState)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                  >
                    <option value="active">启用</option>
                    <option value="archived">已归档</option>
                  </select>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={save}
                disabled={(() => {
                  const mode = (form as FormState & { _createRepoMode?: string })._createRepoMode ?? 'manual'
                  const slug = (form as FormState & { _repoSlug?: string })._repoSlug ?? ''
                  const wr = (form as FormState & { _wr?: string })._wr ?? ''
                  const isAuto = mode === 'auto_gitlab' || mode === 'auto_github'
                  return !form.name.trim() || !wr.trim() || (!form.id && !form.created_by?.trim()) || (!form.id && isAuto && !slug.trim())
                })()}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-50 disabled:pointer-events-none"
              >
                <Check size={14} /> 保存
              </button>
            </div>
                </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
