import type { PartMapping } from "@/types/equipment";

/**
 * Maps glTF node names to display labels and telemetry point IDs.
 * partName must match GLB node names. Run: python scripts/read_glb_nodes.py public/models/001.glb
 *
 * animation: telemetry drives rotation/translation. speedScale * value = motion per second.
 * - rotate: rad/s. Use RPM_TO_RAD_S when value is RPM (滚筒转速).
 */
export const PART_MAPPING: PartMapping[] = [
  {
    // Product box — position driven by L-path animation in ModelViewer (Y feed → X reject)
    partName: "Cube",
    label: "产品方块",
    pointIds: ["roller_speed", "temperature"],
  },
  {
    partName: "Unnamed-0004_ASM",
    label: "横向滚筒",
    pointIds: ["roller_speed", "motor_current"],
  },
  {
    partName: "Unnamed-0004_ASM.001",
    label: "进料段",
    pointIds: ["belt_speed", "oee"],
  },
];
