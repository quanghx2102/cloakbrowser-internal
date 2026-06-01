import { useState, useEffect } from "react";
import { X, ShieldAlert, FileKey, Download, Upload, Loader2, AlertCircle } from "lucide-react";
import { api, type Profile } from "../lib/api";

interface ProfilePackageModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: "import" | "export";
  profileId?: string | null;
  profiles: Profile[];
  onSuccess: (message: string, type: "success" | "error") => void;
}

export function ProfilePackageModal({
  isOpen,
  onClose,
  type,
  profileId,
  profiles,
  onSuccess,
}: ProfilePackageModalProps) {
  const [passphrase, setPassphrase] = useState("");
  const [includeProxySecret, setIncludeProxySecret] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [importMode, setImportMode] = useState<"new_profile" | "overwrite">("new_profile");
  const [targetProfileId, setTargetProfileId] = useState("");
  const [warningConfirmed, setWarningConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);

  // Reset states on type/isOpen change
  useEffect(() => {
    if (isOpen) {
      setPassphrase("");
      setIncludeProxySecret(false);
      setFile(null);
      setImportMode("new_profile");
      setTargetProfileId("");
      setWarningConfirmed(false);
    }
  }, [isOpen, type]);

  if (!isOpen) return null;

  const currentProfile = profiles.find((p) => p.id === (profileId || targetProfileId));
  const isTargetRunning = currentProfile?.status === "running";

  const handleExport = async () => {
    if (!profileId) return;
    if (!warningConfirmed) {
      onSuccess("Vui lòng xác nhận cảnh báo trước khi export.", "error");
      return;
    }
    setLoading(true);
    try {
      const res = await api.exportPackage(profileId, passphrase, includeProxySecret);
      if (res instanceof Blob) {
        // Web mode: download file directly
        const url = window.URL.createObjectURL(res);
        const a = document.createElement("a");
        a.href = url;
        a.download = `profile_${profileId}.cbprofile`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        onSuccess("Profile package exported", "success");
      } else {
        // Desktop mode: return local path
        onSuccess(`Profile package exported: ${res.export_path}`, "success");
      }
      onClose();
    } catch (err: any) {
      onSuccess(err.message || "Export package thất bại", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!file) {
      onSuccess("Vui lòng chọn file .cbprofile", "error");
      return;
    }
    if (importMode === "overwrite" && !targetProfileId) {
      onSuccess("Vui lòng chọn profile cần ghi đè", "error");
      return;
    }
    if (importMode === "overwrite" && isTargetRunning) {
      onSuccess("Không thể ghi đè profile đang chạy", "error");
      return;
    }
    if (!warningConfirmed) {
      onSuccess("Vui lòng xác nhận cảnh báo trước khi import.", "error");
      return;
    }

    setLoading(true);
    try {
      await api.importPackage(file, passphrase, importMode, targetProfileId || null);
      onSuccess("Profile package imported", "success");
      onClose();
    } catch (err: any) {
      const errorMsg = err.message || "";
      if (errorMsg.includes("checksum") || errorMsg.includes("checksum_failed") || errorMsg.includes("PROFILE_PACKAGE_CHECKSUM_FAILED")) {
        onSuccess("Import failed: checksum error", "error");
      } else if (errorMsg.includes("decrypt") || errorMsg.includes("decrypt_failed") || errorMsg.includes("PROFILE_PACKAGE_DECRYPT_FAILED") || errorMsg.includes("passphrase")) {
        onSuccess("Import failed: wrong passphrase", "error");
      } else {
        onSuccess(`Import failed: ${errorMsg}`, "error");
      }
    } finally {
      setLoading(false);
    }
  };

  // Overwrite options should exclude active profiles, or we visually disable/warn them
  const overwriteableProfiles = profiles.filter((p) => p.status !== "running");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div 
        className="w-full max-w-md bg-surface-1 border border-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-2/40">
          <div className="flex items-center gap-2">
            {type === "export" ? (
              <Download className="h-5 w-5 text-accent animate-pulse" />
            ) : (
              <Upload className="h-5 w-5 text-accent animate-pulse" />
            )}
            <h3 className="font-semibold text-gray-100 text-sm">
              {type === "export" ? "Export Profile Package" : "Import Profile Package"}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-surface-3 text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          {type === "export" ? (
            <>
              {/* Profile Details */}
              <div className="p-3 bg-surface-3/30 border border-border/50 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Profile xuất bản</span>
                <span className="text-gray-200 font-medium text-sm">
                  {profiles.find((p) => p.id === profileId)?.name || "Chưa chọn"}
                </span>
              </div>

              {/* Passphrase */}
              <div>
                <label className="label flex items-center gap-1.5">
                  <FileKey className="h-3.5 w-3.5 text-gray-400" />
                  <span>Passphrase bảo mật (Tùy chọn)</span>
                </label>
                <input
                  type="password"
                  placeholder="Nhập mật khẩu mã hóa gói package..."
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  className="input"
                />
                <span className="text-[10px] text-gray-500 block mt-1">
                  Nếu nhập, package sẽ được mã hóa an toàn bằng thuật toán AES.
                </span>
              </div>

              {/* Include Proxy Secrets */}
              <div className="flex items-center justify-between p-3 bg-surface-2/30 rounded-lg border border-border/40">
                <div>
                  <span className="font-medium text-gray-200 block">Include Proxy Secret</span>
                  <span className="text-[10px] text-gray-500">Bao gồm mật khẩu proxy (nếu có) vào package.</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeProxySecret}
                    onChange={(e) => setIncludeProxySecret(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-300 after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent peer-checked:after:bg-white"></div>
                </label>
              </div>

              {/* Warning Confirmation */}
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg space-y-2">
                <div className="flex gap-2">
                  <ShieldAlert className="h-4 w-4 text-rose-400 flex-shrink-0" />
                  <p className="text-rose-300 font-medium leading-relaxed">
                    Package này có thể chứa session đăng nhập. Chỉ export khi bạn có quyền quản lý profile này.
                  </p>
                </div>
                <label className="flex items-center gap-2 text-rose-400 font-semibold cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={warningConfirmed}
                    onChange={(e) => setWarningConfirmed(e.target.checked)}
                    className="rounded border-rose-500/30 bg-rose-950/20 text-rose-500 focus:ring-rose-500 h-3.5 w-3.5"
                  />
                  <span>Tôi đã hiểu và chịu hoàn toàn trách nhiệm</span>
                </label>
              </div>
            </>
          ) : (
            <>
              {/* File Select */}
              <div>
                <label className="label">Chọn file package (.cbprofile)</label>
                <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-dashed border-border rounded-lg hover:border-accent/40 transition-colors cursor-pointer relative">
                  <div className="space-y-1 text-center">
                    <Upload className="mx-auto h-8 w-8 text-gray-500" />
                    <div className="text-gray-400">
                      <label className="relative cursor-pointer rounded-md font-semibold text-accent hover:text-accent-hover">
                        <span>Tải file lên</span>
                        <input
                          type="file"
                          accept=".cbprofile"
                          className="sr-only"
                          onChange={(e) => setFile(e.target.files?.[0] || null)}
                        />
                      </label>
                    </div>
                    <p className="text-[10px] text-gray-500">File định dạng .cbprofile</p>
                  </div>
                  {file && (
                    <div className="absolute inset-0 bg-surface-1 flex items-center justify-center p-3 rounded-lg border border-accent/40">
                      <div className="text-center">
                        <span className="font-semibold text-gray-200 block truncate max-w-[280px]">{file.name}</span>
                        <span className="text-[10px] text-gray-500">{(file.size / 1024).toFixed(1)} KB</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setFile(null);
                          }}
                          className="text-[10px] text-red-400 mt-2 hover:underline block mx-auto"
                        >
                          Thay đổi file
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Passphrase */}
              <div>
                <label className="label flex items-center gap-1.5">
                  <FileKey className="h-3.5 w-3.5 text-gray-400" />
                  <span>Passphrase giải mã</span>
                </label>
                <input
                  type="password"
                  placeholder="Nhập passphrase nếu package đã được mã hóa..."
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  className="input"
                />
              </div>

              {/* Mode Select */}
              <div className="space-y-2">
                <label className="label">Chế độ import</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setImportMode("new_profile")}
                    className={`p-2.5 rounded-lg border text-center font-medium transition-all ${
                      importMode === "new_profile"
                        ? "bg-accent/15 border-accent text-accent"
                        : "bg-surface-2 border-border text-gray-400 hover:bg-surface-3"
                    }`}
                  >
                    Tạo Profile Mới
                  </button>
                  <button
                    type="button"
                    onClick={() => setImportMode("overwrite")}
                    className={`p-2.5 rounded-lg border text-center font-medium transition-all ${
                      importMode === "overwrite"
                        ? "bg-accent/15 border-accent text-accent"
                        : "bg-surface-2 border-border text-gray-400 hover:bg-surface-3"
                    }`}
                  >
                    Ghi Đè Profile Cũ
                  </button>
                </div>
              </div>

              {/* Target Profile for Overwrite */}
              {importMode === "overwrite" && (
                <div className="space-y-1.5">
                  <label className="label">Chọn profile để ghi đè</label>
                  <select
                    className="input"
                    value={targetProfileId}
                    onChange={(e) => setTargetProfileId(e.target.value)}
                  >
                    <option value="">-- Chọn profile cần ghi đè --</option>
                    {overwriteableProfiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                  {isTargetRunning && (
                    <div className="flex items-center gap-1.5 text-rose-400 text-[10px] mt-1 font-medium">
                      <AlertCircle className="h-3.5 w-3.5" />
                      <span>Profile này đang hoạt động. Vui lòng dừng profile trước để ghi đè.</span>
                    </div>
                  )}
                </div>
              )}

              {/* Warning Confirmation */}
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg space-y-2">
                <p className="text-amber-300 leading-relaxed">
                  {importMode === "overwrite"
                    ? "Ghi đè profile sẽ thay thế TOÀN BỘ cookies, phiên đăng nhập, vân tay và dữ liệu cũ của profile đích. Dữ liệu cũ sẽ mất vĩnh viễn!"
                    : "Import profile mới sẽ thêm cấu hình và dữ liệu từ package này vào danh sách quản lý."}
                </p>
                <label className="flex items-center gap-2 text-amber-400 font-semibold cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={warningConfirmed}
                    onChange={(e) => setWarningConfirmed(e.target.checked)}
                    className="rounded border-amber-500/30 bg-amber-950/20 text-amber-500 focus:ring-amber-500 h-3.5 w-3.5"
                  />
                  <span>Tôi đồng ý tiếp tục</span>
                </label>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border bg-surface-2/20">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary"
            disabled={loading}
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={type === "export" ? handleExport : handleImport}
            className="btn-primary flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={loading || !warningConfirmed || (type === "import" && !file) || (type === "import" && importMode === "overwrite" && (!targetProfileId || isTargetRunning))}
          >
            {loading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Đang xử lý...</span>
              </>
            ) : (
              <>
                {type === "export" ? (
                  <>
                    <Download className="h-3.5 w-3.5" />
                    <span>Export .cbprofile</span>
                  </>
                ) : (
                  <>
                    <Upload className="h-3.5 w-3.5" />
                    <span>Import .cbprofile</span>
                  </>
                )}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
