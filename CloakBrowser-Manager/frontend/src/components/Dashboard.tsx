import { Activity, AlertCircle, Box, Loader2, PowerOff, ShieldAlert } from "lucide-react";
import { useDashboard } from "../hooks/useDashboard";
import { formatDistanceToNow } from "date-fns";
import { vi } from "date-fns/locale";

export function Dashboard() {
  const { summary, loading, error, stopAll } = useDashboard();

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="flex items-center justify-center h-full text-red-400 gap-2">
        <AlertCircle className="h-5 w-5" />
        <span>{error}</span>
      </div>
    );
  }

  const handleStopAll = async () => {
    if (window.confirm("Bạn có chắc chắn muốn dừng tất cả profile đang chạy? Hành động này sẽ đóng ngay lập tức tất cả phiên trình duyệt đang hoạt động mà không lưu các tab.")) {
      try {
        const res = await stopAll();
        if (res) {
          alert(`Đã dừng các profile thành công!\nTóm tắt:\n- Tổng số tìm thấy: ${res.total}\n- Đã dừng thành công: ${res.stopped}\n- Thất bại: ${res.failed}`);
        }
      } catch (err) {
        alert("Dừng các profile thất bại: " + (err instanceof Error ? err.message : String(err)));
      }
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">Tổng quan hệ thống và chỉ số vận hành.</p>
        </div>
        <button
          onClick={handleStopAll}
          className="btn-danger flex items-center gap-2"
          disabled={!summary || summary.running_profiles === 0}
        >
          <PowerOff className="h-4 w-4" />
          <span>Dừng tất cả Profile</span>
        </button>
      </div>

      {summary && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Profiles Card */}
            <div className="bg-surface-2 p-4 rounded-xl border border-border">
              <div className="flex items-center gap-3 mb-3 text-gray-400">
                <Box className="h-5 w-5" />
                <h3 className="font-semibold text-gray-200">Profiles</h3>
              </div>
              <div className="text-3xl font-bold text-gray-100 mb-2">{summary.total_profiles}</div>
              <div className="flex flex-col gap-1 text-xs text-gray-500">
                <div className="flex justify-between">
                  <span>Đang chạy / Tối đa cho phép:</span>
                  <span className="text-emerald-400 font-medium">
                    {summary.running_profiles} / {summary.max_running_profiles > 0 ? summary.max_running_profiles : "∞"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Lỗi/Bị sập:</span>
                  <span className={summary.failed_profiles > 0 ? "text-red-400 font-medium" : ""}>
                    {summary.failed_profiles}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Đã dừng:</span>
                  <span>{summary.stopped_profiles}</span>
                </div>
              </div>
            </div>

            {/* Proxies Card */}
            <div className="bg-surface-2 p-4 rounded-xl border border-border">
              <div className="flex items-center gap-3 mb-3 text-gray-400">
                <Activity className="h-5 w-5" />
                <h3 className="font-semibold text-gray-200">Proxies</h3>
              </div>
              <div className="text-3xl font-bold text-gray-100 mb-2">{summary.total_proxies}</div>
              <div className="flex flex-col gap-1 text-xs text-gray-500">
                <div className="flex justify-between">
                  <span>Hoạt động tốt:</span>
                  <span className="text-emerald-400 font-medium">{summary.ok_proxies}</span>
                </div>
                <div className="flex justify-between">
                  <span>Lỗi kết nối:</span>
                  <span className={summary.failed_proxies > 0 ? "text-red-400 font-medium" : ""}>
                    {summary.failed_proxies}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-surface-2 rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border flex items-center gap-3">
              <ShieldAlert className="h-5 w-5 text-red-400" />
              <h3 className="font-semibold text-gray-200">Các lỗi gần đây</h3>
            </div>
            {summary.recent_errors.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">
                Không tìm thấy lỗi nào gần đây. Hệ thống đang hoạt động tốt.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-surface-3 text-gray-400 text-xs uppercase">
                    <tr>
                      <th className="px-4 py-3 font-medium">Thời gian</th>
                      <th className="px-4 py-3 font-medium">Module / Hành động</th>
                      <th className="px-4 py-3 font-medium">Mã lỗi</th>
                      <th className="px-4 py-3 font-medium">Nội dung lỗi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {summary.recent_errors.map((err) => (
                      <tr key={err.id} className="hover:bg-surface-3/50 transition-colors">
                        <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                          {formatDistanceToNow(new Date(err.timestamp), { addSuffix: true, locale: vi })}
                        </td>
                        <td className="px-4 py-3 text-gray-300 whitespace-nowrap">
                          <span className="bg-surface-4 px-2 py-0.5 rounded text-xs">{err.module}</span>
                          <span className="mx-2 text-gray-500">/</span>
                          <span className="text-gray-400 text-xs">{err.action}</span>
                        </td>
                        <td className="px-4 py-3 text-red-400 font-mono text-xs whitespace-nowrap">
                          {err.error_code || "UNKNOWN"}
                        </td>
                        <td className="px-4 py-3 text-gray-400 text-xs truncate max-w-md" title={err.message || ""}>
                          {err.message}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
