import type { EquipmentSummary, TelemetryValue } from "@/types/equipment";
import { Package } from "lucide-react";

interface ProductionPanelProps {
  summary: EquipmentSummary | null;
  telemetry: TelemetryValue[];
}

function formatNumber(n: number): string {
  return n.toLocaleString("zh-CN");
}

export default function ProductionPanel({
  summary,
  telemetry,
}: ProductionPanelProps) {
  if (!summary) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="h-20 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  const passCount = summary.highlights.today_pass?.value ?? 0;
  const target = summary.highlights.today_target?.value ?? 1;
  const rate = target > 0 ? (passCount / target) * 100 : 0;

  const rejectPoint = telemetry.find((t) => t.point_id === "today_reject");
  const rejectCount =
    typeof rejectPoint?.value === "number" ? rejectPoint.value : 0;

  const barColor =
    rate < 50 ? "bg-red-500" : rate < 80 ? "bg-amber-500" : "bg-green-500";

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium text-gray-400">
        <Package className="h-3.5 w-3.5" />
        通过 / 剔除
      </div>

      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-2xl font-bold tabular-nums text-gray-100">
          {formatNumber(passCount)}
        </span>
        <span className="text-sm text-gray-500">
          / {formatNumber(target)} 件
        </span>
      </div>

      <div className="mb-2 h-2 overflow-hidden rounded-full bg-gray-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, rate)}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>通过率 {rate.toFixed(1)}%</span>
        {rejectCount > 0 && (
          <span className="text-amber-400">剔除 {formatNumber(rejectCount)} 件</span>
        )}
      </div>
    </div>
  );
}
