# Design: 罐装机数字孪生 Phase 1

> **目标**：基于多角度图片实现可交互 3D 查看器 + 模拟数据面板  
> **状态**：设计完成  
> **最后更新**：2026-03-10

---

## 1. 架构设计

### 1.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│  浏览器 (React + Vite)                                        │
│  ┌────────────────────────┐  ┌─────────────────────────────┐ │
│  │  EquipmentViewer        │  │  DataPanel                  │ │
│  │  ├─ ImageSphere         │  │  ├─ StatusPanel             │ │
│  │  ├─ OrbitControls       │  │  ├─ ProductionPanel         │ │
│  │  └─ ViewAngleIndicator  │  │  ├─ ParameterPanel          │ │
│  └────────────┬───────────┘  │  ├─ OEEGauge                │ │
│               │              │  └─ AlarmPanel               │ │
│               │              └──────────┬──────────────────┘ │
│               └──────────┬──────────────┘                    │
│                          │ useEquipmentData() — 5s polling   │
└──────────────────────────┼────────────────────────────────────┘
                           │ HTTP REST
┌──────────────────────────▼────────────────────────────────────┐
│  后端 (FastAPI + Uvicorn)                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  twin_api.py — REST endpoints                            │ │
│  │  ├─ GET /api/twin/equipment/{id}/summary                 │ │
│  │  ├─ GET /api/twin/equipment/{id}/telemetry               │ │
│  │  └─ GET /api/twin/equipment/{id}/alarms                  │ │
│  └──────────────────────┬───────────────────────────────────┘ │
│                          │                                     │
│  ┌──────────────────────▼───────────────────────────────────┐ │
│  │  mock_engine.py — 状态机驱动的模拟数据引擎                  │ │
│  │  ├─ EquipmentStateMachine (状态转移)                      │ │
│  │  ├─ TelemetrySimulator (测点模拟)                         │ │
│  │  └─ AlarmGenerator (告警生成)                             │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

#### 组件 1：EquipmentViewer（3D 查看器）

**职责**：渲染 3D 场景，管理相机控制，根据相机角度切换图片。

**接口定义**：
```typescript
interface EquipmentViewerProps {
  images: ViewAngleImage[];
  onAngleChange?: (angle: SphericalAngle) => void;
}

interface ViewAngleImage {
  id: string;
  src: string;
  theta: number;  // 水平角 0-360°（0=前方，顺时针）
  phi: number;    // 垂直角 -90° 到 +90°（0=水平，正=上方）
}

interface SphericalAngle {
  theta: number;
  phi: number;
}
```

#### 组件 2：DataPanel（数据面板）

**职责**：展示设备运行数据，包含 5 个子面板。

**接口定义**：
```typescript
interface DataPanelProps {
  equipmentId: string;
}

// useEquipmentData Hook 返回值
interface EquipmentData {
  equipment: Equipment;
  telemetry: TelemetryValue[];
  alarms: Alarm[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}
```

#### 组件 3：MockEngine（模拟数据引擎）

**职责**：基于状态机生成逼真的设备运行模拟数据。

**接口定义**：
```python
class MockEngine:
    def get_summary(self, equipment_id: str) -> dict:
        """Return equipment summary with highlights."""

    def get_telemetry(self, equipment_id: str) -> list[dict]:
        """Return all data point current values."""

    def get_alarms(self, equipment_id: str, active_only: bool = True) -> list[dict]:
        """Return alarm list."""

    def tick(self) -> None:
        """Advance simulation by one step (called every second)."""
```

---

## 2. 实现细节

### 2.1 文件结构

```
sierac-twin/
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── public/
│   └── images/
│       ├── front.png              # 前
│       ├── back.png               # 后
│       ├── left.png               # 左
│       ├── right.png              # 右
│       ├── top.png                # 上
│       ├── bottom.png             # 下
│       ├── front-left.png         # 左前方
│       ├── front-right.png        # 右前方
│       ├── back-left.png          # 左后方
│       ├── back-right.png         # 右后方
│       ├── top-front.png          # 上前方
│       ├── top-back.png           # 上后方
│       ├── top-left.png           # 上左方
│       └── top-right.png          # 上右方
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css                  # Tailwind directives
│   ├── components/
│   │   ├── viewer/
│   │   │   ├── EquipmentViewer.tsx
│   │   │   ├── ImageSphere.tsx
│   │   │   └── ViewAngleIndicator.tsx
│   │   ├── panel/
│   │   │   ├── StatusPanel.tsx
│   │   │   ├── ProductionPanel.tsx
│   │   │   ├── ParameterPanel.tsx
│   │   │   ├── AlarmPanel.tsx
│   │   │   └── OEEGauge.tsx
│   │   └── layout/
│   │       └── TwinLayout.tsx
│   ├── hooks/
│   │   ├── useEquipmentData.ts
│   │   └── useViewAngle.ts
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── equipment.ts
│   ├── config/
│   │   └── viewAngles.ts          # 14 张图的球面坐标映射
│   └── utils/
│       └── spherical.ts
├── server/
│   ├── main.py
│   ├── mock_engine.py
│   ├── models.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── Dockerfile                     # 前端 Dockerfile (nginx)
```

### 2.2 球面投影 + 视角切换实现

**核心算法**：将 14 张图片映射到球面坐标系，相机旋转时计算与每张图片视角的角度距离，选择最近的图片显示。

**图片球面坐标映射**：

```typescript
// config/viewAngles.ts
export const VIEW_ANGLES: ViewAngleImage[] = [
  { id: "front",       src: "/images/front.png",       theta: 0,   phi: 0 },
  { id: "front-right", src: "/images/front-right.png", theta: 45,  phi: 0 },
  { id: "right",       src: "/images/right.png",       theta: 90,  phi: 0 },
  { id: "back-right",  src: "/images/back-right.png",  theta: 135, phi: 0 },
  { id: "back",        src: "/images/back.png",        theta: 180, phi: 0 },
  { id: "back-left",   src: "/images/back-left.png",   theta: 225, phi: 0 },
  { id: "left",        src: "/images/left.png",        theta: 270, phi: 0 },
  { id: "front-left",  src: "/images/front-left.png",  theta: 315, phi: 0 },
  { id: "top",         src: "/images/top.png",         theta: 0,   phi: 90 },
  { id: "bottom",      src: "/images/bottom.png",      theta: 0,   phi: -90 },
  { id: "top-front",   src: "/images/top-front.png",   theta: 0,   phi: 45 },
  { id: "top-back",    src: "/images/top-back.png",    theta: 180, phi: 45 },
  { id: "top-left",    src: "/images/top-left.png",    theta: 270, phi: 45 },
  { id: "top-right",   src: "/images/top-right.png",   theta: 90,  phi: 45 },
];
```

**角度距离计算**：

```typescript
// utils/spherical.ts
export function angularDistance(
  a: SphericalAngle,
  b: SphericalAngle
): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const phiA = toRad(a.phi), phiB = toRad(b.phi);
  const dTheta = toRad(a.theta - b.theta);
  return Math.acos(
    Math.sin(phiA) * Math.sin(phiB) +
    Math.cos(phiA) * Math.cos(phiB) * Math.cos(dTheta)
  );
}

export function findClosestViews(
  cameraAngle: SphericalAngle,
  views: ViewAngleImage[],
  count: number = 2
): { view: ViewAngleImage; distance: number }[] {
  return views
    .map((view) => ({
      view,
      distance: angularDistance(cameraAngle, { theta: view.theta, phi: view.phi }),
    }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, count);
}
```

**视角切换组件**：

```typescript
// components/viewer/ImageSphere.tsx — 核心逻辑
// 1. 监听 OrbitControls 的 onChange 事件获取相机球面坐标
// 2. 调用 findClosestViews 获取最近的图片
// 3. 当最近图片变化时，做 200ms opacity crossfade
// 4. 用 R3F 的 <mesh> + <planeGeometry> 承载图片纹理，始终面向相机
```

**关键点**：
- OrbitControls 的 `onChange` 回调中提取相机的 spherical 坐标（Three.js Spherical 类）
- 将 Three.js 的 spherical (r, phi, theta) 转换为本项目的约定（theta=水平角，phi=垂直角）
- crossfade 用两层 `<mesh>` 叠加，通过 material.opacity 动画实现
- 图片纹理用 `useTexture` (Drei) 预加载，避免运行时加载延迟

### 2.3 Mock 数据引擎实现

**状态机设计**：

```python
# server/mock_engine.py

class EquipmentState(Enum):
    RUNNING = "running"
    IDLE = "idle"
    FAULT = "fault"
    MAINTENANCE = "maintenance"

TRANSITION_MATRIX = {
    EquipmentState.RUNNING: {
        EquipmentState.RUNNING: 0.95,
        EquipmentState.IDLE: 0.02,
        EquipmentState.FAULT: 0.02,
        EquipmentState.MAINTENANCE: 0.01,
    },
    EquipmentState.IDLE: {
        EquipmentState.RUNNING: 0.30,
        EquipmentState.IDLE: 0.65,
        EquipmentState.MAINTENANCE: 0.05,
    },
    EquipmentState.FAULT: {
        EquipmentState.FAULT: 0.70,
        EquipmentState.MAINTENANCE: 0.30,
    },
    EquipmentState.MAINTENANCE: {
        EquipmentState.MAINTENANCE: 0.80,
        EquipmentState.IDLE: 0.20,
    },
}
```

**测点模拟规则**：

| 测点 | 运行态 | 待机态 | 故障态 | 维护态 | 波动方式 |
|------|--------|--------|--------|--------|----------|
| speed | 200-600 | 0 | 0 | 0 | 高斯随机游走 ±5/tick |
| temperature | 2-8 | 环境温度 20 | 上升趋势 | 环境温度 | 高斯 ±0.2/tick |
| pressure | 2.5-4.0 | 0 | 异常值 | 0 | 高斯 ±0.05/tick |
| today_output | 累加 | 不变 | 不变 | 不变 | speed × tick_interval |
| oee | 70-95 | 下降 | 急降 | 不变 | 滑动平均 |

**告警生成规则**：
- 温度 > 8°C → warning；> 12°C → critical
- 压力 < 2.0 bar 或 > 4.5 bar → warning
- 状态 = fault → critical 告警自动生成
- 告警恢复：参数回到正常范围后 30 秒自动关闭

---

## 3. 数据流

### 3.1 前端数据获取流程

```
App 启动
  ↓
useEquipmentData("filler-001") Hook 初始化
  ↓
setInterval(5000) 开始轮询
  ↓
每 5 秒:
  ├─ fetch /api/twin/equipment/filler-001/summary
  ├─ fetch /api/twin/equipment/filler-001/telemetry
  └─ fetch /api/twin/equipment/filler-001/alarms?active=true
  ↓
更新 React state → 各面板组件 re-render
```

**关键点**：
- 三个请求并行发送（Promise.all）
- 任一请求失败不影响其他面板显示（独立错误处理）
- 网络断开时保留最后一次成功数据，显示「数据更新失败」提示

### 3.2 后端 Mock 数据流

```
FastAPI 启动
  ↓
MockEngine 初始化（设备初始状态 = IDLE）
  ↓
BackgroundTask: 每 1 秒调用 engine.tick()
  ├─ 状态机转移判定
  ├─ 各测点值更新（渐变）
  ├─ 告警检测与生成/恢复
  └─ 产量累加（仅运行态）
  ↓
API 请求到达 → 读取 engine 当前快照 → 返回 JSON
```

---

## 4. 错误处理

### 4.1 前端网络错误

**场景**：后端不可达或响应超时

**处理**：
```typescript
// hooks/useEquipmentData.ts
// 请求超时设为 3 秒
// 失败时保留上次成功数据
// 连续 3 次失败后显示全屏错误提示（含重试按钮）
// 恢复后自动继续轮询
```

### 4.2 后端异常

**场景**：Mock 引擎内部错误

**处理**：
```python
# server/twin_api.py
# 所有端点用 try/except 包裹
# 异常时返回 HTTP 500 + 错误描述 JSON
# Mock 引擎 tick 异常时 log 错误但不中断后续 tick
```

### 4.3 图片加载失败

**场景**：某张图片文件缺失或损坏

**处理**：
```typescript
// components/viewer/ImageSphere.tsx
// useTexture 加载失败时跳过该视角
// 至少需要 6 张基础图片（前后左右上下），否则显示错误提示
```

---

## 5. 配置

### 5.1 前端环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8100` |
| `VITE_POLL_INTERVAL` | 轮询间隔（毫秒） | `5000` |
| `VITE_EQUIPMENT_ID` | 默认设备 ID | `filler-001` |

### 5.2 后端环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TWIN_HOST` | 监听地址 | `0.0.0.0` |
| `TWIN_PORT` | 监听端口 | `8100` |
| `TWIN_TICK_INTERVAL` | 模拟引擎 tick 间隔（秒） | `1` |
| `TWIN_CORS_ORIGINS` | CORS 允许来源 | `*` |

### 5.3 Docker Compose

```yaml
# docker-compose.yml
services:
  twin-server:
    build: ./server
    ports:
      - "8100:8100"
    environment:
      - TWIN_PORT=8100

  twin-web:
    build: .
    ports:
      - "3100:80"
    depends_on:
      - twin-server
```

前端端口 3100，后端端口 8100，避免与 Sierac-tm 主项目冲突（主项目用 3000/8000）。

---

## 6. 测试策略

### 6.1 后端单元测试

```python
# server/tests/test_mock_engine.py

def test_state_machine_transitions():
    """Verify state transitions follow probability matrix."""

def test_telemetry_gradual_change():
    """Verify continuous values change gradually between ticks."""

def test_alarm_generation_on_fault():
    """Verify fault state triggers critical alarm."""

def test_alarm_recovery():
    """Verify alarm clears when parameter returns to normal range."""

def test_output_only_increases_when_running():
    """Verify today_output only increases in RUNNING state."""
```

### 6.2 后端 API 测试

```python
# server/tests/test_api.py

def test_summary_endpoint():
    """GET /api/twin/equipment/filler-001/summary returns valid JSON."""

def test_telemetry_endpoint():
    """GET /api/twin/equipment/filler-001/telemetry returns all data points."""

def test_alarms_endpoint():
    """GET /api/twin/equipment/filler-001/alarms returns alarm list."""

def test_invalid_equipment_id():
    """GET with unknown ID returns 404."""
```

### 6.3 前端测试（手动验收为主）

Phase 1 前端以手动验收为主，验收清单见 requirements.md §9 DoD。

---

## 7. 迁移计划

### 7.1 Phase 1：图片方案 + Mock 数据（本 Spec，4-5 周）

- [ ] 项目脚手架 + 3D 查看器
- [ ] 数据面板 5 个子组件
- [ ] Mock 引擎 + REST API
- [ ] Docker 化部署

### 7.2 Phase 2：真实数据接入（未来 Spec）

- [ ] 数据适配器（OPC-UA / MQTT / Modbus）
- [ ] WebSocket 替代 REST 轮询
- [ ] 时序数据库持久化

### 7.3 Phase 3：孪生增强（未来 Spec）

- [ ] glTF 模型替换图片
- [ ] 部位级交互与告警高亮
- [ ] 历史趋势与回放

---

## 8. 风险与缓解

### 8.1 风险：图片切换不够平滑

**影响**：旋转时有明显的图片跳切感

**缓解**：
- crossfade 过渡时间可调（200ms-500ms）
- 降低 OrbitControls 旋转速度
- 预加载所有纹理避免加载延迟

### 8.2 风险：Mock 数据不够逼真

**影响**：演示效果不佳

**缓解**：
- 状态机概率可调，确保大部分时间设备在运行态
- 连续量用高斯随机游走而非纯随机
- 模拟三班制节奏增加真实感

---

## 9. 契约与 Mock

### 9.1 API 契约

**设备摘要**：
```json
// GET /api/twin/equipment/{id}/summary
// Response 200:
{
  "equipment": {
    "id": "string",
    "name": "string",
    "model": "string",
    "location": "string",
    "status": "running | idle | fault | maintenance"
  },
  "highlights": {
    "speed": { "value": "number", "unit": "string" },
    "today_output": { "value": "number", "unit": "string" },
    "today_target": { "value": "number", "unit": "string" },
    "oee": { "value": "number", "unit": "string" }
  },
  "active_alarms": "number",
  "updated_at": "string (ISO 8601)"
}
```

**实时遥测**：
```json
// GET /api/twin/equipment/{id}/telemetry
// Response 200:
[
  {
    "point_id": "string",
    "name": "string",
    "value": "number | string | boolean",
    "unit": "string | null",
    "min": "number | null",
    "max": "number | null",
    "quality": "good | bad | uncertain",
    "timestamp": "string (ISO 8601)"
  }
]
```

**告警列表**：
```json
// GET /api/twin/equipment/{id}/alarms?active=true
// Response 200:
[
  {
    "id": "string",
    "equipment_id": "string",
    "point_id": "string | null",
    "level": "info | warning | critical",
    "message": "string",
    "start_time": "string (ISO 8601)",
    "end_time": "string | null",
    "acknowledged": "boolean"
  }
]
```

**错误响应**：
```json
// Response 404:
{ "detail": "Equipment not found: {id}" }

// Response 500:
{ "detail": "Internal server error: {message}" }
```

### 9.2 Mock 策略

- Phase 1 全部使用 MockEngine 生成数据，无真实外部依赖
- MockEngine 在 FastAPI 启动时初始化，后台线程每秒 tick
- 前端通过 `VITE_API_BASE_URL` 环境变量指向后端，开发时默认 `http://localhost:8100`

---

## 10. 参考文档

- `docs/DIGITAL_TWIN_PLAN.md` — 总体规划
- [React Three Fiber 文档](https://docs.pmnd.rs/react-three-fiber)
- [Drei 文档](https://github.com/pmndrs/drei)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

---

**维护者**: yeemio  
**最后更新**: 2026-03-10
