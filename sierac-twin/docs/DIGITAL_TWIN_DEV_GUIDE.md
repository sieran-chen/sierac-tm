# 数字孪生 3D 可视化开发指南

> **版本**: v1.0.0  
> **最后更新**: 2026-03-12  
> **适用范围**: sierac-twin 及后续所有设备数字孪生项目

---

## 一、总体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  React + react-three-fiber + @react-three/drei          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 3D Viewer│  │Data Panel│  │ Controls │              │
│  └──────────┘  └──────────┘  └──────────┘              │
├─────────────────────────────────────────────────────────┤
│                    Config Layer                          │
│  modelConfig / partMapping / coordinateSystem           │
│  animationConfig (路径、推板、状态机)                     │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  FastAPI Mock Engine → 未来: OPC-UA / MQTT 真实数据      │
└─────────────────────────────────────────────────────────┘
```

### 核心原则

| 原则 | 说明 |
|------|------|
| **配置驱动** | 模型路径、缩放、旋转、坐标映射、动画路径全部配置化，不硬编码 |
| **关注点分离** | React 管 UI 状态，useFrame 管动画循环，不在动画循环里触发 React 状态更新 |
| **通用坐标系** | 用前/后/左/右/上/下沟通，不直接说 Three.js 的 XYZ |
| **渐进增强** | 模型加载失败有 fallback（图片球），推板等附加件用代码叠加 |

---

## 二、场景坐标系规范

### 2.1 为什么需要场景坐标系

CAD 模型导入 Three.js 后，由于以下原因，Three.js 的 XYZ 轴与人的直觉方向不一致：

- CAD 软件（SolidWorks、Fusion 360）使用 Z-up，glTF 规范使用 Y-up
- 模型导出时可能带有旋转偏移
- 项目中模型可能额外旋转以适配视角（如本项目旋转 85°）

**直接用 XYZ 沟通会导致严重的理解偏差**，这是本项目最大的踩坑点。

### 2.2 场景坐标系定义

以**观察者默认视角（初始相机位置）**为基准：

```
         +前 (FRONT)
           ↑  远离观察者
           │
  +左 ←────┼────→ +右
  (LEFT)   │     (RIGHT)
           ↓
         +后 (BACK)
           靠近观察者

  +上 (UP) = 垂直向上
```

| 方向 | 英文 | 说明 |
|-----|------|------|
| +前 | +FRONT | 远离观察者（画面纵深方向） |
| +后 | +BACK | 靠近观察者 |
| +左 | +LEFT | 屏幕左侧 |
| +右 | +RIGHT | 屏幕右侧 |
| +上 | +UP | 垂直向上 |
| +下 | +DOWN | 垂直向下 |

### 2.3 轴映射配置

每个设备/模型一份映射配置，定义场景方向到 Three.js 世界轴的对应关系：

```typescript
// src/config/coordinateSystem.ts
export const SCENE_COORD: SceneCoordConfig = {
  front: { axis: "x", sign: 1 },   // +前 = +X
  right: { axis: "z", sign: 1 },   // +右 = +Z
  up:    { axis: "y", sign: 1 },   // +上 = +Y
};
```

**换设备时只改这一处**。

### 2.4 坐标转换函数

```typescript
sceneToWorld(front, up, right)  // 场景坐标 → Three.js [x, y, z]
worldToScene(x, y, z)           // Three.js → 场景坐标
```

### 2.5 辅助坐标轴

开发模式下场景中显示带标签的坐标轴（`EquipmentAxes` 组件）：

- **红色** = +前 FRONT
- **蓝色** = +右 RIGHT
- **绿色** = +上 UP

**新设备接入时第一件事：确认坐标轴方向与实际设备朝向一致。**

---

## 三、模型管理规范

### 3.1 模型格式

| 项目 | 规范 |
|------|------|
| 格式 | **glTF 2.0 / GLB**（二进制，体积小，Web 友好） |
| 放置路径 | `public/models/{设备编号}.glb` |
| 命名 | 设备编号，如 `001.glb`、`roller-reject-001.glb` |

### 3.2 模型预处理 Checklist

在 Blender 中完成以下步骤后再导出：

- [ ] **原点归零**：Geometry → Origin → Geometry to Origin
- [ ] **清除空父节点**：删除无用的 Empty 对象
- [ ] **部件独立命名**：需要交互/动画的部件必须是独立 mesh，有唯一名称
- [ ] **统一单位**：确认导出单位与项目一致（米/毫米）
- [ ] **压缩纹理**：使用 Basis Universal 或 KTX2 压缩
- [ ] **验证导出**：用 `scripts/read_glb_nodes.py` 检查节点树

### 3.3 模型配置

```typescript
// src/config/modelConfig.ts
export const MODEL_CONFIG = {
  path: "/models/001.glb",
  scale: 0.03,                              // CAD 模型通常很大，需缩放
  position: [0, 0, 0],
  rotation: [0, (85 * Math.PI) / 180, 0],   // 适配视角的旋转
};
```

### 3.4 踩坑记录

| 坑 | 原因 | 解决方案 |
|----|------|---------|
| 模型加载后方向不对 | CAD Z-up vs glTF Y-up + 导出旋转 | 在 `modelConfig.rotation` 中调整，不改模型文件 |
| 模型太大/太小 | CAD 单位不一致 | `modelConfig.scale` 统一缩放 |
| 部件无法单独控制 | GLB 中部件未拆分为独立 mesh | Blender 中拆分，或用代码叠加虚拟几何体 |
| bbox 计算不准 | 未调用 `updateWorldMatrix(true, true)` | 计算前必须更新世界矩阵 |

---

## 四、动画开发规范

### 4.1 动画分类

| 类型 | 驱动方式 | 示例 |
|------|---------|------|
| **路径动画** | useFrame + offset 累加 | 箱子在输送线上的 L 形路径 |
| **数据驱动动画** | 遥测数据 × speedScale | 滚筒转速驱动旋转 |
| **事件动画** | 状态触发，一次性 | 推板弹出缩回 |
| **告警动画** | 告警级别驱动 | 部件闪红/橙色 |

### 4.2 路径动画开发流程

1. **定义路径关键点**（用场景坐标系描述）
2. **静态验证**：先把物体放在起点，确认位置正确
3. **逐段验证**：一段一段加动画，每段确认后再加下一段
4. **不要一次写完整个路径**——这是最重要的经验教训

```typescript
// 好的做法：先定义关键点，用场景坐标系注释
const X_START = -250;   // 进料区起点 (场景坐标: 后偏左)
const X_MID   = -125;   // 进料区中心
const Z_FEED  = -300;   // 进料区 Z 线
const Z_EXIT  =  580;   // 剔除区出口
```

### 4.3 推板/气缸等附加件

当 GLB 模型中没有独立的推板 mesh 时，用代码叠加虚拟几何体：

```tsx
<mesh ref={pusherRef} castShadow receiveShadow>
  <boxGeometry args={[130, 150, 20]} />
  <meshStandardMaterial color="#64748b" metalness={0.5} roughness={0.4} />
</mesh>
```

**注意事项**：
- 几何体尺寸要和被推物体匹配
- 颜色要和设备主体区分但不突兀
- 弹出/缩回动作要快（0.3s 弹出 + 0.7s 缩回），模拟气缸效果
- 不需要时 `visible = false`，不要用位移隐藏

### 4.4 useFrame 性能注意

```typescript
// ✅ 好：在 useFrame 外计算不变的值
const alarmPartMap = useMemo(() => { ... }, [alarms, partMapping]);

// ❌ 坏：在 useFrame 里每帧创建新对象
useFrame(() => {
  const map = new Map(); // 每帧创建，GC 压力大
});
```

- useFrame 里**不要触发 React setState**
- 用 ref 存储动画状态（如 `productOffsetRef`）
- 材质 clone 只做一次（用 `userData.__cloned` 标记）

---

## 五、部件映射规范（partMapping）

### 5.1 配置结构

```typescript
export const PART_MAPPING: PartMapping[] = [
  {
    partName: "Unnamed-0004_ASM",    // 必须匹配 GLB 节点名
    label: "横向滚筒",                // 中文显示名
    pointIds: ["roller_speed", "motor_current"],  // 关联的遥测点
    animation: {                      // 可选：数据驱动动画
      type: "rotate",
      axis: "z",
      pointId: "roller_speed",
      speedScale: 0.01,
    },
  },
];
```

### 5.2 开发流程

1. 用 `scripts/read_glb_nodes.py` 或 `scripts/dump_all_nodes.py` 列出所有节点名
2. 在浏览器控制台查看 `[ModelViewer] scene nodes` 日志
3. 将需要交互的节点名填入 `partMapping`
4. 如果节点名是 `Unnamed-*`，在 Blender 中重命名后重新导出

---

## 六、新设备接入 Checklist

当需要为新设备创建数字孪生时，按以下步骤执行：

### Phase 0：模型准备
- [ ] 获取设备 3D 模型（STEP/IGES/FBX/OBJ）
- [ ] Blender 中转换为 GLB，执行模型预处理 Checklist（第三章）
- [ ] 放入 `public/models/` 目录

### Phase 1：基础显示
- [ ] 配置 `modelConfig.ts`（路径、缩放、旋转）
- [ ] 打开页面，确认模型加载正常
- [ ] 配置 `coordinateSystem.ts` 的轴映射
- [ ] **确认辅助坐标轴方向与设备实际朝向一致**（最关键的一步）

### Phase 2：部件交互
- [ ] 运行节点列表脚本，记录所有 mesh 名称
- [ ] 配置 `partMapping.ts`
- [ ] 验证 hover/click 交互正常

### Phase 3：动画
- [ ] 定义路径关键点（用场景坐标系）
- [ ] **逐段**实现路径动画，每段静态验证后再动态化
- [ ] 实现附加件（推板、闸门等）
- [ ] 接入遥测数据驱动动画

### Phase 4：数据面板
- [ ] 配置 Mock Engine 的遥测点
- [ ] 连接前端数据面板
- [ ] 告警规则与高亮

---

## 七、踩坑总结（血泪教训）

### 7.1 坐标系混乱（严重度：★★★★★）

**现象**：人说"往 Y 方向走"，AI 理解成 Three.js 的 Y 轴（向上），实际指的是设备的进料方向。来回修改十几次。

**根因**：
- CAD 模型有自己的坐标系
- glTF 有自己的坐标系（Y-up）
- 模型额外旋转了 85° 适配视角
- 人用设备物理方向描述，AI 用 Three.js 轴描述

**解决方案**：
1. 建立**场景坐标系**（前后左右上下），所有沟通用这套语言
2. 场景中显示辅助坐标轴
3. 新设备第一步：确认坐标轴方向

### 7.2 一次写完整个动画路径（严重度：★★★★）

**现象**：一次性写完 L 形路径的所有代码，方向全错，反复修改。

**解决方案**：
1. 先把物体静止放在起点，确认位置
2. 只做第一段动画，确认方向
3. 逐段添加，每段验证

### 7.3 残留代码导致编译错误（严重度：★★★）

**现象**：替换代码块时，旧的变量声明没删干净，导致 `Identifier has already been declared`。

**解决方案**：替换代码时，确保旧代码块**完整删除**，不留残余变量。

### 7.4 附加几何体方向错误（严重度：★★★）

**现象**：推板的 `boxGeometry args` 写成 `[20, 150, 120]`，薄面朝错方向，看起来像从错误方向冲出来。

**解决方案**：
- `boxGeometry args` 是 `[宽X, 高Y, 深Z]`
- 推板从 -Z 冲向 +Z：薄面在 Z 方向 → `args=[130, 150, 20]`
- 先静态放置确认朝向，再加动画

### 7.5 WebGL 截图不可用（严重度：★★）

**现象**：用 Playwright 截图，WebGL Canvas 渲染为黑色。

**解决方案**：WebGL 内容需要用户直接在浏览器截图，或使用 `canvas.toDataURL()` 在页面内导出。

---

## 八、性能优化 Checklist

| 优化项 | 方法 | 优先级 |
|--------|------|--------|
| 模型压缩 | GLB + Draco/Meshopt 压缩 | P0 |
| 纹理压缩 | Basis Universal / KTX2 | P0 |
| LOD | 远距离用低精度模型 | P1 |
| 实例化 | 相同几何体用 InstancedMesh | P1 |
| 按需渲染 | `frameloop="demand"` | P2 |
| 材质复用 | 相同材质共享引用 | P2 |
| useMemo | 不变的计算结果缓存 | P0 |

---

## 九、文件结构约定

```
sierac-twin/
├── public/models/           # GLB 模型文件
├── server/                  # FastAPI Mock Engine
│   ├── main.py              # API 入口
│   ├── mock_engine.py       # 模拟数据引擎
│   └── models.py            # Pydantic 模型
├── scripts/                 # 工具脚本
│   ├── read_glb_nodes.py    # 列出 GLB 节点名
│   └── dump_all_nodes.py    # 完整节点树
├── src/
│   ├── config/
│   │   ├── modelConfig.ts       # 模型路径、缩放、旋转
│   │   ├── coordinateSystem.ts  # 场景坐标系映射
│   │   └── partMapping.ts       # 部件映射
│   ├── components/
│   │   ├── viewer/
│   │   │   ├── EquipmentViewer.tsx   # 3D 场景容器
│   │   │   ├── ModelViewer.tsx       # 模型渲染 + 动画
│   │   │   ├── EquipmentAxes.tsx     # 辅助坐标轴
│   │   │   └── ...
│   │   ├── panel/                    # 数据面板组件
│   │   └── layout/                   # 布局组件
│   ├── hooks/                        # 自定义 Hooks
│   ├── services/                     # API 调用
│   ├── types/                        # TypeScript 类型
│   └── utils/                        # 工具函数
└── docs/
    └── DIGITAL_TWIN_DEV_GUIDE.md     # 本文档
```

---

## 十、沟通规范

### 10.1 描述位置时

```
✅ "箱子在 +前 方向 200 的位置"
✅ "推板从 -右 方向弹出"
✅ "把模型往 +左 移动 50"

❌ "箱子在 X=200 的位置"（哪个 X？模型的还是世界的？）
❌ "往 Y 方向走"（Y 是上还是前？）
```

### 10.2 描述动画时

```
✅ "箱子从进料区起点沿 +前 走到中心，然后转 +右 走到剔除区出口"
✅ "推板从 -右 弹出，碰到箱子后立刻缩回"

❌ "箱子沿 Z 轴走然后转 X 轴"
```

### 10.3 调试位置时

1. 先静态放置，截图确认
2. 每次只改一个轴的值
3. 用辅助坐标轴对照方向

---

**维护者**: yeemio  
**下次审核**: 2026-04-15
