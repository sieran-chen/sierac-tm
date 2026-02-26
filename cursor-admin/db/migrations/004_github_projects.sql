-- ============================================================
-- 004_github_projects.sql — 项目支持 GitHub（与 GitLab 并列）
-- ============================================================

-- 仓库来源：'gitlab' | 'github' | NULL（关联已有）
ALTER TABLE projects ADD COLUMN IF NOT EXISTS repo_provider TEXT;
-- GitHub 仓库标识：owner/name，用于 reinject 等 API
ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_repo_full_name TEXT;
