# Spec Engineering 模板仓库设计

> **创建时间**: 2026-03-02
> **状态**: 设计稿（待实施）
> **目的**: 设计一个干净的 GitHub 模板仓库，让开发者 `Use this template` 后即可开始 spec 驱动的 AI 工程

---

## 一、仓库名称候选

| 候选 | 优点 | 缺点 |
|------|------|------|
| `spec-engineering` | 直接、专业 | 可能太学术 |
| `speceng` | 简短、CLI 友好 | 不够直观 |
| `ai-spec-template` | 清晰描述用途 | 太通用 |
| `spec-driven-dev` | 描述方法论 | 和 Kiro 的 SDD 撞名 |

**建议**: `spec-engineering`（方法论名称 = 仓库名称，便于品牌统一）

---

## 二、目录结构

```
spec-engineering/
├── README.md                           # 方法论介绍 + 快速上手
├── LICENSE                             # CC BY-SA 4.0（方法论）+ MIT（代码）
├── METHODOLOGY.md                      # 完整方法论文档（从 SPEC_ENGINEERING_METHODOLOGY.md 精炼）
│
├── .specs/                             # Spec 文档根目录
│   ├── TASKS_SCAN.md                   # 功能清单 + 检查点（单一真源）
│   ├── SPEC_STANDARD.md                # 三层文档规范标准
│   └── _example/                       # 示例 spec（可删除）
│       ├── requirements.md
│       ├── design.md
│       └── tasks.md
│
├── .agents/                            # AI Agent 配置
│   ├── AGENTS.md                       # 仓库级 AI 指令（通用版）
│   ├── WORKTREE_ASSIGNMENTS.md         # 多 Agent 任务分配
│   └── rules/                          # AI 工作规范
│       ├── spec-loop.md                # Spec 循环规则
│       ├── orchestrator.md             # 统筹循环规则
│       ├── coding-standards.md         # 编码规范（模板，用户自定义）
│       └── testing-standards.md        # 测试规范（模板，用户自定义）
│
├── docs/                               # 项目文档
│   └── WORKTREE_GUIDE.md              # 多 Agent Worktree 协作指南
│
└── scripts/                            # 辅助脚本
    ├── init-worktrees.sh               # 一键创建 worktree 结构
    ├── sync-worktrees.sh               # 一键同步所有 worktree
    ├── spec-health-check.sh            # Spec 健康检查
    └── cleanup-processes.sh            # 清理残留进程（防死机）
```

---

## 三、核心文件内容设计

### 3.1 README.md

```markdown
# Spec Engineering

> 人在 spec 层决策，AI 在代码层执行。

Spec Engineering 是一套半自动 AI 工程方法论，解决 Vibe Coding 在生产级软件中的系统性问题。

## 快速上手

### 1. 使用模板创建项目

点击 "Use this template" 或：

\`\`\`bash
gh repo create my-project --template spec-engineering/spec-engineering
\`\`\`

### 2. 创建第一个 spec

\`\`\`bash
mkdir -p .specs/my-feature
# 按 .specs/SPEC_STANDARD.md 的模板编写三层文档
\`\`\`

### 3. 开始 spec 循环

在 Cursor / Claude Code 中打开项目，AI 会自动读取 `.agents/` 中的规则，
按 spec 循环推进开发。

### 4.（可选）多 Agent 协作

\`\`\`bash
# 创建 worktree 结构
./scripts/init-worktrees.sh
\`\`\`

## 方法论文档

- [完整方法论](METHODOLOGY.md)
- [三层文档规范](.specs/SPEC_STANDARD.md)
- [多 Agent 协作指南](docs/WORKTREE_GUIDE.md)

## 迁移路径

从 Vibe Coding 到 Spec Engineering 的渐进式迁移：

1. **阶段 1**：只加 tasks.md（最小改动）
2. **阶段 2**：加 requirements.md + design.md（三层完整）
3. **阶段 3**：加 Spec 循环（持续推进）
4. **阶段 4**：加多 Agent 协作（团队级）

## 许可证

方法论文档：CC BY-SA 4.0
代码和脚本：MIT
```

### 3.2 .agents/AGENTS.md（通用版）

这是仓库级 AI 指令文件，所有 AI 工具（Cursor、Claude Code、Codex CLI）都会读取。

核心内容：
- 读取 `.specs/SPEC_STANDARD.md` 了解文档规范
- 读取 `.agents/rules/spec-loop.md` 了解 spec 循环规则
- 读取 `.specs/TASKS_SCAN.md` 了解当前进度
- 读取 `.agents/WORKTREE_ASSIGNMENTS.md` 确认自己的任务分配
- 编码规范引用 `.agents/rules/coding-standards.md`
- 测试规范引用 `.agents/rules/testing-standards.md`

### 3.3 .agents/rules/spec-loop.md

从 `owlclaw_core.mdc` 的第四节提炼，去掉所有 OwlClaw 特定内容：
- Spec 循环的 9 步 Loop
- 触发词（继续、spec循环、自主推进等）
- 批次控制、失败处理、健康检查
- 每轮提交、资源释放
- Exit 条件

### 3.4 .agents/rules/orchestrator.md

从 `owlclaw_core.mdc` 的第五节提炼：
- 统筹循环的 8 步 Loop
- 工作状态检测（IDLE/WORKING/DONE）
- 契约先行规则
- Sync 时的冲突处理

### 3.5 scripts/init-worktrees.sh

```bash
#!/bin/bash
# 创建多 Agent worktree 结构
# 用法: ./scripts/init-worktrees.sh [project-name]

PROJECT_NAME="${1:-$(basename $(pwd))}"
PROJECT_DIR="$(pwd)"
PARENT_DIR="$(dirname $PROJECT_DIR)"

echo "Creating worktree structure for: $PROJECT_NAME"

# 创建审校 worktree
git worktree add -b review-work "$PARENT_DIR/${PROJECT_NAME}-review" main
echo "Created: ${PROJECT_NAME}-review (branch: review-work)"

# 创建编码 worktree 1
git worktree add -b agent-1-work "$PARENT_DIR/${PROJECT_NAME}-agent-1" main
echo "Created: ${PROJECT_NAME}-agent-1 (branch: agent-1-work)"

# 创建编码 worktree 2
git worktree add -b agent-2-work "$PARENT_DIR/${PROJECT_NAME}-agent-2" main
echo "Created: ${PROJECT_NAME}-agent-2 (branch: agent-2-work)"

echo ""
echo "Worktree structure:"
git worktree list

echo ""
echo "Next steps:"
echo "  1. Install dependencies in each worktree"
echo "  2. Update .agents/WORKTREE_ASSIGNMENTS.md with task assignments"
echo "  3. Start Codex/Claude Code in each worktree directory"
```

### 3.6 scripts/spec-health-check.sh

```bash
#!/bin/bash
# Spec 健康检查：检查所有 spec 的完整性和进度

SPECS_DIR=".specs"
ERRORS=0
WARNINGS=0

echo "=== Spec Health Check ==="
echo ""

# 检查 TASKS_SCAN.md 是否存在
if [ ! -f "$SPECS_DIR/TASKS_SCAN.md" ]; then
    echo "ERROR: $SPECS_DIR/TASKS_SCAN.md not found"
    ERRORS=$((ERRORS + 1))
fi

# 遍历所有 spec 目录
for spec_dir in "$SPECS_DIR"/*/; do
    [ -d "$spec_dir" ] || continue
    spec_name=$(basename "$spec_dir")
    [ "$spec_name" = "_example" ] && continue

    echo "Checking: $spec_name"

    # 检查三层文档是否齐全
    for doc in requirements.md design.md tasks.md; do
        if [ ! -f "$spec_dir/$doc" ]; then
            echo "  ERROR: Missing $doc"
            ERRORS=$((ERRORS + 1))
        fi
    done

    # 检查 tasks.md 的进度
    if [ -f "$spec_dir/tasks.md" ]; then
        total=$(grep -c '\- \[.\]' "$spec_dir/tasks.md" 2>/dev/null || echo 0)
        done=$(grep -c '\- \[x\]' "$spec_dir/tasks.md" 2>/dev/null || echo 0)
        pending=$((total - done))
        echo "  Progress: $done/$total tasks done ($pending pending)"
    fi

    echo ""
done

echo "=== Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    exit 1
fi
```

---

## 四、与 OwlClaw 的差异

| 维度 | OwlClaw 版本 | 模板仓库版本 |
|------|-------------|-------------|
| 目录名 | `.kiro/specs/` | `.specs/` |
| AI 规则目录 | `.cursor/rules/*.mdc` | `.agents/rules/*.md` |
| 任务分配 | `.kiro/WORKTREE_ASSIGNMENTS.md` | `.agents/WORKTREE_ASSIGNMENTS.md` |
| 功能清单 | `.kiro/specs/SPEC_TASKS_SCAN.md` | `.specs/TASKS_SCAN.md` |
| 文档标准 | `.kiro/SPEC_DOCUMENTATION_STANDARD.md` | `.specs/SPEC_STANDARD.md` |
| 项目特定内容 | OwlClaw 的包结构、Poetry、Python 规范 | 通用，用户自定义 |
| AI 工具绑定 | Cursor `.mdc` 格式 | 通用 `.md` 格式（兼容所有 AI 工具） |

**关键设计决策**：
- 用 `.agents/` 替代 `.cursor/rules/`，因为方法论不绑定特定 IDE
- 用 `.specs/` 替代 `.kiro/specs/`，因为 `.kiro` 是 Kiro IDE 的约定
- 规则文件用 `.md` 而非 `.mdc`，因为 `.mdc` 是 Cursor 私有格式

---

## 五、示例 spec（_example/）

### _example/requirements.md

一个简单但完整的示例，展示三层文档的写法。建议用一个通用场景（如"用户认证"或"数据导出"），让用户理解格式后删除。

### _example/design.md

对应的架构设计，展示 ASCII 架构图、组件设计、数据流的写法。

### _example/tasks.md

对应的任务清单，展示层级编号、复选框、验收清单的写法。

---

## 六、实施计划

| 步骤 | 做什么 | 前置条件 |
|------|--------|---------|
| 1 | 在 GitHub 创建 `spec-engineering` 仓库 | 无 |
| 2 | 从本设计文档生成目录结构和核心文件 | 步骤 1 |
| 3 | 从 `SPEC_ENGINEERING_METHODOLOGY.md` 精炼 `METHODOLOGY.md` | 步骤 2 |
| 4 | 从 OwlClaw 的规则文件提炼通用版 `.agents/rules/` | 步骤 2 |
| 5 | 编写示例 spec（`_example/`） | 步骤 4 |
| 6 | 编写辅助脚本（`scripts/`） | 步骤 2 |
| 7 | 写一篇介绍文章发布 | 步骤 5 |
| 8 | 设置为 GitHub Template Repository | 步骤 6 |

**预计工作量**: 2-3 天（可用 AI 辅助加速）

---

## 七、命名约定总结

| 概念 | OwlClaw 内部名称 | 模板仓库名称 | 理由 |
|------|-----------------|-------------|------|
| Spec 目录 | `.kiro/specs/` | `.specs/` | 去掉 Kiro 绑定 |
| AI 规则 | `.cursor/rules/*.mdc` | `.agents/rules/*.md` | 去掉 Cursor 绑定 |
| 功能清单 | `SPEC_TASKS_SCAN.md` | `TASKS_SCAN.md` | 简化 |
| 文档标准 | `SPEC_DOCUMENTATION_STANDARD.md` | `SPEC_STANDARD.md` | 简化 |
| 任务分配 | `WORKTREE_ASSIGNMENTS.md` | `WORKTREE_ASSIGNMENTS.md` | 保持不变 |
| Spec 循环 | owlclaw_core.mdc §4 | spec-loop.md | 独立文件 |
| 统筹循环 | owlclaw_core.mdc §5 | orchestrator.md | 独立文件 |

---

**维护者**: yeemio
**下次更新**: 创建实际仓库时
