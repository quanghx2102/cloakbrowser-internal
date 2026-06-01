import { Save, Trash2, Eye, EyeOff, Activity, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import type { Proxy, ProxyCreateData } from "../lib/api";

interface ProxyFormProps {
  proxy: Proxy | null;
  onSave: (data: ProxyCreateData) => Promise<void>;
  onDelete?: () => Promise<void>;
  onCheck?: () => Promise<void>;
  onCancel: () => void;
}

export function ProxyForm({ proxy, onSave, onDelete, onCheck, onCancel }: ProxyFormProps) {
  const isEdit = proxy !== null;

  const [form, setForm] = useState<ProxyCreateData>({
    name: "",
    type: "http",
    host: "",
    port: 8080,
    username: "",
    password: "",
    status: "active",
  });

  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (proxy) {
      setForm({
        name: proxy.name,
        type: proxy.type,
        host: proxy.host,
        port: proxy.port,
        username: proxy.username || "",
        password: proxy.password || "",
        status: proxy.status,
      });
    }
  }, [proxy?.id]);

  const set = <K extends keyof ProxyCreateData>(key: K, value: ProxyCreateData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.host.trim() || !form.port) return;
    setSaving(true);
    try {
      await onSave({
        ...form,
        username: form.username?.trim() || null,
        password: form.password?.trim() || null,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    if (!confirm("Xóa proxy này? Các profile đang sử dụng nó sẽ không thể kết nối Internet nếu bắt buộc có proxy.")) return;
    setDeleting(true);
    try {
      await onDelete();
    } finally {
      setDeleting(false);
    }
  };

  const handleCheck = async () => {
    if (!onCheck) return;
    setChecking(true);
    try {
      await onCheck();
    } finally {
      setChecking(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-6 max-w-xl mx-auto w-full h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">
            {isEdit ? "Chỉnh sửa Proxy" : "Thêm Proxy"}
          </h2>
          {isEdit && onCheck && (
            <button
              type="button"
              onClick={handleCheck}
              disabled={checking}
              className="btn-secondary flex items-center gap-1.5"
            >
              {checking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Activity className="h-3.5 w-3.5" />}
              <span>{checking ? "Đang kiểm tra..." : "Kiểm tra"}</span>
            </button>
          )}
          {isEdit && onDelete && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="btn-danger flex items-center gap-1.5"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{deleting ? "Đang xóa..." : "Xóa"}</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onCancel} className="btn-secondary">
            Hủy
          </button>
          <button type="submit" disabled={saving} className="btn-primary flex items-center gap-1.5">
            <Save className="h-3.5 w-3.5" />
            <span>{saving ? "Đang lưu..." : isEdit ? "Lưu" : "Thêm mới"}</span>
          </button>
        </div>
      </div>

      <div className="space-y-5">
        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Thông tin cơ bản</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="label">Tên Proxy</label>
              <input
                className="input"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Ví dụ: US Residential #1"
                required
              />
            </div>
            <div>
              <label className="label">Giao thức</label>
              <select
                className="input"
                value={form.type}
                onChange={(e) => set("type", e.target.value as "http" | "socks5")}
              >
                <option value="http">HTTP/HTTPS</option>
                <option value="socks5">SOCKS5</option>
              </select>
            </div>
            <div>
              <label className="label">Trạng thái</label>
              <select
                className="input"
                value={form.status}
                onChange={(e) => set("status", e.target.value as "active" | "inactive")}
              >
                <option value="active">Hoạt động</option>
                <option value="inactive">Không hoạt động</option>
              </select>
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Kết nối</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="label">Địa chỉ IP / Host</label>
              <input
                className="input"
                value={form.host}
                onChange={(e) => set("host", e.target.value)}
                placeholder="Ví dụ: proxy.example.com hoặc 192.168.1.1"
                required
              />
            </div>
            <div>
              <label className="label">Cổng (Port)</label>
              <input
                className="input"
                type="number"
                min={1}
                max={65535}
                value={form.port || ""}
                onChange={(e) => set("port", Number(e.target.value))}
                placeholder="8080"
                required
              />
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Xác thực (Tùy chọn)</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Tài khoản (Username)</label>
              <input
                className="input"
                value={form.username || ""}
                onChange={(e) => set("username", e.target.value)}
                placeholder="Ví dụ: user123"
              />
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  className="input pr-10"
                  type={showPassword ? "text" : "password"}
                  value={form.password || ""}
                  onChange={(e) => set("password", e.target.value)}
                  placeholder="***"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        </section>

        {isEdit && proxy && proxy.last_checked_at && (
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Lần kiểm tra cuối</h3>
            <div className="p-3 bg-surface-2 rounded-lg text-sm grid grid-cols-2 gap-2">
              <div className="text-gray-500">Độ trễ (Latency): <span className="text-gray-200">{proxy.latency_ms !== null ? `${proxy.latency_ms}ms` : "—"}</span></div>
              <div className="text-gray-500">IP đầu ra: <span className="text-gray-200">{proxy.last_ip || "—"}</span></div>
              <div className="text-gray-500">Múi giờ (Timezone): <span className="text-gray-200">{proxy.timezone || "—"}</span></div>
              <div className="text-gray-500">Ngôn ngữ (Locale): <span className="text-gray-200">{proxy.locale || "—"}</span></div>
              <div className="text-gray-500 col-span-2">Thời gian kiểm tra: <span className="text-gray-200">{new Date(proxy.last_checked_at).toLocaleString()}</span></div>
            </div>
          </section>
        )}
      </div>
    </form>
  );
}
