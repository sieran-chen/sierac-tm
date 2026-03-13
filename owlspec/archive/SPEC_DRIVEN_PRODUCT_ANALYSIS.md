# Spec 驱动 AI 工程工作流的产品化分析

> **创建时间**: 2026-03-02
> **来源**: Cursor 对话讨论，基于 OwlClaw 开发实践的战略分析
> **关联文档**: `AI_ENGINEERING_TEAM_PLAN.md`（AI 工程团队搭建方案）

---

## 一、核心发现

在 OwlClaw 开发过程中，无意间验证了一套完整的 **spec 驱动半自动 AI 工程工作流**：

```
人工决策层（最难的部分）
├─ 业务需求分析 → requirements.md
├─ 架构设计 → design.md
├─ 任务拆解 → tasks.md
└─ 验收标准定义
    ↓ spec 文档作为"契约"传递
AI 执行层（已有成熟工具）
├─ Codex CLI / Claude Code（自主编码）
├─ Worktree 隔离（并行不冲突）
├─ Review Loop（质量门控）
└─ 统筹循环（merge + 分配 + 同步）
    ↓ 反馈
人工决策层（下一轮迭代）
```

**核心洞察：最难的不是让 AI 写代码，而是告诉 AI 写什么。**

---

## 二、竞品全景（2026.3 实况）

这个赛道已经非常热闹：

| 产品 | 背景 | 模式 | 价格 | 核心特点 |
|------|------|------|------|---------|
| **Amazon Kiro IDE** | AWS 官方 | spec-driven IDE | 免费 50 actions/月 | EARS 需求语法 + Claude 驱动 + Agent Hooks |
| **GitHub Spec Kit** | GitHub 官方 | CLI 工具包 | MIT 开源 | 28K stars、11+ AI Agent 集成、`/specify` → `/plan` → `/tasks` → `/implement` |
| **CodeGuide** | 独立产品 | SaaS | $24-29/月 | 41K+ 用户、idea → PRD/tech spec/wireframe、Chrome 扩展 |
| **SpecWeave** | 独立产品 | CLI 框架 | 付费 | 68+ 专精 Agent、`/sw:auto` 自主执行数小时、质量门控 |
| **OpenSpec** | Fission-AI | 开源框架 | 免费 | 中国社区主流、腾讯/阿里有实战指南、四阶段生命周期 |
| **Traycer** | 独立产品 | CLI 工具 | 付费 | Plan/Phases/Review/Epic 四种模式、GitHub/JIRA 集成 |

### 残酷现实

- Amazon 和 GitHub 已经入场，且**免费/开源**
- 中国社区已有 OpenSpec + 腾讯 CodeBuddy 的组合
- 纯 spec 生成是**低壁垒**功能——任何 LLM 都能做，差异化空间小

---

## 三、我们的真正差异化

对比竞品，我们验证的工作流有几个**独特之处**是市场上没有的：

| 我们有的 | 竞品没有的 | 为什么重要 |
|---------|-----------|-----------|
| **三层文档结构** (requirements → design → tasks) | 大多只有 PRD + tasks，缺 design 层 | design 层是架构决策的载体，防止 AI 做出错误架构选择 |
| **多 Agent 并行 + Worktree 隔离** | 大多是单 Agent 串行 | 真正的团队级并行，不是玩具 |
| **Review Loop 质量门控** | 大多只有测试通过/失败 | 有独立的"技术经理"角色做 spec 一致性审校 |
| **统筹循环（Orchestrator）** | 无 | 跨 Agent 的 merge/分配/同步/阻塞解锁 |
| **契约先行规则** | 无 | 多端并行开发时，强制先输出共享契约 |
| **Spec 循环的健康检查** | 无 | 连续失败自动标记 blocked，防止死循环 |
| **半自动决策模型** | 要么全自动要么全手动 | 人在 spec 层决策，AI 在代码层执行——这是验证过的最佳平衡点 |

**关键洞察**：竞品解决的是"从 idea 到 spec"（单次生成），我们解决的是"spec 驱动的持续工程"（多轮循环 + 多 Agent 协作 + 质量门控）。这是两个不同的问题。

---

## 四、产品方向判断

### 方向 A：Spec 生成工具（不推荐）

做一个类似 CodeGuide/Kiro 的 spec 生成器。

**不推荐原因**：
- Amazon Kiro 免费 + GitHub Spec Kit 开源 = 无法在价格上竞争
- 纯 spec 生成是 LLM 的基础能力，壁垒低
- 中国市场已有 OpenSpec + CodeBuddy

### 方向 B：AI 工程团队编排器（谨慎）

做一个类似 SpecWeave/Crux 的多 Agent 编排器。

**谨慎原因**：
- 这是"赢家通吃 + 模型厂商会自己做"的赛道
- Claude Code Agent Teams 是 Anthropic 官方在做

### 方向 C：Spec 驱动的"AI 工程方法论 + 工具包"（推荐探索）

**不做一个产品，做一个方法论 + 配套工具包。**

验证的不是一个工具，而是一套**工程方法论**：
- 三层文档结构（requirements → design → tasks）
- Spec 循环（Check → Plan → Do → Doc → Evaluate）
- 多 Agent 协作规范（Worktree 隔离 + 契约先行 + Review Loop）
- 半自动决策模型（人在 spec 层，AI 在代码层）
- 健康检查 + 阻塞管理

**产品形态**：
1. **方法论文档**（开源，建立影响力）— 类似 12-Factor App 或 Semantic Versioning
2. **模板仓库**（开源）— 目录结构 + 文档标准 + 协作规范 + 统筹循环模板
3. **CLI 工具**（开源）— 初始化项目结构、生成 spec 骨架、健康检查、统筹状态报告
4. **培训/咨询**（收费）— 这和 OwlClaw 的商业化路径完全一致

### 方向 C 和 OwlClaw 的关系

```
Spec 方法论（独立产品）          OwlClaw（业务 Agent 基础设施）
├─ 三层文档标准                  ├─ SKILL.md 知识体系
├─ Spec 循环规范     ──产出──→   ├─ 治理层
├─ 多 Agent 协作规范             ├─ 持久执行
└─ CLI 工具包        ──包含──→   └─ 业务接入（scan/migrate）
```

- Spec 方法论用来**开发** OwlClaw（也用来开发任何其他项目）
- OwlClaw 的 SKILL.md 是 spec 方法论产出的一种**特化形式**
- 两者独立但互补：方法论是"怎么做 AI 工程"，OwlClaw 是"怎么让业务系统变聪明"

---

## 五、中国市场的独特机会

"国内稳定跑这个要的技术门槛还挺高"——这恰恰是机会：

| 门槛 | 竞品现状 | 我们的优势 |
|------|---------|-----------|
| 稳定翻墙 | CodeGuide/Kiro/Spec Kit 全部依赖海外 API | 方案已考虑 LiteLLM 本地+云端混合路由 |
| 中文 spec 支持 | 竞品全英文，OpenSpec 有中文但不够深 | 三层文档标准天然中文 |
| 工作流编排 | 竞品假设单人单 Agent | 有完整的多 Agent 协作规范 |
| 落地培训 | 竞品是 SaaS，无本地服务 | 商业化路径本就包含培训/咨询 |

---

## 六、建议的下一步

1. **整理方法论文档** — 把 Spec 循环、统筹循环、三层文档标准抽取为独立的、项目无关的方法论文档
2. **创建模板仓库** — 一个干净的 GitHub 模板仓库，包含骨架 + 模板 + worktree 配置 + spec 循环 rules
3. **写一篇文章** — "从 Vibe Coding 到 Spec Engineering：一个人如何用 AI 团队开发生产级软件"
4. **评估 CLI 工具** — 是否值得做一个 `speceng init` / `speceng check` / `speceng status` 的 CLI

**暂不建议**：
- 不急着做 SaaS 产品（市场已有太多，且大厂免费）
- 不急着做 Agent 编排器（等 Claude Code Agent Teams 稳定后再评估）
- 不急着定目标用户（先发文章/模板，看谁来用）

---

## 七、风险提示

- **方法论产品的变现难度高** — 12-Factor App 影响了整个行业但没直接赚钱。变现靠培训/咨询/衍生工具
- **AI 工程方法论迭代极快** — 今天验证的工作流，6 个月后可能被新工具颠覆。方法论需要持续更新
- **和 OwlClaw 的精力分配** — OwlClaw 本身还在开发中，同时做两个产品需要评估资源

---

**维护者**: yeemio
**下次更新**: M5 Max 到手后 / 方法论文档完成后
