# Design: 罐装机数字孪生 Phase 2 — 3D 模型孪生体

> **目标**：用 glTF 模型替换图片方案，实现部件交互、告警高亮、历史趋势  
> **状态**：设计完成  
> **最后更新**：2026-03-10

---

## 1. 架构设计

### 1.1 整体架构（Phase 2 新增部分用 ★ 标注）

```
┌──────────────────────────────────────────────────────────────────┐
│  浏览器                                                           │
│  ┌──────────────────────────┐  ┌───────────────────────────────┐ │
│  │  3D 查看器 (升级)         │  │  数据面板 (Phase 1 保留)       │ │
│  │  ├─ ★ ModelViewer        │  │  ├─ StatusPanel               │ │
│  │  │   (useGLTF + 光照)    │  │  ├─ ProductionPanel           │ │
│  │  ├─ ★ PartInteraction    │  │  ├─ ParameterPanel            │ │
│  │  │   (Raycaster+高亮)    │  │  ├─ OEEGauge                  │ │
│  │  ├─ ★ AlarmHighlight     │  │  ├─ AlarmPanel                │ │
│  │  │   (部件闪烁/变色)      │  │  └─ ★ HistoryChart           │ │
│  │  ├─ ★ PartInfoPopup      │  │                               │ │
│  │  │   (部件参数浮动面板)    │  │                               │ │
│  │  ├─ ★ PresetViews        │  │                               │ │
│  │  │   (预设视角按钮)       │  │                               │ │
│  │  └─ OrbitControls         │  │                               │ │
│  └──────────────┬───────────┘  └──────────┬────────────────────┘ │
│                 └──────────┬──────────────┘                      │
│                            │ useEquipmentData (Phase 1)          │
│                            │ ★ useHistory (新增)                  │
└────────────────────────────┼─────────────────────────────────────┘
                             │ HTTP REST
┌────────────────────────────▼─────────────────────────────────────┐
│  后端 (FastAPI)                                                    │
│  Phase 1 端点保留 +                                                │
│  ★ GET /api/twin/equipment/{id}/history?point_id=...&hours=...   │
│                                                                   │
│  MockEngine (Phase 1) + ★ HistoryBuffer (环形缓冲区)              │
└───────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

#### ★ 组件 1：ModelViewer（3D 模型渲染器）

**职责**：替换 Phase 1 的 ImageSphere，加载并渲染 glTF 模型。

**接口定义**：
```typescript
interface ModelViewerProps {
  modelPath: string;               // GLB 文件路径
  partMapping: PartMapping[];      // 部件-测点映射
  alarms: Alarm[];                 // 当前告警（驱动高亮）
  onPartClick?: (part: PartInfo) => void;
  onPartHover?: (part: PartInfo | null) => void;
}

interface PartMapping {
  partName: string;    // 模型中的部件名（与 glTF node name 对应）
  label: string;       // 中文显示名
  pointIds: string[];  // 关联的测点 ID
}

interface PartInfo {
  partName: string;
  label: string;
  pointIds: string[];
  screenPosition: { x: number; y: number }; // 屏幕投影坐标（用于定位弹窗）
}
```

#### ★ 组件 2：PartInteraction（部件交互管理）

**职责**：管理 Raycaster 检测、悬停高亮、点击事件。

```typescript
// 核心逻辑：
// 1. useFrame 中做 Raycaster 检测
// 2. 悬停时给部件添加 OutlinePass 或 emissive 发光
// 3. 点击时计算部件屏幕坐标，触发 onPartClick
```

#### ★ 组件 3：AlarmHighlight（告警高亮渲染）

**职责**：根据活跃告警列表，驱动对应部件的材质变色/闪烁。

```typescript
// 核心逻辑：
// 1. 遍历 alarms，通过 point_id → partMapping 找到部件
// 2. critical：useFrame 中做 sin 波闪烁（emissive 红色）
// 3. warning：持续设置 emissive 橙色
// 4. 无告警时恢复原始材质
```

#### ★ 组件 4：HistoryChart（历史趋势图表）

**职责**：展示测点历史曲线。

```typescript
interface HistoryChartProps {
  equipmentId: string;
  pointId: string;
  pointName: string;
  unit: string | null;
  min: number | null;
  max: number | null;
  hours: number;       // 时间范围
}
```

#### ★ 组件 5：HistoryBuffer（后端历史缓冲）

**职责**：在内存中保存最近 24 小时的测点值，支持按时间范围查询。

```python
class HistoryBuffer:
    def __init__(self, max_seconds: int = 86400):
        """Ring buffer storing (timestamp, point_id, value) tuples."""

    def append(self, point_id: str, value: float, ts: datetime) -> None:
        """Append a data point."""

    def query(self, point_id: str, hours: float) -> list[dict]:
        """Return data points for the given point_id within the last N hours."""
```

---

## 2. 实现细节

### 2.1 新增/修改文件

```
sierac-twin/
├── public/
│   └── models/
│       └── filler.glb              # ★ 罐装机 3D 模型
├── src/
│   ├── components/
│   │   ├── viewer/
│   │   │   ├── EquipmentViewer.tsx  # 修改：条件渲染 ModelViewer 或 ImageSphere
│   │   │   ├── ★ ModelViewer.tsx    # glTF 模型加载+渲染
│   │   │   ├── ★ PartInteraction.tsx # Raycaster+高亮
│   │   │   ├── ★ AlarmHighlight.tsx # 告警部件变色/闪烁
│   │   │   ├── ★ PartInfoPopup.tsx  # 部件参数浮动面板
│   │   │   ├── ★ PresetViews.tsx    # 预设视角按钮组
│   │   │   ├── ImageSphere.tsx      # 保留（模型未到位时降级）
│   │   │   └── ViewAngleIndicator.tsx
│   │   └── panel/
│   │       ├── ★ HistoryChart.tsx   # 历史趋势图表
│   │       └── ... (Phase 1 面板保留)
│   ├── config/
│   │   ├── viewAngles.ts            # 保留
│   │   └── ★ partMapping.ts         # 部件-测点映射配置
│   ├── hooks/
│   │   ├── useEquipmentData.ts      # 保留
│   │   ├── ★ usePartInteraction.ts  # 部件交互 Hook
│   │   └── ★ useHistory.ts          # 历史数据获取 Hook
│   └── services/
│       └── api.ts                   # 新增 fetchHistory
└── server/
    ├── main.py                      # 新增 history 端点
    ├── mock_engine.py               # 修改：tick 时写入 HistoryBuffer
    └── ★ history_buffer.py          # 环形缓冲区
```

### 2.2 glTF 模型加载

```typescript
// components/viewer/ModelViewer.tsx
import { useGLTF } from "@react-three/drei";

function ModelViewer({ modelPath, ...props }: ModelViewerProps) {
  const { scene } = useGLTF(modelPath);

  // 遍历 scene.children，为可交互部件注册事件
  // 保存每个部件的原始材质（用于告警恢复）

  return <primitive object={scene} />;
}
```

**关键点**：
- `useGLTF` 自动处理 glTF 加载和缓存
- 模型中的 node name 必须与 `partMapping` 配置中的 `partName` 对应
- 首次加载时遍历场景树，建立 `partName → Object3D` 的查找表

### 2.3 部件交互实现

```typescript
// hooks/usePartInteraction.ts
// 1. 用 useThree() 获取 camera, raycaster, scene
// 2. 监听 pointermove 事件做 Raycaster 检测
// 3. 命中可交互部件时：
//    - 设置 cursor: pointer
//    - 给部件添加 emissive 发光（或用 @react-three/postprocessing 的 Outline）
// 4. 监听 click 事件：
//    - 命中部件时计算屏幕坐标（Vector3.project）
//    - 触发 onPartClick 回调
```

**高亮方案选择**：

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| emissive 发光 | 简单，无额外依赖 | 效果一般 | 备选 |
| Outline 描边 (postprocessing) | 效果好，专业感强 | 需要额外包 | **推荐** |
| 材质替换 | 完全可控 | 需要管理原始材质 | 备选 |

推荐使用 `@react-three/postprocessing` 的 `Outline` 效果，悬停时描边，点击时加粗描边。

### 2.4 告警高亮实现

```typescript
// components/viewer/AlarmHighlight.tsx
// 每帧（useFrame）：
// 1. 遍历 alarms，通过 partMapping 找到对应部件 Object3D
// 2. critical：emissive = red * abs(sin(time * 6))  // 0.5秒闪烁
// 3. warning：emissive = orange (常亮)
// 4. 无告警的部件：恢复原始 emissive
//
// 材质管理：
// - 首次加载时 clone 每个部件的材质（避免修改共享材质）
// - 保存 originalEmissive Map<string, Color>
```

### 2.5 历史数据存储

```python
# server/history_buffer.py
from collections import deque
from datetime import datetime, timezone

class HistoryBuffer:
    def __init__(self, max_seconds: int = 86400):
        self._buffer: deque[tuple[datetime, str, float]] = deque()
        self._max_seconds = max_seconds

    def append(self, point_id: str, value: float, ts: datetime) -> None:
        self._buffer.append((ts, point_id, value))
        self._trim()

    def query(self, point_id: str, hours: float) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            {"timestamp": ts.isoformat(), "value": val}
            for ts, pid, val in self._buffer
            if pid == point_id and ts >= cutoff
        ]

    def _trim(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._max_seconds)
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()
```

**关键点**：
- 使用 `deque` 实现 O(1) 追加和头部删除
- 每秒 tick 时写入 13 个测点 × 1 条 = 每秒 13 条
- 24 小时 = 86400 秒 × 13 = ~112 万条，内存约 50-100 MB，可接受
- 降采样：history API 返回时可按间隔采样（如每 10 秒取 1 条），减少前端数据量

---

## 3. 数据流

### 3.1 部件交互数据流

```
用户鼠标移动
  ↓
usePartInteraction Hook → Raycaster 检测
  ↓
命中部件 → 查找 partMapping → 获取 partName + pointIds
  ↓
悬停高亮（Outline 效果）+ tooltip 显示部件名
  ↓
用户点击
  ↓
计算屏幕坐标 → onPartClick(partInfo)
  ↓
PartInfoPopup 弹出 → 从 telemetry 数据中筛选 pointIds 对应的值
```

### 3.2 告警高亮数据流

```
useEquipmentData → alarms 列表更新（每 5 秒）
  ↓
AlarmHighlight 组件接收 alarms prop
  ↓
遍历 alarms → point_id → partMapping → partName → Object3D
  ↓
useFrame 每帧更新材质 emissive（闪烁/常亮/恢复）
```

### 3.3 历史数据流

```
MockEngine.tick() 每秒
  ↓
HistoryBuffer.append(point_id, value, now) 写入环形缓冲
  ↓
用户在 HistoryChart 选择测点 + 时间范围
  ↓
GET /api/twin/equipment/{id}/history?point_id=speed&hours=4
  ↓
HistoryBuffer.query() → 返回数据点数组
  ↓
Recharts LineChart 渲染曲线
```

---

## 4. 错误处理

### 4.1 模型加载失败

**场景**：GLB 文件不存在或格式错误

**处理**：
- 显示加载错误提示 + 降级到 Phase 1 图片方案
- `EquipmentViewer` 中用 `Suspense` + `ErrorBoundary` 包裹 `ModelViewer`
- fallback 渲染 `ImageSphere`（Phase 1 组件）

### 4.2 部件名不匹配

**场景**：partMapping 中的 partName 在模型中找不到

**处理**：
- 启动时遍历模型场景树，与 partMapping 对比
- 不匹配的部件在 console.warn 中提示
- 不影响其他部件的交互

### 4.3 历史数据量过大

**场景**：24 小时 × 每秒 13 点 = 112 万条，前端渲染卡顿

**处理**：
- 后端 API 支持 `interval` 参数（降采样间隔，默认 10 秒）
- 1 小时范围：每秒 1 条 = 3600 点
- 24 小时范围：每 30 秒 1 条 = 2880 点

---

## 5. 配置

### 5.1 部件映射配置

```typescript
// config/partMapping.ts
export const PART_MAPPING: PartMapping[] = [
  {
    partName: "filling_heads",
    label: "灌装头组件",
    pointIds: ["head_active", "head_total", "fill_accuracy"],
  },
  {
    partName: "conveyor_in",
    label: "进瓶传送带",
    pointIds: ["speed"],
  },
  {
    partName: "conveyor_out",
    label: "出瓶传送带",
    pointIds: ["speed", "reject_count"],
  },
  {
    partName: "tank",
    label: "液缸",
    pointIds: ["temperature", "pressure", "fill_volume"],
  },
  {
    partName: "control_panel",
    label: "控制柜",
    pointIds: ["status", "oee"],
  },
  // ... 根据实际模型部件扩展
];
```

### 5.2 模型配置

```typescript
// config/modelConfig.ts
export const MODEL_CONFIG = {
  path: "/models/filler.glb",
  scale: 0.01,           // 如果模型单位是 mm，需要缩放到 m
  position: [0, 0, 0],
  rotation: [0, 0, 0],   // 调整朝向
};
```

### 5.3 新增环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_MODEL_PATH` | GLB 模型路径 | `/models/filler.glb` |
| `VITE_USE_MODEL` | 是否使用 3D 模型（false 则降级图片） | `true` |

---

## 6. 测试策略

### 6.1 后端测试

```python
# server/tests/test_history_buffer.py
def test_append_and_query():
    """Verify data can be appended and queried by point_id and time range."""

def test_trim_old_data():
    """Verify data older than max_seconds is automatically trimmed."""

def test_query_empty():
    """Verify empty result for unknown point_id."""

# server/tests/test_api.py (追加)
def test_history_endpoint():
    """GET /api/twin/equipment/filler-001/history returns time series data."""

def test_history_unknown_point():
    """GET with unknown point_id returns empty array."""
```

### 6.2 前端测试

Phase 2 前端以手动验收为主（3D 交互难以自动化测试）。

验收清单见 requirements.md §9 DoD。

---

## 7. 迁移计划

### 7.1 模型到位前（可并行）

- [ ] 实现 HistoryBuffer + history API + HistoryChart
- [ ] 实现 PartInteraction / AlarmHighlight 框架（用 placeholder 几何体测试）
- [ ] 实现 PartInfoPopup + PresetViews
- [ ] 实现 partMapping 配置加载

### 7.2 模型到位后

- [ ] 模型格式转换（如需从 STEP 转 glTF）
- [ ] 在 Blender 中检查/调整部件命名
- [ ] 模型减面（如需）
- [ ] 更新 partMapping 配置匹配实际部件名
- [ ] 集成测试 + 验收

---

## 8. 风险与缓解

### 8.1 风险：模型部件命名不规范

**影响**：partMapping 无法匹配，部件交互失效

**缓解**：
- 提供 `3D_MODEL_REQUEST.md` 明确命名要求
- 在 Blender 中可以重命名部件
- 代码中做模糊匹配（如忽略大小写、下划线/连字符）

### 8.2 风险：Outline 后处理影响性能

**影响**：帧率下降

**缓解**：
- 仅对悬停/选中的部件做 Outline，不全局应用
- 如性能不足，降级为 emissive 发光方案

---

## 9. 契约与 Mock

### 9.1 新增 API 契约

**历史数据**：
```json
// GET /api/twin/equipment/{id}/history?point_id=speed&hours=4&interval=10
// Response 200:
{
  "point_id": "speed",
  "point_name": "灌装速度",
  "unit": "瓶/分钟",
  "min": 200,
  "max": 600,
  "data": [
    { "timestamp": "2026-03-10T10:00:00Z", "value": 450.2 },
    { "timestamp": "2026-03-10T10:00:10Z", "value": 451.5 },
    ...
  ]
}
```

### 9.2 Mock 策略

- 历史数据由 MockEngine tick 写入 HistoryBuffer，无需额外 Mock
- 模型未到位时，`VITE_USE_MODEL=false` 降级到 Phase 1 图片方案

---

## 10. 参考文档

- `docs/3D_MODEL_REQUEST.md` — 厂商模型需求
- [React Three Fiber useGLTF](https://docs.pmnd.rs/drei/loaders/gltf)
- [@react-three/postprocessing Outline](https://docs.pmnd.rs/react-postprocessing/effects/outline)

---

**维护者**: yeemio  
**最后更新**: 2026-03-10
