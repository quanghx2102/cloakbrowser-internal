import { useState, useEffect, useCallback } from "react";
import { api, DashboardSummary } from "../lib/api";

export function useDashboard(refreshInterval = 5000) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api.getDashboardSummary();
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch dashboard summary");
    } finally {
      setLoading(false);
    }
  }, []);

  const stopAll = useCallback(async () => {
    try {
      const res = await api.stopAllProfiles();
      await fetchSummary();
      return res;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop profiles");
      throw err;
    }
  }, [fetchSummary]);

  useEffect(() => {
    fetchSummary();
    const interval = setInterval(fetchSummary, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchSummary, refreshInterval]);

  return { summary, loading, error, refresh: fetchSummary, stopAll };
}
