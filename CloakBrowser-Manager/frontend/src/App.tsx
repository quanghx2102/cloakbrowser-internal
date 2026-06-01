import { useState, useCallback, useEffect } from "react";
import { Lock, PanelLeftClose, PanelLeft } from "lucide-react";
import { useProfiles } from "./hooks/useProfiles";
import { useProxies } from "./hooks/useProxies";
import { api, setOnUnauthorized, type ProfileCreateData, type ProxyCreateData } from "./lib/api";
import { ProfileList } from "./components/ProfileList";
import { ProfileForm } from "./components/ProfileForm";
import { ProxyList } from "./components/ProxyList";
import { ProxyForm } from "./components/ProxyForm";
import { ProfileViewer } from "./components/ProfileViewer";
import { LaunchButton } from "./components/LaunchButton";
import { StatusIndicator } from "./components/StatusIndicator";
import { LoginPage } from "./components/LoginPage";
import { Dashboard } from "./components/Dashboard";

type AuthState = "checking" | "required" | "ok" | "error";
type View = "empty" | "create_profile" | "edit_profile" | "view_profile" | "logs_profile" | "create_proxy" | "edit_proxy";
type Tab = "dashboard" | "profiles" | "proxies";
type Toast = { message: string; type: "success" | "error" } | null;

export default function App() {
  const [authState, setAuthState] = useState<AuthState>("checking");
  const [authRequired, setAuthRequired] = useState(false);

  useEffect(() => {
    setOnUnauthorized(() => setAuthState("required"));

    api.authStatus()
      .then(({ auth_required, authenticated }) => {
        setAuthRequired(auth_required);
        if (!auth_required || authenticated) {
          setAuthState("ok");
        } else {
          setAuthState("required");
        }
      })
      .catch((err) => {
        console.warn("[auth] status check failed:", err);
        setAuthState("error");
      });

    return () => setOnUnauthorized(null);
  }, []);

  if (authState === "checking") {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-gray-500 text-sm">Đang tải...</div>
      </div>
    );
  }

  if (authState === "error") {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-0">
        <div className="text-center">
          <p className="text-red-400 text-sm mb-2">Không thể kết nối đến máy chủ</p>
          <button
            onClick={() => {
              setAuthState("checking");
              api.authStatus()
                .then(({ auth_required, authenticated }) => {
                  setAuthRequired(auth_required);
                  setAuthState(!auth_required || authenticated ? "ok" : "required");
                })
                .catch(() => setAuthState("error"));
            }}
            className="text-xs text-gray-400 hover:text-gray-200 underline"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  if (authState === "required") {
    return <LoginPage onSuccess={() => setAuthState("ok")} />;
  }

  return (
    <AppContent
      authRequired={authRequired}
      onLogout={async () => {
        await api.logout();
        setAuthState("required");
      }}
    />
  );
}

interface AppContentProps {
  authRequired: boolean;
  onLogout: () => void;
}

function AppContent({ authRequired, onLogout }: AppContentProps) {
  const { profiles, loading: profilesLoading, error: profilesError, create: createProfile, update: updateProfile, remove: removeProfile, launch, stop } = useProfiles();
  const { proxies, loading: proxiesLoading, error: proxiesError, create: createProxy, update: updateProxy, remove: removeProxy, check: checkProxy } = useProxies();

  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [selectedProxyId, setSelectedProxyId] = useState<string | null>(null);

  const [view, setView] = useState<View>("empty");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [toast, setToast] = useState<Toast>(null);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    api.getStatus()
      .then((status) => {
        setIsDesktop(!!status.is_desktop);
      })
      .catch((err) => {
        console.warn("[status] fetch failed:", err);
      });
  }, []);

  const showToast = useCallback((message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) ?? null;
  const selectedProxy = proxies.find((p) => p.id === selectedProxyId) ?? null;

  const handleSelectProfile = useCallback((id: string) => {
    setSelectedProfileId(id);
    const profile = profiles.find((p) => p.id === id);
    setView(profile?.status === "running" ? "view_profile" : "edit_profile");
  }, [profiles]);

  const handleSelectProxy = useCallback((id: string) => {
    setSelectedProxyId(id);
    setView("edit_proxy");
  }, []);

  const handleNewProfile = useCallback(() => {
    setSelectedProfileId(null);
    setView("create_profile");
  }, []);

  const handleNewProxy = useCallback(() => {
    setSelectedProxyId(null);
    setView("create_proxy");
  }, []);

  const handleCreateProfile = useCallback(async (data: ProfileCreateData) => {
    try {
      const profile = await createProfile(data);
      if (profile) {
        setSelectedProfileId(profile.id);
        setView("edit_profile");
        showToast("Tạo profile thành công", "success");
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Tạo profile thất bại", "error");
    }
  }, [createProfile, showToast]);

  const handleUpdateProfile = useCallback(async (data: ProfileCreateData) => {
    if (!selectedProfileId) return;
    try {
      await updateProfile(selectedProfileId, data);
      showToast("Cập nhật profile thành công", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Cập nhật profile thất bại", "error");
    }
  }, [selectedProfileId, updateProfile, showToast]);

  const handleDeleteProfile = useCallback(async () => {
    if (!selectedProfileId) return;
    try {
      await removeProfile(selectedProfileId);
      setSelectedProfileId(null);
      setView("empty");
      showToast("Xóa profile thành công", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Xóa profile thất bại", "error");
    }
  }, [selectedProfileId, removeProfile, showToast]);

  const handleCreateProxy = useCallback(async (data: ProxyCreateData) => {
    try {
      const proxy = await createProxy(data);
      if (proxy) {
        setSelectedProxyId(proxy.id);
        setView("edit_proxy");
        showToast("Tạo proxy thành công", "success");
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Tạo proxy thất bại", "error");
    }
  }, [createProxy, showToast]);

  const handleUpdateProxy = useCallback(async (data: ProxyCreateData) => {
    if (!selectedProxyId) return;
    try {
      await updateProxy(selectedProxyId, data);
      showToast("Cập nhật proxy thành công", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Cập nhật proxy thất bại", "error");
    }
  }, [selectedProxyId, updateProxy, showToast]);

  const handleDeleteProxy = useCallback(async () => {
    if (!selectedProxyId) return;
    try {
      await removeProxy(selectedProxyId);
      setSelectedProxyId(null);
      setView("empty");
      showToast("Xóa proxy thành công", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Xóa proxy thất bại", "error");
    }
  }, [selectedProxyId, removeProxy, showToast]);

  const handleCheckProxy = useCallback(async (id: string) => {
    try {
      const result = await checkProxy(id);
      if (result.status_code === "PROXY_OK") {
        showToast(`Proxy hoạt động tốt: ${result.proxy.latency_ms}ms`, "success");
      } else {
        showToast(`Kiểm tra Proxy thất bại: ${result.status_code}`, "error");
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Kiểm tra proxy thất bại", "error");
    }
  }, [checkProxy, showToast]);

  const handleLaunch = useCallback(async (id?: string) => {
    const targetId = id ?? selectedProfileId;
    if (!targetId) return;
    const result = await launch(targetId);
    if (result) {
      setSelectedProfileId(targetId);
      if (isDesktop) {
        setView("edit_profile");
      } else {
        setView("view_profile");
      }
    }
  }, [selectedProfileId, launch, isDesktop]);

  const handleStop = useCallback(async (id?: string) => {
    const targetId = id ?? selectedProfileId;
    if (!targetId) return;
    await stop(targetId);
    if (targetId === selectedProfileId) setView("edit_profile");
  }, [selectedProfileId, stop]);

  const handleVncDisconnect = useCallback(() => {
    setView("edit_profile");
  }, []);

  const handleViewProfile = useCallback((id: string) => {
    const profile = profiles.find((p) => p.id === id);
    if (profile?.status === "running") {
      setSelectedProfileId(id);
      setView("view_profile");
    }
  }, [profiles]);

  const handleEditProfile = useCallback((id: string) => {
    setSelectedProfileId(id);
    setView("edit_profile");
  }, []);

  const handleLogsProfile = useCallback((id: string) => {
    setSelectedProfileId(id);
    setView("logs_profile");
  }, []);

  if (profilesLoading || proxiesLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-gray-500 text-sm">Đang tải...</div>
      </div>
    );
  }

  return (
    <div className="h-screen flex">
      {/* Sidebar Navigation */}
      <div className="w-[60px] bg-surface-0 border-r border-border flex flex-col items-center py-4 gap-4 flex-shrink-0 z-20">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`p-3 rounded-xl transition-colors ${
            activeTab === "dashboard"
              ? "bg-accent/15 text-accent"
              : "text-gray-500 hover:text-gray-300 hover:bg-surface-2"
          }`}
          title="Bảng điều khiển"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>
        </button>
        <button
          onClick={() => setActiveTab("profiles")}
          className={`p-3 rounded-xl transition-colors ${
            activeTab === "profiles"
              ? "bg-accent/15 text-accent"
              : "text-gray-500 hover:text-gray-300 hover:bg-surface-2"
          }`}
          title="Profile"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
        </button>
        <button
          onClick={() => setActiveTab("proxies")}
          className={`p-3 rounded-xl transition-colors ${
            activeTab === "proxies"
              ? "bg-accent/15 text-accent"
              : "text-gray-500 hover:text-gray-300 hover:bg-surface-2"
          }`}
          title="Proxy"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"></path></svg>
        </button>
      </div>

      {/* Sidebar */}
      {sidebarOpen && activeTab !== "dashboard" && (
        <div className="w-[680px] border-r border-border bg-surface-1 flex-shrink-0">
          {activeTab === "profiles" ? (
            <ProfileList
              profiles={profiles}
              selectedId={selectedProfileId}
              onSelect={handleSelectProfile}
              onNew={handleNewProfile}
              onLaunch={async (id) => { await handleLaunch(id); }}
              onStop={async (id) => { await handleStop(id); }}
              onView={handleViewProfile}
              onEdit={handleEditProfile}
              onLogs={handleLogsProfile}
              isDesktop={isDesktop}
            />
          ) : (
            <ProxyList
              proxies={proxies}
              selectedId={selectedProxyId}
              onSelect={handleSelectProxy}
              onNew={handleNewProxy}
              onEdit={handleSelectProxy}
              onCheck={handleCheckProxy}
            />
          )}
        </div>
      )}

      {/* Main panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-1">
          <div className="flex items-center gap-3">
            {activeTab !== "dashboard" && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-gray-500 hover:text-gray-300 p-1"
                title={sidebarOpen ? "Ẩn thanh bên" : "Hiện thanh bên"}
              >
                {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
              </button>
            )}
            {activeTab === "dashboard" && <span className="text-sm font-medium">Bảng điều khiển</span>}
            {selectedProfile && activeTab === "profiles" && (
              <div className="flex items-center gap-2">
                <StatusIndicator status={selectedProfile.status} size="md" />
                <span className="text-sm font-medium">{selectedProfile.name}</span>
                <span className="text-xs text-gray-500 capitalize">{selectedProfile.platform}</span>
              </div>
            )}
            {selectedProxy && activeTab === "proxies" && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{selectedProxy.name}</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {selectedProfile && activeTab === "profiles" && (
              <LaunchButton
                status={selectedProfile.status}
                onLaunch={() => handleLaunch()}
                onStop={() => handleStop()}
                isDesktop={isDesktop}
              />
            )}
            {authRequired && (
              <button
                onClick={onLogout}
                className="text-gray-500 hover:text-gray-300 p-1"
                title="Đăng xuất"
              >
                <Lock className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Error banner */}
        {(profilesError || proxiesError) && (
          <div className="px-4 py-2 bg-red-600/15 border-b border-red-600/30 text-red-400 text-sm">
            {profilesError || proxiesError}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 bg-surface-2 flex flex-col relative overflow-hidden">
          {activeTab === "dashboard" && (
            <div className="flex-1 overflow-y-auto">
              <Dashboard />
            </div>
          )}
          {activeTab !== "dashboard" && view === "empty" && (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
              <div className="h-16 w-16 mb-4 rounded-full bg-surface-3 flex items-center justify-center">
                <span className="text-2xl">✨</span>
              </div>
              <p className="text-sm font-medium">Chọn một mục từ thanh bên để bắt đầu</p>
            </div>
          )}
          {view === "create_profile" && (
            <ProfileForm
              profile={null}
              proxies={proxies}
              onSave={handleCreateProfile}
              onCancel={() => setView("empty")}
            />
          )}

          {view === "edit_profile" && selectedProfile && (
            <ProfileForm
              profile={selectedProfile}
              proxies={proxies}
              onSave={handleUpdateProfile}
              onDelete={handleDeleteProfile}
              onCancel={() => {
                setSelectedProfileId(null);
                setView("empty");
              }}
            />
          )}

          {view === "view_profile" && selectedProfile && selectedProfile.status === "running" && (
            <ProfileViewer
              key={selectedProfile.id}
              profileId={selectedProfile.id}
              cdpUrl={selectedProfile.cdp_url}
              clipboardSync={selectedProfile.clipboard_sync}
              onDisconnect={handleVncDisconnect}
              vncWsPort={selectedProfile.vnc_ws_port}
            />
          )}

          {view === "logs_profile" && selectedProfile && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-gray-400 text-sm font-medium mb-1">
                  Nhật ký hoạt động — {selectedProfile.name}
                </p>
                <p className="text-gray-600 text-xs">
                  Trình xem nhật ký sẽ được cập nhật ở giai đoạn sau.
                </p>
                <button
                  onClick={() => setView("edit_profile")}
                  className="mt-3 text-xs text-gray-500 hover:text-gray-300 underline"
                >
                  ← Quay lại profile
                </button>
              </div>
            </div>
          )}

          {view === "create_proxy" && (
            <ProxyForm
              proxy={null}
              onSave={handleCreateProxy}
              onCancel={() => setView("empty")}
            />
          )}

          {view === "edit_proxy" && selectedProxy && (
            <ProxyForm
              proxy={selectedProxy}
              onSave={handleUpdateProxy}
              onDelete={handleDeleteProxy}
              onCheck={() => handleCheckProxy(selectedProxy.id)}
              onCancel={() => {
                setSelectedProxyId(null);
                setView("empty");
              }}
            />
          )}
        </div>

        {/* Toast */}
        {toast && (
          <div className="absolute bottom-4 right-4 z-50">
            <div
              className={`px-4 py-2 rounded-md shadow-lg text-sm font-medium border ${
                toast.type === "success"
                  ? "bg-emerald-900/50 text-emerald-400 border-emerald-500/30"
                  : "bg-red-900/50 text-red-400 border-red-500/30"
              }`}
            >
              {toast.message}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
