# 传送带方块位置「刷新后像没效果」问题总结

供寻求他人帮助时使用。包含：现象、当前代码改动、原因猜测、相关文件与行号。

---

## 1. 现象

- 在 `ModelViewer.tsx` 里把传送带上「方块」（代表传送物）的偏移改成了 **offsetUp = 50、offsetLeft = 10**。
- 改完后有时位置看起来正确，但**每次刷新页面**，位置又像没改过一样（偏移似乎失效或不稳定）。
- 用户希望这两个偏移量能稳定生效，不因刷新而「时灵时不灵」。

---

## 2. 当前实现（改动后）

**文件**：`sierac-twin/src/components/viewer/ModelViewer.tsx`

### 2.1 基准数据：从 useMemo 改为 useFrame + ref

- **之前**：用 `useMemo` 依赖 `scene` 计算一次 bbox，得到 `conveyorSurfaceY`（含 `y, centerX, centerZ, sizeX, sizeZ`），用作方块位置的基准。
- **现在**：
  - 删掉了基于 `scene` 的 `useMemo` 计算。
  - 新增 `conveyorSurfaceYRef`（ref），初始为 `null`。
  - 在 **useFrame** 里每帧检查：若 `conveyorSurfaceYRef.current == null`，则用 `new THREE.Box3().setFromObject(scene)` 算 bbox；仅当 `size.x > 1 && size.y > 1` 时，认为几何已就绪，把 `{ y, centerX, centerZ, sizeX, sizeZ }` 写入 ref，之后不再重算。
  - 方块位置（含 offsetUp、offsetLeft）只使用 ref 里这份基准数据。

### 2.2 方块位置计算（未改逻辑，只改数据来源）

- 仍在 **useFrame** 内：
  - `offsetUp = 50`，`offsetLeft = 10`（写死在约 157–158 行）。
  - `x = surface.centerX - offsetLeft + ((productOffsetRef.current % span) - span / 2)`
  - `y = surface.y + productHalfH + offsetUp`
  - `productMesh.position.set(x, y, surface.centerZ)`
- 其中 `surface` 来自 `conveyorSurfaceYRef.current`（有值后才更新方块位置）。

### 2.3 相关行号（便于他人查看）

| 内容 | 行号 |
|------|------|
| `conveyorSurfaceYRef` 定义 | 41–47 |
| useFrame 内 bbox 计算与 ref 写入 | 126–146 |
| 方块位置（offsetUp/offsetLeft 使用处） | 148–161 |

---

## 3. 原因猜测（当前假设）

- **useMemo 时机问题**：`useMemo` 在首帧或 GLB 刚挂上时就会执行，此时 `scene` 的几何可能尚未完全加载或 world matrix 未更新，`Box3().setFromObject(scene)` 可能得到：
  - 空或接近零的 size，或
  - 每帧/每次刷新不同的结果（取决于加载时序）。
- 因此基准 (centerX, centerY, centerZ) 不稳定，导致即使用户固定了 offsetUp=50、offsetLeft=10，**基准在变**，看起来就像「刷新后改的偏移没效果」。
- **改动的意图**：把 bbox 计算推迟到 **useFrame** 里，并在「第一次得到有效 bbox」（size 足够大）时写进 ref，之后一直用这份稳定基准，使 50/10 的偏移能稳定生效。

**注意**：上述是推测，尚未经过充分验证；若问题仍存在，可能是其他原因（例如模型 scale、group 变换、或 R3F 渲染顺序等）。

---

## 4. 若需还原到「useMemo 版本」

若要恢复成用 useMemo 算 bbox 的写法，大致是：

1. 删除 `conveyorSurfaceYRef` 的 ref 定义（41–47 行）。
2. 恢复 `conveyorSurfaceY` 的 useMemo（在 partMap 的 useMemo 之前），例如：
   ```ts
   const conveyorSurfaceY = useMemo(() => {
     const box = new THREE.Box3().setFromObject(scene);
     const center = new THREE.Vector3();
     box.getCenter(center);
     const size = new THREE.Vector3();
     box.getSize(size);
     return { y: center.y, centerX: center.x, centerZ: center.z, sizeX: size.x, sizeZ: size.z };
   }, [scene]);
   ```
3. 在 useFrame 里去掉「if (!surface) { ... bbox 计算 ... }」整块，把 `surface` 改为直接使用 `conveyorSurfaceY`，并保证 `conveyorSurfaceY` 在 useFrame 闭包中可用。

---

## 5. 相关文件

- **主要**：`sierac-twin/src/components/viewer/ModelViewer.tsx`
- 模型配置（scale 等）：`sierac-twin/src/config/modelConfig.ts`（例如 `scale: 0.03`）
- 设备/测点：`sierac-twin/server/mock_engine.py`（`roller-001`，含 `belt_speed` 等）

---

**文档生成目的**：把当前改动和猜测整理成文，便于交给其他人排查或给出更好方案。
