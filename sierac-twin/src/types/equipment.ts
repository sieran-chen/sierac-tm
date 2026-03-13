export type EquipmentStatus = "running" | "idle" | "fault" | "maintenance";

export interface Equipment {
  id: string;
  name: string;
  model: string;
  location: string;
  status: EquipmentStatus;
}

export interface HighlightValue {
  value: number;
  unit: string;
}

export interface EquipmentSummary {
  equipment: Equipment;
  highlights: Record<string, HighlightValue>;
  active_alarms: number;
  updated_at: string;
}

export interface TelemetryValue {
  point_id: string;
  name: string;
  value: number | string | boolean;
  unit: string | null;
  min: number | null;
  max: number | null;
  quality: "good" | "bad" | "uncertain";
  timestamp: string;
}

export type AlarmLevel = "info" | "warning" | "critical";

export interface Alarm {
  id: string;
  equipment_id: string;
  point_id: string | null;
  level: AlarmLevel;
  message: string;
  start_time: string;
  end_time: string | null;
  acknowledged: boolean;
}

export interface SphericalAngle {
  theta: number;
  phi: number;
}

export interface ViewAngleImage {
  id: string;
  src: string;
  theta: number;
  phi: number;
}

export interface EquipmentData {
  summary: EquipmentSummary | null;
  telemetry: TelemetryValue[];
  alarms: Alarm[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

/** Data-driven animation: which telemetry point drives this part and how. */
export interface PartAnimationConfig {
  /** Telemetry point_id (e.g. "belt_speed", "roller_speed"). Value must be numeric. */
  pointId: string;
  /** Rotation around axis, or linear translation along axis. */
  type: "rotate" | "translate";
  /** Axis in local space: "x" | "y" | "z". */
  axis: "x" | "y" | "z";
  /**
   * Converts telemetry value to motion per second.
   * - rotate: value * speedScale = radians per second.
   * - translate: value * speedScale = units per second.
   * Example: value is RPM, then speedScale = (2*Math.PI)/60 for rad/s.
   */
  speedScale?: number;
}

export interface PartMapping {
  partName: string;
  label: string;
  pointIds: string[];
  /** Optional: drive this part's transform from a telemetry point. */
  animation?: PartAnimationConfig;
}

export interface PartInfo {
  partName: string;
  label: string;
  pointIds: string[];
  screenPosition: { x: number; y: number };
}

export interface HistoryDataPoint {
  timestamp: string;
  value: number;
}

export interface HistoryResponse {
  point_id: string;
  point_name: string;
  unit: string | null;
  min: number | null;
  max: number | null;
  data: HistoryDataPoint[];
}
