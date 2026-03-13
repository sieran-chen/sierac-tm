# OwlSpec — 产品决策空间

> **创建时间**: 2026-03-02
> **状态**: 早期探索（v3.1，需求真源统一）
> **最高原则**: 所有需求来自业务专家。业务专家可以做到很深。研发不翻译需求、不补充需求，只做技术决策。

---

## 这是什么

OwlSpec 是 OwlClaw 品牌体系中的**需求规范化产品**，核心发现：

> **"业务分析"和"研发规范"是两个完全不同的阶段，不应该混在一起。**
> **业务专家用 Skill + 云端大模型做需求分析（输出数据流、线框图、业务规则）；**
> **研发专家拿到交付物后，用 Spec 三件套做架构设计和开发规范。**

### 两阶段模型

```
阶段 1：业务分析（业务专家）
  输入：Excel 表格、流程文档、系统截图
  工具：OwlSpec Business Analyzer Skill + 云端大模型
  输出：数据流图、信息流图、HTML 线框图、业务规则清单
  ──────────── 交付物移交 ────────────
阶段 2：研发规范（研发专家）
  输入：阶段 1 的交付物
  工具：Cursor/Claude Code + OwlSpec Spec 循环
  输出：requirements.md / design.md / tasks.md
```

### 品牌体系

```
OwlSpec  — 看清需求：业务分析 + 研发规范（两阶段桥梁）
OwlClaw  — 精准执行：结构化规范 → AI Agent 自主决策（运行时）
OpenClaw — 连接万物：AI 助理 + IM 入口（沟通层）
OwlHub   — 知识聚集：Skills 生态市场（生态层）
```

---

## 核心假设（待验证）

1. **业务专家 + AI 可以做到字段级的精确需求** — 不再是"说个大概"
2. **需求真源统一能根本性减少研发返工** — 研发不猜就不会猜错
3. **阶段 1 用 Skill 就够了** — 云端大模型已有足够的分析能力，Skill 引导业务专家做到足够深
4. **Mermaid/HTML 是最 AI 友好的交付格式** — 文本格式可版本控制，AI 可直接解析
5. **Spec 三件套属于研发阶段** — 业务专家输出需求真源，研发做技术决策
6. **中国市场有独特机会** — 翻墙门槛 + 中文原生 + 落地培训

---

## 文件索引

### 核心产品

| 文件 | 内容 | 状态 |
|------|------|------|
| **[skills/business-analyzer/SKILL.md](skills/business-analyzer/SKILL.md)** | **Business Analyzer Skill（阶段 1 核心产品）** | **v0.1 已完成** |

### 实战案例

| 文件 | 内容 | 状态 |
|------|------|------|
| **[examples/sierac-mes/SOURCE.md](examples/sierac-mes/SOURCE.md)** | **Sierac 设备制造 MOM 系统需求真源** | **v0.1 草稿** |

### 产品文档

| 文件 | 内容 | 状态 |
|------|------|------|
| **[TWO_PHASE_MODEL.md](TWO_PHASE_MODEL.md)** | **两阶段模型（核心架构文档）** | **v3 当前** |
| [PRODUCT_ANALYSIS.md](PRODUCT_ANALYSIS.md) | 产品分析（含行业调研） | v2（待更新至 v3） |
| [PRODUCT_DECISIONS.md](PRODUCT_DECISIONS.md) | 产品决策记录（ADR 风格） | 持续更新 |
| [COMPETITIVE_WATCH.md](COMPETITIVE_WATCH.md) | 竞品动态追踪 | 持续更新 |
| [METHODOLOGY.md](METHODOLOGY.md) | OwlSpec 方法论文档 | v0.2（待更新至 v0.3） |
| [TEMPLATE_REPO_DESIGN.md](TEMPLATE_REPO_DESIGN.md) | 模板仓库设计 | v2 设计稿 |

### 已归档

| 文件 | 说明 |
|------|------|
| SPEC_DRIVEN_PRODUCT_ANALYSIS.md | 第一版分析（已被 PRODUCT_ANALYSIS.md 替代） |
| SPEC_ENGINEERING_METHODOLOGY.md | 第一版方法论（已被 METHODOLOGY.md 替代） |
| SPEC_ENGINEERING_TEMPLATE_REPO.md | 第一版模板设计（已被 TEMPLATE_REPO_DESIGN.md 替代） |

---

## 下一步行动

- [x] **写 Business Analyzer Skill**：阶段 1 的核心产品 → `skills/business-analyzer/SKILL.md`
- [x] 用真实业务表格测试 Skill 效果 → `examples/sierac-mes/SOURCE.md`
- [ ] 业务专家审核需求真源文档（SOURCE.md 中有 13 个待确认项）
- [ ] 写第一篇文章："AI 让业务专家做到很深：从 Excel 到完整需求真源"
- [ ] 等 M5 Max 到手后，用两阶段模型搭建 AI 工程团队，作为实战案例

---

**维护者**: yeemio
