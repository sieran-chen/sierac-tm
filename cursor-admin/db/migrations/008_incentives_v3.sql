-- ============================================================
-- 008_incentives_v3.sql — v3.0 激励字段：contribution_scores 新增 ai_code_commits 维度
-- incentive_rules 简化（移除 weights/caps，保留 period_type）
-- ============================================================

-- contribution_scores: 新增 v3.0 字段（幂等）
ALTER TABLE contribution_scores ADD COLUMN IF NOT EXISTS ai_lines_added    INT NOT NULL DEFAULT 0;
ALTER TABLE contribution_scores ADD COLUMN IF NOT EXISTS total_lines_added INT NOT NULL DEFAULT 0;
ALTER TABLE contribution_scores ADD COLUMN IF NOT EXISTS ai_ratio          NUMERIC(5,4) NOT NULL DEFAULT 0;
ALTER TABLE contribution_scores ADD COLUMN IF NOT EXISTS contribution_pct  NUMERIC(5,4) NOT NULL DEFAULT 0;
ALTER TABLE contribution_scores ADD COLUMN IF NOT EXISTS delivery_factor   NUMERIC(3,2) NOT NULL DEFAULT 1.0;
ALTER TABLE contribution_scores ADD COLUMN IF NOT EXISTS incentive_amount  NUMERIC(12,2) NOT NULL DEFAULT 0;

-- incentive_rules: 新增 description 字段（可选）
ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
