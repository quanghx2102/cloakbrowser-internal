"""Launch/stop/track CloakBrowser instances per profile."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cloakbrowser import launch_persistent_context_async

try:
    from .vnc_manager import VNCManager
    from . import database as db
    from .logger_utils import log_activity, log_error
except ImportError:
    from backend.vnc_manager import VNCManager
    import backend.database as db
    from backend.logger_utils import log_activity, log_error

logger = logging.getLogger("cloakbrowser.manager.browser")


def _normalize_proxy(raw: str) -> str:
    """Convert common proxy formats to scheme://user:pass@host:port.

    Accepts:
      - http://user:pass@host:port  (already valid)
      - host:port:user:pass
      - host:port
      - socks5://host:port:user:pass
      - socks5://host:port
    """
    scheme = "http"
    cleaned = raw
    if raw.startswith(("http://", "https://", "socks5://")):
        # Check if it's already a valid standard URL
        from urllib.parse import urlparse
        try:
            parsed = urlparse(raw)
            if parsed.hostname and parsed.port:
                return raw
        except Exception:
            pass
        
        # If it starts with a scheme but is not in standard URL format (e.g. socks5://host:port:user:pass)
        if raw.startswith("socks5://"):
            scheme = "socks5"
            cleaned = raw[9:]
        elif raw.startswith("https://"):
            scheme = "https"
            cleaned = raw[8:]
        elif raw.startswith("http://"):
            scheme = "http"
            cleaned = raw[7:]

    parts = cleaned.split(":")
    if len(parts) == 4:
        host, port, user, passwd = parts
        return f"{scheme}://{user}:{passwd}@{host}:{port}"
    if len(parts) == 2:
        return f"{scheme}://{cleaned}"
    return raw


def _validate_proxy(url: str) -> None:
    """Validate that a normalized proxy URL has scheme, host, and port."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "socks5"):
        raise ValueError(
            f"Invalid proxy scheme '{parsed.scheme}'. Must be http, https, or socks5."
        )
    if not parsed.hostname:
        raise ValueError(f"Proxy URL missing hostname: {url}")
    if not parsed.port:
        raise ValueError(f"Proxy URL missing port: {url}")


def _init_profile_defaults(user_data_dir: Path) -> None:
    """Set up bookmarks and DuckDuckGo search on first launch."""
    default_dir = user_data_dir / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)

    # --- Bookmarks (only on first launch) ---
    bookmarks_path = default_dir / "Bookmarks"
    if not bookmarks_path.exists():
        ts = str(int(time.time() * 1_000_000))  # Chrome timestamp format
        _id = 1

        def bm(name: str, url: str) -> dict:
            nonlocal _id
            _id += 1
            return {"type": "url", "id": str(_id), "name": name, "url": url, "date_added": ts}

        def folder(name: str, children: list) -> dict:
            nonlocal _id
            _id += 1
            return {"type": "folder", "id": str(_id), "name": name, "children": children, "date_added": ts, "date_modified": ts}

        bookmarks = {
            "checksum": "",
            "roots": {
                "bookmark_bar": {
                    "type": "folder", "id": "1", "name": "Bookmarks bar",
                    "date_added": ts, "date_modified": ts,
                    "children": [
                        folder("Detection Tests", [
                            bm("Rebrowser Bot Detector", "https://bot-detector.rebrowser.net/"),
                            bm("Incolumitas", "https://bot.incolumitas.com/"),
                            bm("SannySort", "https://bot.sannysoft.com/"),
                            bm("BrowserScan Bot", "https://www.browserscan.net/bot-detection"),
                            bm("FingerprintJS Demo", "https://demo.fingerprint.com/web-scraping"),
                            bm("Pixelscan", "https://pixelscan.net/fingerprint-check"),
                            bm("CreepJS", "https://abrahamjuliot.github.io/creepjs/"),
                            bm("fingerprint-scan", "https://fingerprint-scan.com/"),
                            bm("DeviceInfo Bot", "https://deviceandbrowserinfo.com/are_you_a_bot"),
                        ]),
                        folder("Fingerprint", [
                            bm("BrowserLeaks Canvas", "https://browserleaks.com/canvas"),
                            bm("BrowserLeaks WebGL", "https://browserleaks.com/webgl"),
                            bm("BrowserLeaks Fonts", "https://browserleaks.com/fonts"),
                            bm("BrowserLeaks JS", "https://browserleaks.com/javascript"),
                            bm("FingerprintJS OSS", "https://fingerprintjs.github.io/fingerprintjs/"),
                            bm("Audio FP", "https://audiofingerprint.openwpm.com/"),
                            bm("DeviceInfo", "https://deviceandbrowserinfo.com/info_device"),
                        ]),
                        folder("Headers & TLS", [
                            bm("httpbin headers", "https://httpbin.org/headers"),
                            bm("httpbin IP", "https://httpbin.org/ip"),
                            bm("TLS Fingerprint", "https://tls.browserleaks.com/"),
                        ]),
                        folder("reCAPTCHA", [
                            bm("Google v3 Demo", "https://recaptcha-demo.appspot.com/recaptcha-v3-request-scores.php"),
                            bm("2captcha v3", "https://2captcha.com/demo/recaptcha-v3"),
                            bm("Turnstile", "https://peet.ws/turnstile-test/non-interactive.html"),
                        ]),
                    ],
                },
                "other": {"type": "folder", "id": "2", "name": "Other bookmarks", "children": []},
                "synced": {"type": "folder", "id": "3", "name": "Mobile bookmarks", "children": []},
            },
            "version": 1,
        }
        bookmarks_path.write_text(json.dumps(bookmarks, indent=2))
        logger.info("Created default bookmarks for %s", user_data_dir.name)

    # --- DuckDuckGo as default search engine ---
    prefs_path = default_dir / "Preferences"
    if not prefs_path.exists():
        prefs = {
            "default_search_provider_data": {
                "template_url_data": {
                    "keyword": "duckduckgo.com",
                    "short_name": "DuckDuckGo",
                    "url": "https://duckduckgo.com/?q={searchTerms}",
                    "suggestions_url": "https://duckduckgo.com/ac/?q={searchTerms}&type=list",
                    "favicon_url": "https://duckduckgo.com/favicon.ico",
                }
            },
            "default_search_provider": {
                "enabled": True,
            },
        }
        prefs_path.write_text(json.dumps(prefs, indent=2))
        logger.info("Set DuckDuckGo as default search for %s", user_data_dir.name)


BASE_CDP_PORT = 5100
CDP_PORT_RANGE = 100  # cycle through 5100-5199 to avoid TIME_WAIT collisions


@dataclass
class RunningProfile:
    profile_id: str
    context: Any  # Playwright BrowserContext
    display: int | None
    ws_port: int | None
    cdp_port: int
    pid: int | None = None


class BrowserManager:
    def __init__(self):
        self.running: dict[str, RunningProfile] = {}
        self.statuses: dict[str, str] = {}  # starting, running, stopping, failed, crashed
        self.vnc = VNCManager()
        self._lock = asyncio.Lock()
        self._next_cdp_port = BASE_CDP_PORT
        self._auto_launch_task: asyncio.Task | None = None
        self.is_desktop = os.environ.get("CLOAK_DESKTOP", "0") == "1"

    async def launch(self, profile: dict[str, Any]) -> RunningProfile:
        """Launch a browser instance for the given profile."""
        profile_id = profile["id"]
        profile_name = profile.get("name") or "unknown"

        async with self._lock:
            current_status = self.statuses.get(profile_id)
            if current_status in ("starting", "running", "stopping"):
                log_error(
                    module="browser_manager",
                    action="launch_profile",
                    error_code="PROFILE_ALREADY_RUNNING",
                    message=f"Profile {profile_id} is already {current_status}",
                    profile_id=profile_id,
                )
                logger.error("PROFILE_ALREADY_RUNNING: Profile %s is already %s", profile_id, current_status)
                raise RuntimeError(f"Profile {profile_id} is already {current_status}")

            max_allowed = int(os.environ.get("MAX_RUNNING_PROFILES", "5"))
            if max_allowed > 0:
                running_or_starting = sum(1 for status in self.statuses.values() if status in ("starting", "running"))
                if running_or_starting >= max_allowed:
                    log_error(
                        module="browser_manager",
                        action="launch_profile",
                        error_code="RESOURCE_LIMIT_REACHED",
                        message=f"Maximum running profiles limit ({max_allowed}) reached.",
                        profile_id=profile_id,
                    )
                    raise RuntimeError(f"RESOURCE_LIMIT_REACHED: Maximum running profiles limit ({max_allowed}) reached.")

            self.statuses[profile_id] = "starting"

        start_time = time.monotonic()
        
        display = None
        ws_port = None
        if not self.is_desktop:
            display, ws_port = await self.vnc.allocate()

        try:
            cdp_port = self._allocate_cdp_port()
        except ValueError as exc:
            async with self._lock:
                self.statuses[profile_id] = "failed"
            log_error("browser_manager", "launch_profile", f"Could not allocate CDP port for {profile_id}: {exc}", profile_id)
            if not self.is_desktop and display is not None:
                await self.vnc.stop_vnc(display)
            raise

        # Clean stale Chromium lock files (left by previous container crashes)
        user_data_dir = Path(profile["user_data_dir"])
        for lock_file in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            lock_path = user_data_dir / lock_file
            lock_path.unlink(missing_ok=True)

        # Set up bookmarks and search engine on first launch
        _init_profile_defaults(user_data_dir)

        try:
            # Start KasmVNC on the allocated display
            if not self.is_desktop:
                await self.vnc.start_vnc(
                    display,
                    ws_port,
                    width=profile.get("screen_width", 1920),
                    height=profile.get("screen_height", 1080),
                )

            # Build fingerprint args from profile settings
            extra_args = self._build_fingerprint_args(profile)
            extra_args += profile.get("launch_args") or []
            extra_args.append(f"--remote-debugging-port={cdp_port}")

            # Resolve proxy
            proxy_id = profile.get("proxy_id")
            proxy = None
            if proxy_id:
                proxy_record = db.get_proxy(proxy_id)
                if proxy_record and proxy_record.get("status") == "active":
                    phost = proxy_record["host"]
                    pport = proxy_record["port"]
                    ptype = proxy_record.get("type", "http")
                    puser = proxy_record.get("username")
                    ppwd = proxy_record.get("password")
                    if puser and ppwd:
                        proxy = f"{ptype}://{puser}:{ppwd}@{phost}:{pport}"
                    else:
                        proxy = f"{ptype}://{phost}:{pport}"
            else:
                # Fallback to old proxy string
                raw_proxy = profile.get("proxy") or None
                proxy = _normalize_proxy(raw_proxy) if raw_proxy else None

            if proxy:
                _validate_proxy(proxy)

            binary_path = None
            path_configured = False

            # 1. Env overrides for dev/debug
            env_path = os.environ.get("CLOAK_BROWSER_BINARY_PATH") or os.environ.get("CLOAKBROWSER_BINARY_PATH")
            if env_path:
                binary_path = env_path
                path_configured = True

            # 2. Config saved in app-config.json
            if not binary_path:
                data_dir = os.environ.get("CLOAK_DATA_DIR")
                if data_dir:
                    config_path = Path(data_dir) / "config" / "app-config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, "r", encoding="utf-8") as f:
                                config_data = json.load(f)
                                saved_path = config_data.get("cloakbrowser_binary_path")
                                if saved_path:
                                    binary_path = saved_path
                                    path_configured = True
                        except Exception as e:
                            logger.warning(f"Failed to read app-config.json in python backend: {e}")

            # 3. Auto-detect on macOS
            if not binary_path and platform.system() == "Darwin":
                home_dir = Path.home()
                base_dir = home_dir / ".cloakbrowser"
                if base_dir.exists():
                    try:
                        for entry in base_dir.iterdir():
                            if entry.is_dir() and entry.name.startswith("chromium-"):
                                candidate = entry / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
                                if candidate.exists():
                                    binary_path = str(candidate.resolve())
                                    break
                    except Exception as e:
                        logger.warning(f"Error scanning for macOS auto-detect binary: {e}")

            # 4. Bundled binary in app resources if available
            if not binary_path:
                bin_name = "cloakbrowser.exe" if platform.system() == "Windows" else "cloakbrowser"
                candidate_dirs = []
                data_dir = os.environ.get("CLOAK_DATA_DIR")
                if data_dir:
                    candidate_dirs.append(Path(data_dir) / "browsers")
                candidate_dirs.extend([
                    Path("binaries"),
                    Path("backend") / "binaries",
                    Path("..") / "binaries",
                    Path(os.getcwd()) / "binaries"
                ])
                for candidate_dir in candidate_dirs:
                    candidate = candidate_dir / bin_name
                    if candidate.exists():
                        binary_path = str(candidate.resolve())
                        break

            # Validate resolved binary path
            if binary_path:
                binary_path = os.path.realpath(binary_path)

            if not binary_path or not Path(binary_path).exists() or not Path(binary_path).is_file():
                error_code = "CLOAK_BROWSER_BINARY_NOT_FOUND" if path_configured else "CLOAK_BROWSER_BINARY_NOT_CONFIGURED"
                log_error(
                    module="browser_manager",
                    action="launch_profile",
                    error_code=error_code,
                    message=f"CloakBrowser binary not found or configured at '{binary_path or 'unknown'}'",
                    profile_id=profile_id,
                )
                raise FileNotFoundError(f"{error_code}: CloakBrowser binary not configured or not found. Please set CLOAK_BROWSER_BINARY_PATH or configure it in settings.")

            # Validate execution permission on non-Windows systems
            if platform.system() != "Windows":
                if not os.access(binary_path, os.X_OK):
                    try:
                        os.chmod(binary_path, 0o755)
                    except Exception as e:
                        logger.warning(f"Failed to set executable permissions on {binary_path}: {e}")
                    if not os.access(binary_path, os.X_OK):
                        raise PermissionError(f"CLOAK_BROWSER_BINARY_PERMISSION_DENIED: Binary at '{binary_path}' does not have execute permission.")

            os.environ["CLOAKBROWSER_BINARY_PATH"] = binary_path
            logger.info(f"Using validated CloakBrowser binary: {binary_path}")

            # Log launch request details clearly (with sanitized proxy)
            proxy_log_status = "no"
            if proxy:
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(proxy)
                    port_str = f":{parsed.port}" if parsed.port else ""
                    proxy_log_status = f"yes ({parsed.scheme}://{parsed.hostname}{port_str})"
                except Exception:
                    proxy_log_status = "yes"

            logger.info(
                f"[Launch Profile] Initiating native launch. "
                f"ID: {profile_id}, Name: {profile_name}, "
                f"Binary Path: {binary_path}, "
                f"User Data Dir: {profile['user_data_dir']}, "
                f"Proxy: {proxy_log_status}"
            )

            env_args = {**os.environ}
            if not self.is_desktop and display is not None:
                env_args["DISPLAY"] = f":{display}"

            # Resolve timezone and locale, overriding with proxy details if geoip is enabled
            timezone = profile.get("timezone") or None
            locale = profile.get("locale") or None
            if bool(profile.get("geoip", False)) and proxy_id:
                proxy_record = db.get_proxy(proxy_id)
                if proxy_record:
                    if proxy_record.get("timezone"):
                        timezone = proxy_record["timezone"]
                    if proxy_record.get("locale"):
                        locale = proxy_record["locale"]

            # Launch CloakBrowser on that display
            # DISPLAY is passed via env kwarg to avoid process-wide os.environ mutation
            if self.is_desktop:
                from cloakbrowser import build_args
                chrome_args = [f"--user-data-dir={profile['user_data_dir']}"]
                stealth_chrome_args = build_args(
                    stealth_args=True,
                    extra_args=extra_args,
                    timezone=timezone,
                    locale=locale,
                    headless=bool(profile.get("headless", False)),
                )
                chrome_args.extend(stealth_chrome_args)
                if proxy:
                    chrome_args.append(f"--proxy-server={proxy}")
                if user_agent := (profile.get("user_agent") or None):
                    chrome_args.append(f"--user-agent={user_agent}")

                # Resolve log path for native browser
                browser_log_fd = None
                data_dir = os.environ.get("CLOAK_DATA_DIR")
                if data_dir:
                    try:
                        browser_log_dir = Path(data_dir) / "logs" / "browser"
                        browser_log_dir.mkdir(parents=True, exist_ok=True)
                        browser_log_path = browser_log_dir / f"profile_{profile_id}.log"
                        browser_log_fd = open(browser_log_path, "a", encoding="utf-8")
                    except Exception as log_err:
                        logger.warning(f"Failed to create/open browser log file: {log_err}")

                # Launch native subprocess
                process = await asyncio.create_subprocess_exec(
                    binary_path,
                    *chrome_args,
                    env=env_args,
                    stdout=browser_log_fd if browser_log_fd else asyncio.subprocess.DEVNULL,
                    stderr=browser_log_fd if browser_log_fd else asyncio.subprocess.DEVNULL,
                )
                pid = process.pid

                if browser_log_fd:
                    browser_log_fd.close()

                running = RunningProfile(
                    profile_id=profile_id,
                    context=None,
                    display=display,
                    ws_port=ws_port,
                    cdp_port=cdp_port,
                    pid=pid,
                )

                # Monitor native process exit
                async def watch_process(proc, p_id):
                    await proc.wait()
                    await self._on_browser_closed(p_id)

                asyncio.create_task(watch_process(process, profile_id))
            else:
                context = await launch_persistent_context_async(
                    user_data_dir=profile["user_data_dir"],
                    headless=bool(profile.get("headless", False)),
                    proxy=proxy,
                    args=extra_args,
                    timezone=timezone,
                    locale=locale,
                    humanize=bool(profile.get("humanize", False)),
                    human_preset=profile.get("human_preset", "default"),
                    geoip=bool(profile.get("geoip", False)),
                    color_scheme=profile.get("color_scheme") or None,
                    user_agent=profile.get("user_agent") or None,
                    viewport={
                        "width": profile.get("screen_width", 1920),
                        "height": profile.get("screen_height", 1080) - 133,
                    },
                    env=env_args,
                )

                # Inject clipboard listener: captures copied text on every page
                # so the GET /clipboard endpoint can read it via page.evaluate()
                _clipboard_init_js = """
                    window.__clipboardText = '';
                    document.addEventListener('copy', () => {
                        const sel = window.getSelection();
                        if (sel) window.__clipboardText = sel.toString();
                    });
                    document.addEventListener('keydown', (e) => {
                        if ((e.ctrlKey || e.metaKey) && e.key === 'c' && !e.altKey && !e.shiftKey) {
                            const sel = window.getSelection();
                            if (sel && sel.toString()) window.__clipboardText = sel.toString();
                        }
                    });
                """
                await context.add_init_script(_clipboard_init_js)
                # Also inject into already-open pages (about:blank created before init_script)
                for p in context.pages:
                    try:
                        await p.evaluate(_clipboard_init_js)
                    except Exception as exc:
                        logger.debug("Clipboard init failed on existing page: %s", exc)

                # Get browser process PID
                import subprocess
                pid = None
                try:
                    out = subprocess.check_output(["pgrep", "-f", f"--remote-debugging-port={cdp_port}"])
                    lines = out.decode().strip().split('\n')
                    if lines and lines[0]:
                        pid = int(lines[0])
                except Exception as e:
                    logger.warning("Failed to find PID for profile %s: %s", profile_id, e)

                running = RunningProfile(
                    profile_id=profile_id,
                    context=context,
                    display=display,
                    ws_port=ws_port,
                    cdp_port=cdp_port,
                    pid=pid,
                )

                # Auto-cleanup if browser crashes or user closes Chrome via VNC
                context.on("close", lambda: asyncio.ensure_future(
                    self._on_browser_closed(profile_id)
                ))

            async with self._lock:
                if self.statuses.get(profile_id) not in ("starting", "running"):
                    # Cancelled/stopped during launch!
                    logger.info("Profile launch cancelled/stopped for %s", profile_id)
                    if running.context is not None:
                        await running.context.close()
                    else:
                        if running.pid:
                            try:
                                if platform.system() == "Windows":
                                    import subprocess
                                    subprocess.run(["taskkill", "/PID", str(running.pid)], capture_output=True, text=True)
                                else:
                                    os.kill(running.pid, 9)
                            except OSError:
                                pass
                    if display is not None:
                        await self.vnc.stop_vnc(display)
                    raise RuntimeError("Profile launch was cancelled or stopped")
                self.running[profile_id] = running
                self.statuses[profile_id] = "running"

            duration = int((time.monotonic() - start_time) * 1000)
            if self.is_desktop:
                logger.info(
                    f"[Launch Profile Success] Profile: {profile_id}, "
                    f"Name: {profile_name}, PID: {pid or 'unknown'}"
                )
                log_activity(
                    module="browser_manager",
                    action="launch_profile",
                    status="BROWSER_NATIVE_STARTED",
                    message=f"Launched native profile {profile_id} with PID {pid or 'unknown'}",
                    profile_id=profile_id,
                    duration_ms=duration
                )
            else:
                log_activity(
                    module="browser_manager",
                    action="launch_profile",
                    status="success",
                    message=f"Launched profile {profile_id} via VNC",
                    profile_id=profile_id,
                    duration_ms=duration
                )

            return running

        except BaseException as exc:
            async with self._lock:
                if self.statuses.get(profile_id) not in ("stopped", "stopping"):
                    self.statuses[profile_id] = "failed"
            logger.error(
                f"[Launch Profile Failed] Profile: {profile_id}, "
                f"Name: {profile_name}, Error: {exc}"
            )
            if self.is_desktop:
                log_error(
                    module="browser_manager",
                    action="launch_profile",
                    error_code="BROWSER_NATIVE_START_FAILED",
                    message=f"Failed to launch native browser {profile_id}: {exc}",
                    profile_id=profile_id,
                )
                if isinstance(exc, PermissionError):
                    raise exc
                raise RuntimeError(f"BROWSER_NATIVE_START_FAILED: Failed to launch native browser: {exc}")
            else:
                log_error(
                    module="browser_manager",
                    action="launch_profile",
                    error_code="BROWSER_START_FAILED",
                    message=f"Failed to launch browser {profile_id} via VNC: {exc}",
                    profile_id=profile_id,
                )
                raise exc
            if display is not None:
                await self.vnc.stop_vnc(display)

    def _save_session_timestamp(self, profile_id: str):
        """Update last_session_save_at timestamp if session_auto_save is enabled."""
        try:
            profile = db.get_profile(profile_id)
            if profile and bool(profile.get("session_auto_save", True)):
                db.update_profile(profile_id, last_session_save_at=db._now())
        except Exception as e:
            logger.warning(f"Failed to update last_session_save_at for profile {profile_id}: {e}")

    async def _on_browser_closed(self, profile_id: str):
        """Called when browser exits (crash, user closed via VNC, or stop())."""
        async with self._lock:
            running = self.running.pop(profile_id, None)
            current_status = self.statuses.get(profile_id)
            if current_status in ("stopping", "crashed", "stopped"):
                return  # handled by stop() or crash watcher

        if running:
            # Reached if browser was closed externally (normal close by user or window closed)
            self._save_session_timestamp(profile_id)
            async with self._lock:
                self.statuses[profile_id] = "stopped"
            log_activity(
                module="browser_manager",
                action="browser_closed",
                status="success",
                message=f"Browser closed by user or externally for profile {profile_id}",
                profile_id=profile_id
            )
            if running.display is not None:
                await self.vnc.stop_vnc(running.display)

    async def stop(self, profile_id: str):
        """Stop a running browser instance."""
        if self.is_desktop:
            log_activity(
                module="browser_manager",
                action="stop_profile",
                status="BROWSER_NATIVE_STOP_REQUESTED",
                message=f"Stop requested for native profile {profile_id}",
                profile_id=profile_id,
            )

        async with self._lock:
            running = self.running.pop(profile_id, None)
            current_status = self.statuses.get(profile_id)
            if not running:
                if current_status == "starting":
                    self.statuses[profile_id] = "stopped"
                    log_activity("browser_manager", "stop_profile", "success", f"Cancelled starting profile {profile_id}", profile_id)
                elif self.is_desktop:
                    self.statuses[profile_id] = "stopped"
                    log_activity(
                        module="browser_manager",
                        action="stop_profile",
                        status="BROWSER_NATIVE_STOPPED",
                        message=f"Native profile {profile_id} was already stopped.",
                        profile_id=profile_id,
                    )
                return
            self.statuses[profile_id] = "stopping"

        if not self.is_desktop:
            log_activity("browser_manager", "stop_profile", "stopping", f"Stopping profile {profile_id}", profile_id)

        try:
            # 1. Resolve PID if not already done
            if running.pid is None:
                try:
                    import subprocess
                    out = subprocess.check_output(["pgrep", "-f", f"--remote-debugging-port={running.cdp_port}"])
                    lines = out.decode().strip().split('\n')
                    if lines and lines[0]:
                        running.pid = int(lines[0])
                except Exception:
                    pass

            # 2. Check if process exists/is alive
            process_alive = False
            if running.pid:
                try:
                    os.kill(running.pid, 0)
                    process_alive = True
                except OSError:
                    process_alive = False

            if running.pid and not process_alive:
                async with self._lock:
                    self.statuses[profile_id] = "stopped"
                if self.is_desktop:
                    log_activity(
                        module="browser_manager",
                        action="stop_profile",
                        status="BROWSER_NATIVE_STOPPED",
                        message=f"Process {running.pid} for profile {profile_id} is already dead.",
                        profile_id=profile_id,
                    )
                else:
                    log_activity("browser_manager", "stop_profile", "success", f"Process {running.pid} does not exist", profile_id)
                if running.display is not None:
                    await self.vnc.stop_vnc(running.display)
                return

            # 3. Try graceful stop
            graceful_success = False
            sent_sigterm = False
            if running.context is not None:
                try:
                    await asyncio.wait_for(running.context.close(), timeout=5.0)
                    graceful_success = True
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for context close on %s, forcing kill", profile_id)
                except Exception as exc:
                    exc_str = str(exc)
                    if any(msg in exc_str for msg in ("Connection closed", "Target closed", "Target page, context or browser has been closed", "Browser closed")):
                        logger.info("Browser context closed during shutdown for %s: %s", profile_id, exc_str)
                        graceful_success = True
                    else:
                        log_error("browser_manager", "stop_profile", f"Error closing context for {profile_id}: {exc}", profile_id)
            else:
                if running.pid:
                    try:
                        import platform
                        if platform.system() == "Windows":
                            import subprocess
                            subprocess.run(["taskkill", "/PID", str(running.pid)], capture_output=True, text=True)
                            sent_sigterm = True
                        else:
                            os.kill(running.pid, 15)  # SIGTERM
                            sent_sigterm = True
                        graceful_success = True
                    except OSError:
                        pass

            # 4. Wait 3-5 seconds (we will check for up to 4.0 seconds, checking every 0.2s)
            if graceful_success and running.pid:
                for _ in range(20):  # 20 * 0.2 = 4.0 seconds
                    try:
                        os.kill(running.pid, 0)
                        await asyncio.sleep(0.2)
                    except OSError:
                        process_alive = False
                        break

            # 5. Force kill if still alive
            if process_alive and running.pid:
                if self.is_desktop:
                    log_activity(
                        module="browser_manager",
                        action="stop_profile",
                        status="BROWSER_NATIVE_FORCE_KILLED",
                        message=f"Forcing kill on process {running.pid} for profile {profile_id}",
                        profile_id=profile_id,
                    )
                else:
                    logger.info("Forcing kill on process %d for profile %s", running.pid, profile_id)
                try:
                    import platform
                    if platform.system() == "Windows":
                        import subprocess
                        subprocess.run(["taskkill", "/F", "/PID", str(running.pid)], capture_output=True, text=True)
                    else:
                        os.kill(running.pid, 9)  # SIGKILL
                    # Wait briefly to let OS clean it up (up to 1.0 second)
                    for _ in range(10):
                        try:
                            os.kill(running.pid, 0)
                            await asyncio.sleep(0.1)
                        except OSError:
                            process_alive = False
                            break
                    # Reap to prevent zombies if it's a direct child
                    if platform.system() != "Windows":
                        try:
                            os.waitpid(running.pid, os.WNOHANG)
                        except ChildProcessError:
                            pass
                except OSError as e:
                    logger.warning("Failed to kill process %d: %s", running.pid, e)

            # 6. Fallback for non-PID cases or if still somehow alive
            if process_alive or not running.pid:
                import subprocess
                try:
                    subprocess.run(
                        ["pkill", "-f", f"--remote-debugging-port={running.cdp_port}"],
                        check=False
                    )
                    # Small sleep after fallback kill
                    await asyncio.sleep(0.5)
                except Exception as e:
                    log_error("browser_manager", "stop_profile", f"Error running pkill for {profile_id}: {e}", profile_id)

            if running.display is not None:
                await self.vnc.stop_vnc(running.display)

            # 7. Verify process liveness one last time
            still_alive = False
            if process_alive and running.pid:
                try:
                    os.kill(running.pid, 0)
                    still_alive = True
                except OSError:
                    still_alive = False

            if still_alive:
                async with self._lock:
                    self.statuses[profile_id] = "failed"
                if self.is_desktop:
                    log_error(
                        module="browser_manager",
                        action="stop_profile",
                        error_code="BROWSER_NATIVE_STOP_FAILED",
                        message=f"Failed to stop native profile {profile_id}. Process {running.pid} is still alive.",
                        profile_id=profile_id,
                    )
                else:
                    log_activity("browser_manager", "stop_profile", "failed", f"Failed to stop profile {profile_id}", profile_id)
                return

            self._save_session_timestamp(profile_id)
            async with self._lock:
                self.statuses[profile_id] = "stopped"

            if self.is_desktop:
                if sent_sigterm and not process_alive:
                    log_activity(
                        module="browser_manager",
                        action="stop_profile",
                        status="BROWSER_NATIVE_TERMINATED",
                        message=f"Successfully terminated native profile {profile_id} with SIGTERM/terminate",
                        profile_id=profile_id,
                    )
                log_activity(
                    module="browser_manager",
                    action="stop_profile",
                    status="BROWSER_NATIVE_STOPPED",
                    message=f"Successfully stopped native profile {profile_id}",
                    profile_id=profile_id,
                )
            else:
                log_activity("browser_manager", "stop_profile", "success", f"Successfully stopped profile {profile_id}", profile_id)

        except Exception as e:
            async with self._lock:
                self.statuses[profile_id] = "failed"
            if self.is_desktop:
                log_error(
                    module="browser_manager",
                    action="stop_profile",
                    error_code="BROWSER_NATIVE_STOP_FAILED",
                    message=f"Exception during stop for native profile {profile_id}: {e}",
                    profile_id=profile_id,
                )
            else:
                log_error("browser_manager", "stop_profile", "BROWSER_STOP_FAILED", f"Exception during stop for profile {profile_id}: {e}", profile_id)

    async def restart(self, profile: dict[str, Any]):
        """Restart a browser instance by stopping it fully and launching again."""
        profile_id = profile["id"]
        logger.info("Restarting profile %s", profile_id)
        
        await self.stop(profile_id)
        
        # Wait a moment for resources/files to be fully freed
        await asyncio.sleep(1.0)
        
        await self.launch(profile)
        
        if self.is_desktop:
            log_activity(
                module="browser_manager",
                action="restart_profile",
                status="BROWSER_NATIVE_RESTARTED",
                message=f"Successfully restarted native profile {profile_id}",
                profile_id=profile_id,
            )

    def get_status(self, profile_id: str) -> dict[str, Any]:
        """Get running status for a profile."""
        running = self.running.get(profile_id)
        current_status = self.statuses.get(profile_id, "running" if running else "stopped")
        
        if running:
            return {
                "status": current_status,
                "vnc_ws_port": running.ws_port,
                "display": f":{running.display}" if running.display is not None else None,
                "cdp_url": f"/api/profiles/{profile_id}/cdp",
            }
        return {"status": current_status, "vnc_ws_port": None, "display": None, "cdp_url": None}

    async def cleanup_all(self):
        """Stop all running profiles. Called on shutdown."""
        if getattr(self, "skip_cleanup", False):
            logger.info("Skipping profile cleanup on shutdown as requested.")
            return

        async with self._lock:
            profile_ids = list(self.running.keys())

        for pid in profile_ids:
            await self.stop(pid)

        if not self.is_desktop:
            await self.vnc.cleanup_all()

    async def cleanup_stale(self):
        """Kill orphan processes from previous container runs."""
        if not self.is_desktop:
            await self.vnc.cleanup_stale()

    async def auto_launch_all(self):
        """Launch all profiles with auto_launch=True. Called on startup."""
        try:
            from . import database as db
        except ImportError:
            import backend.database as db

        profiles = db.list_profiles()
        auto_profiles = [p for p in profiles if p.get("auto_launch")]
        if not auto_profiles:
            logger.info("No profiles configured for auto-launch")
            return

        logger.info("Auto-launching %d profile(s)...", len(auto_profiles))
        for profile in auto_profiles:
            try:
                await asyncio.wait_for(self.launch(profile), timeout=60)
                logger.info("Auto-launched profile %s (%s)", profile["name"], profile["id"])
            except Exception as exc:
                logger.error(
                    "Auto-launch failed for profile %s (%s): %s",
                    profile["name"], profile["id"], exc,
                )
        logger.info("Auto-launch complete: %d running", len(self.running))

    async def start_crash_watcher(self):
        """Watcher loop checking if running processes are still alive."""
        logger.info("Starting browser crash watcher...")
        while True:
            try:
                await asyncio.sleep(3.0)
                async with self._lock:
                    running_profiles = list(self.running.items())
                
                for profile_id, running in running_profiles:
                    # 1. If PID is not resolved yet, try resolving it
                    if running.pid is None:
                        try:
                            import subprocess
                            out = subprocess.check_output(["pgrep", "-f", f"--remote-debugging-port={running.cdp_port}"])
                            lines = out.decode().strip().split('\n')
                            if lines and lines[0]:
                                running.pid = int(lines[0])
                        except Exception:
                            pass
                    
                    # 2. Check if process is alive
                    alive = False
                    if running.pid is not None:
                        try:
                            os.kill(running.pid, 0)
                            alive = True
                        except OSError:
                            alive = False
                    else:
                        # Fallback: if we don't have PID, assume alive unless closed
                        alive = True

                    if not alive:
                        logger.error("Browser process (PID %s) died unexpectedly for profile %s", running.pid, profile_id)
                        # Mark as crashed and cleanup
                        asyncio.create_task(self._handle_crash(profile_id, running))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in crash watcher loop: %s", exc)

    async def _handle_crash(self, profile_id: str, running: RunningProfile):
        async with self._lock:
            # Check if it was already removed or status is stopping/stopped
            if profile_id not in self.running or self.statuses.get(profile_id) in ("stopping", "stopped"):
                return
            
            # Remove from running mapping
            self.running.pop(profile_id, None)
            self.statuses[profile_id] = "crashed"
            
        log_error(
            module="browser_manager",
            action="crash_watcher",
            error_code="BROWSER_CRASHED",
            message=f"Browser process (PID {running.pid}) for profile {profile_id} crashed or was killed abnormally.",
            profile_id=profile_id
        )
        
        # Cleanup VNC
        if running.display is not None:
            await self.vnc.stop_vnc(running.display)

    def _allocate_cdp_port(self) -> int:
        """Find a free CDP port using a rotating counter to avoid TIME_WAIT collisions."""
        for _ in range(CDP_PORT_RANGE):
            port = self._next_cdp_port
            self._next_cdp_port = BASE_CDP_PORT + (
                (self._next_cdp_port + 1 - BASE_CDP_PORT) % CDP_PORT_RANGE
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise ValueError("No free CDP ports available in range %d-%d" % (BASE_CDP_PORT, BASE_CDP_PORT + CDP_PORT_RANGE - 1))

    def _build_fingerprint_args(self, profile: dict[str, Any]) -> list[str]:
        """Build extra Chromium args from profile fingerprint settings."""
        args: list[str] = [
            "--disable-infobars",
            "--test-type",  # suppress "unsupported flag: --no-sandbox" bad flags warning
            "--use-angle=swiftshader",  # software GL for VNC (no GPU in container)
        ]

        seed = profile.get("fingerprint_seed")
        if seed is not None:
            args.append(f"--fingerprint={seed}")

        p = profile.get("platform")
        if p:
            # Map our "macos" to binary's "macos"
            args.append(f"--fingerprint-platform={p}")

        vendor = profile.get("gpu_vendor")
        if vendor:
            args.append(f"--fingerprint-gpu-vendor={vendor}")

        renderer = profile.get("gpu_renderer")
        if renderer:
            args.append(f"--fingerprint-gpu-renderer={renderer}")

        hw = profile.get("hardware_concurrency")
        if hw is not None:
            args.append(f"--fingerprint-hardware-concurrency={hw}")

        sw = profile.get("screen_width")
        sh = profile.get("screen_height")
        if sw:
            args.append(f"--fingerprint-screen-width={sw}")
        if sh:
            args.append(f"--fingerprint-screen-height={sh}")

        return args
