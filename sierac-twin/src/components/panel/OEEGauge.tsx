import { useState } from "react";
import type { TelemetryValue } from "@/types/equipment";
import { Target, ChevronDown, ChevronUp } from "lucide-react";

interface OEEGaugeProps {
  telemetry: TelemetryValue[];
}

function GaugeRing({
  value,
  size = 100,
  strokeWidth = 8,
  color,
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
  color: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - value / 100);

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-gray-800"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700"
      />
    </svg>
  );
}

function getTelemetryNumber(telemetry: TelemetryValue[], pointId: string): number {
  const p = telemetry.find((t) => t.point_id === pointId);
  return typeof p?.value === "number" ? p.value : 0;
}

export default function OEEGauge({ telemetry }: OEEGaugeProps) {
  const [expanded, setExpanded] = useState(false);
  const oee = getTelemetryNumber(telemetry, "oee");
  const availability = getTelemetryNumber(telemetry, "availability_rate");
  const performance = getTelemetryNumber(telemetry, "performance_rate");
  const quality = getTelemetryNumber(telemetry, "quality_rate");

  const oeeColor =
    oee >= 85 ? "#22c55e" : oee >= 70 ? "#f59e0b" : "#ef4444";

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="mb-3 flex items-center justify-between text-xs font-medium text-gray-400">
        <span className="flex items-center gap-2">
          <Target className="h-3.5 w-3.5" />
          设备综合效率 (OEE)
        </span>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-0.5 text-gray-500 hover:text-gray-300"
        >
          {expanded ? (
            <>
              收起 <ChevronUp className="h-3 w-3" />
            </>
          ) : (
            <>
              分解 <ChevronDown className="h-3 w-3" />
            </>
          )}
        </button>
      </div>

      <div className="flex items-center justify-center">
        <div className="relative">
          <GaugeRing value={oee} size={120} strokeWidth={10} color={oeeColor} />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="text-2xl font-bold tabular-nums"
              style={{ color: oeeColor }}
            >
              {oee.toFixed(1)}
            </span>
            <span className="text-xs text-gray-500">%</span>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 space-y-1.5 rounded border border-gray-800 bg-gray-950/50 px-3 py-2 text-sm">
          <div className="flex justify-between text-gray-400">
            <span>可用率</span>
            <span className="tabular-nums text-gray-200">{availability.toFixed(1)}%</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>性能率</span>
            <span className="tabular-nums text-gray-200">{performance.toFixed(1)}%</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>良品率</span>
            <span className="tabular-nums text-gray-200">{quality.toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
