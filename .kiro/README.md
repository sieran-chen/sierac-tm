# Sierac-tm Spec 文档目录

> **规范文档**: `.kiro/SPEC_DOCUMENTATION_STANDARD.md`  
> **架构真源**: `docs/ARCHITECTURE.md`

---

## 目录结构

```
.kiro/
├── SPEC_DOCUMENTATION_STANDARD.md  # 文档规范标准（必读）
├── README.md                       # 本文件
├── WORKTREE_ASSIGNMENTS.md         # 多 worktree 任务分配（可选）
└── specs/                          # 功能文档
    ├── SPEC_TASKS_SCAN.md          # 任务总览（单一真源）
    ├── cursor-admin-core/          # 用量、支出、告警、会话
    │   ├── requirements.md
    │   ├── design.md
    │   └── tasks.md
    ├── cursor-admin-hooks/         # 多语言 Hook 与协议
    │   ├── requirements.md
    │   ├── design.md
    │   └── tasks.md
    └── cursor-admin-incentives/    # 团队激励（预留）
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

---

## 快速开始

### 创建新功能文档

```bash
mkdir -p .kiro/specs/{feature-name}
# 按 SPEC_DOCUMENTATION_STANDARD.md 第二、三、四章模板编写
# requirements.md → design.md → tasks.md
```

### 查看规范

阅读 `.kiro/SPEC_DOCUMENTATION_STANDARD.md` 了解完整文档规范。

---

## 功能总览

**任务总览（单一真源）**：`.kiro/specs/SPEC_TASKS_SCAN.md`

| 功能 | 状态 | 路径 |
|------|------|------|
| **cursor-admin-core** | ✅ 已创建 | `.kiro/specs/cursor-admin-core/` |
| **cursor-admin-hooks** | ✅ 已创建 | `.kiro/specs/cursor-admin-hooks/` |
| **cursor-admin-incentives** | 🟡 预留 | `.kiro/specs/cursor-admin-incentives/` |

---

## 规范要点

1. **requirements.md** — WHAT（用户故事、验收标准）
2. **design.md** — HOW（架构、数据模型、API）
3. **tasks.md** — WHO/WHEN（任务清单、验收）

适用范围：新功能与重大重构必须三层；小功能建议至少 requirements + tasks。

---

**维护者**: 团队  
**最后更新**: 2026-02-25
