# 罐装机数字孪生 — 统筹规划

> **角色**：技术负责人 / 统筹规划  
> **版本**: v1.0.0  
> **最后更新**: 2026-03-11  
> **真源**：`docs/DIGITAL_TWIN_PLAN.md`、`.kiro/specs/sierac-twin-phase1/`、`.kiro/specs/sierac-twin-phase2/`

---

## 一、项目定位与边界

| 项目 | 路径 | 说明 |
|------|------|------|
| **罐装机数字孪生** | `sierac-twin/` | 独立子项目，独立 package.json、独立构建与部署 |
| 总体规划 | `docs/DIGITAL_TWIN_PLAN.md` | 落地规划、技术架构、数据模型、API、分阶段路线 |
| 3D 模型需求 | `docs/3D_MODEL_REQUEST.md` | 向厂商索要 glTF/GLB 的说明 |

**做什么**：可交互 3D 设备查看器 + 运行数据面板；数据接口抽象（Mock/真实可切换）。  
**不做**：反向控制设备；与 Sierac-tm 激励系统、sierac-mes 强耦合；Phase 1/2 不做多设备管理。

---

## 二、阶段总览与当前状态

| 阶段 | Spec 路径 | 状态 | 任务进度 | 备注 |
|------|------------|------|----------|------|
| **Phase 1** | `.kiro/specs/sierac-twin-phase1/` | ✅ 已完成 | 42/42 | 图片方案 3D 查看器 + 模拟数据面板，已验收 |
| **Phase 2** | `.kiro/specs/sierac-twin-phase2/` | 📋 未开始 | 0/34 | 3D 模型孪生体；部分工作不依赖模型可先做 |
| **Phase 3** | 见 DIGITAL_TWIN_PLAN | 规划中 | — | 真实数据接入（OPC-UA/MQTT/Modbus），需工厂配合 |

---

## 三、Phase 2 工作分解与可并行块

Phase 2 共 **34 个任务**，按「是否依赖厂商 3D 模型」拆成两条线：

### 3.1 不依赖模型 — 可立即开始（建议优先）

| 模块 | 预估 | 任务数 | 说明 |
|------|------|--------|------|
| **Section 1：历史趋势** | 3 天 | ~12 | 后端 HistoryBuffer + 历史 API + 前端 HistoryChart、useHistory |
| **Section 2：部件交互框架** | 4 天 | ~15 | partMapping、usePartInteraction、PartInteraction、PartInfoPopup、PresetViews、AlarmHighlight（用 placeholder 几何体测试） |

**并行策略**：单人在同一代码库内可按「先 Section 1，再 Section 2」顺序；若多 Agent，可拆成「Agent A：历史趋势」「Agent B：部件交互框架」，注意共享边界（见下）。

### 3.2 依赖模型 — 关键路径（模型到位后）

| 模块 | 预估 | 任务数 | 阻塞条件 |
|------|------|--------|----------|
| **Section 3：3D 模型集成** | 5 天 | ~10 | 厂商交付 glTF/GLB；或 Blender 转换 + 放入 `public/models/filler.glb` |
| **Section 4：测试与优化** | 2 天 | ~7 | 依赖 Section 1–3 完成 |

### 3.3 文件边界（防冲突）

若多 Agent 并行 Section 1 与 Section 2：

| 共享/可能重叠 | Agent 1（历史） | Agent 2（部件交互） |
|---------------|------------------|----------------------|
| `server/main.py` | 仅新增 history 端点 | 不修改 |
| `server/mock_engine.py` | 仅 tick 时 append history_buffer | 不修改 |
| `sierac-twin/src/` 布局 | 仅 `services/api.ts`、`hooks/useHistory.ts`、`components/panel/HistoryChart.tsx`、TwinLayout 底部集成 | 仅 `config/`、`hooks/usePartInteraction.ts`、`components/viewer/Part*.tsx`、PresetViews、AlarmHighlight |
| `TwinLayout.tsx` | 底部集成 HistoryChart | 不修改布局结构，或约定仅一方改 TwinLayout |

建议：**先 Section 1 再 Section 2**，可避免 TwinLayout 同时被两人改；若必须并行，在 ORCHESTRATION 或 tasks 中明确「TwinLayout 由历史模块负责人集成，部件模块只提供子组件」。

---

## 四、依赖与阻塞

| 依赖项 | 影响 | 负责方 |
|--------|------|--------|
| 厂商交付 3D 模型（glTF/GLB） | Section 3 无法启动 | 商务/项目 |
| 模型部件命名与 partMapping 一致 | 部件交互、告警高亮依赖 | 开发 + 厂商/Blender |
| Blender（若需格式转换） | STEP/IGES/FBX → GLB | 开发 |
| `@react-three/postprocessing` | 部件 Outline 效果 | 开发（npm 已列在 Phase 2） |

**当前无阻塞**：Section 1 与 Section 2 可立即开工。

---

## 五、建议推进顺序（单线）

1. **Section 1：历史趋势**（3 天）  
   - 后端：`server/history_buffer.py`、mock_engine 写入、`GET .../history`  
   - 前端：`fetchHistory`、`useHistory`、`HistoryChart`，TwinLayout 集成  
   - 测试：`test_history_buffer.py`、history 端点测试  

2. **Section 2：部件交互框架**（4 天）  
   - 配置与类型：`partMapping.ts`、`modelConfig.ts`、equipment 类型扩展  
   - 交互与 UI：`usePartInteraction`、PartInteraction、PartInfoPopup、PresetViews、AlarmHighlight（placeholder）  

3. **Section 3：3D 模型集成**（模型到位后，5 天）  
   - 模型准备与放入 `public/models/filler.glb`  
   - ModelViewer、EquipmentViewer 条件渲染、集成 PartInteraction + AlarmHighlight  
   - 联调与验收  

4. **Section 4：测试与优化**（2 天）  
   - 性能、回归、验收清单  

---

## 六、与 SPEC_TASKS_SCAN 的关系

- **cursor-admin** 相关 spec 由 `.kiro/specs/SPEC_TASKS_SCAN.md` 统一扫描与循环。
- **数字孪生** 为独立子项目，本文件（`sierac-twin/ORCHESTRATION.md`）为孪生专项统筹入口；Phase 任务清单以各 phase 的 `tasks.md` 为准。
- 若希望统一入口：可在 SPEC_TASKS_SCAN 中增加「sierac-twin-phase2」一行，检查点指向本目录或 phase2 的 tasks.md。

---

## 七、下一步行动（统筹视角）

| 优先级 | 行动 | 执行方 |
|--------|------|--------|
| 1 | 启动 Phase 2 Section 1（历史趋势） | 开发 / Agent |
| 2 | 启动 Phase 2 Section 2（部件交互框架），可与 Section 1 串行或按边界并行 | 开发 / Agent |
| 3 | 持续跟进厂商 3D 模型交付，模型到位后启动 Section 3 | 项目 / 开发 |
| 4 | 每完成一个 Section 更新 `sierac-twin-phase2/tasks.md` 勾选与检查点 | 开发 / 统筹 |

回复「**统筹**」或「**继续**」可执行下一轮统筹循环（检查进度、更新检查点、分配下一批任务）。

---

**维护者**: yeemio  
**文档引用**: `docs/DIGITAL_TWIN_PLAN.md`、`.kiro/specs/sierac-twin-phase2/tasks.md`
