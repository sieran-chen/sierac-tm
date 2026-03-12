-- ============================================================
-- 007_projects_v3.sql — v3.0 轻量立项：新增预算与激励池字段
-- 不删除旧字段（向后兼容），代码层不再使用 workspace_rules/hook_initialized 等
-- ============================================================

ALTER TABLE projects ADD COLUMN IF NOT EXISTS budget_amount    NUMERIC(12,2);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS budget_period    TEXT DEFAULT 'monthly';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS incentive_pool   NUMERIC(12,2);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS incentive_rule_id INT REFERENCES incentive_rules(id);
