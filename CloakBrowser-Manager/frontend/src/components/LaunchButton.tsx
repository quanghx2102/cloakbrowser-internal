import { Play, Square, Loader2 } from "lucide-react";
import { useState } from "react";

interface LaunchButtonProps {
  status: "running" | "stopped";
  onLaunch: () => Promise<void>;
  onStop: () => Promise<void>;
  isDesktop?: boolean;
}

export function LaunchButton({ status, onLaunch, onStop, isDesktop }: LaunchButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    try {
      if (status === "running") {
        await onStop();
      } else {
        await onLaunch();
      }
    } catch (err) {
      let msg = err instanceof Error ? err.message : "Thao tác thất bại";
      if (msg.includes("CLOAK_BROWSER_BINARY_NOT_CONFIGURED")) {
        msg = "Chưa cấu hình binary. Vui lòng cấu hình CLOAK_BROWSER_BINARY_PATH trong phần Cài đặt.";
      } else if (msg.includes("CLOAK_BROWSER_BINARY_NOT_FOUND") || msg.includes("CloakBrowser binary not found")) {
        msg = "Binary không tồn tại ở đường dẫn cấu hình.";
      } else if (msg.includes("CLOAK_BROWSER_BINARY_PERMISSION_DENIED")) {
        msg = "Binary không có quyền execute (Quyền thực thi bị từ chối).";
      } else if (msg.includes("BROWSER_NATIVE_START_FAILED") || msg.includes("BROWSER_START_FAILED") || msg.includes("Failed to launch")) {
        msg = "Launch failed. Không thể khởi chạy trình duyệt.";
      }
      setError(msg);
      console.error("Action failed:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <button disabled className="btn-secondary opacity-60 cursor-not-allowed flex items-center gap-1.5">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>{status === "running" ? (isDesktop ? "Đang đóng..." : "Đang dừng...") : (isDesktop ? "Đang mở..." : "Đang khởi chạy...")}</span>
      </button>
    );
  }

  if (status === "running") {
    return (
      <button onClick={handleClick} className="btn-danger flex items-center gap-1.5">
        <Square className="h-3.5 w-3.5" />
        <span>{isDesktop ? "Đóng" : "Dừng"}</span>
      </button>
    );
  }

  return (
    <div>
      <button onClick={handleClick} className="btn-primary flex items-center gap-1.5">
        <Play className="h-3.5 w-3.5" />
        <span>{isDesktop ? "Mở CloakBrowser" : "Khởi chạy"}</span>
      </button>
      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
    </div>
  );
}
