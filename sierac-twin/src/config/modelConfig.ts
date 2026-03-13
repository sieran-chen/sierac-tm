/** GLB path; when missing or load error, viewer falls back to image sphere. */
export const MODEL_CONFIG = {
  path: "/models/roller_reject.glb",
  /** FreeCAD exports in meters; scale up so ~1.3m model fills the view. */
  scale: 8,
  position: [0, -6, 0] as [number, number, number],
  rotation: [0, (85 * Math.PI) / 180, 0] as [number, number, number],
};

/**
 * STEP AP214 encodes non-ASCII as \X2\<UTF-16BE hex>\X0\.
 * Node names in GLB exported from FreeCAD keep this encoding.
 */
export const KNOWN_PARTS = {
  pusher: "\\X2\\52549664\\X0\\",       // 剔除 (reject pusher plate)
  rollerPrefix: "DR2-08B11T-D50X15T-AGL670-RL", // 双排链滚筒 RL610~616
  idleRollerPrefix: "无动力滚筒",        // encoded as \X2\...\X0\ in GLB
} as const;
