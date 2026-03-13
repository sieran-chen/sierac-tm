import { useState, useEffect, useCallback, useRef } from "react";
import type { EquipmentData } from "@/types/equipment";
import { fetchSummary, fetchTelemetry, fetchAlarms } from "@/services/api";

const POLL_INTERVAL = Number(import.meta.env.VITE_POLL_INTERVAL ?? 5000);

export function useEquipmentData(equipmentId: string): EquipmentData {
  const [data, setData] = useState<EquipmentData>({
    summary: null,
    telemetry: [],
    alarms: [],
    loading: true,
    error: null,
    lastUpdated: null,
  });

  const failCount = useRef(0);

  const refresh = useCallback(async () => {
    try {
      const [summary, telemetry, alarms] = await Promise.all([
        fetchSummary(equipmentId),
        fetchTelemetry(equipmentId),
        fetchAlarms(equipmentId),
      ]);

      failCount.current = 0;
      setData({
        summary,
        telemetry,
        alarms,
        loading: false,
        error: null,
        lastUpdated: new Date(),
      });
    } catch (err) {
      failCount.current += 1;
      const message =
        err instanceof Error ? err.message : "Unknown error";

      setData((prev) => ({
        ...prev,
        loading: false,
        error:
          failCount.current >= 3
            ? `连接失败 (${failCount.current} 次): ${message}`
            : message,
      }));
    }
  }, [equipmentId]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [refresh]);

  return data;
}
