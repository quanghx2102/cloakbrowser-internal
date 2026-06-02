import { useCallback, useEffect, useState } from "react";
import { api, type Profile, type ProfileCreateData } from "../lib/api";

export function useProfiles() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listProfiles();
      setProfiles(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch profiles");
    } finally {
      setLoading(false);
    }
  }, []);

  const pollRuntimeStatus = useCallback(async () => {
    try {
      const statusMap = await api.getRuntimeStatus();
      setProfiles((prev) =>
        prev.map((p) => {
          const status = statusMap[p.id];
          if (status) {
            return {
              ...p,
              runtime_guardian_enabled: status.runtime_guardian_enabled,
              runtime_guardian_status: status.runtime_guardian_status,
              runtime_risk_level: status.runtime_risk_level,
              last_runtime_check_at: status.last_runtime_check_at,
              last_runtime_check_result: status.last_runtime_check_result,
            };
          }
          return p;
        })
      );
    } catch (err) {
      console.warn("Failed to poll runtime guardian status:", err);
    }
  }, []);

  useEffect(() => {
    refresh();
    // Poll for status changes every 3 seconds
    const interval = setInterval(refresh, 3000);
    // Poll specifically for runtime guardian status every 5 seconds
    const guardianInterval = setInterval(pollRuntimeStatus, 5000);
    return () => {
      clearInterval(interval);
      clearInterval(guardianInterval);
    };
  }, [refresh, pollRuntimeStatus]);

  const create = useCallback(
    async (data: ProfileCreateData): Promise<Profile> => {
      try {
        const profile = await api.createProfile(data);
        setProfiles((prev) => [profile, ...prev]);
        return profile;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create profile");
        throw err;
      }
    },
    [],
  );

  const update = useCallback(
    async (id: string, data: Partial<ProfileCreateData>) => {
      try {
        const profile = await api.updateProfile(id, data);
        setProfiles((prev) => prev.map((p) => (p.id === id ? profile : p)));
        return profile;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to update profile");
        throw err;
      }
    },
    [],
  );

  const remove = useCallback(
    async (id: string) => {
      try {
        await api.deleteProfile(id);
        setProfiles((prev) => prev.filter((p) => p.id !== id));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete profile");
        throw err;
      }
    },
    [],
  );

  const removeBatch = useCallback(
    async (ids: string[]) => {
      try {
        await api.deleteProfilesBatch(ids);
        setProfiles((prev) => prev.filter((p) => !ids.includes(p.id)));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete profiles");
        throw err;
      }
    },
    [],
  );

  const launch = useCallback(
    async (id: string) => {
      try {
        const result = await api.launchProfile(id);
        await refresh();
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to launch profile");
      }
    },
    [refresh],
  );

  const stop = useCallback(
    async (id: string) => {
      try {
        await api.stopProfile(id);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to stop profile");
      }
    },
    [refresh],
  );

  return { profiles, loading, error, refresh, create, update, remove, removeBatch, launch, stop };
}
