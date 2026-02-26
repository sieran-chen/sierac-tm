-- ============================================================
-- 003_incentives.sql — 贡献度与激励（incentive_rules、contribution_scores、leaderboard_snapshots）
-- ============================================================

-- 激励规则（权重、上限、周期类型）
CREATE TABLE IF NOT EXISTS incentive_rules (
    id              SERIAL PRIMARY KEY,
    name            TEXT        NOT NULL,
    period_type     TEXT        NOT NULL DEFAULT 'weekly',
    weights         JSONB       NOT NULL,
    caps            JSONB       NOT NULL DEFAULT '{}',
    enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 贡献得分（按人、按项目、按周期）
CREATE TABLE IF NOT EXISTS contribution_scores (
    id                      SERIAL PRIMARY KEY,
    user_email              TEXT        NOT NULL,
    project_id              INT         REFERENCES projects(id),
    period_type             TEXT        NOT NULL,
    period_key              TEXT        NOT NULL,
    rule_id                 INT         REFERENCES incentive_rules(id),
    lines_added             INT         NOT NULL DEFAULT 0,
    lines_removed          INT         NOT NULL DEFAULT 0,
    commit_count            INT         NOT NULL DEFAULT 0,
    files_changed           INT         NOT NULL DEFAULT 0,
    session_duration_hours  NUMERIC(8,2) NOT NULL DEFAULT 0,
    agent_requests          INT         NOT NULL DEFAULT 0,
    score_breakdown         JSONB       NOT NULL DEFAULT '{}',
    total_score             NUMERIC(10,2) NOT NULL DEFAULT 0,
    rank                    INT,
    hook_adopted            BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_email, project_id, period_type, period_key)
);

CREATE INDEX IF NOT EXISTS idx_contribution_scores_period ON contribution_scores (period_type, period_key, total_score DESC);
CREATE INDEX IF NOT EXISTS idx_contribution_scores_user ON contribution_scores (user_email, period_type, period_key);

-- 排行榜快照（审计）
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id          SERIAL PRIMARY KEY,
    period_type TEXT        NOT NULL,
    period_key  TEXT        NOT NULL,
    snapshot    JSONB       NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (period_type, period_key)
);

-- 默认规则（幂等：仅当无规则时插入）
INSERT INTO incentive_rules (id, name, period_type, weights, caps, enabled)
SELECT 1, '默认规则', 'weekly',
    '{"lines_added": 0.35, "commit_count": 0.20, "session_duration_hours": 0.25, "agent_requests": 0.10, "files_changed": 0.10}'::jsonb,
    '{"session_duration_hours_per_day": 12, "agent_requests_per_day": 500}'::jsonb,
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM incentive_rules WHERE id = 1);
