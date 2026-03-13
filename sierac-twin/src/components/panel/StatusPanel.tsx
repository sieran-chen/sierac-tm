import type { EquipmentSummary, EquipmentStatus, TelemetryValue } from "@/types/equipment";
import { Activity, Pause, AlertOctagon, Wrench } from "lucide-react";

interface StatusPanelProps {
  summary: EquipmentSummary | null;
  telemetry?: TelemetryValue[];
}

const STATUS_CONFIG: Record<
  EquipmentStatus,
  { label: string; color: string; bg: string; icon: typeof Activity }
> = {
  running: {
    label: "运行中",
    color: "text-green-400",
    bg: "bg-green-500/10 border-green-500/20",
    icon: Activity,
  },
  idle: {
    label: "待机",
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
    icon: Pause,
  },
  fault: {
    label: "故障",
    color: "text-red-400",
    bg: "bg-red-500/10 border-red-500/20",
    icon: AlertOctagon,
  },
  maintenance: {
    label: "维护中",
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    icon: Wrench,
  },
};

function formatDuration(hours: number): string {
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h > 0 && m > 0) return `${h}h${m}m`;
  if (h > 0) return `${h}h`;
  if (m > 0) return `${m}m`;
  return "—";
}

export default function StatusPanel({ summary, telemetry = [] }: StatusPanelProps) {
  if (!summary) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="h-12 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  const status = summary.equipment.status;
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  const runtimePoint = telemetry.find((t) => t.point_id === "runtime_today");
  const runtimeHours = typeof runtimePoint?.value === "number" ? runtimePoint.value : 0;
  const durationText =
    status === "running"
      ? `已运行 ${formatDuration(runtimeHours)}`
      : status === "idle"
        ? "已待机 —"
        : status === "fault"
          ? "故障中 —"
          : "维护中 —";

  return (
    <div className={`rounded-lg border p-4 ${config.bg}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg p-2 ${config.color} bg-white/5`}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs text-gray-400">设备状态</p>
            <p className={`text-lg font-semibold ${config.color}`}>
              {config.label}
            </p>
            <p className="text-xs text-gray-500">{durationText}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">活跃告警</p>
          <p
            className={`text-lg font-semibold ${
              summary.active_alarms > 0 ? "text-red-400" : "text-gray-400"
            }`}
          >
            {summary.active_alarms}
          </p>
        </div>
      </div>
    </div>
  );
}
