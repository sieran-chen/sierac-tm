/**
 * Scene Coordinate System (场景坐标系)
 *
 * 通用的设备场景坐标系，用于人机沟通和动画编程。
 * 以观察者默认视角为基准，定义前后左右上下六个方向。
 * 所有设备共用同一套方向语言，具体映射到 Three.js 世界轴由配置决定。
 *
 * ┌──────────────────────────────────────────────┐
 * │              场景坐标系定义                     │
 * │                                              │
 * │   以观察者默认视角（初始相机位置）为基准：        │
 * │                                              │
 * │         +前 (FRONT)                           │
 * │           ↑  远离观察者                        │
 * │           │                                   │
 * │  +左 ←────┼────→ +右                          │
 * │  (LEFT)   │     (RIGHT)                       │
 * │           ↓                                   │
 * │         +后 (BACK)                            │
 * │           靠近观察者                           │
 * │                                              │
 * │   +上 (UP)    = 垂直向上                      │
 * │   +下 (DOWN)  = 垂直向下                      │
 * │                                              │
 * │   原点: 设备中心 / 两区交汇处                   │
 * │                                              │
 * └──────────────────────────────────────────────┘
 *
 * 方向名称约定（中英对照，沟通时任选）：
 *
 * | 方向    | 英文    | 说明               |
 * |--------|--------|--------------------|
 * | +前    | +FRONT | 远离观察者（画面纵深） |
 * | +后    | +BACK  | 靠近观察者           |
 * | +左    | +LEFT  | 屏幕左侧            |
 * | +右    | +RIGHT | 屏幕右侧            |
 * | +上    | +UP    | 垂直向上            |
 * | +下    | +DOWN  | 垂直向下            |
 */

/**
 * Axis mapping: which Three.js world axis corresponds to each scene direction.
 * sign: +1 or -1 indicates whether the scene direction aligns or opposes the world axis.
 *
 * This mapping is per-model/per-scene. When the model rotates or a new device is loaded,
 * only this config needs to change.
 */
export interface AxisMapping {
  axis: "x" | "y" | "z";
  sign: 1 | -1;
}

export interface SceneCoordConfig {
  /** +FRONT direction in Three.js world */
  front: AxisMapping;
  /** +RIGHT direction in Three.js world */
  right: AxisMapping;
  /** +UP direction in Three.js world */
  up: AxisMapping;
}

/**
 * Current scene mapping (roller reject device, model rotated 85°).
 *
 * | 场景方向 | Three.js 轴 | 屏幕表现     |
 * |---------|------------|-------------|
 * | +前     | +X         | 从近到远     |
 * | +右     | +Z         | 从左到右     |
 * | +上     | +Y         | 向上        |
 */
export const SCENE_COORD: SceneCoordConfig = {
  front: { axis: "x", sign: 1 },
  right: { axis: "z", sign: 1 },
  up:    { axis: "y", sign: 1 },
};

/**
 * Convert scene coordinates (front, up, right) to Three.js world [x, y, z].
 *
 * Usage:
 *   sceneToWorld(100, 0, 50)  // 前100, 上0, 右50
 *   → returns [x, y, z] in Three.js world space
 */
export function sceneToWorld(
  front: number,
  up: number,
  right: number,
  config: SceneCoordConfig = SCENE_COORD,
): [x: number, y: number, z: number] {
  const result: [number, number, number] = [0, 0, 0];
  const axisIndex = { x: 0, y: 1, z: 2 } as const;

  result[axisIndex[config.front.axis]] += front * config.front.sign;
  result[axisIndex[config.up.axis]]    += up    * config.up.sign;
  result[axisIndex[config.right.axis]] += right * config.right.sign;

  return result;
}

/**
 * Convert Three.js world [x, y, z] to scene coordinates.
 */
export function worldToScene(
  x: number,
  y: number,
  z: number,
  config: SceneCoordConfig = SCENE_COORD,
): { front: number; up: number; right: number } {
  const world = [x, y, z];
  const axisIndex = { x: 0, y: 1, z: 2 } as const;

  return {
    front: world[axisIndex[config.front.axis]] * config.front.sign,
    up:    world[axisIndex[config.up.axis]]    * config.up.sign,
    right: world[axisIndex[config.right.axis]] * config.right.sign,
  };
}
