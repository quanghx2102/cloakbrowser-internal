import React, { useState, useEffect } from "react";
import { FolderOpen, CheckCircle, AlertTriangle, XCircle, HelpCircle, Save } from "lucide-react";
import { api } from "../lib/api";

declare global {
  interface Window {
    electron?: {
      isDesktop: boolean;
      platform: string;
      version: string;
      getBinaryStatus: () => Promise<{ path: string | null; status: "Ready" | "Missing" | "Invalid"; errorCode?: string }>;
      selectBinary: () => Promise<{ success: boolean; canceled?: boolean; path?: string; error?: string }>;
      saveBinaryPath: (path: string) => Promise<{ success: boolean; error?: string }>;
    };
  }
}

interface SettingsTabProps {
  showToast: (message: string, type: "success" | "error") => void;
}

export function SettingsTab({ showToast }: SettingsTabProps) {
  const [binaryPath, setBinaryPath] = useState<string>("");
  const [status, setStatus] = useState<"Ready" | "Missing" | "Invalid">("Missing");
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [isDesktop, setIsDesktop] = useState<boolean>(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      if (window.electron && typeof window.electron.getBinaryStatus === "function") {
        setIsDesktop(true);
        const result = await window.electron.getBinaryStatus();
        setBinaryPath(result.path || "");
        setStatus(result.status);
      } else {
        // Fallback to HTTP API
        const result = await api.getBinaryStatus();
        setBinaryPath(result.path || "");
        setStatus(result.status);
        setIsDesktop(!!result.is_desktop);
      }
    } catch (err) {
      console.error("Failed to load binary status:", err);
      showToast("Không thể tải trạng thái CloakBrowser Binary", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleSelectBinary = async () => {
    if (window.electron && typeof window.electron.selectBinary === "function") {
      try {
        const res = await window.electron.selectBinary();
        if (res.success && res.path) {
          setBinaryPath(res.path);
          showToast("Cập nhật đường dẫn thành công", "success");
          fetchStatus();
        } else if (res.error) {
          showToast(res.error, "error");
        }
      } catch (err) {
        showToast("Lỗi khi mở hộp thoại chọn file", "error");
      }
    } else {
      showToast("Vui lòng nhập trực tiếp đường dẫn trên giao diện web", "error");
    }
  };

  const handleSaveBinary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!binaryPath.trim()) {
      showToast("Vui lòng nhập đường dẫn", "error");
      return;
    }

    setSaving(true);
    try {
      if (window.electron && typeof window.electron.saveBinaryPath === "function") {
        const res = await window.electron.saveBinaryPath(binaryPath.trim());
        if (res.success) {
          showToast("Lưu cấu hình thành công", "success");
          fetchStatus();
        } else {
          showToast(res.error || "Lưu cấu hình thất bại", "error");
        }
      } else {
        const res = await api.updateBinaryStatus(binaryPath.trim());
        if (res.ok) {
          showToast("Lưu cấu hình thành công", "success");
          fetchStatus();
        } else {
          showToast("Lưu cấu hình thất bại", "error");
        }
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Lưu cấu hình thất bại", "error");
    } finally {
      setSaving(false);
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case "Ready":
        return (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.05)]">
            <CheckCircle className="h-5 w-5 text-emerald-400 animate-pulse" />
            <div>
              <p className="font-semibold text-sm">Ready (Sẵn sàng)</p>
              <p className="text-xs text-emerald-500/70">CloakBrowser binary đã được cấu hình và sẵn sàng hoạt động.</p>
            </div>
          </div>
        );
      case "Invalid":
        return (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.05)]">
            <XCircle className="h-5 w-5 text-red-400" />
            <div>
              <p className="font-semibold text-sm">Invalid (Không hợp lệ)</p>
              <p className="text-xs text-red-500/70">File không tồn tại hoặc thiếu quyền thực thi (executable permission).</p>
            </div>
          </div>
        );
      case "Missing":
      default:
        return (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.05)]">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <div>
              <p className="font-semibold text-sm">Missing (Chưa cấu hình)</p>
              <p className="text-xs text-amber-500/70">Không tìm thấy CloakBrowser. Trình duyệt sẽ không thể khởi chạy.</p>
            </div>
          </div>
        );
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-gray-500 text-sm">Đang tải trạng thái cấu hình...</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto flex flex-col gap-8 overflow-y-auto h-full">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
          <span>⚙️</span> Cấu hình Hệ thống
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Quản lý đường dẫn, cấu hình CloakBrowser và các thiết lập hệ thống khác.
        </p>
      </div>

      {/* Main Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left column: path settings */}
        <div className="md:col-span-2 flex flex-col gap-6">
          {/* Binary Path card */}
          <div className="bg-surface-1 border border-border rounded-2xl p-6 flex flex-col gap-6 shadow-sm">
            <h2 className="text-base font-semibold text-gray-200">
              Đường dẫn CloakBrowser Binary
            </h2>

            {/* Status indicator */}
            {getStatusBadge()}

            {/* Form */}
            <form onSubmit={handleSaveBinary} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-xs text-gray-400 font-medium">Đường dẫn file thực thi</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={binaryPath}
                    onChange={(e) => setBinaryPath(e.target.value)}
                    placeholder="/Users/quang/.cloakbrowser/chromium-xxx/Chromium.app/Contents/MacOS/Chromium"
                    className="flex-1 px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm text-gray-200 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 placeholder-gray-600 transition-all font-mono"
                  />
                  {isDesktop && (
                    <button
                      type="button"
                      onClick={handleSelectBinary}
                      className="px-4 py-2.5 bg-surface-3 hover:bg-surface-4 border border-border text-gray-300 rounded-xl hover:text-white transition-colors flex items-center gap-1.5 text-sm"
                      title="Chọn tệp từ máy tính"
                    >
                      <FolderOpen className="h-4 w-4" />
                      <span>Chọn file</span>
                    </button>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-2">
                <button
                  type="button"
                  onClick={fetchStatus}
                  className="px-4 py-2 bg-transparent hover:bg-surface-2 text-gray-400 hover:text-gray-200 rounded-xl text-sm font-medium transition-colors"
                >
                  Làm mới
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm font-medium transition-all shadow-[0_4px_12px_rgba(59,130,246,0.2)] flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  <span>{saving ? "Đang lưu..." : "Lưu thay đổi"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right column: help & guidelines */}
        <div className="flex flex-col gap-6">
          <div className="bg-surface-1 border border-border rounded-2xl p-5 flex flex-col gap-4 shadow-sm">
            <h3 className="text-sm font-bold text-gray-200 flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-accent" />
              <span>Hướng dẫn Cài đặt</span>
            </h3>

            <div className="flex flex-col gap-3 text-xs leading-relaxed text-gray-400">
              <p>
                CloakBrowser là phiên bản Chromium tùy chỉnh nâng cao phục vụ cho việc giả lập vân tay trình duyệt. Bạn cần tải và chỉ định đúng đường dẫn tệp thực thi.
              </p>
              
              <div className="border-t border-border/60 my-1"></div>

              <p className="font-semibold text-gray-300">Thứ tự ưu tiên phân giải:</p>
              <ol className="list-decimal pl-4 flex flex-col gap-1">
                <li>Biến môi trường <code className="bg-surface-2 px-1 py-0.5 rounded text-accent font-mono">CLOAK_BROWSER_BINARY_PATH</code></li>
                <li>Đường dẫn đã cấu hình trong <code className="bg-surface-2 px-1 py-0.5 rounded text-accent font-mono">app-config.json</code></li>
                <li>Tự động quét trên macOS (<code className="bg-surface-2 px-1 py-0.5 rounded font-mono">~/.cloakbrowser/chromium-*</code>)</li>
                <li>Binary đóng gói kèm ứng dụng (Resources)</li>
              </ol>

              <div className="border-t border-border/60 my-1"></div>

              <p className="font-semibold text-gray-300">Đường dẫn mặc định trên macOS:</p>
              <p className="bg-surface-2 p-2 rounded text-[10px] font-mono select-all overflow-x-auto text-gray-300 border border-border/40">
                ~/.cloakbrowser/chromium-xxx/Chromium.app/Contents/MacOS/Chromium
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
