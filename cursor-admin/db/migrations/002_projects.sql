-- ============================================================
-- 002_projects.sql — 项目立项与治理（projects、git_contributions、agent_sessions 扩展）
-- ============================================================

-- projects 表
CREATE TABLE IF NOT EXISTS projects (
    id              SERIAL PRIMARY KEY,
    name            TEXT        NOT NULL,
    description     TEXT        DEFAULT '',
    git_repos       TEXT[]      DEFAULT '{}',
    workspace_rules TEXT[]      NOT NULL,
    member_emails   TEXT[]      DEFAULT '{}',
    status          TEXT        NOT NULL DEFAULT 'active',
    gitlab_project_id INT,
    repo_url        TEXT        DEFAULT '',
    repo_ssh_url    TEXT        DEFAULT '',
    hook_initialized BOOLEAN    DEFAULT FALSE,
    created_by      TEXT        NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status);

-- git_contributions 表
CREATE TABLE IF NOT EXISTS git_contributions (
    id              SERIAL PRIMARY KEY,
    project_id      INT         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_email    TEXT        NOT NULL,
    commit_date     DATE        NOT NULL,
    commit_count    INT         NOT NULL DEFAULT 0,
    lines_added     INT         NOT NULL DEFAULT 0,
    lines_removed   INT         NOT NULL DEFAULT 0,
    files_changed   INT         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, author_email, commit_date)
);

CREATE INDEX IF NOT EXISTS idx_git_contributions_project ON git_contributions (project_id, commit_date DESC);
CREATE INDEX IF NOT EXISTS idx_git_contributions_author  ON git_contributions (author_email, commit_date DESC);

-- agent_sessions 扩展 project_id
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS project_id INT REFERENCES projects(id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_project ON agent_sessions (project_id, ended_at DESC);
