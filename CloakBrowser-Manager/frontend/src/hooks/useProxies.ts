import { useState, useEffect, useCallback } from "react";
import { api, type Proxy, type ProxyCreateData } from "../lib/api";

export function useProxies() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProxies = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listProxies();
      setProxies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load proxies");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProxies();
  }, [fetchProxies]);

  const create = useCallback(async (data: ProxyCreateData) => {
    try {
      setError(null);
      const newProxy = await api.createProxy(data);
      setProxies((prev) => [newProxy, ...prev]);
      return newProxy;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create proxy");
      throw err;
    }
  }, []);

  const update = useCallback(async (id: string, data: Partial<ProxyCreateData>) => {
    try {
      setError(null);
      const updated = await api.updateProxy(id, data);
      setProxies((prev) => prev.map((p) => (p.id === id ? updated : p)));
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update proxy");
      throw err;
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.deleteProxy(id);
      setProxies((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete proxy");
      throw err;
    }
  }, []);

  const removeBatch = useCallback(async (ids: string[]) => {
    try {
      setError(null);
      await api.deleteProxiesBatch(ids);
      setProxies((prev) => prev.filter((p) => !ids.includes(p.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete proxies");
      throw err;
    }
  }, []);

  const check = useCallback(async (id: string) => {
    try {
      setError(null);
      const result = await api.checkProxy(id);
      setProxies((prev) => prev.map((p) => (p.id === id ? result.proxy : p)));
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check proxy");
      throw err;
    }
  }, []);

  return {
    proxies,
    loading,
    error,
    create,
    update,
    remove,
    removeBatch,
    check,
    refresh: fetchProxies,
  };
}
