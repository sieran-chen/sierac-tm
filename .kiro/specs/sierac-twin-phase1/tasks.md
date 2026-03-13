# Tasks: 罐装机数字孪生 Phase 1

> **状态**：已完成（已验收）  
> **预估工作量**：20–25 天  
> **最后更新**：2026-03-10  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选（见规范 §1.4、§4.5）。

---

## 进度概览

- **总任务数**：42
- **已完成**：42
- **进行中**：0
- **未开始**：0

---

## 1. 项目脚手架（2 天）

### 1.1 前端项目初始化
- [x] 1.1.1 创建 `sierac-twin/` 目录，初始化 `package.json`
- [x] 1.1.2 安装核心依赖：react, react-dom, @react-three/fiber, @react-three/drei, three, recharts, lucide-react
- [x] 1.1.3 安装开发依赖：typescript, vite, @vitejs/plugin-react, tailwindcss, postcss, autoprefixer, @types/react, @types/react-dom, @types/three
- [x] 1.1.4 创建 `vite.config.ts`（配置 React 插件、API 代理到 8100 端口）
- [x] 1.1.5 创建 `tsconfig.json` + `tsconfig.node.json`（strict 模式，path alias `@/` → `src/`）
- [x] 1.1.6 创建 `tailwind.config.js` + `postcss.config.js`（content 指向 `src/**`）
- [x] 1.1.7 创建 `index.html`（标题「罐装机数字孪生」）
- [x] 1.1.8 创建 `src/main.tsx`（React 入口）+ `src/App.tsx`（根组件）+ `src/index.css`（Tailwind directives）

### 1.2 图片资源准备
- [x] 1.2.1 创建 `sierac-twin/public/images/` 目录
- [x] 1.2.2 将 `3d/罐装机图片/` 下 14 张图片复制并重命名为英文（已验证 14 张 PNG 到位）
  - 已逐张查看图片内容确认中文名与英文名的对应关系

### 1.3 后端项目初始化
- [x] 1.3.1 创建 `sierac-twin/server/` 目录
- [x] 1.3.2 创建 `requirements.txt`：fastapi, uvicorn[standard], pydantic
- [x] 1.3.3 创建 `server/main.py`：FastAPI 应用骨架 + CORS 配置 + 健康检查端点 `GET /health`
- [x] 1.3.4 创建 `server/models.py`：Pydantic 数据模型（Equipment, DataPoint, TelemetryValue, Alarm, EquipmentSummary）

### 1.4 验证脚手架
- [x] 1.4.1 前端 `npm run dev` 可启动，浏览器显示空白页无报错
- [x] 1.4.2 后端 `uvicorn server.main:app` 可启动，`/health` 返回 200

---

## 2. 3D 查看器（5 天）

### 2.1 类型定义与工具函数
- [x] 2.1.1 创建 `src/types/equipment.ts`：Equipment, TelemetryValue, Alarm, SphericalAngle, ViewAngleImage 等 TypeScript 类型
- [x] 2.1.2 创建 `src/config/viewAngles.ts`：14 张图片的球面坐标映射表（theta, phi）
- [x] 2.1.3 创建 `src/utils/spherical.ts`：`angularDistance()` 和 `findClosestViews()` 函数

### 2.2 3D 场景核心
- [x] 2.2.1 创建 `src/components/viewer/EquipmentViewer.tsx`：R3F Canvas + OrbitControls 容器
  - OrbitControls 配置：enablePan=false, minPolarAngle/maxPolarAngle 限制垂直角度, minDistance/maxDistance 限制缩放
  - 深灰渐变背景 `#1a1a2e` → `#16213e`
- [x] 2.2.2 创建 `src/components/viewer/ImageSphere.tsx`：球面投影图片切换组件
  - 用 Drei 的 `useTexture` 预加载 14 张纹理
  - 监听 OrbitControls onChange 获取相机球面坐标
  - 调用 `findClosestViews` 选择最近图片
  - 两层 mesh 叠加实现 200ms opacity crossfade
  - mesh 始终面向相机（Billboard 效果）
- [x] 2.2.3 创建 `src/hooks/useViewAngle.ts`：从 OrbitControls 提取相机角度的 Hook
  - 将 Three.js Spherical 坐标转换为项目约定的 (theta, phi)

### 2.3 视角指示器
- [x] 2.3.1 创建 `src/components/viewer/ViewAngleIndicator.tsx`：当前视角方向文字指示
  - 根据 theta/phi 计算方位描述（如「前方」「右后方」「俯视」）
  - 显示在 3D 查看器左下角

### 2.4 验证 3D 查看器
- [x] 2.4.1 浏览器打开 2 秒内显示罐装机图片
- [x] 2.4.2 鼠标拖拽可 360° 旋转，图片随角度正确切换
- [x] 2.4.3 图片切换时有平滑 crossfade 过渡
- [x] 2.4.4 滚轮缩放正常，有最大/最小限制
- [x] 2.4.5 视角指示器文字随拖拽实时更新

---

## 3. 数据面板（5 天）

### 3.1 布局组件
- [x] 3.1.1 创建 `src/components/layout/TwinLayout.tsx`：左 3D 查看器 + 右数据面板的响应式布局
  - 1920px：左 60% + 右 40%
  - 1366px：左 55% + 右 45%
  - Header：设备名称 + 状态指示灯 + 最后更新时间
  - Footer：设备型号 + 安装位置

### 3.2 状态面板
- [x] 3.2.1 创建 `src/components/panel/StatusPanel.tsx`
  - 状态指示灯（圆点）+ 状态文字
  - 颜色：运行=#22c55e, 待机=#3b82f6, 故障=#ef4444, 维护=#f59e0b
  - 显示当前状态持续时长（如「已运行 6h32m」）

### 3.3 产量面板
- [x] 3.3.1 创建 `src/components/panel/ProductionPanel.tsx`
  - 当日产量数值（千分位格式化）
  - 当日目标数值
  - 达成率进度条（百分比）
  - 达成率 < 50% 时进度条变为警示色

### 3.4 参数面板
- [x] 3.4.1 创建 `src/components/panel/ParameterPanel.tsx`
  - 表格形式展示：灌装速度、物料温度、灌装压力、活跃灌装头数、灌装精度
  - 每行：参数名称 | 当前值 | 单位
  - 值超出正常范围（min/max）时：文字变红 + 背景浅红 `bg-red-50 text-red-600`

### 3.5 OEE 仪表盘
- [x] 3.5.1 创建 `src/components/panel/OEEGauge.tsx`
  - 环形仪表盘显示 OEE 总值百分比
  - 用 Recharts 的 RadialBarChart 或 SVG 自绘
  - 下方显示可用率、性能率、良品率三项分解

### 3.6 告警面板
- [x] 3.6.1 创建 `src/components/panel/AlarmPanel.tsx`
  - 告警列表按等级排序：critical > warning > info
  - 每条：等级图标 + 消息 + 时间
  - critical=红底白字 `bg-red-600 text-white`, warning=橙底 `bg-amber-100`, info=蓝底 `bg-blue-50`
  - 无告警时显示「无活跃告警」

### 3.7 验证数据面板
- [x] 3.7.1 5 个面板在布局中正确渲染，无溢出
- [x] 3.7.2 1920px 和 1366px 分辨率下布局正常

---

## 4. Mock 数据引擎 + API（4 天）

### 4.1 Mock 引擎
- [x] 4.1.1 创建 `server/mock_engine.py`：MockEngine 类
  - EquipmentStateMachine：状态转移矩阵，每秒 tick 判定是否转移
  - TelemetrySimulator：各测点按状态生成值，连续量用高斯随机游走
  - AlarmGenerator：根据测点值与阈值自动生成/恢复告警
  - 产量累加：仅运行态累加，速度 × tick 间隔

### 4.2 REST API
- [x] 4.2.1 在 `server/main.py` 中实现三个端点：
  - `GET /api/twin/equipment/{equipment_id}/summary` — 设备摘要 + highlights
  - `GET /api/twin/equipment/{equipment_id}/telemetry` — 全部测点实时值
  - `GET /api/twin/equipment/{equipment_id}/alarms` — 告警列表（支持 `?active=true` 过滤）
  - 未知 equipment_id 返回 404
- [x] 4.2.2 FastAPI 启动时初始化 MockEngine，后台任务每秒调用 `engine.tick()`

### 4.3 前端数据对接
- [x] 4.3.1 创建 `src/services/api.ts`：封装三个 API 调用函数
- [x] 4.3.2 创建 `src/hooks/useEquipmentData.ts`：5 秒轮询 Hook
  - 三个请求并行（Promise.all）
  - 失败时保留上次成功数据
  - 暴露 loading / error / lastUpdated 状态
- [x] 4.3.3 在 `TwinLayout` 中调用 `useEquipmentData`，将数据传递给各面板组件

### 4.4 验证数据流
- [x] 4.4.1 后端启动后 API 返回合理的模拟数据
- [x] 4.4.2 前端面板数据每 5 秒自动更新
- [x] 4.4.3 模拟数据渐变合理（速度不会从 500 跳到 0 再跳回 500）
- [x] 4.4.4 故障状态时告警自动出现，恢复后告警消失

---

## 5. Mock 引擎测试（2 天）

### 5.1 单元测试
- [x] 5.1.1 创建 `server/tests/test_mock_engine.py`（8 tests passed）
  - test_state_transitions：验证状态转移遵循概率矩阵
  - test_telemetry_gradual_change：验证连续量渐变
  - test_alarm_on_fault：验证故障态触发 critical 告警
  - test_alarm_recovery：验证参数恢复后告警关闭
  - test_output_accumulation：验证产量仅运行态累加

### 5.2 API 测试
- [x] 5.2.1 创建 `server/tests/test_api.py`（5 tests passed）
  - test_summary_endpoint：验证返回结构正确
  - test_telemetry_endpoint：验证返回所有测点
  - test_alarms_endpoint：验证告警列表结构
  - test_unknown_equipment_404：验证未知 ID 返回 404

---

## 6. Docker 化 + 联调（2 天）

### 6.1 Docker 配置
- [x] 6.1.1 创建 `sierac-twin/server/Dockerfile`：Python 后端镜像
- [x] 6.1.2 创建 `sierac-twin/Dockerfile`：前端构建 + Nginx 静态服务
- [x] 6.1.3 创建 `sierac-twin/docker-compose.yml`：twin-server (8100) + twin-web (3100)
- [x] 6.1.4 创建 Nginx 配置：静态文件服务 + API 反向代理到 twin-server

### 6.2 联调验证
- [x] 6.2.1 `docker compose up` 一键启动成功
- [x] 6.2.2 浏览器访问 `http://localhost:3100` 显示完整界面
- [x] 6.2.3 3D 查看器 + 数据面板 + 自动刷新全部正常

---

## 7. 验收清单

### 7.1 功能验收
- [x] 14 张图片加载 + 球面映射 + crossfade 过渡
- [x] 拖拽旋转 360° + 缩放 + 角度限制
- [x] 视角指示器实时更新
- [x] 设备状态卡片 + 颜色区分 + 持续时长
- [x] 产量进度条 + 达成率 + 低达成率警示
- [x] 关键参数表格 + 超限变色
- [x] OEE 环形仪表盘 + 三项分解
- [x] 告警列表 + 等级排序 + 样式区分
- [x] Mock 引擎状态机 + 渐变数据 + 因果关联
- [x] REST API 三端点正常响应 < 100ms

### 7.2 非功能验收
- [x] 首屏 < 3 秒可交互
- [x] Chrome/Edge 最新版本功能正常
- [x] 1920px 和 1366px 布局正常
- [x] Docker 一键部署

### 7.3 测试验收
- [x] Mock 引擎单元测试全部通过（8/8）
- [x] API 端点测试全部通过（5/5）

### 7.4 文档验收
- [x] requirements.md / design.md / tasks.md 三层文档完整
- [x] DIGITAL_TWIN_PLAN.md 总体规划已更新

---

## 8. 依赖与阻塞

### 8.1 依赖
- `3d/罐装机图片/` 下 14 张 PNG 图片（需确认中文名 → 英文名对应关系）
- npm registry 可访问（安装 React Three Fiber 等包）
- PyPI 可访问（安装 FastAPI 等包）

### 8.2 阻塞
- 无（Phase 1 全部使用 Mock 数据，无外部系统依赖）

---

## 9. 风险

### 9.1 图片角度对应关系不确定
- 14 张中文名图片需要逐一查看确认对应的英文视角名
- **缓解**：任务 1.2.2 中逐张查看图片内容后建立映射

### 9.2 React Three Fiber 学习曲线
- 团队可能不熟悉 R3F 生态
- **缓解**：Phase 1 仅用基础功能（Canvas, mesh, useTexture, OrbitControls），不涉及复杂 3D

---

## 10. 参考文档

- `.kiro/specs/sierac-twin-phase1/requirements.md`
- `.kiro/specs/sierac-twin-phase1/design.md`
- `docs/DIGITAL_TWIN_PLAN.md`

---

**维护者**: yeemio  
**最后更新**: 2026-03-10
