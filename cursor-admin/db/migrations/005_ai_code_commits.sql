-- ============================================================
-- 005_ai_code_commits.sql — AI Code Tracking API 同步（commit 级 AI 归因）
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_code_commits (
    id                      SERIAL PRIMARY KEY,
    commit_hash             TEXT NOT NULL,
    user_id                 TEXT,
    user_email              TEXT NOT NULL,
    repo_name               TEXT NOT NULL,
    branch_name             TEXT,
    project_id              INT REFERENCES projects(id),
    total_lines_added       INT NOT NULL DEFAULT 0,
    total_lines_deleted     INT NOT NULL DEFAULT 0,
    tab_lines_added         INT NOT NULL DEFAULT 0,
    tab_lines_deleted       INT NOT NULL DEFAULT 0,
    composer_lines_added    INT NOT NULL DEFAULT 0,
    composer_lines_deleted  INT NOT NULL DEFAULT 0,
    non_ai_lines_added      INT NOT NULL DEFAULT 0,
    non_ai_lines_deleted    INT NOT NULL DEFAULT 0,
    commit_message          TEXT,
    commit_ts               TIMESTAMPTZ NOT NULL,
    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (commit_hash, user_email)
);

CREATE INDEX IF NOT EXISTS idx_ai_code_commits_project_ts ON ai_code_commits (project_id, commit_ts DESC);
CREATE INDEX IF NOT EXISTS idx_ai_code_commits_user_ts   ON ai_code_commits (user_email, commit_ts DESC);
CREATE INDEX IF NOT EXISTS idx_ai_code_commits_repo_ts   ON ai_code_commits (repo_name, commit_ts DESC);
CREATE INDEX IF NOT EXISTS idx_ai_code_commits_commit_ts ON ai_code_commits (commit_ts DESC);
