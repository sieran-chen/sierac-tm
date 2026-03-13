import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import type { TelemetryValue } from "@/types/equipment";
import { useHistory } from "@/hooks/useHistory";
import { TrendingUp } from "lucide-react";

const HOUR_OPTIONS = [1, 4, 8, 24] as const;

interface HistoryChartProps {
  equipmentId: string;
  telemetry: TelemetryValue[];
}

function isNumericPoint(t: TelemetryValue): boolean {
  return typeof t.value === "number";
}

export default function HistoryChart({
  equipmentId,
  telemetry,
}: HistoryChartProps) {
  const numericPoints = useMemo(
    () => telemetry.filter(isNumericPoint),
    [telemetry]
  );
  const [pointId, setPointId] = useState<string>(
    () => numericPoints[0]?.point_id ?? ""
  );
  const [hours, setHours] = useState<number>(4);

  const { data, loading, error } = useHistory(equipmentId, pointId, hours);

  const chartData = useMemo(() => {
    if (!data?.data?.length) return [];
    return data.data.map((d) => ({
      time: new Date(d.timestamp).getTime(),
      value: d.value,
      label: new Date(d.timestamp).toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    }));
  }, [data]);

  const yMin =
    data?.min != null && data?.max != null
      ? Math.min(data.min, ...chartData.map((d) => d.value))
      : undefined;
  const yMax =
    data?.max != null && data?.min != null
      ? Math.max(data.max, ...chartData.map((d) => d.value))
      : undefined;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-xs font-medium text-gray-400">
          <TrendingUp className="h-3.5 w-3.5" />
          历史趋势
        </span>
        <div className="flex items-center gap-2">
          <select
            className="rounded border border-gray-700 bg-gray-800 px-2 py-1 text-xs text-gray-200"
            value={pointId}
            onChange={(e) => setPointId(e.target.value)}
          >
            {numericPoints.map((t) => (
              <option key={t.point_id} value={t.point_id}>
                {t.name}
              </option>
            ))}
          </select>
          {HOUR_OPTIONS.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHours(h)}
              className={`rounded px-2 py-0.5 text-xs ${
                hours === h
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {h}h
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="py-4 text-center text-sm text-amber-400">{error}</p>
      )}
      {loading && (
        <div className="flex h-48 items-center justify-center text-sm text-gray-500">
          加载中…
        </div>
      )}
      {!loading && !error && chartData.length === 0 && (
        <p className="py-8 text-center text-sm text-gray-500">
          暂无历史数据，请稍后刷新
        </p>
      )}
      {!loading && !error && chartData.length > 0 && (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10 }}
                stroke="#6b7280"
              />
              <YAxis
                tick={{ fontSize: 10 }}
                stroke="#6b7280"
                domain={yMin != null && yMax != null ? [yMin, yMax] : ["auto", "auto"]}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                labelFormatter={(_, payload) =>
                  payload[0]?.payload?.label ?? ""
                }
                formatter={(value: number) => [
                  `${value}${data?.unit ?? ""}`,
                  data?.point_name ?? pointId,
                ]}
              />
              {data?.min != null && data?.max != null && (
                <>
                  <ReferenceArea
                    y1={data.min}
                    y2={data.max}
                    fill="#22c55e"
                    fillOpacity={0.15}
                  />
                  {yMin != null && yMin < data.min && (
                    <ReferenceArea
                      y1={yMin}
                      y2={data.min}
                      fill="#ef4444"
                      fillOpacity={0.12}
                    />
                  )}
                  {yMax != null && yMax > data.max && (
                    <ReferenceArea
                      y1={data.max}
                      y2={yMax}
                      fill="#ef4444"
                      fillOpacity={0.12}
                    />
                  )}
                </>
              )}
              <Line
                type="monotone"
                dataKey="value"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
