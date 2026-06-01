import { Plus, Search, Server, Pencil, Activity, Loader2 } from "lucide-react";
import { useState } from "react";
import type { Proxy } from "../lib/api";

interface ProxyListProps {
  proxies: Proxy[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onEdit: (id: string) => void;
  onCheck: (id: string) => Promise<void>;
}

export function ProxyList({
  proxies,
  selectedId,
  onSelect,
  onNew,
  onEdit,
  onCheck,
}: ProxyListProps) {
  const [search, setSearch] = useState("");
  const [checkingId, setCheckingId] = useState<string | null>(null);

  const filtered = proxies.filter((p) => {
    return (
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.host.toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-accent" />
            <h1 className="text-sm font-semibold tracking-tight">Proxy</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500">Tổng số: {proxies.length}</span>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
          <input
            type="text"
            placeholder="Tìm kiếm proxy..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-8 py-1.5 text-xs"
          />
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="text-center text-gray-500 text-xs py-10">
            {proxies.length === 0
              ? "Chưa có proxy nào. Hãy tạo một cái để bắt đầu."
              : "Không có proxy nào khớp với tìm kiếm."}
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-1 z-10">
              <tr className="border-b border-border">
                <th className="text-left px-3 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[35%]">
                  Tên proxy
                </th>
                <th className="text-left px-2 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[25%]">
                  Địa chỉ
                </th>
                <th className="text-left px-2 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[25%]">
                  Trạng thái
                </th>
                <th className="text-right px-3 py-2 text-[10px] font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((proxy) => {
                const isSelected = selectedId === proxy.id;

                return (
                  <tr
                    key={proxy.id}
                    onClick={() => onSelect(proxy.id)}
                    className={`border-b border-border/50 cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-accent/10 border-l-2 border-l-accent"
                        : "hover:bg-surface-2 border-l-2 border-l-transparent"
                    }`}
                  >
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-gray-100 truncate max-w-[150px]" title={proxy.name}>
                        {proxy.name}
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase">
                        {proxy.type}
                      </div>
                    </td>
                    <td className="px-2 py-2.5">
                      <div className="font-mono text-gray-300 truncate max-w-[150px]">
                        {proxy.host}:{proxy.port}
                      </div>
                      {proxy.username && (
                        <div className="text-[10px] text-gray-500 truncate max-w-[150px]">
                          tài khoản: {proxy.username}
                        </div>
                      )}
                    </td>
                    <td className="px-2 py-2.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            proxy.status === "active"
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "bg-red-500/15 text-red-400"
                          }`}
                        >
                          {proxy.status}
                        </span>
                        {proxy.latency_ms !== null && (
                          <span className="text-[10px] text-gray-400 flex items-center gap-1" title={`Last IP: ${proxy.last_ip || "Unknown"}`}>
                            <Activity className="h-3 w-3" />
                            {proxy.latency_ms}ms
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <div
                        className="flex items-center justify-end gap-0.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            setCheckingId(proxy.id);
                            try {
                              await onCheck(proxy.id);
                            } finally {
                              setCheckingId(null);
                            }
                          }}
                          disabled={checkingId === proxy.id}
                          className="p-1 text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors disabled:opacity-50"
                          title="Kiểm tra Proxy"
                        >
                          {checkingId === proxy.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Activity className="h-3.5 w-3.5" />
                          )}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onEdit(proxy.id);
                          }}
                          className="p-1 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded transition-colors"
                          title="Sửa"
                        >
                          <Pencil className="h-3.5 w-3.5" />
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

      {/* New proxy button */}
      <div className="p-3 border-t border-border flex-shrink-0">
        <button
          onClick={onNew}
          className="btn-secondary w-full flex items-center justify-center gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Thêm Proxy</span>
        </button>
      </div>
    </div>
  );
}
