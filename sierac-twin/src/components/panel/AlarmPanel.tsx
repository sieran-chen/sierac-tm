import type { Alarm, AlarmLevel } from "@/types/equipment";
import { Bell, AlertTriangle, AlertOctagon, Info } from "lucide-react";

interface AlarmPanelProps {
  alarms: Alarm[];
}

const LEVEL_CONFIG: Record<
  AlarmLevel,
  { icon: typeof Bell; bg: string; text: string; label: string }
> = {
  critical: {
    icon: AlertOctagon,
    bg: "bg-red-600",
    text: "text-white",
    label: "严重",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-amber-100",
    text: "text-amber-800",
    label: "警告",
  },
  info: {
    icon: Info,
    bg: "bg-blue-50",
    text: "text-blue-800",
    label: "信息",
  },
};

const LEVEL_ORDER: AlarmLevel[] = ["critical", "warning", "info"];

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function AlarmPanel({ alarms }: AlarmPanelProps) {
  const sorted = [...alarms].sort(
    (a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level)
  );

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium text-gray-400">
        <Bell className="h-3.5 w-3.5" />
        告警
        {sorted.length > 0 && (
          <span className="rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] text-white">
            {sorted.length}
          </span>
        )}
      </div>

      {sorted.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-600">无活跃告警</p>
      ) : (
        <div className="space-y-2">
          {sorted.map((alarm) => {
            const config = LEVEL_CONFIG[alarm.level];
            const Icon = config.icon;
            return (
              <div
                key={alarm.id}
                className={`flex items-start gap-2 rounded-md px-3 py-2 ${config.bg} ${config.text}`}
              >
                <Icon className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm leading-tight">{alarm.message}</p>
                  <p className="mt-0.5 text-xs opacity-70">
                    {formatTime(alarm.start_time)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
