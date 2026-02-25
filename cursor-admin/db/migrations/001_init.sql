-- ============================================================
-- 001_init.sql  —  Cursor Admin 数据库初始化
-- ============================================================

-- 成员表（从 Admin API 同步）
CREATE TABLE IF NOT EXISTS members (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT        NOT NULL UNIQUE,   -- Cursor userId（数字或 user_xxx）
    email       TEXT        NOT NULL UNIQUE,
    name        TEXT,
    role        TEXT        DEFAULT 'member',
    is_removed  BOOLEAN     DEFAULT FALSE,
    synced_at   TIMESTAMPTZ DEFAULT NOW(),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 每日用量快照（从 Admin API /teams/daily-usage-data 拉取）
CREATE TABLE IF NOT EXISTS daily_usage (
    id                      SERIAL PRIMARY KEY,
    email                   TEXT        NOT NULL,
    day                     DATE        NOT NULL,
    agent_requests          INT         DEFAULT 0,
    chat_requests           INT         DEFAULT 0,
    composer_requests       INT         DEFAULT 0,
    total_tabs_accepted     INT         DEFAULT 0,
    total_tabs_shown        INT         DEFAULT 0,
    total_lines_added       INT         DEFAULT 0,
    total_lines_deleted     INT         DEFAULT 0,
    accepted_lines_added    INT         DEFAULT 0,
    subscription_reqs       INT         DEFAULT 0,
    usage_based_reqs        INT         DEFAULT 0,
    most_used_model         TEXT,
    client_version          TEXT,
    is_active               BOOLEAN     DEFAULT FALSE,
    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (email, day)
);

-- 支出快照（从 Admin API /teams/spend 拉取，按计费周期）
CREATE TABLE IF NOT EXISTS spend_snapshots (
    id                      SERIAL PRIMARY KEY,
    email                   TEXT        NOT NULL,
    billing_cycle_start     DATE        NOT NULL,
    spend_cents             INT         DEFAULT 0,
    fast_premium_requests   INT         DEFAULT 0,
    monthly_limit_dollars   NUMERIC,
    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (email, billing_cycle_start)
);

-- Agent 会话记录（来自 Hook 上报，每次 Agent 任务 1 条）
CREATE TABLE IF NOT EXISTS agent_sessions (
    id                  SERIAL PRIMARY KEY,
    conversation_id     TEXT        NOT NULL UNIQUE,
    user_email          TEXT        NOT NULL,
    machine_id          TEXT,
    workspace_roots     TEXT[],                        -- 工作目录数组
    primary_workspace   TEXT GENERATED ALWAYS AS (
                            CASE WHEN array_length(workspace_roots, 1) > 0
                                 THEN workspace_roots[1]
                                 ELSE NULL
                            END
                        ) STORED,
    started_at          TIMESTAMPTZ,
    ended_at            TIMESTAMPTZ NOT NULL,
    duration_seconds    INT,                           -- NULL 表示未能计算时长
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 告警规则
CREATE TABLE IF NOT EXISTS alert_rules (
    id              SERIAL PRIMARY KEY,
    name            TEXT        NOT NULL,
    metric          TEXT        NOT NULL,   -- 'daily_agent_requests' | 'daily_spend_cents' | 'monthly_spend_cents'
    scope           TEXT        NOT NULL,   -- 'user' | 'team'
    target_email    TEXT,                   -- scope='user' 时填写
    threshold       NUMERIC     NOT NULL,
    notify_channels JSONB       DEFAULT '[]',  -- [{"type":"email","address":"..."},{"type":"webhook","url":"..."}]
    enabled         BOOLEAN     DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 告警触发历史
CREATE TABLE IF NOT EXISTS alert_events (
    id              SERIAL PRIMARY KEY,
    rule_id         INT         REFERENCES alert_rules(id) ON DELETE CASCADE,
    triggered_at    TIMESTAMPTZ DEFAULT NOW(),
    metric_value    NUMERIC,
    threshold       NUMERIC,
    detail          JSONB
);

-- 常用查询索引
CREATE INDEX IF NOT EXISTS idx_daily_usage_email_day   ON daily_usage (email, day DESC);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_email    ON agent_sessions (user_email, ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_ws       ON agent_sessions (primary_workspace, ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_spend_snapshots_email   ON spend_snapshots (email, billing_cycle_start DESC);
CREATE INDEX IF NOT EXISTS idx_alert_events_rule       ON alert_events (rule_id, triggered_at DESC);
