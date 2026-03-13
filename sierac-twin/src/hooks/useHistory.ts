import { useState, useEffect, useCallback } from "react";
import type { HistoryResponse } from "@/types/equipment";
import { fetchHistory } from "@/services/api";

export function useHistory(
  equipmentId: string,
  pointId: string,
  hours: number = 4
) {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!pointId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchHistory(equipmentId, pointId, hours, 10);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [equipmentId, pointId, hours]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, refresh: load };
}
