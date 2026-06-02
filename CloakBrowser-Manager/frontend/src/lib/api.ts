/**
 * API client for CloakBrowser Manager backend.
 */

export interface Profile {
  id: string;
  name: string;
  fingerprint_seed: number;
  proxy: string | null;
  proxy_id: string | null;
  timezone: string | null;
  locale: string | null;
  platform: string;
  user_agent: string | null;
  screen_width: number;
  screen_height: number;
  gpu_vendor: string | null;
  gpu_renderer: string | null;
  hardware_concurrency: number | null;
  humanize: boolean;
  human_preset: string;
  headless: boolean;
  geoip: boolean;
  clipboard_sync: boolean;
  auto_launch: boolean;
  color_scheme: string | null;
  launch_args: string[];
  notes: string | null;
  user_data_dir: string;
  created_at: string;
  updated_at: string;
  tags: { tag: string; color: string | null }[];
  status: "running" | "stopped";
  vnc_ws_port: number | null;
  cdp_url: string | null;
  last_launched: string | null;
  fingerprint_locked: boolean;
  session_auto_save: boolean;
  auto_sync_timezone_with_proxy: boolean;
  auto_sync_locale_with_proxy: boolean;
  auto_sync_geolocation_with_proxy: boolean;
  last_fingerprint_change_at: string | null;
  last_session_save_at: string | null;
  last_proxy_change_at: string | null;
  verification_status?: "unverified" | "checking" | "verified" | "warning" | "failed" | "expired";
  last_verified_at?: string | null;
  last_verification_result?: string | null;
  require_verification_before_use?: boolean;
  verification_expires_minutes?: number;
  runtime_guardian_enabled?: boolean;
  runtime_guardian_status?: "idle" | "monitoring" | "healthy" | "warning" | "critical" | "stopped_by_guardian";
  runtime_risk_level?: "normal" | "warning" | "critical";
  last_runtime_check_at?: string | null;
  last_runtime_check_result?: any;
  deep_check_interval_minutes?: number;
}

export interface ProfileCreateData {
  name: string;
  fingerprint_seed?: number | null;
  proxy?: string | null;
  proxy_id?: string | null;
  timezone?: string | null;
  locale?: string | null;
  platform?: string;
  user_agent?: string | null;
  screen_width?: number;
  screen_height?: number;
  gpu_vendor?: string | null;
  gpu_renderer?: string | null;
  hardware_concurrency?: number | null;
  humanize?: boolean;
  human_preset?: string;
  headless?: boolean;
  geoip?: boolean;
  clipboard_sync?: boolean;
  auto_launch?: boolean;
  color_scheme?: string | null;
  launch_args?: string[];
  notes?: string | null;
  tags?: { tag: string; color: string | null }[];
  fingerprint_locked?: boolean;
  session_auto_save?: boolean;
  auto_sync_timezone_with_proxy?: boolean;
  auto_sync_locale_with_proxy?: boolean;
  auto_sync_geolocation_with_proxy?: boolean;
  verification_status?: "unverified" | "checking" | "verified" | "warning" | "failed" | "expired";
  last_verified_at?: string | null;
  last_verification_result?: string | null;
  require_verification_before_use?: boolean;
  verification_expires_minutes?: number;
  runtime_guardian_enabled?: boolean;
  runtime_guardian_status?: "idle" | "monitoring" | "healthy" | "warning" | "critical" | "stopped_by_guardian";
  runtime_risk_level?: "normal" | "warning" | "critical";
  last_runtime_check_at?: string | null;
  last_runtime_check_result?: any;
  deep_check_interval_minutes?: number;
}

export interface Proxy {
  id: string;
  name: string;
  type: "http" | "socks5";
  host: string;
  port: number;
  username: string | null;
  password: string | null;
  status: "active" | "inactive";
  latency_ms: number | null;
  last_ip: string | null;
  last_checked_at: string | null;
  timezone?: string | null;
  locale?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProxyCheckResult {
  status_code: string;
  proxy: Proxy;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  module: string;
  action: string;
  status: string;
  error_code: string | null;
  message: string | null;
  profile_id: string | null;
  proxy_id: string | null;
  duration_ms: number | null;
}

export interface DashboardSummary {
  total_profiles: number;
  running_profiles: number;
  stopped_profiles: number;
  failed_profiles: number;
  total_proxies: number;
  ok_proxies: number;
  failed_proxies: number;
  recent_errors: LogEntry[];
  max_running_profiles: number;
}

export interface ProxyCreateData {
  name: string;
  type?: "http" | "socks5";
  host: string;
  port: number;
  username?: string | null;
  password?: string | null;
  status?: "active" | "inactive";
}

export interface LaunchResult {
  profile_id: string;
  status: string;
  vnc_ws_port: number;
  display: string;
  cdp_url: string | null;
}

export interface SystemStatus {
  running_count: number;
  binary_version: string;
  profiles_total: number;
  is_desktop?: boolean;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// Global 401 callback — set by App to trigger login page on auth failure
let _onUnauthorized: (() => void) | null = null;
export function setOnUnauthorized(cb: (() => void) | null) {
  _onUnauthorized = cb;
}

const params = new URLSearchParams(window.location.search);
const apiPort = params.get("api_port") || "8080";
const API_BASE = `http://127.0.0.1:${apiPort}`;

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const simulatedRole = localStorage.getItem("cloak_simulated_role") || "user";
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": simulatedRole,
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    if (res.status === 401 && _onUnauthorized) {
      _onUnauthorized();
      throw new ApiError(401, "Unauthorized");
    }
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    let msg = res.statusText;
    if (typeof body.detail === "string") {
      msg = body.detail;
    } else if (body.detail && typeof body.detail === "object" && body.detail.message) {
      msg = body.detail.message;
    } else if (body.detail) {
      msg = JSON.stringify(body.detail);
    }
    throw new ApiError(res.status, msg);
  }
  return res.json();
}

export const api = {
  authStatus: () =>
    request<{ auth_required: boolean; authenticated: boolean }>("/api/auth/status"),

  login: (token: string) =>
    request<{ ok: boolean }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  logout: () =>
    request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

  listProfiles: () => request<Profile[]>("/api/profiles"),

  getProfile: (id: string) => request<Profile>(`/api/profiles/${id}`),

  createProfile: (data: ProfileCreateData) =>
    request<Profile>("/api/profiles", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProfile: (id: string, data: Partial<ProfileCreateData>) =>
    request<Profile>(`/api/profiles/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteProfile: (id: string) =>
    request<{ ok: boolean }>(`/api/profiles/${id}`, { method: "DELETE" }),

  deleteProfilesBatch: (ids: string[]) =>
    request<{ ok: boolean; deleted_count: number }>("/api/profiles-batch/delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  listProxies: () => request<Proxy[]>("/api/proxies"),

  getProxy: (id: string) => request<Proxy>(`/api/proxies/${id}`),

  createProxy: (data: ProxyCreateData) =>
    request<Proxy>("/api/proxies", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProxy: (id: string, data: Partial<ProxyCreateData>) =>
    request<Proxy>(`/api/proxies/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteProxy: (id: string) =>
    request<{ ok: boolean }>(`/api/proxies/${id}`, { method: "DELETE" }),

  deleteProxiesBatch: (ids: string[]) =>
    request<{ ok: boolean; deleted_count: number }>("/api/proxies-batch/delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  checkProxy: (id: string) =>
    request<ProxyCheckResult>(`/api/proxies/${id}/check`, { method: "POST" }),

  launchProfile: (id: string) =>
    request<LaunchResult>(`/api/profiles/${id}/launch`, { method: "POST" }),

  stopProfile: (id: string) =>
    request<{ ok: boolean }>(`/api/profiles/${id}/stop`, { method: "POST" }),

  getDashboardSummary: () =>
    request<DashboardSummary>("/api/dashboard/summary"),

  stopAllProfiles: () =>
    request<{ ok: boolean; total: number; stopped: number; failed: number }>("/api/profiles/stop-all", { method: "POST" }),

  getStatus: () => request<SystemStatus>("/api/status"),

  getBinaryStatus: () =>
    request<{ path: string | null; status: "Ready" | "Missing" | "Invalid"; is_desktop: boolean }>("/api/status/binary"),

  updateBinaryStatus: (path: string) =>
    request<{ ok: boolean; path: string }>("/api/status/binary", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  setClipboard: (id: string, text: string) =>
    request<{ ok: boolean }>(`/api/profiles/${id}/clipboard`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  getClipboard: (id: string) =>
    request<{ text: string }>(`/api/profiles/${id}/clipboard`),

  regenerateFingerprint: (id: string) =>
    request<Profile>(`/api/profiles/${id}/regenerate-fingerprint`, { method: "POST" }),

  verifyProfile: (id: string) =>
    request<Profile>(`/api/profiles/${id}/verify`, { method: "POST" }),

  getRuntimeStatus: () =>
    request<Record<string, {
      runtime_guardian_enabled: boolean;
      runtime_guardian_status: "idle" | "monitoring" | "healthy" | "warning" | "critical" | "stopped_by_guardian";
      runtime_risk_level: "normal" | "warning" | "critical";
      last_runtime_check_at: string | null;
      last_runtime_check_result: any;
    }>>("/api/profiles/runtime-status"),

  getRuntimeReport: (id: string) =>
    request<{
      profile_id: string;
      status: string;
      score: number;
      checked_at: string | null;
      checks: {
        proxy: "pass" | "warning" | "failed";
        fingerprint: "pass" | "warning" | "failed";
        headers: "pass" | "warning" | "failed";
        session: "pass" | "warning" | "failed";
      };
      blocking_issues: string[];
      warnings: string[];
      action_taken: string;
    }>(`/api/profiles/${id}/runtime-report`),


  exportPackage: async (id: string, passphrase?: string | null, include_proxy_secret: boolean = false): Promise<{ export_path?: string } | Blob> => {
    const simulatedRole = localStorage.getItem("cloak_simulated_role") || "user";
    const res = await fetch(`${API_BASE}/api/profiles/${id}/export-package`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Role": simulatedRole,
      },
      body: JSON.stringify({ passphrase: passphrase || null, include_proxy_secret }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      let msg = res.statusText;
      if (body.detail) {
        msg = body.detail.message || body.detail || res.statusText;
      }
      throw new Error(msg);
    }
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return res.json();
    } else {
      return res.blob();
    }
  },

  overrideWarning: (id: string, reason: string) =>
    request<Profile>(`/api/profiles/${id}/override-warning`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  importPackage: async (file: File, passphrase?: string | null, mode: "new_profile" | "overwrite" = "new_profile", targetProfileId?: string | null): Promise<{ status: string; profile_id: string }> => {
    const simulatedRole = localStorage.getItem("cloak_simulated_role") || "user";
    const formData = new FormData();
    formData.append("file", file);
    if (passphrase) {
      formData.append("passphrase", passphrase);
    }
    formData.append("mode", mode);
    if (targetProfileId) {
      formData.append("target_profile_id", targetProfileId);
    }
    const res = await fetch(`${API_BASE}/api/profiles/import-package`, {
      method: "POST",
      headers: {
        "X-User-Role": simulatedRole,
      },
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      let msg = res.statusText;
      if (body.detail) {
        msg = body.detail.message || body.detail || res.statusText;
      }
      throw new Error(msg);
    }
    return res.json();
  },
};
