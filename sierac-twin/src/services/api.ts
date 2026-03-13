import type {
  EquipmentSummary,
  TelemetryValue,
  Alarm,
  HistoryResponse,
} from "@/types/equipment";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function fetchSummary(equipmentId: string): Promise<EquipmentSummary> {
  return fetchJSON(`${BASE_URL}/api/twin/equipment/${equipmentId}/summary`);
}

export function fetchTelemetry(equipmentId: string): Promise<TelemetryValue[]> {
  return fetchJSON(`${BASE_URL}/api/twin/equipment/${equipmentId}/telemetry`);
}

export function fetchAlarms(equipmentId: string): Promise<Alarm[]> {
  return fetchJSON(
    `${BASE_URL}/api/twin/equipment/${equipmentId}/alarms?active=true`
  );
}

export function fetchHistory(
  equipmentId: string,
  pointId: string,
  hours: number = 4,
  interval: number = 10
): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    point_id: pointId,
    hours: String(hours),
    interval: String(interval),
  });
  return fetchJSON(
    `${BASE_URL}/api/twin/equipment/${equipmentId}/history?${params}`
  );
}
