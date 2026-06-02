import {
  Plus,
  Search,
  Monitor,
  Play,
  Square,
  Eye,
  Pencil,
  ScrollText,
  Filter,
  Loader2,
  Download,
  Upload,
  Cookie,
  Trash2,
} from "lucide-react";
import { useState, useEffect } from "react";
import { api } from "../lib/api";
import type { Profile } from "../lib/api";
import { StatusIndicator } from "./StatusIndicator";
import { RuntimeStatusBadges } from "./RuntimeStatusBadges";


type StatusFilter = "all" | "running" | "stopped";

interface ProfileListProps {
  profiles: Profile[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onLaunch: (id: string) => Promise<void>;
  onStop: (id: string) => Promise<void>;
  onView: (id: string) => void;
  onEdit: (id: string) => void;
  onLogs: (id: string) => void;
  onExportClick: (id: string) => void;
  onImportClick: () => void;
  onDelete?: (id: string) => Promise<void>;
  onDeleteBatch?: (ids: string[]) => Promise<void>;
  isDesktop?: boolean;
}

function formatLastLaunched(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Vừa xong";
  if (diffMins < 60) return `${diffMins} phút trước`;
  if (diffHours < 24) return `${diffHours} giờ trước`;
  if (diffDays < 7) return `${diffDays} ngày trước`;
  return date.toLocaleDateString();
}

function formatProxy(proxy: string | null): string {
  if (!proxy) return "—";
  try {
    const url = new URL(proxy);
    return url.hostname + (url.port ? `:${url.port}` : "");
  } catch {
    return proxy.length > 24 ? proxy.slice(0, 22) + "…" : proxy;
  }
}

export function ProfileList({
  profiles,
  selectedId,
  onSelect,
  onNew,
  onLaunch,
  onStop,
  onView,
  onEdit,
  onLogs,
  onExportClick,
  onImportClick,
  onDelete,
  onDeleteBatch,
  isDesktop,
}: ProfileListProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [reportProfile, setReportProfile] = useState<Profile | null>(null);
  const [reportData, setReportData] = useState<any | null>(null);
  const [loadingReport, setLoadingReport] = useState<boolean>(false);

  // Bulk select & Pagination states
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Clear selections when status changes or filter changes
  useEffect(() => {
    setSelectedIds([]);
  }, [statusFilter]);

  const handleSearchChange = (val: string) => {
    setSearch(val);
    setCurrentPage(1);
  };

  const handleFilterChange = (val: StatusFilter) => {
    setStatusFilter(val);
    setCurrentPage(1);
  };

  const handleOpenReport = async (profile: Profile) => {
    setReportProfile(profile);
    setLoadingReport(true);
    setReportData(null);
    try {
      const data = await api.getRuntimeReport(profile.id);
      setReportData(data);
    } catch (err) {
      console.error("Failed to load report", err);
      // Fallback
      setReportData({
        profile_id: profile.id,
        status: profile.runtime_guardian_status || "critical",
        score: profile.runtime_guardian_status === "critical" ? 45 : 100,
        checked_at: profile.last_runtime_check_at,
        checks: {
          proxy: "failed",
          fingerprint: "pass",
          headers: "warning",
          session: "pass"
        },
        blocking_issues: [],
        warnings: [],
        action_taken: "stop_profile"
      });
    } finally {
      setLoadingReport(false);
    }
  };

  const role = localStorage.getItem("cloak_simulated_role") || "user";
  const isStaff = role === "staff" || role === "user";

  const filtered = profiles.filter((p) => {
    const matchName = p.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    return matchName && matchStatus;
  });

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const paginatedItems = filtered.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const runningCount = profiles.filter((p) => p.status === "running").length;

  const handleLaunch = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setLoadingId(id);
    try {
      await onLaunch(id);
    } finally {
      setLoadingId(null);
    }
  };

  const handleStop = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setLoadingId(id);
    try {
      await onStop(id);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Monitor className="h-4 w-4 text-accent" />
            <h1 className="text-sm font-semibold tracking-tight">Profiles</h1>
          </div>
          <div className="flex items-center gap-2">
            {runningCount > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">
                {runningCount} đang chạy
              </span>
            )}
            <span className="text-[10px] text-gray-500">Tổng số: {profiles.length}</span>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
          <input
            id="profile-search"
            type="text"
            placeholder="Tìm kiếm profile..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="input pl-8 py-1.5 text-xs"
          />
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-1">
          <Filter className="h-3 w-3 text-gray-500 flex-shrink-0" />
          {(["all", "running", "stopped"] as StatusFilter[]).map((s) => (
            <button
              key={s}
              id={`filter-${s}`}
              onClick={() => handleFilterChange(s)}
              className={`text-[10px] px-2 py-0.5 rounded-full capitalize transition-colors ${
                statusFilter === s
                  ? s === "running"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : s === "stopped"
                      ? "bg-gray-500/20 text-gray-300"
                      : "bg-accent/20 text-accent"
                  : "text-gray-500 hover:text-gray-300 hover:bg-surface-3"
              }`}
            >
              {s === "all" ? `Tất cả (${profiles.length})` : s === "running" ? `Đang chạy (${runningCount})` : `Đã dừng (${profiles.length - runningCount})`}
            </button>
          ))}
        </div>

        {/* Bulk Delete Banner */}
        {selectedIds.length > 0 && (
          <div className="mt-3 p-2 rounded bg-rose-500/10 border border-rose-500/20 flex items-center justify-between animate-in fade-in slide-in-from-top-1 duration-150">
            <span className="text-[11px] font-medium text-rose-400">
              Đang chọn {selectedIds.length} profiles
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedIds([])}
                className="text-[10px] px-2 py-0.5 rounded hover:bg-surface-2 text-gray-400 font-medium transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={async () => {
                  if (window.confirm(`Bạn có chắc chắn muốn xóa ${selectedIds.length} profile đã chọn không?`)) {
                    if (onDeleteBatch) {
                      await onDeleteBatch(selectedIds);
                      setSelectedIds([]);
                    }
                  }
                }}
                className="text-[10px] px-2 py-0.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium transition-colors flex items-center gap-1"
              >
                <Trash2 className="h-3 w-3" />
                <span>Xóa hàng loạt</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="text-center text-gray-500 text-xs py-10">
            {profiles.length === 0 ? "Chưa có profile nào. Hãy tạo một cái để bắt đầu." : "Không có profile nào khớp với bộ lọc."}
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-1 z-10">
              <tr className="border-b border-border">
                <th className="text-left px-3 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[5%]">
                  <input
                    type="checkbox"
                    checked={paginatedItems.length > 0 && paginatedItems.every(p => selectedIds.includes(p.id))}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedIds(prev => {
                          const next = [...prev];
                          paginatedItems.forEach(p => {
                            if (!next.includes(p.id)) next.push(p.id);
                          });
                          return next;
                        });
                      } else {
                        setSelectedIds(prev => prev.filter(id => !paginatedItems.some(p => p.id === id)));
                      }
                    }}
                    className="rounded border-gray-700 bg-surface-2 text-accent focus:ring-accent"
                  />
                </th>
                <th className="text-left px-3 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[35%]">
                  Tên Profile
                </th>
                <th className="text-left px-2 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                  Trạng thái
                </th>
                <th className="text-left px-2 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[20%]">
                  Proxy
                </th>
                <th className="text-left px-2 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                  Lần chạy cuối
                </th>
                <th className="text-right px-3 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedItems.map((profile) => {
                const isSelected = selectedId === profile.id;
                const isLoading = loadingId === profile.id;
                const effectiveStatus = isLoading
                  ? "launching"
                  : profile.status;

                const result = (() => {
                  if (!profile.last_runtime_check_result) return {};
                  try {
                    return typeof profile.last_runtime_check_result === "string"
                      ? JSON.parse(profile.last_runtime_check_result)
                      : profile.last_runtime_check_result;
                  } catch {
                    return {};
                  }
                })();

                const errCode = result?.error_code || result?.policy_report?.error_code || result?.proxy_check?.status_code;
                const isCritical = profile.runtime_guardian_status === "critical" || profile.runtime_guardian_status === "stopped_by_guardian" || profile.runtime_risk_level === "critical";
                const isWarning = profile.runtime_guardian_status === "warning" || profile.runtime_risk_level === "warning";

                let criticalMessage = "Phát hiện sự cố bảo mật nghiêm trọng. Profile đã dừng.";
                if (profile.runtime_guardian_status === "stopped_by_guardian") {
                  criticalMessage = "Session đã được lưu sau khi dừng profile.";
                } else if (["PROXY_CONNECTION_FAILED", "PROXY_TIMEOUT", "PROXY_AUTH_FAILED", "PROXY_CHECK_FAILED"].includes(errCode)) {
                  criticalMessage = "Proxy đã mất kết nối. Profile đã được dừng để đảm bảo an toàn.";
                } else if (["PROXY_EXIT_IP_CHANGED", "PROXY_COUNTRY_CHANGED", "PROXY_ASN_CHANGED"].includes(errCode)) {
                  criticalMessage = "IP proxy đã thay đổi ngoài chính sách.";
                } else if (["FINGERPRINT_UA_MISMATCH", "HEADERS_MISMATCH_CRITICAL", "FINGERPRINT_WEBGL_MISMATCH", "FINGERPRINT_CANVAS_MISMATCH", "FINGERPRINT_FONT_MISMATCH"].includes(errCode)) {
                  criticalMessage = "Fingerprint không khớp cấu hình đã khóa.";
                } else if (["TLS_CHECK_UNAVAILABLE", "expired"].includes(errCode) || profile.verification_status === "expired") {
                  criticalMessage = "Kết quả xác minh đã hết hạn. Vui lòng Verify lại profile.";
                }

                let warningMessage = "Cảnh báo giám sát thời gian thực phát hiện sự cố.";
                if (profile.verification_status === "expired") {
                  warningMessage = "Kết quả xác minh đã hết hạn. Vui lòng Verify lại profile.";
                } else if (errCode === "TLS_CHECK_UNAVAILABLE") {
                  warningMessage = "Dịch vụ xác thực TLS bên thứ ba hiện không khả dụng.";
                }

                return (
                  <tr
                    key={profile.id}
                    id={`profile-row-${profile.id}`}
                    onClick={() => onSelect(profile.id)}
                    className={`border-b border-border/50 cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-accent/10 border-l-2 border-l-accent"
                        : isCritical
                          ? "bg-rose-950/10 border-l-2 border-l-rose-500 hover:bg-rose-950/20"
                          : isWarning
                            ? "bg-amber-950/10 border-l-2 border-l-amber-500 hover:bg-amber-950/20"
                            : "hover:bg-surface-2 border-l-2 border-l-transparent"
                    }`}
                  >
                    {/* Checkbox */}
                    <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(profile.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedIds(prev => [...prev, profile.id]);
                          } else {
                            setSelectedIds(prev => prev.filter(id => id !== profile.id));
                          }
                        }}
                        className="rounded border-gray-700 bg-surface-2 text-accent focus:ring-accent"
                      />
                    </td>
                    {/* Name */}
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2 min-w-0 flex-wrap">
                        <span
                          className="font-medium text-gray-100 truncate max-w-[120px]"
                          title={profile.name}
                        >
                          {profile.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] text-gray-500 capitalize">
                          {profile.platform}
                        </span>
                        {profile.tags.length > 0 && (
                          <>
                            <span className="text-gray-600">·</span>
                            {profile.tags.slice(0, 2).map((t) => (
                              <span
                                key={t.tag}
                                className="text-[9px] px-1 py-0.5 rounded-full bg-surface-4 text-gray-400"
                                style={
                                  t.color
                                    ? {
                                        backgroundColor: `${t.color}20`,
                                        color: t.color,
                                      }
                                    : undefined
                                }
                              >
                                {t.tag}
                              </span>
                            ))}
                            {profile.tags.length > 2 && (
                              <span className="text-[9px] text-gray-600">
                                +{profile.tags.length - 2}
                              </span>
                            )}
                          </>
                        )}
                      </div>
                      
                      {/* Runtime Status Badges */}
                      <RuntimeStatusBadges
                        proxyStatus={result?.proxy_check?.status_code}
                        verificationStatus={profile.verification_status}
                        runtimeGuardianStatus={profile.runtime_guardian_status}
                        fingerprintLocked={profile.fingerprint_locked}
                        lastCheck={profile.last_runtime_check_at}
                      />

                      {/* Critical Banner */}
                      {isCritical && (
                        <div className="mt-2 px-2 py-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px] font-medium flex items-center justify-between shadow-sm">
                          <span className="truncate">{criticalMessage}</span>
                          <button
                            id={`btn-report-${profile.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenReport(profile);
                            }}
                            className="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-[9px] font-semibold transition-all ml-2 flex-shrink-0"
                          >
                            View Report
                          </button>
                        </div>
                      )}

                      {/* Warning Banner */}
                      {isWarning && !isCritical && (
                        <div className="mt-2 px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-medium flex flex-col gap-0.5 shadow-sm">
                          <span>{warningMessage}</span>
                          {["admin", "super_admin"].includes(role.toLowerCase()) && (
                            <div className="mt-1 flex items-center justify-between gap-2">
                              <span className="text-[9px] text-amber-500 font-semibold italic">
                                * Quyền Override: Bạn có thể ghi đè để chạy profile.
                              </span>
                              <button
                                id={`btn-override-${profile.id}`}
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  const reason = window.prompt("Nhập lý do ghi đè cảnh báo (Reason required):");
                                  if (!reason || !reason.trim()) {
                                    alert("Lý do không được để trống!");
                                    return;
                                  }
                                  try {
                                    await api.overrideWarning(profile.id, reason);
                                    alert("Ghi đè cảnh báo thành công!");
                                    window.location.reload();
                                  } catch (err: any) {
                                    alert("Lỗi ghi đè: " + err.message);
                                  }
                                }}
                                className="px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-[9px] font-semibold transition-all flex-shrink-0"
                              >
                                Override Warning
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Expired Banner */}
                      {profile.verification_status === "expired" && !isCritical && (
                        <div className="mt-2 px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-medium flex flex-col gap-0.5 shadow-sm">
                          <span>Proxy changed. Re-verification required. (Proxy đã thay đổi. Yêu cầu xác thực lại.)</span>
                        </div>
                      )}
                    </td>

                    {/* Status */}
                    <td className="px-2 py-2.5">
                      <StatusIndicator
                        status={effectiveStatus as "running" | "stopped" | "launching"}
                        showLabel
                        size="sm"
                      />
                    </td>

                    {/* Proxy */}
                    <td className="px-2 py-2.5">
                      <span
                        className={`text-[10px] font-mono ${profile.proxy ? "text-gray-300" : "text-gray-600"}`}
                        title={profile.proxy ?? undefined}
                      >
                        {formatProxy(profile.proxy)}
                      </span>
                    </td>

                    {/* Last Launched */}
                    <td className="px-2 py-2.5">
                      <span className="text-[10px] text-gray-500">
                        {formatLastLaunched(profile.last_launched)}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-3 py-2.5">
                      <div
                        className="flex items-center justify-end gap-0.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {/* Launch / Stop */}
                        {isLoading ? (
                          <span className="p-1 text-gray-500">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          </span>
                        ) : profile.status === "running" ? (
                          <button
                            id={`btn-stop-${profile.id}`}
                            onClick={(e) => handleStop(e, profile.id)}
                            className="p-1 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-colors"
                            title={isDesktop ? "Đóng" : "Dừng"}
                          >
                            <Square className="h-3.5 w-3.5" />
                          </button>
                        ) : (
                          <button
                            id={`btn-launch-${profile.id}`}
                            onClick={(e) => handleLaunch(e, profile.id)}
                            disabled={(() => {
                              if (isCritical) return true;
                              if (!profile.require_verification_before_use) return false;
                              const status = profile.verification_status || "unverified";
                              if (["failed", "unverified", "expired", "checking"].includes(status)) return true;
                              if (status === "warning") {
                                return !["admin", "super_admin"].includes(role.toLowerCase());
                              }
                              return false;
                            })()}
                            className={`p-1 rounded transition-colors ${
                              (() => {
                                if (isCritical) return "text-gray-700 cursor-not-allowed";
                                if (!profile.require_verification_before_use) return "text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10";
                                const status = profile.verification_status || "unverified";
                                if (["failed", "unverified", "expired", "checking"].includes(status)) return "text-gray-700 cursor-not-allowed";
                                if (status === "warning") {
                                  return ["admin", "super_admin"].includes(role.toLowerCase())
                                    ? "text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                                    : "text-gray-700 cursor-not-allowed";
                                }
                                return "text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10";
                              })()
                            }`}
                            title={isDesktop ? "Mở CloakBrowser" : "Khởi chạy"}
                          >
                            <Play className="h-3.5 w-3.5" />
                          </button>
                        )}

                        {/* View (only when running & viewer available) */}
                        {(!isDesktop || profile.vnc_ws_port) && (
                          <button
                            id={`btn-view-${profile.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              onView(profile.id);
                            }}
                            disabled={profile.status !== "running"}
                            className={`p-1 rounded transition-colors ${
                              profile.status === "running"
                                ? "text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                                : "text-gray-700 cursor-not-allowed"
                            }`}
                            title="Xem (VNC)"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                        )}

                        {/* Edit */}
                        <button
                          id={`btn-edit-${profile.id}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onEdit(profile.id);
                          }}
                          className="p-1 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded transition-colors"
                          title="Sửa"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>

                        {/* Export Profile */}
                        {!isStaff && (
                          <button
                            id={`btn-export-${profile.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              onExportClick(profile.id);
                            }}
                            className="p-1 text-accent hover:text-accent-hover hover:bg-accent/10 rounded transition-colors"
                            title="Export Profile"
                          >
                            <Download className="h-3.5 w-3.5" />
                          </button>
                        )}

                        {/* Advanced Cookie Tools */}
                        {role === "super_admin" && (
                          <button
                            id={`btn-cookie-${profile.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              alert("Advanced Cookie Tools are currently under development.");
                            }}
                            className="p-1 text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded transition-colors"
                            title="Advanced Cookie Tools (Super Admin)"
                          >
                            <Cookie className="h-3.5 w-3.5" />
                          </button>
                        )}

                        {/* Logs */}
                        <button
                          id={`btn-logs-${profile.id}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onLogs(profile.id);
                          }}
                          className="p-1 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded transition-colors"
                          title="Nhật ký"
                        >
                          <ScrollText className="h-3.5 w-3.5" />
                        </button>

                        {/* Delete */}
                        {onDelete && (
                          <button
                            id={`btn-delete-${profile.id}`}
                            onClick={async (e) => {
                              e.stopPropagation();
                              if (window.confirm(`Bạn có chắc chắn muốn xóa profile "${profile.name}" không?`)) {
                                await onDelete(profile.id);
                              }
                            }}
                            className="p-1 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                            title="Xóa"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Controls */}
      {filtered.length > 0 && (
        <div className="px-4 py-2 border-t border-border flex items-center justify-between text-xs text-gray-400 bg-surface-1 select-none flex-shrink-0">
          <div className="flex items-center gap-2">
            <span>Hiển thị</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-surface-2 border border-border rounded px-1.5 py-0.5 text-xs text-gray-200 focus:outline-none focus:border-accent"
            >
              {[5, 10, 20, 50].map((size) => (
                <option key={size} value={size}>
                  {size} dòng
                </option>
              ))}
            </select>
            <span>/ {filtered.length} dòng</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2 py-0.5 rounded bg-surface-2 border border-border hover:bg-surface-3 disabled:opacity-40 disabled:hover:bg-surface-2 transition-colors text-[10px]"
            >
              Trước
            </button>
            <span className="px-2 py-0.5 font-medium text-gray-200 text-[10px]">
              Trang {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2 py-0.5 rounded bg-surface-2 border border-border hover:bg-surface-3 disabled:opacity-40 disabled:hover:bg-surface-2 transition-colors text-[10px]"
            >
              Sau
            </button>
          </div>
        </div>
      )}

      {/* New profile and Import buttons */}
      <div className="p-3 border-t border-border flex-shrink-0 flex gap-2">
        <button
          id="btn-new-profile"
          onClick={onNew}
          className="btn-secondary flex-1 flex items-center justify-center gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Thêm Profile</span>
        </button>
        {!isStaff && (
          <button
            id="btn-import-profile"
            onClick={onImportClick}
            className="btn-secondary flex-1 flex items-center justify-center gap-1.5 border-dashed border-accent/40 text-accent hover:text-accent-hover hover:border-accent"
            title="Import Profile package"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Import Package</span>
          </button>
        )}
      </div>

      {/* Report Modal */}
      {reportProfile && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-1 border border-border rounded-xl shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-4 border-b border-border bg-surface-0 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-rose-400 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
                Báo cáo giám sát thời gian thực (Runtime Guardian)
              </h3>
              <button
                onClick={() => {
                  setReportProfile(null);
                  setReportData(null);
                }}
                className="text-gray-500 hover:text-gray-300 transition-colors text-xs"
              >
                ✕ Đóng
              </button>
            </div>

            {/* Content */}
            <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto text-xs">
              {loadingReport && (
                <div className="flex flex-col items-center justify-center py-10 gap-3">
                  <Loader2 className="h-8 w-8 animate-spin text-accent" />
                  <span className="text-gray-400">Đang tải báo cáo giám sát mới nhất...</span>
                </div>
              )}

              {!loadingReport && reportData && (
                <>
                  {/* Summary Box */}
                  <div className="bg-surface-2 p-3 rounded-lg border border-border space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Tên Profile:</span>
                      <span className="text-gray-200 font-semibold">{reportProfile.name}</span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Mức độ an toàn (Score):</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full ${
                              reportData.score >= 90
                                ? "bg-emerald-500"
                                : reportData.score >= 70
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                            }`}
                            style={{ width: `${reportData.score}%` }}
                          />
                        </div>
                        <span
                          className={`font-bold ${
                            reportData.score >= 90
                              ? "text-emerald-400"
                              : reportData.score >= 70
                                ? "text-amber-400"
                                : "text-rose-400"
                          }`}
                        >
                          {reportData.score}/100
                        </span>
                      </div>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Trạng thái tổng quan:</span>
                      {(() => {
                        const statusInfo = ((status: string) => {
                          switch (status) {
                            case "healthy":
                              return { label: "AN TOÀN", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" };
                            case "warning":
                              return { label: "CẢNH BÁO", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" };
                            case "critical":
                              return { label: "NGUY HIỂM", color: "text-rose-400 bg-rose-500/10 border-rose-500/20 font-bold" };
                            case "stopped_by_guardian":
                              return { label: "ĐÃ DỪNG BỞI GUARDIAN", color: "text-rose-500 bg-rose-600/10 border-rose-600/20 font-extrabold animate-pulse" };
                            case "idle":
                              return { label: "CHỜ GIÁM SÁT", color: "text-gray-400 bg-gray-500/10 border-gray-500/20" };
                            default:
                              return { label: status.toUpperCase(), color: "text-gray-400 bg-gray-500/10 border-gray-500/20" };
                          }
                        })(reportData.status);

                        return (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${statusInfo.color}`}>
                            {statusInfo.label}
                          </span>
                        );
                      })()}
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Hành động can thiệp (Action):</span>
                      <span className="text-gray-300 font-medium">
                        {((act: string) => {
                          switch (act) {
                            case "stop_profile":
                              return "Dừng Profile lập tức và lưu Session";
                            case "warn_only":
                              return "Chỉ hiển thị Cảnh báo";
                            case "none":
                              return "Không can thiệp";
                            default:
                              return act;
                          }
                        })(reportData.action_taken)}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Thời gian kiểm tra:</span>
                      <span className="text-gray-400">
                        {reportData.checked_at ? new Date(reportData.checked_at).toLocaleString("vi-VN") : "N/A"}
                      </span>
                    </div>
                  </div>

                  {/* Components Checks List */}
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Trạng thái các thành phần kiểm tra</span>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(reportData.checks || {}).map(([key, value]) => {
                        const checkLabel = ((k) => {
                          switch (k) {
                            case "proxy": return "Kết nối Proxy & IP";
                            case "fingerprint": return "Cấu hình phần cứng";
                            case "headers": return "Tiêu đề & Ngôn ngữ";
                            case "session": return "Toàn vẹn Session";
                            default: return k;
                          }
                        })(key);

                        const valColor = ((v) => {
                          switch (v) {
                            case "pass": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
                            case "warning": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
                            case "failed": return "text-rose-400 bg-rose-500/10 border-rose-500/20";
                            default: return "text-gray-400 bg-gray-500/10";
                          }
                        })(value as string);

                        return (
                          <div key={key} className="p-2 border border-border/50 bg-surface-2 rounded-lg flex justify-between items-center">
                            <span className="text-gray-400 capitalize">{checkLabel}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${valColor}`}>
                              {value === "pass" ? "ĐẠT" : value === "warning" ? "CẢNH BÁO" : "LỖI"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Blocking Issues */}
                  {reportData.blocking_issues.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] uppercase font-bold text-rose-400 tracking-wider">Lỗi Nghiêm Trọng Bị Khóa</span>
                      <div className="p-3 bg-rose-950/20 border border-rose-500/20 rounded-lg space-y-1.5">
                        {reportData.blocking_issues.map((issue: string) => (
                          <div key={issue} className="flex gap-2 text-rose-300">
                            <span className="font-mono px-1 rounded bg-rose-500/20 h-fit text-[8px]">{issue}</span>
                            <span className="leading-relaxed font-medium">
                              {((iss) => {
                                switch (iss) {
                                  case "PROXY_EXIT_IP_CHANGED": return "Địa chỉ IP proxy thoát bị thay đổi bất thường ngoài chính sách.";
                                  case "PROXY_CONNECTION_FAILED": return "Kết nối tới Proxy thất bại hoàn toàn. Không thể truy cập.";
                                  case "PROXY_TIMEOUT": return "Thời gian kết nối tới Proxy quá hạn (Timeout).";
                                  case "PROXY_AUTH_FAILED": return "Xác thực tài khoản/mật khẩu Proxy thất bại.";
                                  case "PROXY_COUNTRY_MISMATCH": return "Quốc gia của IP proxy hiện tại không khớp cấu hình mong đợi.";
                                  case "PROXY_ASN_MISMATCH": return "Nhà mạng (ASN) của IP proxy hiện tại không khớp cấu hình mong đợi.";
                                  case "FINGERPRINT_UA_MISMATCH": return "User-Agent trình duyệt thực tế không khớp với cấu hình Fingerprint đã khóa.";
                                  case "HEADERS_MISMATCH_CRITICAL": return "Cấu hình tiêu đề (Headers/Platform/Screen) trình duyệt thực tế không khớp nghiêm trọng.";
                                  case "SESSION_DATA_CORRUPTED": return "Cơ sở dữ liệu Cookies hoặc thư mục phiên làm việc của Profile bị lỗi/hỏng.";
                                  default: return iss;
                                }
                              })(issue)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Warnings */}
                  {reportData.warnings.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider">Cảnh Báo Phát Hiện</span>
                      <div className="p-3 bg-amber-950/20 border border-amber-500/20 rounded-lg space-y-1.5">
                        {reportData.warnings.map((warn: string) => (
                          <div key={warn} className="flex gap-2 text-amber-300">
                            <span className="font-mono px-1 rounded bg-amber-500/20 h-fit text-[8px]">{warn}</span>
                            <span className="leading-relaxed font-medium">
                              {((w) => {
                                switch (w) {
                                  case "PROXY_IP_ROTATED": return "IP proxy đã xoay địa chỉ tự động trong cùng mạng/quốc gia cho phép.";
                                  case "PROXY_LATENCY_HIGH": return "Độ trễ Proxy cực kỳ cao (>1500ms), kết nối mạng bị chậm.";
                                  case "HEADERS_MISMATCH": return "Cấu hình ngôn ngữ hoặc tiêu đề gửi đi không đồng nhất.";
                                  case "TLS_CHECK_UNAVAILABLE": return "Dịch vụ xác thực TLS (peet.ws) tạm thời không phản hồi.";
                                  default: return w;
                                }
                              })(warn)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendations */}
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Đề xuất xử lý</span>
                    <ul className="list-disc pl-4 space-y-1 text-gray-400 leading-relaxed">
                      <li>Kiểm tra tính ổn định của đường truyền mạng và nhà cung cấp proxy.</li>
                      <li>Đảm bảo các cấu hình thiết bị (User-Agent, GPU Renderer, Timezone) không bị chỉnh sửa thủ công từ bên ngoài.</li>
                      <li>Nếu profile chưa được xác thực (Unverified hoặc Expired), vui lòng chạy quy trình Verify Profile để cập nhật lại cấu hình an toàn trước khi mở lại.</li>
                    </ul>
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border bg-surface-0 flex justify-end gap-2">
              <button
                onClick={() => {
                  setReportProfile(null);
                  setReportData(null);
                }}
                className="px-4 py-1.5 rounded-lg bg-surface-3 hover:bg-surface-4 text-gray-300 transition-all font-semibold"
              >
                Đóng Báo Cáo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
