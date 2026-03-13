# Tasks: 罐装机数字孪生 Phase 2 — 3D 模型孪生体

> **状态**：开发完成（待人工性能/验收）  
> **预估工作量**：15–20 天（模型到位后）  
> **最后更新**：2026-03-12  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选（见规范 §1.4、§4.5）。

---

## 进度概览

- **总任务数**：34
- **已完成**：32（Section 1–4 已实现）
- **进行中**：0
- **未开始**：2（4.1.1/4.1.2 需人工性能验收）

---

## 1. 历史趋势功能（3 天，可在模型到位前并行）

### 1.1 后端历史缓冲
- [x] 1.1.1 创建 `server/history_buffer.py`：HistoryBuffer 类
  - deque 环形缓冲区，保留最近 24 小时数据
  - `append(point_id, value, ts)` 追加数据点
  - `query(point_id, hours, interval)` 按时间范围查询 + 降采样
  - `_trim()` 自动清理过期数据
- [x] 1.1.2 修改 `server/mock_engine.py`：tick 时调用 `history_buffer.append()` 写入所有测点值
  - 实现在 main.py 的 tick_loop 中 _append_telemetry_to_history
- [x] 1.1.3 在 `server/main.py` 新增端点：
  - `GET /api/twin/equipment/{id}/history?point_id=speed&hours=4&interval=10`
  - 返回 `{ point_id, point_name, unit, min, max, data: [{timestamp, value}] }`
  - 未知 point_id 返回空 data 数组（不是 404）

### 1.2 前端历史图表
- [x] 1.2.1 创建 `src/services/api.ts` 新增 `fetchHistory()` 函数
- [x] 1.2.2 创建 `src/hooks/useHistory.ts`：按需获取历史数据的 Hook
  - 参数：equipmentId, pointId, hours
  - 切换 pointId 或 hours 时自动重新请求
- [x] 1.2.3 创建 `src/components/panel/HistoryChart.tsx`
  - Recharts LineChart 渲染曲线
  - X 轴时间，Y 轴测点值
  - 正常范围用绿色半透明 ReferenceArea 标注
  - 超限区间用红色 ReferenceArea 标注
  - 时间范围切换按钮组：1h / 4h / 8h / 24h
  - 测点选择下拉框（从 telemetry 列表中选）
- [x] 1.2.4 在 `TwinLayout` 数据面板底部集成 HistoryChart

### 1.3 历史功能测试
- [x] 1.3.1 创建 `server/tests/test_history_buffer.py`
  - test_append_and_query：写入后可查询
  - test_trim_old_data：过期数据自动清理
  - test_query_empty：未知 point_id 返回空
  - test_interval_sampling：降采样正确
- [x] 1.3.2 在 `server/tests/test_api.py` 追加 test_history_endpoint

### 1.4 验证历史功能
- [x] 1.4.1 后端启动运行 60 秒后，history API 返回有数据
- [x] 1.4.2 前端图表正确渲染曲线，切换时间范围正常
- [x] 1.4.3 正常范围和超限区间标注正确

---

## 2. 部件交互框架（4 天，可在模型到位前用 placeholder 测试）

### 2.1 配置与类型
- [x] 2.1.1 创建 `src/config/partMapping.ts`：部件-测点映射配置
  - 当前为滚筒剔除装置：Cube, Unnamed-0004_ASM, Unnamed-0004_ASM.001
- [x] 2.1.2 创建 `src/config/modelConfig.ts`：模型路径、缩放、位置、旋转配置
- [x] 2.1.3 在 `src/types/equipment.ts` 新增 PartMapping, PartInfo 类型

### 2.2 部件交互 Hook
- [x] 2.2.1 创建 `src/hooks/usePartInteraction.ts`
  - Raycaster 检测鼠标悬停部件，返回 hoveredPart，提供 onPartHover/onPartClick 回调
  - 根据 partMap（partMapping 过滤）仅可交互部件响应

### 2.3 部件高亮组件
- [x] 2.3.1 安装 `@react-three/postprocessing` 依赖
- [x] 2.3.2 创建 `src/components/viewer/PartInteraction.tsx`
  - EffectComposer + Outline 悬停描边；cursor pointer 与 tooltip 在 EquipmentViewer

### 2.4 部件参数弹窗
- [x] 2.4.1 创建 `src/components/viewer/PartInfoPopup.tsx`
  - 浮动面板、部件名+测点列表、关闭按钮；从 telemetry 筛选 pointIds

### 2.5 预设视角
- [x] 2.5.1 PresetViews.tsx + PresetCameraController 已实现正面/背面/左侧/右侧/俯视平滑过渡

### 2.6 告警高亮组件
- [x] 2.6.1 告警高亮逻辑在 ModelViewer useFrame 中（emissive critical 闪烁 / warning 常亮）

---

## 3. 3D 模型集成（5 天，模型到位后）

### 3.1 模型准备
- [x] 3.1.1 接收厂商模型文件，确认格式（当前使用 001.glb）
- [x] 3.1.2 如非 glTF：Blender 转换流程见 docs/3D_MODEL_REQUEST.md
- [x] 3.1.3 GLB 已放入 `public/models/001.glb`，modelConfig.path 已配置
- [x] 3.1.4 partMapping 已按 read_glb_nodes.py 输出匹配（Cube, Unnamed-0004_ASM*）

### 3.2 模型渲染组件
- [x] 3.2.1 ModelViewer：useGLTF、光照、partMap、PartInteraction + 告警 emissive
- [x] 3.2.2 EquipmentViewer：VITE_USE_MODEL、Suspense、ViewerErrorBoundary 降级 ImageSphere

### 3.3 集成联调
- [x] 3.3.1–3.3.5 已实现；人工验收：模型外观、悬停/点击、告警高亮、预设视角、数据面板

---

## 4. 测试与优化（2 天）

### 4.1 性能优化
- [ ] 4.1.1 Chrome DevTools Performance 确认渲染 >= 30fps（需人工验证）
- [ ] 4.1.2 模型加载时间 < 5 秒（需人工验证）

### 4.2 回归测试
- [x] 4.2.1 Phase 1 后端测试：pytest tests/ 20 个全部通过
- [x] 4.2.2 Phase 2 history_buffer + history API 测试通过
- [x] 4.2.3 TypeScript 编译无错误
- [x] 4.2.4 Vite 构建成功

---

## 5. 验收清单

### 5.1 功能验收
- [x] glTF 模型加载渲染正常，光照材质合理
- [x] 旋转/缩放/平移/预设视角全部正常
- [x] 部件悬停高亮 + tooltip（当前模型 3 节点）
- [x] 点击部件弹出参数面板，数据正确
- [x] critical 告警部件闪烁红色；warning 橙色常亮
- [x] 告警恢复后部件颜色自动还原
- [x] 历史趋势图表、1h/4h/8h/24h、正常/超限区间标注

### 5.2 非功能验收
- [ ] 渲染帧率 >= 30fps（人工验证）
- [ ] 模型加载 < 5 秒（人工验证）
- [x] Phase 1 所有功能不退化

### 5.3 测试验收
- [x] 后端测试 20/20 通过
- [x] TypeScript 编译 + Vite 构建成功

### 5.4 文档验收
- [x] Phase 2 三层文档完整
- [x] partMapping 与 001.glb 节点匹配
- [ ] 3D_MODEL_REQUEST.md 已发送给厂商（按需）

---

## 6. 依赖与阻塞

### 6.1 依赖
- **设备厂商交付 3D 模型文件**（关键路径，阻塞 Section 3）
- Blender（如需格式转换）
- `@react-three/postprocessing` npm 包

### 6.2 阻塞
- Section 1（历史趋势）和 Section 2（部件交互框架）**不依赖模型**，可立即开始
- Section 3（模型集成）**依赖模型到位**，是关键路径

### 6.3 并行策略

```
立即开始（不依赖模型）          等待模型
├─ Section 1: 历史趋势 (3天)    │
├─ Section 2: 部件交互框架 (4天) │
│   （用 placeholder 几何体测试） │
│                                ↓
│                         厂商交付模型
│                                ↓
└──────────────────────→ Section 3: 模型集成 (5天)
                                ↓
                         Section 4: 测试优化 (2天)
```

---

## 7. 风险

### 7.1 厂商模型交付延迟
- **缓解**：Section 1 + 2 不依赖模型，可先推进；用开源工业模型做技术验证

### 7.2 模型部件未拆分
- **缓解**：在 Blender 中手动拆分（增加 1-2 周），已在 3D_MODEL_REQUEST.md 中明确要求

### 7.3 模型面数过高
- **缓解**：Blender Decimate 减面；Three.js LOD 多层次细节

---

## 8. 参考文档

- `.kiro/specs/sierac-twin-phase2/requirements.md`
- `.kiro/specs/sierac-twin-phase2/design.md`
- `docs/3D_MODEL_REQUEST.md`
- `docs/DIGITAL_TWIN_PLAN.md`

---

**维护者**: yeemio  
**最后更新**: 2026-03-12
