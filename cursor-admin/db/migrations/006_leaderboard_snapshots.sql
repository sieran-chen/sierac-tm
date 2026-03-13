-- ============================================================
-- 006_leaderboard_snapshots.sql — 排行榜快照（仅表结构，由定时任务写入）
-- ============================================================

CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id          SERIAL PRIMARY KEY,
    period_type TEXT        NOT NULL,
    period_key  TEXT        NOT NULL,
    snapshot    JSONB       NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (period_type, period_key)
);
