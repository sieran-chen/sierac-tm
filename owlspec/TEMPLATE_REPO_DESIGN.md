# OwlSpec 模板仓库设计

> **版本**: v0.2.0 (2026-03-02)
> **状态**: 设计稿（第二版，增加 PM 侧模板）
> **目标**: 设计 `owlspec/owlspec-template` GitHub 模板仓库

---

## 一、仓库定位

### 用途

GitHub 模板仓库，用户通过 `Use this template` 一键创建项目，自带 OwlSpec 方法论的完整骨架。

### 目标用户

| 用户 | 使用方式 |
|------|---------|
| PM 带 AI 做 MVP | 用 requirements 模板写需求，AI 按 spec 执行 |
| 技术负责人 | 用完整三层 + Spec 循环管理 AI 研发团队 |
| 独立开发者 | 用三层文档 + Spec 循环管理自己的 AI 编码 |
| 多 Agent 团队 | 用 Worktree + 统筹循环协调多个 AI Agent |

---

## 二、仓库结构

```
owlspec-template/
├── .specs/                          # Spec 文档根目录
│   ├── TASKS_SCAN.md                # 全局进度追踪（单一真源）
│   ├── _example/                    # 示例 spec（可删除）
│   │   ├── requirements.md          # 需求文档示例
│   │   ├── design.md                # 设计文档示例
│   │   └── tasks.md                 # 任务文档示例
│   └── _templates/                  # 空白模板
│       ├── requirements.template.md # PM 用的需求模板
│       ├── design.template.md       # 设计文档模板
│       └── tasks.template.md        # 任务文档模板
│
├── .agents/                         # 多 Agent 协作配置
│   ├── WORKTREE_ASSIGNMENTS.md      # Worktree 任务分配
│   └── config/                      # 各 Agent 配置
│       ├── reviewer.md              # 审校 Agent 规则
│       └── coder.md                 # 编码 Agent 规则
│
├── scripts/                         # 自动化脚本
│   ├── init-worktrees.sh            # 创建多 Agent worktree 结构
│   ├── spec-health-check.sh         # Spec 健康检查
│   └── sync-worktrees.sh            # 同步所有 worktree
│
├── AGENTS.md                        # AI Agent 工作指南
├── CLAUDE.md                        # Claude Code 规则（symlink → AGENTS.md）
├── CODEX.md                         # Codex CLI 规则（symlink → AGENTS.md）
├── .cursorrules                     # Cursor 规则（symlink → AGENTS.md）
├── README.md                        # 项目 README
└── .gitignore
```

---

## 三、核心模板内容

### requirements.template.md — PM 的需求模板

```markdown
# Requirements: {功能名称}

> **目标**：{一句话描述这个功能解决什么问题}
> **优先级**：P0 / P1 / P2
> **预估工作量**：{天数}

## 用户故事

**故事 1**：{场景名称}
- 作为 {角色}，我希望 {行为}
- 这样我可以 {价值}

**验收标准**：
- [ ] {可检验的条件 1}
- [ ] {可检验的条件 2}

## 业务规则

> 把隐含的业务规则显式写出来，AI 无法猜到这些。

- 规则 1：{描述}
- 规则 2：{描述}

## 不做什么（边界）

- {明确排除的功能 1}
- {明确排除的功能 2}

## 非功能需求

- 性能：{如有}
- 安全：{如有}
- 兼容性：{如有}
```

### design.template.md — 架构设计模板

```markdown
# Design: {功能名称}

> **关联需求**：`.specs/{feature}/requirements.md`
> **设计者**：{人名/AI}
> **审核者**：{PM/Tech Lead}

## 架构决策

### 决策 1：{决策主题}
- **选项 A**：{描述}
- **选项 B**：{描述}
- **决策**：选 {A/B}
- **理由**：{为什么}

## 数据模型

{表结构/API 契约/数据流}

## 技术约束

- {约束 1}
- {约束 2}

## 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| {场景 1} | {处理} |
```

### tasks.template.md — 任务清单模板

```markdown
# Tasks: {功能名称}

> **关联需求**：`.specs/{feature}/requirements.md`
> **关联设计**：`.specs/{feature}/design.md`

## Task 0: 文档与契约

- [ ] requirements.md 完成并审核
- [ ] design.md 完成并审核
- [ ] 共享契约输出（如有多端协作）

## Task 1: {任务描述}

- [ ] {子任务 1}
- [ ] {子任务 2}
- [ ] 验收：{验收标准}

## Task 2: {任务描述}

- [ ] {子任务 1}
- [ ] 验收：{验收标准}
```

---

## 四、AGENTS.md — AI Agent 工作指南

```markdown
# AI Agent 工作指南

## 你是谁

你是一个 AI 编码 Agent，在一个使用 OwlSpec 方法论的项目中工作。

## 核心规则

1. **先读 spec 再写代码**：每个功能都有 `.specs/{feature}/` 三层文档，先读完再动手
2. **不猜需求**：需求不清楚时，标记 blocked 并说明缺什么信息
3. **按 Spec 循环推进**：Check → Plan → Do → Doc → Commit → Evaluate
4. **每轮最多 3 个 task**：避免上下文溢出
5. **每轮必须 commit**：保持工作目录干净
6. **连续失败 3 次 → blocked**：不要死磕，标记后等人工介入

## 验收标准

- 代码必须通过 requirements.md 中的验收标准
- 架构必须符合 design.md 中的约束
- 完成的 task 在 tasks.md 中打勾 `[x]`

## 禁止行为

- 不留 TODO/FIXME
- 不硬编码业务规则
- 不猜测 PM 没写的需求
- 不跳过测试
```

---

## 五、脚本设计

### init-worktrees.sh

```bash
#!/bin/bash
PROJECT_NAME="${1:-$(basename $(pwd))}"
PARENT_DIR="$(dirname $(pwd))"

echo "Creating OwlSpec worktree structure for: $PROJECT_NAME"

git worktree add -b review-work "$PARENT_DIR/${PROJECT_NAME}-review" main
echo "  Created: ${PROJECT_NAME}-review (branch: review-work)"

git worktree add -b agent-1-work "$PARENT_DIR/${PROJECT_NAME}-agent-1" main
echo "  Created: ${PROJECT_NAME}-agent-1 (branch: agent-1-work)"

git worktree add -b agent-2-work "$PARENT_DIR/${PROJECT_NAME}-agent-2" main
echo "  Created: ${PROJECT_NAME}-agent-2 (branch: agent-2-work)"

echo ""
echo "Worktree structure:"
git worktree list

echo ""
echo "Next steps:"
echo "  1. Update .agents/WORKTREE_ASSIGNMENTS.md"
echo "  2. Start your AI coding tool in each worktree directory"
```

### spec-health-check.sh

```bash
#!/bin/bash
SPECS_DIR=".specs"
ERRORS=0

echo "=== OwlSpec Health Check ==="
echo ""

if [ ! -f "$SPECS_DIR/TASKS_SCAN.md" ]; then
    echo "ERROR: $SPECS_DIR/TASKS_SCAN.md not found"
    ERRORS=$((ERRORS + 1))
fi

for spec_dir in "$SPECS_DIR"/*/; do
    [ -d "$spec_dir" ] || continue
    spec_name=$(basename "$spec_dir")
    [ "$spec_name" = "_example" ] || [ "$spec_name" = "_templates" ] && continue

    echo "Checking: $spec_name"

    for doc in requirements.md design.md tasks.md; do
        if [ ! -f "$spec_dir/$doc" ]; then
            echo "  MISSING: $doc"
            ERRORS=$((ERRORS + 1))
        fi
    done

    if [ -f "$spec_dir/tasks.md" ]; then
        total=$(grep -c '\- \[.\]' "$spec_dir/tasks.md" 2>/dev/null || echo 0)
        done=$(grep -c '\- \[x\]' "$spec_dir/tasks.md" 2>/dev/null || echo 0)
        echo "  Progress: $done/$total tasks"
    fi
    echo ""
done

echo "=== Summary: $ERRORS errors ==="
[ $ERRORS -gt 0 ] && exit 1 || exit 0
```

---

## 六、发布计划

| 阶段 | 内容 | 时间 |
|------|------|------|
| v0.1 | 三层模板 + AGENTS.md + 健康检查脚本 | M5 到手后 |
| v0.2 | Worktree 脚本 + 统筹循环文档 | v0.1 + 2 周 |
| v0.3 | CLI 工具（`owlspec init/new/check`） | v0.2 + 1 月 |
| v1.0 | 完整文档 + 实战案例 + 视频教程 | v0.3 + 2 月 |

---

**维护者**: yeemio
