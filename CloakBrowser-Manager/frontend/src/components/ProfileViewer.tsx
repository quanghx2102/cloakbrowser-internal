import { useEffect, useRef, useState } from "react";
import { ClipboardCopy, Code2, Maximize2, Minimize2 } from "lucide-react";
import { api } from "../lib/api";

interface ProfileViewerProps {
  profileId: string;
  cdpUrl: string | null;
  clipboardSync: boolean;
  onDisconnect: () => void;
  vncWsPort: number | null;
}

// X11 keysym for V key (Ctrl is already held in VNC by the time we intercept)
const XK_v = 0x0076;

export function ProfileViewer({ profileId, cdpUrl, clipboardSync: initialClipboardSync, onDisconnect, vncWsPort }: ProfileViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<any>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [clipboardSync, setClipboardSync] = useState(initialClipboardSync);
  const [cdpCopied, setCdpCopied] = useState(false);

  if (vncWsPort === null) {
    return (
      <div className="flex-1 bg-surface-2 p-6 flex flex-col items-center justify-center h-full">
        <div className="max-w-md w-full bg-surface-1 border border-border rounded-2xl p-8 text-center shadow-xl flex flex-col items-center">
          <div className="relative mb-6">
            <div className="absolute inset-0 bg-accent/20 rounded-full blur-xl animate-pulse" />
            <div className="relative h-20 w-20 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent text-4xl shadow-inner">
              🖥️
            </div>
          </div>
          <h3 className="text-lg font-semibold text-gray-200 mb-2">
            Profile Đang Chạy Vật Lý
          </h3>
          <p className="text-gray-400 text-sm mb-6 leading-relaxed">
            Trình duyệt CloakBrowser đang mở trực tiếp dưới dạng một cửa sổ thực trên màn hình máy tính của bạn.
          </p>
          
          <div className="w-full bg-surface-2 border border-border rounded-xl p-4 mb-6 flex flex-col gap-3 text-left">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500">Trạng thái:</span>
              <span className="font-medium text-emerald-400 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Active (Native)
              </span>
            </div>
            {cdpUrl && (
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-500">Cổng Debugging (CDP):</span>
                  <button
                    onClick={() => {
                      const base = `${window.location.protocol}//${window.location.host}${cdpUrl}`;
                      navigator.clipboard?.writeText(base).then(() => {
                        setCdpCopied(true);
                        setTimeout(() => setCdpCopied(false), 2000);
                      }).catch((err) => console.warn("[cdp] copy failed:", err));
                    }}
                    className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                      cdpCopied 
                        ? "bg-emerald-950/30 text-emerald-400 border-emerald-500/30" 
                        : "bg-surface-3 text-gray-400 border-border hover:text-gray-200"
                    }`}
                  >
                    {cdpCopied ? "Đã sao chép" : "Sao chép"}
                  </button>
                </div>
                <div className="bg-surface-3 px-3 py-2 rounded-lg font-mono text-[10px] text-gray-400 select-all truncate">
                  {`${window.location.protocol}//${window.location.host}${cdpUrl}`}
                </div>
              </div>
            )}
          </div>

          <button
            onClick={async () => {
              try {
                await api.stopProfile(profileId);
                onDisconnect();
              } catch (err) {
                console.error("Failed to stop profile:", err);
              }
            }}
            className="w-full py-2.5 px-4 rounded-xl bg-red-600/10 hover:bg-red-600/20 border border-red-500/20 hover:border-red-500/30 text-red-400 text-sm font-semibold transition-all shadow-sm"
          >
            Tắt Trình Duyệt (Stop)
          </button>
        </div>
      </div>
    );
  }

  useEffect(() => {
    let rfb: any = null;
    let cancelled = false;

    async function connect() {
      try {
        // Import noVNC dynamically
        const { default: RFB } = await import("@novnc/novnc/core/rfb.js");

        if (cancelled) return;

        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/api/profiles/${profileId}/vnc`;

        rfb = new RFB(containerRef.current!, wsUrl, {
          wsProtocols: ["binary"],
        });
        rfbRef.current = rfb;

        rfb.scaleViewport = true;
        rfb.resizeSession = false;
        rfb.showDotCursor = true;

        rfb.addEventListener("connect", () => {
          if (!cancelled) setConnected(true);
        });

        rfb.addEventListener("disconnect", () => {
          if (!cancelled) {
            setConnected(false);
            onDisconnect();
          }
        });

        rfb.addEventListener("securityfailure", (e: any) => {
          setError(`Lỗi bảo mật (Security failure): ${e.detail.reason}`);
        });
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Kết nối thất bại");
        }
      }
    }

    connect();

    return () => {
      cancelled = true;
      if (rfb) {
        try {
          rfb.disconnect();
        } catch (err) {
          console.debug("[vnc] disconnect cleanup failed:", err);
        }
      }
      rfbRef.current = null;
    };
  }, [profileId, onDisconnect]);

  // Host→VNC: intercept Ctrl+V/Cmd+V at keydown (capture phase)
  // Must fire BEFORE noVNC's canvas listener to prevent the race condition
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !clipboardSync || !connected) return;

    const handleKeyDown = async (e: KeyboardEvent) => {
      console.log("[clipboard] keydown:", e.key, "ctrl:", e.ctrlKey, "meta:", e.metaKey, "clipboardSync:", true);

      const isPaste =
        e.key === "v" && (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey;
      if (!isPaste) return;

      console.log("[clipboard] intercepted Ctrl+V");

      // Block noVNC from sending the keystroke before clipboard is updated
      e.stopPropagation();
      e.preventDefault();

      const rfb = rfbRef.current;
      if (!rfb) {
        console.log("[clipboard] no rfb ref, aborting");
        return;
      }

      try {
        const text = await navigator.clipboard.readText();
        console.log("[clipboard] host clipboard text:", text?.substring(0, 50), "len:", text?.length);
        if (text) {
          console.log("[clipboard] calling setClipboard API...");
          await api.setClipboard(profileId, text);
          console.log("[clipboard] setClipboard API success");
        }
      } catch (err) {
        console.warn("[clipboard] error:", err);
        setClipboardSync(false);
        return;
      }

      // Send full Ctrl+V sequence to VNC. We can't rely on Ctrl still being
      // held because the user may have released it during the async API call.
      console.log("[clipboard] sending Ctrl+V to VNC");
      rfb.sendKey(0xffe3, "ControlLeft", true);   // Ctrl press
      rfb.sendKey(XK_v, "KeyV", true);             // V press
      rfb.sendKey(XK_v, "KeyV", false);            // V release
      rfb.sendKey(0xffe3, "ControlLeft", false);   // Ctrl release
    };

    // capture: true ensures we fire before noVNC's canvas listener
    container.addEventListener("keydown", handleKeyDown, true);
    return () => container.removeEventListener("keydown", handleKeyDown, true);
  }, [profileId, clipboardSync, connected]);

  // VNC→Host: listen for noVNC "clipboard" event (fired when proxy converts
  // KasmVNC BinaryClipboard type 180 → standard ServerCutText type 3)
  useEffect(() => {
    const rfb = rfbRef.current;
    console.log("[clipboard] VNC→Host effect: rfb=", !!rfb, "sync=", clipboardSync, "connected=", connected);
    if (!rfb || !clipboardSync || !connected) return;

    const handleClipboard = (e: any) => {
      const text = e.detail?.text;
      console.log("[clipboard] VNC→Host event fired, text:", text?.substring(0, 50), "len:", text?.length);
      if (text) {
        navigator.clipboard.writeText(text).then(() => {
          console.log("[clipboard] writeText success");
        }).catch((err) => {
          console.warn("[clipboard] writeText failed:", err);
        });
      }
    };

    console.log("[clipboard] registering clipboard event listener on rfb");
    rfb.addEventListener("clipboard", handleClipboard);
    return () => {
      console.log("[clipboard] removing clipboard event listener");
      rfb.removeEventListener("clipboard", handleClipboard);
    };
  }, [clipboardSync, connected]);

  // VNC→Host polling: Chrome doesn't write to X11 clipboard under KasmVNC,
  // so type 180 events won't fire for Chrome copies. Poll via Playwright CDP.
  useEffect(() => {
    if (!clipboardSync || !connected) return;

    let cancelled = false;
    let lastText = "";

    const poll = async () => {
      if (cancelled) return;
      try {
        const { text } = await api.getClipboard(profileId);
        if (text && text !== lastText) {
          lastText = text;
          console.log("[clipboard] poll: new VNC clipboard:", text.substring(0, 50), "len:", text.length);
          await navigator.clipboard.writeText(text).catch((err) =>
            console.warn("[clipboard] poll writeText failed:", err)
          );
        }
      } catch (err) {
        console.warn("[clipboard] poll error, stopping:", err);
        cancelled = true;
        return;
      }
      if (!cancelled) {
        setTimeout(poll, 2000);
      }
    };

    // Start polling after a short delay
    const timer = setTimeout(poll, 2000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [profileId, clipboardSync, connected]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen();
      setFullscreen(true);
    } else {
      document.exitFullscreen();
      setFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFsChange = () => {
      setFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFsChange);
    return () => document.removeEventListener("fullscreenchange", handleFsChange);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-400 text-sm mb-2">Kết nối thất bại</p>
          <p className="text-gray-500 text-xs">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-1 border-b border-border">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-yellow-400 animate-pulse"}`} />
          <span className="text-xs text-gray-400">
            {connected ? "Đã kết nối" : "Đang kết nối..."}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {cdpUrl && (
            <button
              onClick={() => {
                const base = `${window.location.protocol}//${window.location.host}${cdpUrl}`;
                navigator.clipboard?.writeText(base).then(() => {
                  setCdpCopied(true);
                  setTimeout(() => setCdpCopied(false), 2000);
                }).catch((err) => console.warn("[cdp] copy failed:", err));
              }}
              className={`p-1 ${cdpCopied ? "text-emerald-400" : "text-gray-500 hover:text-gray-300"}`}
              title={cdpCopied ? "Đã sao chép!" : "Sao chép URL cổng CDP"}
            >
              <Code2 className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            onClick={() => { console.log("[clipboard] toggle:", !clipboardSync); setClipboardSync(!clipboardSync); }}
            className={`p-1 ${clipboardSync ? "text-accent" : "text-gray-500 hover:text-gray-300"}`}
            title={clipboardSync ? "Tắt đồng bộ Clipboard" : "Bật đồng bộ Clipboard"}
            disabled={!connected}
          >
            <ClipboardCopy className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={toggleFullscreen}
            className="text-gray-500 hover:text-gray-300 p-1"
            title={fullscreen ? "Thoát toàn màn hình" : "Toàn màn hình"}
          >
            {fullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* VNC canvas container */}
      <div
        ref={containerRef}
        className="flex-1 bg-black overflow-hidden"
        style={{ minHeight: 0 }}
      />
    </div>
  );
}
