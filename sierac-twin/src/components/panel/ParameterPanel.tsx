import type { TelemetryValue } from "@/types/equipment";
import { Gauge } from "lucide-react";

interface ParameterPanelProps {
  telemetry: TelemetryValue[];
}

const DISPLAY_POINTS = [
  "roller_speed",
  "belt_speed",
  "motor_current",
  "temperature",
  "today_reject",
  "runtime_today",
];

function isOutOfRange(point: TelemetryValue): boolean {
  if (typeof point.value !== "number") return false;
  if (point.min !== null && point.value < point.min) return true;
  if (point.max !== null && point.value > point.max) return true;
  return false;
}

function formatValue(value: number | string | boolean): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  }
  return String(value);
}

export default function ParameterPanel({ telemetry }: ParameterPanelProps) {
  const points = telemetry.filter((t) => DISPLAY_POINTS.includes(t.point_id));

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="h-24 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium text-gray-400">
        <Gauge className="h-3.5 w-3.5" />
        关键参数
      </div>

      <div className="space-y-1.5">
        {points.map((point) => {
          const outOfRange = isOutOfRange(point);
          return (
            <div
              key={point.point_id}
              className={`flex items-center justify-between rounded px-2 py-1.5 text-sm ${
                outOfRange
                  ? "bg-red-500/10 text-red-400"
                  : "text-gray-300"
              }`}
            >
              <span className="text-gray-400">{point.name}</span>
              <span className="tabular-nums font-medium">
                {formatValue(point.value)}
                {point.unit && (
                  <span className="ml-1 text-xs text-gray-500">
                    {point.unit}
                  </span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
