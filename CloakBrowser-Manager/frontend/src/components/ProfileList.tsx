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
} from "lucide-react";
import { useState } from "react";
import type { Profile } from "../lib/api";
import { StatusIndicator } from "./StatusIndicator";

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
  isDesktop,
}: ProfileListProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const filtered = profiles.filter((p) => {
    const matchName = p.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    return matchName && matchStatus;
  });

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
            onChange={(e) => setSearch(e.target.value)}
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
              onClick={() => setStatusFilter(s)}
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
              {filtered.map((profile) => {
                const isSelected = selectedId === profile.id;
                const isLoading = loadingId === profile.id;
                const effectiveStatus = isLoading
                  ? "launching"
                  : profile.status;

                return (
                  <tr
                    key={profile.id}
                    id={`profile-row-${profile.id}`}
                    onClick={() => onSelect(profile.id)}
                    className={`border-b border-border/50 cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-accent/10 border-l-2 border-l-accent"
                        : "hover:bg-surface-2 border-l-2 border-l-transparent"
                    }`}
                  >
                    {/* Name */}
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2 min-w-0">
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
                            className="p-1 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 rounded transition-colors"
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
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* New profile button */}
      <div className="p-3 border-t border-border flex-shrink-0">
        <button
          id="btn-new-profile"
          onClick={onNew}
          className="btn-secondary w-full flex items-center justify-center gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Thêm Profile</span>
        </button>
      </div>
    </div>
  );
}
