import { useEquipmentData } from "@/hooks/useEquipmentData";
import EquipmentViewer from "../viewer/EquipmentViewer";
import StatusPanel from "../panel/StatusPanel";
import ProductionPanel from "../panel/ProductionPanel";
import ParameterPanel from "../panel/ParameterPanel";
import OEEGauge from "../panel/OEEGauge";
import AlarmPanel from "../panel/AlarmPanel";
import HistoryChart from "../panel/HistoryChart";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface TwinLayoutProps {
  equipmentId: string;
}

export default function TwinLayout({ equipmentId }: TwinLayoutProps) {
  const { summary, telemetry, alarms, loading, error, lastUpdated } =
    useEquipmentData(equipmentId);

  const status = summary?.equipment.status ?? "idle";
  const statusColors: Record<string, string> = {
    running: "bg-green-500",
    idle: "bg-blue-500",
    fault: "bg-red-500",
    maintenance: "bg-amber-500",
  };
  const statusLabels: Record<string, string> = {
    running: "运行中",
    idle: "待机",
    fault: "故障",
    maintenance: "维护中",
  };

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">
            {summary?.equipment.name ?? "滚筒剔除装置"}
          </h1>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[status]} text-white`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-white/80" />
            {statusLabels[status] ?? status}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          {error && (
            <span className="flex items-center gap-1 text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              {error}
            </span>
          )}
          {loading && <RefreshCw className="h-3 w-3 animate-spin" />}
          {lastUpdated && (
            <span>更新于 {lastUpdated.toLocaleTimeString("zh-CN")}</span>
          )}
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: 3D Viewer */}
        <div className="flex-[3] min-w-0">
          <EquipmentViewer equipmentId={equipmentId} alarms={alarms} telemetry={telemetry} />
        </div>

        {/* Right: Data Panel */}
        <div className="flex-[2] overflow-y-auto border-l border-gray-800 p-4 space-y-4">
          <StatusPanel summary={summary} telemetry={telemetry} />
          <ProductionPanel summary={summary} telemetry={telemetry} />
          <ParameterPanel telemetry={telemetry} />
          <OEEGauge telemetry={telemetry} />
          <AlarmPanel alarms={alarms} />
          <HistoryChart equipmentId={equipmentId} telemetry={telemetry} />
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-2 text-xs text-gray-600">
        {summary?.equipment.model ?? "—"} · {summary?.equipment.location ?? "—"}
      </footer>
    </div>
  );
}
