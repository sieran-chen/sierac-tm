# Cursor 规则说明（Sierac-tm）

本工程采用**文档驱动**开发，规范以 **Sierac-tm** 规则为准。

## 生效规则

| 规则文件 | 适用范围 | 说明 |
|----------|----------|------|
| **sierac_architecture.mdc** | cursor-admin/**、docs/**、.kiro/specs/** | 包结构、集成边界、Hook、DB |
| **sierac_principles.mdc** | cursor-admin/** | 语言、代码质量、禁止 TODO/假数据 |
| **sierac_development.mdc** | cursor-admin/** | 依赖、Git、代码风格 |
| **sierac_spec_standards.mdc** | .kiro/** | Spec 三层文档标准 |
| **sierac_testing.mdc** | collector、tests/** | 测试规范 |
| **sierac_database.mdc** | db/**、collector 中 DB 相关 | 迁移与表设计 |

## 架构与 Spec

- **架构真源**：`docs/ARCHITECTURE.md`
- **Spec 规范**：`.kiro/SPEC_DOCUMENTATION_STANDARD.md`
- **任务总览**：`.kiro/specs/SPEC_TASKS_SCAN.md`

---

**最后更新**: 2026-02-25
