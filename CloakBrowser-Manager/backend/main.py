"""CloakBrowser Manager — FastAPI application.

Serves the React dashboard (static files) and provides a REST API
for browser profile management with live VNC viewing.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import os
import struct
import shutil
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import starlette.requests
from starlette.types import ASGIApp, Receive, Scope, Send

try:
    from . import database as db
    from .browser_manager import BrowserManager
    from .models import (
        ClipboardRequest,
        LaunchResponse,
        LoginRequest,
        ProfileCreate,
        ProfileResponse,
        ProfileStatusResponse,
        ProfileUpdate,
        ProxyCreate,
        ProxyResponse,
        ProxyUpdate,
        ProxyCheckResult,
        StatusResponse,
        TagResponse,
        DashboardSummary,
        BackupResponse,
        BackupCreateResponse,
        ProfileBackupResponse,
        RestoreRequest,
        ProfileRestoreRequest,
        RestoreResponse,
    )
    from .proxy_checker import check_proxy
    from .logger_utils import log_activity, log_error
except ImportError:
    import backend.database as db
    from backend.browser_manager import BrowserManager
    from backend.models import (
        ClipboardRequest,
        LaunchResponse,
        LoginRequest,
        ProfileCreate,
        ProfileResponse,
        ProfileStatusResponse,
        ProfileUpdate,
        ProxyCreate,
        ProxyResponse,
        ProxyUpdate,
        ProxyCheckResult,
        StatusResponse,
        TagResponse,
        DashboardSummary,
        BackupResponse,
        BackupCreateResponse,
        ProfileBackupResponse,
        RestoreRequest,
        ProfileRestoreRequest,
        RestoreResponse,
    )
    from backend.proxy_checker import check_proxy
    from backend.logger_utils import log_activity, log_error

logger = logging.getLogger("cloakbrowser.manager")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# Optional authentication via AUTH_TOKEN env var.
# If not set, all routes are open (local dev). If set, all /api/* routes
# (except /api/auth/* and /api/status) require Bearer token or cookie.
AUTH_TOKEN: str | None = os.environ.get("AUTH_TOKEN") or None

# Paths that bypass authentication even when AUTH_TOKEN is set
_AUTH_EXEMPT = frozenset({"/api/auth/status", "/api/auth/login", "/api/status"})


def _check_auth(scope: Scope) -> bool:
    """Check if the request has a valid auth token (header or cookie)."""
    # Check Authorization: Bearer <token> header
    for key, val in scope.get("headers", []):
        if key == b"authorization":
            auth_value = val.decode()
            if auth_value.startswith("Bearer "):
                token = auth_value[7:]
                if token and hmac.compare_digest(token, AUTH_TOKEN):
                    return True
            break

    # Check auth_token cookie
    for key, val in scope.get("headers", []):
        if key == b"cookie":
            cookies = SimpleCookie()
            cookies.load(val.decode())
            if "auth_token" in cookies:
                cookie_val = cookies["auth_token"].value
                if cookie_val and hmac.compare_digest(cookie_val, AUTH_TOKEN):
                    return True
            break

    return False


def _is_https(request: Request) -> bool:
    """Check if the original client connection was HTTPS (via reverse proxy header)."""
    proto = request.headers.get("x-forwarded-proto", "")
    return "https" in proto


async def _check_websocket_origin(websocket: WebSocket) -> bool:
    """Reject cross-origin WebSocket connections (CSWSH protection).

    Browsers always send an Origin header on WebSocket upgrades.
    Non-browser clients (Playwright, curl) typically don't — those are allowed.
    If Origin is present, its host must match the request Host header.
    """
    origin = None
    host = None
    for key, val in websocket.scope.get("headers", []):
        if key == b"origin":
            origin = val.decode("latin-1")
        elif key == b"host":
            host = val.decode("latin-1")

    # No Origin header → non-browser client (Playwright, Puppeteer) → allow
    if not origin:
        return True

    # Parse origin to extract host:port
    try:
        parsed = urlparse(origin)
        origin_host = parsed.hostname or ""
        origin_port = parsed.port
    except ValueError:
        logger.warning("WebSocket origin malformed: %s", origin)
        await websocket.close(code=4403, reason="Origin not allowed")
        return False
    # Build origin netloc (host:port or just host if default port)
    if origin_port and origin_port not in (80, 443):
        origin_netloc = f"{origin_host}:{origin_port}"
    else:
        origin_netloc = origin_host

    if not host:
        return True  # no Host header to compare against

    # Strip default port from Host too (some proxies send "example.com:443")
    host_normalized = host
    if host.endswith(":80") or host.endswith(":443"):
        host_normalized = host.rsplit(":", 1)[0]

    if origin_netloc == host_normalized:
        return True

    logger.warning("WebSocket origin mismatch: origin=%s host=%s", origin, host)
    await websocket.close(code=4403, reason="Origin not allowed")
    return False


class AuthMiddleware:
    """Raw ASGI middleware for optional token auth.

    Uses raw ASGI instead of BaseHTTPMiddleware because the latter
    breaks WebSocket routes (wraps request body, preventing WS upgrade).
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Pass through if auth disabled, or non-HTTP/WS scope (e.g. lifespan)
        if not AUTH_TOKEN or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Skip auth for exempt endpoints and non-API paths (static frontend)
        if path in _AUTH_EXEMPT or not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        if _check_auth(scope):
            await self.app(scope, receive, send)
            return

        # Reject — unauthenticated
        if scope["type"] == "websocket":
            # ASGI requires receiving websocket.connect before sending close
            await receive()
            await send({"type": "websocket.close", "code": 4401, "reason": "Unauthorized"})
        else:
            response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)


# Singleton browser manager
browser_mgr = BrowserManager()

# Frontend build directory (React production build)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


# ---------------------------------------------------------------------------
# RFB server message translator — KasmVNC BinaryClipboard → standard RFB
# ---------------------------------------------------------------------------


def _parse_kasmvnc_clipboard(data: bytes) -> str | None:
    """Extract text/plain from KasmVNC BinaryClipboard (type 180).

    Format: type(1) + action(1) + flags(4) + entries...
    Each entry: mime_len(u8) + mime(N) + data_len(u32 BE) + data(M)
    """
    if len(data) < 7:
        return None
    offset = 6  # skip type(1) + action(1) + flags(4)
    while offset < len(data):
        if offset + 1 > len(data):
            break
        mime_len = data[offset]
        offset += 1
        if offset + mime_len > len(data):
            break
        mime_type = data[offset:offset + mime_len]
        offset += mime_len
        if offset + 4 > len(data):
            break
        data_len = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        if mime_type == b"text/plain":
            end = min(offset + data_len, len(data))
            return data[offset:end].decode("utf-8", errors="replace")
        offset += data_len
    return None


def _build_server_cut_text(text: str) -> bytes:
    """Build standard RFB ServerCutText (type 3) message.

    RFB spec mandates Latin-1 encoding for ServerCutText.
    Characters outside Latin-1 (CJK, emoji, etc.) are replaced with '?'.
    """
    text_bytes = text.encode("latin-1", errors="replace")
    return struct.pack(">BxxxI", 3, len(text_bytes)) + text_bytes


# ---------------------------------------------------------------------------
# RFB client message filter — strip extension types KasmVNC doesn't support
# ---------------------------------------------------------------------------
# noVNC v1.4 batches multiple RFB messages into one WebSocket frame.
# KasmVNC 1.3.3 crashes on unsupported types (150, 248, etc.).
# We parse message boundaries using known sizes and keep only standard types.

# Client→server message sizes (fixed, except 2 and 6 which encode length)
_RFB_MSG_SIZE: dict[int, int | None] = {
    0: 20,    # SetPixelFormat
    2: None,  # SetEncodings — 4 + numEncodings*4 (rewritten to strip bad pseudo-encodings)
    3: 10,    # FramebufferUpdateRequest
    4: 8,     # KeyEvent
    5: 6,     # PointerEvent
    6: None,  # ClientCutText — 8 + length
}

# Extension types that noVNC sends — known sizes so we can skip past them
# instead of breaking and dropping all trailing data in the frame.
_RFB_EXTENSION_SIZE: dict[int, int] = {
    150: 10,  # EnableContinuousUpdates (1+1+2+2+2+2)
    248: 10,  # QEMU-like key event (observed from noVNC 1.4.0)
    252: 4,   # xvp (1+1+1+1)
    255: 4,   # QEMU audio control (1+1+2) — noVNC QEMUExtendedKeyEvent is actually 12
}

# Whitelist of encodings safe to send to KasmVNC.
# Instead of trying to blocklist problematic pseudo-encodings (error-prone —
# we had wrong numbers), we ONLY keep known-good encodings.
# Anything not on this list is stripped from SetEncodings.
_ALLOWED_ENCODINGS: set[int] = {
    # Framebuffer encodings (standard RFB)
    0,    # Raw
    1,    # CopyRect
    2,    # RRE
    5,    # Hextile
    7,    # Tight
    16,   # ZRLE
    # Safe pseudo-encodings
    -239,  # Cursor (0xFFFFFF11) — cursor shape
    -224,  # LastRect (0xFFFFFF20) — performance optimization
    # Tight quality/compress levels (these are just hints)
    *range(-32, -22),   # quality levels 0-9
    *range(-256, -246),  # compress levels 0-9
}


def _rfb_msg_length(data: bytes, offset: int) -> int | None:
    """Return total length of the RFB message at offset, or None if unrecognized."""
    if offset >= len(data):
        return None
    msg_type = data[offset]
    fixed = _RFB_MSG_SIZE.get(msg_type)
    if fixed is not None:
        return fixed
    remaining = len(data) - offset
    if msg_type == 2 and remaining >= 4:  # SetEncodings
        num_enc = struct.unpack_from(">H", data, offset + 2)[0]
        return 4 + num_enc * 4
    if msg_type == 6 and remaining >= 8:  # ClientCutText
        length = struct.unpack_from(">I", data, offset + 4)[0]
        return 8 + length
    # Known extension types — skip past them instead of giving up
    ext_size = _RFB_EXTENSION_SIZE.get(msg_type)
    if ext_size is not None:
        return ext_size
    return None  # truly unknown type


def _rewrite_set_encodings(data: bytes, offset: int, msg_len: int) -> bytes:
    """Keep only whitelisted encodings in a SetEncodings message."""
    _log = logging.getLogger("cloakbrowser.manager")
    num_enc = struct.unpack_from(">H", data, offset + 2)[0]
    kept = []
    stripped = []
    for i in range(num_enc):
        enc = struct.unpack_from(">i", data, offset + 4 + i * 4)[0]  # signed
        if enc in _ALLOWED_ENCODINGS:
            kept.append(enc)
        else:
            stripped.append(enc)
    if not stripped:
        return data[offset:offset + msg_len]
    _log.info("RFB filter: SetEncodings keeping %d: %s, stripped %d: %s", len(kept), kept, len(stripped), stripped)
    result = struct.pack(">BxH", 2, len(kept))
    for enc in kept:
        result += struct.pack(">i", enc)
    return result


def _rewrite_pointer_event(data: bytes, offset: int) -> bytes:
    """Convert standard 6-byte PointerEvent to KasmVNC's 11-byte format.

    Standard RFB:  [5:u8][mask:u8][x:u16][y:u16]          = 6 bytes
    KasmVNC:       [5:u8][mask:u16][x:u16][y:u16][sx:s16][sy:s16] = 11 bytes
    """
    mask = data[offset + 1]
    x = struct.unpack_from(">H", data, offset + 2)[0]
    y = struct.unpack_from(">H", data, offset + 4)[0]
    # Expand mask from u8 to u16.  Scroll deltas (sx, sy) are zero because
    # noVNC encodes scroll as button-mask bits (3=up, 4=down, 5=left, 6=right)
    # which pass through in the mask.  KasmVNC accepts mask-bit scroll on its
    # extended 11-byte format, so explicit deltas are unnecessary.
    return struct.pack(">BHHHhh", 5, mask, x, y, 0, 0)


def _filter_rfb_client_messages(data: bytes) -> bytes:
    """Parse concatenated RFB messages, keep only standard types (0-6).

    Rewrites PointerEvents from 6-byte standard to 11-byte KasmVNC format
    and strips unsupported pseudo-encodings from SetEncodings.
    """
    _log = logging.getLogger("cloakbrowser.manager")
    result = bytearray()
    offset = 0
    msg_idx = 0
    while offset < len(data):
        msg_type = data[offset]
        msg_len = _rfb_msg_length(data, offset)
        if msg_len is None:
            _log.info("RFB filter: DROPPING unknown type=%d at offset=%d/%d, skipping %d trailing bytes, hex=%s",
                       msg_type, offset, len(data), len(data) - offset, data[offset:offset+20].hex())
            break
        if offset + msg_len > len(data):
            # Incomplete message — DO NOT forward partial data, it desynchronizes
            # the RFB stream (KasmVNC buffers partial reads across frames).
            _log.warning("RFB filter: DROPPING incomplete type=%d need=%d have=%d — would desync stream",
                         msg_type, msg_len, len(data) - offset)
            break
        msg_idx += 1
        if msg_type in _RFB_MSG_SIZE:
            # Standard RFB type — keep (with rewrites for KasmVNC compatibility)
            _log.debug("RFB filter: KEEP type=%d len=%d at offset=%d (msg #%d in frame)", msg_type, msg_len, offset, msg_idx)
            if msg_type == 2:  # SetEncodings — whitelist safe encodings
                result.extend(_rewrite_set_encodings(data, offset, msg_len))
            elif msg_type == 5:  # PointerEvent — expand to KasmVNC's 11-byte format
                result.extend(_rewrite_pointer_event(data, offset))
            else:
                result.extend(data[offset:offset + msg_len])
        else:
            # Extension type (150, 248, etc.) — skip but continue parsing
            _log.debug("RFB filter: SKIP extension type=%d len=%d at offset=%d (msg #%d in frame)", msg_type, msg_len, offset, msg_idx)
        offset += msg_len
    if len(result) != len(data):
        _log.info("RFB filter: input=%d output=%d (delta %+d bytes)", len(data), len(result), len(result) - len(data))
    return bytes(result)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    await browser_mgr.cleanup_stale()
    browser_mgr._auto_launch_task = asyncio.create_task(browser_mgr.auto_launch_all())
    browser_mgr._crash_watcher_task = asyncio.create_task(browser_mgr.start_crash_watcher())
    logger.info("CloakBrowser Manager started")
    yield
    logger.info("Shutting down — stopping all browsers...")
    if browser_mgr._auto_launch_task and not browser_mgr._auto_launch_task.done():
        browser_mgr._auto_launch_task.cancel()
        await asyncio.gather(browser_mgr._auto_launch_task, return_exceptions=True)
    if hasattr(browser_mgr, "_crash_watcher_task") and browser_mgr._crash_watcher_task and not browser_mgr._crash_watcher_task.done():
        browser_mgr._crash_watcher_task.cancel()
        await asyncio.gather(browser_mgr._crash_watcher_task, return_exceptions=True)
    await browser_mgr.cleanup_all()


app = FastAPI(title="CloakBrowser Manager", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)


# ── Authentication ────────────────────────────────────────────────────────────


@app.get("/api/auth/status")
async def auth_status(request: starlette.requests.Request):
    """Check if auth is enabled and if the current request is authenticated.

    Exempt from auth middleware so the frontend can always call it.
    """
    authenticated = False
    if AUTH_TOKEN:
        authenticated = _check_auth(request.scope)
    return {"auth_required": AUTH_TOKEN is not None, "authenticated": authenticated}


@app.post("/api/auth/login")
async def auth_login(body: LoginRequest, request: Request, response: Response):
    if not AUTH_TOKEN:
        return {"ok": True}
    if not body.token or not hmac.compare_digest(body.token, AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid token")
    is_https = _is_https(request)
    response.set_cookie(
        key="auth_token",
        value=AUTH_TOKEN,
        httponly=True,
        samesite="strict",
        secure=is_https,
        path="/",
    )
    return {"ok": True}


@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    is_https = _is_https(request)
    response.delete_cookie(
        key="auth_token", path="/", secure=is_https, samesite="strict",
    )
    return {"ok": True}


# ── Profile CRUD ──────────────────────────────────────────────────────────────


@app.get("/api/profiles", response_model=list[ProfileResponse])
async def list_profiles():
    profiles = db.list_profiles()
    result = []
    for p in profiles:
        status = browser_mgr.get_status(p["id"])
        p["status"] = status["status"]
        p["vnc_ws_port"] = status["vnc_ws_port"]
        p["cdp_url"] = status["cdp_url"]
        p["tags"] = [TagResponse(**t) for t in p.get("tags", [])]
        result.append(ProfileResponse(**p))
    return result


@app.post("/api/profiles", response_model=ProfileResponse, status_code=201)
async def create_profile(req: ProfileCreate):
    if not req.name or not req.name.strip():
        logger.error("PROFILE_CREATE_FAILED: Name cannot be empty")
        raise HTTPException(status_code=400, detail={"error_code": "PROFILE_CREATE_FAILED", "message": "Name cannot be empty"})
    
    try:
        data = req.model_dump()
        tags = data.pop("tags", None)
        if tags:
            data["tags"] = [t.model_dump() if hasattr(t, "model_dump") else t for t in tags]
        else:
            data["tags"] = []
        profile = db.create_profile(**data)
        log_activity(
            module="main",
            action="create_profile",
            status="success",
            message=f"Created profile {profile['name']}",
            profile_id=profile["id"],
        )
        return ProfileResponse(**profile)
    except Exception as exc:
        log_error(
            module="main",
            action="create_profile",
            error_code="PROFILE_CREATE_FAILED",
            message=str(exc),
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROFILE_CREATE_FAILED", "message": str(exc)})


@app.get("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    status = browser_mgr.get_status(profile_id)
    profile["status"] = status["status"]
    profile["vnc_ws_port"] = status["vnc_ws_port"]
    profile["cdp_url"] = status["cdp_url"]
    profile["tags"] = [TagResponse(**t) for t in profile.get("tags", [])]
    return ProfileResponse(**profile)


@app.put("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: str, req: ProfileUpdate):
    if req.name is not None and not req.name.strip():
        logger.error("PROFILE_UPDATE_FAILED: Name cannot be empty")
        raise HTTPException(status_code=400, detail={"error_code": "PROFILE_UPDATE_FAILED", "message": "Name cannot be empty"})

    try:
        data = req.model_dump(exclude_unset=True)
        tags = data.pop("tags", None)
        if tags is not None:
            data["tags"] = [t.model_dump() if hasattr(t, "model_dump") else t for t in tags]
        profile = db.update_profile(profile_id, **data)
        if not profile:
            log_error(
                module="main",
                action="update_profile",
                error_code="PROFILE_UPDATE_FAILED",
                message="Profile not found",
                profile_id=profile_id,
            )
            raise HTTPException(status_code=404, detail={"error_code": "PROFILE_UPDATE_FAILED", "message": "Profile not found"})
        log_activity(
            module="main",
            action="update_profile",
            status="success",
            message=f"Updated profile {profile['name']}",
            profile_id=profile_id,
        )
        return ProfileResponse(**profile)
    except HTTPException:
        raise
    except Exception as exc:
        log_error(
            module="main",
            action="update_profile",
            error_code="PROFILE_UPDATE_FAILED",
            message=str(exc),
            profile_id=profile_id,
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROFILE_UPDATE_FAILED", "message": str(exc)})


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    current_status = browser_mgr.statuses.get(profile_id)
    if current_status in ("starting", "running", "stopping"):
        logger.warning("PROFILE_LOCKED: Cannot delete running profile %s", profile_id)
        raise HTTPException(status_code=409, detail={"error_code": "PROFILE_LOCKED", "message": "Cannot delete running profile"})

    try:
        profile = db.get_profile(profile_id)
        if not profile:
            log_error(
                module="main",
                action="delete_profile",
                error_code="PROFILE_DELETE_FAILED",
                message="Profile not found",
                profile_id=profile_id,
            )
            raise HTTPException(status_code=404, detail={"error_code": "PROFILE_DELETE_FAILED", "message": "Profile not found"})

        # Stop browser if running
        await browser_mgr.stop(profile_id)

        db.delete_profile(profile_id)
        log_activity(
            module="main",
            action="delete_profile",
            status="success",
            message="Profile deleted successfully",
            profile_id=profile_id,
        )
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        log_error(
            module="main",
            action="delete_profile",
            error_code="PROFILE_DELETE_FAILED",
            message=str(exc),
            profile_id=profile_id,
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROFILE_DELETE_FAILED", "message": str(exc)})


# ── Proxy CRUD ────────────────────────────────────────────────────────────────

def _mask_proxy(proxy: dict) -> dict:
    if proxy.get("password"):
        proxy["password"] = "***"
    return proxy


@app.get("/api/proxies", response_model=list[ProxyResponse])
async def list_proxies():
    proxies = db.list_proxies()
    return [_mask_proxy(p) for p in proxies]


@app.post("/api/proxies", response_model=ProxyResponse, status_code=201)
async def create_proxy(req: ProxyCreate):
    try:
        data = req.model_dump()
        proxy = db.create_proxy(**data)
        log_activity(
            module="main",
            action="create_proxy",
            status="success",
            message=f"Created proxy {proxy['name']}",
            proxy_id=proxy["id"],
        )
        return _mask_proxy(proxy)
    except Exception as exc:
        log_error(
            module="main",
            action="create_proxy",
            error_code="PROXY_CREATE_FAILED",
            message=str(exc),
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROXY_CREATE_FAILED", "message": str(exc)})


@app.get("/api/proxies/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(proxy_id: str):
    proxy = db.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return _mask_proxy(proxy)


@app.put("/api/proxies/{proxy_id}", response_model=ProxyResponse)
async def update_proxy_route(proxy_id: str, req: ProxyUpdate):
    try:
        data = req.model_dump(exclude_unset=True)
        # If frontend sends back "***" for password, do not update it
        if "password" in data and data["password"] == "***":
            data.pop("password")

        proxy = db.update_proxy(proxy_id, **data)
        if not proxy:
            log_error(
                module="main",
                action="update_proxy",
                error_code="PROXY_UPDATE_FAILED",
                message="Proxy not found",
                proxy_id=proxy_id,
            )
            raise HTTPException(status_code=404, detail={"error_code": "PROXY_UPDATE_FAILED", "message": "Proxy not found"})
        log_activity(
            module="main",
            action="update_proxy",
            status="success",
            message=f"Updated proxy {proxy['name']}",
            proxy_id=proxy_id,
        )
        return _mask_proxy(proxy)
    except HTTPException:
        raise
    except Exception as exc:
        log_error(
            module="main",
            action="update_proxy",
            error_code="PROXY_UPDATE_FAILED",
            message=str(exc),
            proxy_id=proxy_id,
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROXY_UPDATE_FAILED", "message": str(exc)})


@app.delete("/api/proxies/{proxy_id}")
async def delete_proxy_route(proxy_id: str):
    try:
        proxy = db.get_proxy(proxy_id)
        if not proxy:
            log_error(
                module="main",
                action="delete_proxy",
                error_code="PROXY_DELETE_FAILED",
                message="Proxy not found",
                proxy_id=proxy_id,
            )
            raise HTTPException(status_code=404, detail={"error_code": "PROXY_DELETE_FAILED", "message": "Proxy not found"})

        db.delete_proxy(proxy_id)
        log_activity(
            module="main",
            action="delete_proxy",
            status="success",
            message="Proxy deleted successfully",
            proxy_id=proxy_id,
        )
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        log_error(
            module="main",
            action="delete_proxy",
            error_code="PROXY_DELETE_FAILED",
            message=str(exc),
            proxy_id=proxy_id,
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROXY_DELETE_FAILED", "message": str(exc)})


@app.post("/api/proxies/{proxy_id}/check", response_model=ProxyCheckResult)
async def check_proxy_route(proxy_id: str):
    proxy = db.get_proxy(proxy_id)
    if not proxy:
        log_error(
            module="main",
            action="check_proxy",
            error_code="PROXY_CHECK_FAILED",
            message="Proxy not found",
            proxy_id=proxy_id,
        )
        raise HTTPException(status_code=404, detail={"error_code": "PROXY_CHECK_FAILED", "message": "Proxy not found"})

    result = await check_proxy(proxy)
    
    # Update database
    try:
        from .database import _now
    except ImportError:
        from backend.database import _now
    update_data = {
        "latency_ms": result["latency_ms"],
        "last_ip": result["last_ip"],
        "last_checked_at": _now()
    }
    if "timezone" in result and result["timezone"]:
        update_data["timezone"] = result["timezone"]
    if "locale" in result and result["locale"]:
        update_data["locale"] = result["locale"]
    
    updated_proxy = db.update_proxy(proxy_id, **update_data)
    if not updated_proxy:
        log_error(
            module="main",
            action="check_proxy",
            error_code="PROXY_CHECK_FAILED",
            message="Failed to update proxy record",
            proxy_id=proxy_id,
        )
        raise HTTPException(status_code=500, detail={"error_code": "PROXY_CHECK_FAILED", "message": "Failed to update proxy record"})
        
    log_activity(
        module="main",
        action="check_proxy",
        status="success" if result["status_code"] == "PROXY_OK" else "failed",
        message=f"Check result: {result['status_code']}",
        proxy_id=proxy_id,
        duration_ms=result["latency_ms"],
    )
    
    return {
        "status_code": result["status_code"],
        "proxy": _mask_proxy(updated_proxy)
    }

# ── Backups ───────────────────────────────────────────────────────────────────

@app.post("/api/backups", response_model=BackupCreateResponse, status_code=201)
async def create_backup():
    try:
        backup_path = db.backup_database()
        log_activity(
            module="main",
            action="create_backup",
            status="success",
            message=f"Database backed up to {Path(backup_path).name}"
        )
        return {"ok": True, "backup_path": backup_path}
    except Exception as exc:
        log_error(
            module="main",
            action="create_backup",
            error_code="BACKUP_FAILED",
            message=str(exc)
        )
        raise HTTPException(status_code=500, detail={"error_code": "BACKUP_FAILED", "message": str(exc)})

@app.get("/api/backups", response_model=list[BackupResponse])
async def list_backups():
    return db.list_backups()

@app.post("/api/backups/restore", response_model=RestoreResponse)
async def restore_database_route(req: RestoreRequest):
    # Stop all profiles before restoring database to avoid corruption
    await browser_mgr.cleanup_all()
    
    try:
        db.restore_database(req.backup_filename)
        # Integrity check: try to fetch profiles to ensure DB is readable
        db.list_profiles()
        
        log_activity(
            module="main",
            action="restore_database",
            status="success",
            message=f"Database restored from {req.backup_filename}"
        )
        return {"ok": True, "message": "Database restored and integrity checked."}
    except Exception as exc:
        log_error(
            module="main",
            action="restore_database",
            error_code="RESTORE_FAILED",
            message=str(exc)
        )
        raise HTTPException(status_code=500, detail={"error_code": "RESTORE_FAILED", "message": str(exc)})

@app.post("/api/profiles/{profile_id}/restore", response_model=RestoreResponse)
async def restore_profile_route(profile_id: str, req: ProfileRestoreRequest):
    # Safest approach is to stop all profiles before I/O heavy operations
    await browser_mgr.cleanup_all()
    
    try:
        db.restore_profile(profile_id, req.backup_filename)
        
        # Launch test
        profile = db.get_profile(profile_id)
        if profile:
            # We don't want to block the request on browser launch indefinitely, 
            # but we can try to start it and stop it as a quick integrity check.
            running = await browser_mgr.launch(profile)
            await asyncio.sleep(2) # Give it 2 seconds to initialize
            
            # Check if it didn't crash
            if browser_mgr.statuses.get(profile_id) == "running":
                await browser_mgr.stop(profile_id)
            else:
                raise RuntimeError("Profile crashed immediately after launch")
                
        log_activity(
            module="main",
            action="restore_profile",
            status="success",
            message=f"Profile {profile_id} restored from {req.backup_filename}",
            profile_id=profile_id
        )
        return {"ok": True, "message": f"Profile restored and successfully test launched."}
    except Exception as exc:
        log_error(
            module="main",
            action="restore_profile",
            error_code="RESTORE_FAILED",
            message=str(exc),
            profile_id=profile_id
        )
        raise HTTPException(status_code=500, detail={"error_code": "RESTORE_FAILED", "message": str(exc)})

@app.post("/api/profiles/{profile_id}/backup", response_model=ProfileBackupResponse, status_code=201)
async def backup_profile_folder(profile_id: str):
    # Check if profile is running
    status = browser_mgr.get_status(profile_id)["status"]
    if status in ("starting", "running", "stopping"):
        log_error(
            module="main",
            action="backup_profile",
            error_code="BACKUP_FAILED",
            message="Cannot backup profile while it is running. Please stop it first.",
            profile_id=profile_id
        )
        raise HTTPException(status_code=409, detail={"error_code": "BACKUP_FAILED", "message": "Cannot backup profile while it is running."})

    try:
        metadata = db.backup_profile(profile_id)
        log_activity(
            module="main",
            action="backup_profile",
            status="success",
            message=f"Profile backed up to {metadata['filename']}",
            profile_id=profile_id
        )
        return {"ok": True, "backup_path": str(metadata["path"]), "metadata": metadata}
    except Exception as exc:
        log_error(
            module="main",
            action="backup_profile",
            error_code="BACKUP_FAILED",
            message=str(exc),
            profile_id=profile_id
        )
        raise HTTPException(status_code=500, detail={"error_code": "BACKUP_FAILED", "message": str(exc)})


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/api/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary():
    profiles = db.list_profiles()
    total_profiles = len(profiles)
    
    running_profiles = 0
    stopped_profiles = 0
    failed_profiles = 0
    
    for p in profiles:
        status = browser_mgr.get_status(p["id"])["status"]
        if status in ("starting", "running"):
            running_profiles += 1
        elif status in ("failed", "crashed"):
            failed_profiles += 1
        else:
            stopped_profiles += 1

    proxies = db.list_proxies()
    total_proxies = len(proxies)
    
    ok_proxies = sum(1 for px in proxies if px.get("latency_ms") is not None and px.get("status") == "active")
    failed_proxies = sum(1 for px in proxies if px.get("status") == "active" and px.get("last_checked_at") is not None and px.get("latency_ms") is None)
    
    recent_errors = db.get_recent_errors(limit=10)
    
    max_allowed = int(os.environ.get("MAX_RUNNING_PROFILES", "5"))
    
    return {
        "total_profiles": total_profiles,
        "running_profiles": running_profiles,
        "stopped_profiles": stopped_profiles,
        "failed_profiles": failed_profiles,
        "total_proxies": total_proxies,
        "ok_proxies": ok_proxies,
        "failed_proxies": failed_proxies,
        "recent_errors": recent_errors,
        "max_running_profiles": max_allowed
    }


# ── Launch / Stop ─────────────────────────────────────────────────────────────

@app.post("/api/profiles/stop-all")
async def stop_all_profiles():
    # 1. Get all profiles currently running or starting
    to_stop = []
    for profile_id, status in list(browser_mgr.statuses.items()):
        if status in ("running", "starting"):
            to_stop.append(profile_id)
    
    total = len(to_stop)
    stopped = 0
    failed = 0
    
    log_activity(
        module="main",
        action="stop_all_profiles",
        status="info",
        message=f"Starting stop-all for {total} profiles"
    )
    
    for profile_id in to_stop:
        try:
            await browser_mgr.stop(profile_id)
            stopped += 1
        except Exception as exc:
            logger.error("Failed to stop profile %s during stop-all: %s", profile_id, exc)
            log_error(
                module="main",
                action="stop_all_profiles",
                error_code="PROFILE_STOP_FAILED",
                message=str(exc),
                profile_id=profile_id
            )
            failed += 1
            
    log_activity(
        module="main",
        action="stop_all_profiles",
        status="success",
        message=f"Stop all profiles summary: total={total}, stopped={stopped}, failed={failed}"
    )
    
    return {
        "ok": True,
        "total": total,
        "stopped": stopped,
        "failed": failed
    }


@app.post("/api/profiles/skip-cleanup")
async def skip_cleanup():
    browser_mgr.skip_cleanup = True
    logger.info("skip_cleanup flag set to True in browser_mgr")
    return {"ok": True}


@app.post("/api/profiles/{profile_id}/launch", response_model=LaunchResponse)
async def launch_profile(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    current_status = browser_mgr.statuses.get(profile_id)
    if profile_id in browser_mgr.running or current_status in ("starting", "running", "stopping"):
        raise HTTPException(status_code=409, detail={"error_code": "PROFILE_ALREADY_RUNNING", "message": f"Profile is already {current_status or 'running'}"})

    try:
        running = await browser_mgr.launch(profile)
    except FileNotFoundError as exc:
        err_msg = str(exc)
        if "CLOAK_BROWSER_BINARY_NOT_FOUND" in err_msg:
            clean_msg = err_msg.replace("CLOAK_BROWSER_BINARY_NOT_FOUND: ", "")
            raise HTTPException(status_code=400, detail={"error_code": "CLOAK_BROWSER_BINARY_NOT_FOUND", "message": clean_msg})
        elif "CLOAK_BROWSER_BINARY_NOT_CONFIGURED" in err_msg:
            clean_msg = err_msg.replace("CLOAK_BROWSER_BINARY_NOT_CONFIGURED: ", "")
            raise HTTPException(status_code=400, detail={"error_code": "CLOAK_BROWSER_BINARY_NOT_CONFIGURED", "message": clean_msg})
        raise HTTPException(status_code=500, detail="Failed to launch browser")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        err_msg = str(exc)
        if "RESOURCE_LIMIT_REACHED" in err_msg:
            clean_msg = err_msg.replace("RESOURCE_LIMIT_REACHED: ", "")
            raise HTTPException(status_code=409, detail={"error_code": "RESOURCE_LIMIT_REACHED", "message": clean_msg})
        elif "PROFILE_ALREADY_RUNNING" in err_msg:
            clean_msg = err_msg.replace("PROFILE_ALREADY_RUNNING: ", "")
            raise HTTPException(status_code=409, detail={"error_code": "PROFILE_ALREADY_RUNNING", "message": clean_msg})
        elif "BROWSER_NATIVE_START_FAILED" in err_msg:
            clean_msg = err_msg.replace("BROWSER_NATIVE_START_FAILED: ", "")
            raise HTTPException(status_code=500, detail={"error_code": "BROWSER_NATIVE_START_FAILED", "message": clean_msg})
        raise HTTPException(status_code=500, detail="Failed to launch browser")
    except Exception as exc:
        logger.error("Failed to launch profile %s: %s", profile_id, exc)
        raise HTTPException(status_code=500, detail="Failed to launch browser")

    db.set_last_launched(profile_id)

    return LaunchResponse(
        profile_id=profile_id,
        status="running",
        vnc_ws_port=running.ws_port,
        display=f":{running.display}" if running.display is not None else None,
        cdp_url=f"/api/profiles/{profile_id}/cdp",
    )


@app.post("/api/profiles/{profile_id}/stop")
async def stop_profile(profile_id: str):
    if profile_id not in browser_mgr.running:
        raise HTTPException(status_code=404, detail="Profile is not running")
    await browser_mgr.stop(profile_id)
    return {"ok": True}


@app.post("/api/profiles/{profile_id}/restart", response_model=LaunchResponse)
async def restart_profile(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Gracefully stop first
    await browser_mgr.stop(profile_id)
    
    # Launch again
    try:
        running = await browser_mgr.launch(profile)
    except FileNotFoundError as exc:
        err_msg = str(exc)
        if "CLOAK_BROWSER_BINARY_NOT_FOUND" in err_msg:
            clean_msg = err_msg.replace("CLOAK_BROWSER_BINARY_NOT_FOUND: ", "")
            raise HTTPException(status_code=400, detail={"error_code": "CLOAK_BROWSER_BINARY_NOT_FOUND", "message": clean_msg})
        elif "CLOAK_BROWSER_BINARY_NOT_CONFIGURED" in err_msg:
            clean_msg = err_msg.replace("CLOAK_BROWSER_BINARY_NOT_CONFIGURED: ", "")
            raise HTTPException(status_code=400, detail={"error_code": "CLOAK_BROWSER_BINARY_NOT_CONFIGURED", "message": clean_msg})
        raise HTTPException(status_code=500, detail="Failed to restart browser")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        err_msg = str(exc)
        if "RESOURCE_LIMIT_REACHED" in err_msg:
            clean_msg = err_msg.replace("RESOURCE_LIMIT_REACHED: ", "")
            raise HTTPException(status_code=409, detail={"error_code": "RESOURCE_LIMIT_REACHED", "message": clean_msg})
        elif "PROFILE_ALREADY_RUNNING" in err_msg:
            clean_msg = err_msg.replace("PROFILE_ALREADY_RUNNING: ", "")
            raise HTTPException(status_code=409, detail={"error_code": "PROFILE_ALREADY_RUNNING", "message": clean_msg})
        elif "BROWSER_NATIVE_START_FAILED" in err_msg:
            clean_msg = err_msg.replace("BROWSER_NATIVE_START_FAILED: ", "")
            raise HTTPException(status_code=500, detail={"error_code": "BROWSER_NATIVE_START_FAILED", "message": clean_msg})
        raise HTTPException(status_code=500, detail="Failed to restart browser")
    except Exception as exc:
        logger.error("Failed to restart profile %s: %s", profile_id, exc)
        raise HTTPException(status_code=500, detail="Failed to restart browser")

    db.set_last_launched(profile_id)

    return LaunchResponse(
        profile_id=profile_id,
        status="running",
        vnc_ws_port=running.ws_port,
        display=f":{running.display}" if running.display is not None else None,
        cdp_url=f"/api/profiles/{profile_id}/cdp",
    )


@app.get("/api/profiles/{profile_id}/status", response_model=ProfileStatusResponse)
async def get_profile_status(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    status = browser_mgr.get_status(profile_id)
    return ProfileStatusResponse(**status)


# ── System Status ─────────────────────────────────────────────────────────────


@app.get("/api/status", response_model=StatusResponse)
async def get_system_status():
    from cloakbrowser.config import CHROMIUM_VERSION

    profiles = db.list_profiles()
    return StatusResponse(
        running_count=len(browser_mgr.running),
        binary_version=CHROMIUM_VERSION,
        profiles_total=len(profiles),
        is_desktop=browser_mgr.is_desktop,
    )


@app.get("/api/status/binary")
async def get_binary_status_route():
    import platform
    from pathlib import Path
    import os
    import json

    binary_path = None
    path_configured = False

    # 1. Env overrides
    env_path = os.environ.get("CLOAK_BROWSER_BINARY_PATH") or os.environ.get("CLOAKBROWSER_BINARY_PATH")
    if env_path:
        binary_path = env_path
        path_configured = True

    # 2. Config
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
                except Exception:
                    pass

    # 3. macOS Auto-detect
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
            except Exception:
                pass

    # 4. Bundled
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

    # Determine status
    status = "Missing"
    if binary_path:
        p = Path(binary_path)
        if p.exists() and p.is_file():
            if platform.system() != "Windows":
                if os.access(binary_path, os.X_OK):
                    status = "Ready"
                else:
                    status = "Invalid"
            else:
                status = "Ready"
        else:
            status = "Invalid"

    return {
        "path": binary_path,
        "status": status,
        "is_desktop": browser_mgr.is_desktop,
    }


from pydantic import BaseModel

class BinaryPathUpdate(BaseModel):
    path: str


@app.post("/api/status/binary")
async def update_binary_status_route(body: BinaryPathUpdate):
    import platform
    from pathlib import Path
    import os
    import json

    data_dir = os.environ.get("CLOAK_DATA_DIR")
    if not data_dir:
        raise HTTPException(status_code=500, detail="CLOAK_DATA_DIR is not configured")

    binary_path = body.path
    p = Path(binary_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=400, detail={"error_code": "CLOAK_BROWSER_BINARY_NOT_FOUND", "message": "File does not exist"})

    if platform.system() != "Windows":
        if not os.access(binary_path, os.X_OK):
            try:
                os.chmod(binary_path, 0o755)
            except Exception:
                raise HTTPException(status_code=400, detail={"error_code": "CLOAK_BROWSER_BINARY_NOT_FOUND", "message": "File is not executable"})

    # Save to config
    config_dir = Path(data_dir) / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "app-config.json"
    
    config_data = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            pass

    config_data["cloakbrowser_binary_path"] = binary_path
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    # Update env in current process
    os.environ["CLOAKBROWSER_BINARY_PATH"] = binary_path

    return {"ok": True, "path": binary_path}


# ── Clipboard Relay ──────────────────────────────────────────────────────────

_CLIPBOARD_MAX_READ = 1_048_576  # 1MB cap on GET response

# Track xclip processes per display so we can kill the old one before spawning new
_xclip_procs: dict[int, asyncio.subprocess.Process] = {}


@app.post("/api/profiles/{profile_id}/clipboard")
async def set_clipboard(profile_id: str, body: ClipboardRequest):
    """Push text into the VNC session's X clipboard via xclip."""
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")

    if running.display is None:
        return {"ok": True}

    import os

    # Kill previous xclip for this display (it stays alive to serve paste)
    old = _xclip_procs.pop(running.display, None)
    if old and old.returncode is None:
        old.kill()
        await old.wait()

    env = {**os.environ, "DISPLAY": f":{running.display}"}
    proc = await asyncio.create_subprocess_exec(
        "xclip", "-selection", "clipboard",
        stdin=asyncio.subprocess.PIPE,
        env=env,
    )
    # xclip reads stdin then stays alive to serve paste requests.
    proc.stdin.write(body.text.encode())  # type: ignore[union-attr]
    await proc.stdin.drain()  # type: ignore[union-attr]
    proc.stdin.close()  # type: ignore[union-attr]

    _xclip_procs[running.display] = proc

    return {"ok": True}


@app.get("/api/profiles/{profile_id}/clipboard")
async def get_clipboard(profile_id: str):
    """Read the VNC session's clipboard.

    Chrome doesn't write to X11 clipboard under KasmVNC, so xclip can't read it.
    Instead, read via Playwright's CDP connection to Chrome (navigator.clipboard.readText).
    Falls back to xclip for non-Chrome clipboard owners.
    """
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")

    if running.display is None:
        return {"text": ""}

    # Read Chrome's current text selection via Playwright.
    # Chrome's native copy (via VNC Ctrl+C) doesn't write to X11 clipboard
    # and doesn't fire DOM events, so we read the visible selection instead.
    # The init script also captures copy events when they do fire.
    # Check all pages — user may have copied in any tab
    try:
        for page in running.context.pages:
            try:
                text = await page.evaluate("window.__clipboardText || ''")
                if text:
                    return {"text": text[:_CLIPBOARD_MAX_READ]}
            except Exception as exc:
                logger.debug("Clipboard read failed on page: %s", exc)
                continue
    except Exception as exc:
        logger.debug("Playwright clipboard read failed: %s", exc)

    # Fallback: xclip for non-Chrome clipboard owners
    import os

    env = {**os.environ, "DISPLAY": f":{running.display}"}
    proc = await asyncio.create_subprocess_exec(
        "xclip", "-selection", "clipboard", "-o",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"text": ""}

    if proc.returncode != 0:
        return {"text": ""}

    text = stdout[:_CLIPBOARD_MAX_READ].decode("utf-8", errors="replace")
    return {"text": text}


# ── VNC WebSocket Proxy ──────────────────────────────────────────────────────


@app.websocket("/api/profiles/{profile_id}/vnc")
async def vnc_proxy(websocket: WebSocket, profile_id: str):
    """Proxy WebSocket frames between the frontend and a profile's KasmVNC."""
    if not await _check_websocket_origin(websocket):
        return

    running = browser_mgr.running.get(profile_id)
    if not running:
        await websocket.close(code=4004, reason="Profile not running")
        return

    if running.display is None or running.ws_port is None:
        await websocket.close(code=4004, reason="VNC not available in native desktop mode")
        return

    # Accept with client's requested subprotocol (if any) — RFC 6455 requires
    # the server must not respond with a subprotocol the client didn't request.
    requested = websocket.scope.get("subprotocols", [])
    subprotocol = "binary" if "binary" in requested else None
    await websocket.accept(subprotocol=subprotocol)

    import websockets

    vnc_url = f"ws://127.0.0.1:{running.ws_port}/websockify"

    try:
        async with websockets.connect(
            vnc_url,
            subprotocols=["binary"],
            origin=f"http://127.0.0.1:{running.ws_port}",
            max_size=None,  # VNC frames can be large (1920x1080 framebuffer)
            ping_interval=None,  # KasmVNC doesn't respond to WS pings
            ping_timeout=None,
            compression=None,  # KasmVNC can't handle permessage-deflate
        ) as vnc_ws:
            logger.info(
                "VNC proxy: connected to KasmVNC for %s (subprotocol=%s)",
                profile_id, vnc_ws.subprotocol,
            )

            # noVNC v1.4 sends extension message types (150=ContinuousUpdates,
            # 248=QEMUKey, etc.) that KasmVNC 1.3.3 doesn't support, causing
            # "unknown message type" → disconnect.
            #
            # noVNC batches multiple RFB messages into a single WebSocket frame,
            # so we must parse the RFB stream to find message boundaries and strip
            # unsupported types before forwarding. Standard client→server types
            # have known fixed sizes (except SetEncodings and ClientCutText which
            # encode their length).

            async def client_to_vnc():
                count = 0
                handshake = 0  # first 3 messages are RFB handshake
                dropped = 0
                try:
                    while True:
                        msg = await websocket.receive()
                        msg_type = msg.get("type", "")
                        if msg_type == "websocket.disconnect":
                            logger.info("VNC proxy [c->v]: client disconnect (code=%s) after %d msgs (%d dropped)", msg.get("code"), count, dropped)
                            break
                        if "bytes" in msg and msg["bytes"]:
                            count += 1
                            data = msg["bytes"]
                            handshake += 1

                            # First 3 messages are RFB handshake — forward as-is
                            if handshake <= 3:
                                logger.debug("VNC handshake #%d: %d bytes hex=%s", handshake, len(data), data[:20].hex())
                                await vnc_ws.send(data)
                                continue

                            # Parse RFB messages and strip unsupported types
                            filtered = _filter_rfb_client_messages(data)
                            if filtered:
                                # Safety: verify first byte is a valid RFB client type
                                if filtered[0] not in _RFB_MSG_SIZE:
                                    logger.error("RFB SAFETY: refusing to send data with invalid first byte=%d hex=%s",
                                                 filtered[0], filtered[:20].hex())
                                    dropped += 1
                                    continue
                                logger.debug("VNC send: %d bytes first_type=%d hex=%s", len(filtered), filtered[0], filtered[:100].hex())
                                await vnc_ws.send(filtered)
                            else:
                                dropped += 1

                        elif "text" in msg and msg["text"]:
                            # noVNC only sends binary frames — text frames are unexpected
                            # and would bypass the RFB filter, so drop them.
                            count += 1
                            logger.warning("VNC proxy [c->v]: DROPPING text frame len=%d (noVNC should only send binary)", len(msg["text"]))
                            dropped += 1
                        else:
                            logger.warning("VNC proxy [c->v]: unhandled msg keys=%s type=%s", list(msg.keys()), msg_type)
                except WebSocketDisconnect as exc:
                    logger.info("VNC proxy [c->v]: WebSocketDisconnect code=%s after %d msgs (%d dropped)", exc.code, count, dropped)
                except Exception as exc:
                    logger.warning("VNC proxy [c->v]: %s: %s (after %d msgs)", type(exc).__name__, exc, count)

            async def vnc_to_client():
                count = 0
                try:
                    async for msg in vnc_ws:
                        count += 1
                        if isinstance(msg, bytes) and len(msg) > 0:
                            msg_type = msg[0]
                            if msg_type == 180:
                                # KasmVNC BinaryClipboard → convert to standard
                                # ServerCutText (type 3) so noVNC can handle it
                                text = _parse_kasmvnc_clipboard(msg)
                                if text:
                                    logger.info("VNC proxy [v->c]: clipboard %d chars", len(text))
                                    await websocket.send_bytes(_build_server_cut_text(text))
                                else:
                                    logger.info("VNC proxy [v->c]: dropped type 180 (no text/plain)")
                                continue
                            await websocket.send_bytes(msg)
                        elif isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                    logger.info("VNC proxy [v->c]: KasmVNC stream ended after %d msgs (close_code=%s)", count, vnc_ws.close_code)
                except WebSocketDisconnect as exc:
                    logger.info("VNC proxy [v->c]: client disconnect code=%s after %d msgs", exc.code, count)
                except Exception as exc:
                    logger.warning("VNC proxy [v->c]: %s: %s (after %d msgs)", type(exc).__name__, exc, count)

            c2v = asyncio.create_task(client_to_vnc(), name="c2v")
            v2c = asyncio.create_task(vnc_to_client(), name="v2c")

            done, pending = await asyncio.wait(
                [c2v, v2c],
                return_when=asyncio.FIRST_COMPLETED,
            )
            finished = [t.get_name() for t in done]
            still_running = [t.get_name() for t in pending]

            # Check if Xvnc is still alive
            vnc_instance = browser_mgr.vnc._allocated.get(running.display)
            xvnc_alive = vnc_instance and vnc_instance.process and vnc_instance.process.poll() is None
            logger.info(
                "VNC proxy: finished=%s pending=%s xvnc_alive=%s display=:%d for %s",
                finished, still_running, xvnc_alive, running.display, profile_id,
            )

            # Dump Xvnc log on disconnect
            import os
            xvnc_log = f"/tmp/xvnc-{running.display}.log"
            if os.path.exists(xvnc_log):
                with open(xvnc_log) as f:
                    log_content = f.read()
                if log_content.strip():
                    for line in log_content.strip().split("\n")[-20:]:
                        logger.info("Xvnc[:%d] %s", running.display, line)

            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.error("VNC_CONNECT_FAILED for profile %s: %s: %s", profile_id, type(exc).__name__, exc)
    finally:
        try:
            await websocket.close()
        except Exception as exc:
            logger.debug("VNC proxy: websocket.close() failed: %s", exc)


# ── CDP WebSocket Proxy ──────────────────────────────────────────────────────
# Simple bidirectional passthrough — CDP is standard JSON over WebSocket,
# no protocol translation needed (unlike VNC which requires RFB filtering).


@app.get("/api/profiles/{profile_id}/cdp")
async def cdp_info(profile_id: str):
    """Return CDP connection info. Prevents SPA catch-all from serving index.html."""
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")
    return {
        "cdp_url": f"/api/profiles/{profile_id}/cdp",
        "usage": "playwright.chromium.connect_over_cdp('http://<host>/api/profiles/"
        + profile_id + "/cdp')",
    }


@app.get("/api/profiles/{profile_id}/cdp/json/version/")
@app.get("/api/profiles/{profile_id}/cdp/json/version")
async def cdp_json_version(profile_id: str, request: Request):
    """Proxy Chrome's /json/version, rewriting WS URLs to go through our proxy."""
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://127.0.0.1:{running.cdp_port}/json/version", timeout=5
            )
            data = resp.json()
    except Exception as exc:
        logger.error("CDP proxy: failed to reach Chrome CDP for %s: %s", profile_id, exc)
        raise HTTPException(status_code=502, detail="CDP endpoint unreachable")

    # Rewrite webSocketDebuggerUrl to point through our proxy
    host = request.headers.get("host", "localhost:8080")
    ws_scheme = "wss" if _is_https(request) else "ws"
    data["webSocketDebuggerUrl"] = f"{ws_scheme}://{host}/api/profiles/{profile_id}/cdp"
    return data


@app.get("/api/profiles/{profile_id}/cdp/json/list/")
@app.get("/api/profiles/{profile_id}/cdp/json/list")
@app.get("/api/profiles/{profile_id}/cdp/json/")
@app.get("/api/profiles/{profile_id}/cdp/json")
async def cdp_json_list(profile_id: str, request: Request):
    """Proxy Chrome's /json/list, rewriting WS URLs."""
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://127.0.0.1:{running.cdp_port}/json/list", timeout=5
            )
            data = resp.json()
    except Exception as exc:
        logger.error("CDP proxy: failed to reach Chrome CDP for %s: %s", profile_id, exc)
        raise HTTPException(status_code=502, detail="CDP endpoint unreachable")

    host = request.headers.get("host", "localhost:8080")
    ws_scheme = "wss" if _is_https(request) else "ws"
    for entry in data:
        if "webSocketDebuggerUrl" in entry:
            ws_path = entry["webSocketDebuggerUrl"].split("/devtools/")[-1]
            entry["webSocketDebuggerUrl"] = (
                f"{ws_scheme}://{host}/api/profiles/{profile_id}/cdp/devtools/{ws_path}"
            )
    return data


async def _proxy_cdp_websocket(
    websocket: WebSocket, target_url: str, label: str,
) -> None:
    """Bidirectional WebSocket proxy between a FastAPI client and a CDP target.

    Used by both browser-level and page-level CDP proxy endpoints.
    """
    import websockets

    try:
        async with websockets.connect(
            target_url, max_size=None, ping_interval=None, ping_timeout=None
        ) as cdp_ws:
            logger.info("%s: connected to %s", label, target_url)

            async def client_to_cdp():
                try:
                    while True:
                        msg = await websocket.receive()
                        if msg.get("type") == "websocket.disconnect":
                            break
                        if "text" in msg and msg["text"]:
                            await cdp_ws.send(msg["text"])
                        elif "bytes" in msg and msg["bytes"]:
                            await cdp_ws.send(msg["bytes"])
                except WebSocketDisconnect:
                    pass
                except Exception as exc:
                    logger.warning("%s [c->cdp]: %s: %s", label, type(exc).__name__, exc)

            async def cdp_to_client():
                try:
                    async for msg in cdp_ws:
                        if isinstance(msg, str):
                            await websocket.send_text(msg)
                        else:
                            await websocket.send_bytes(msg)
                except WebSocketDisconnect:
                    pass
                except Exception as exc:
                    logger.warning("%s [cdp->c]: %s: %s", label, type(exc).__name__, exc)

            c2d = asyncio.create_task(client_to_cdp(), name="c2d")
            d2c = asyncio.create_task(cdp_to_client(), name="d2c")
            done, pending = await asyncio.wait(
                [c2d, d2c], return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            logger.info("%s: disconnected", label)

    except Exception as exc:
        logger.error("CDP_CONNECT_FAILED: %s error: %s", label, exc)
    finally:
        try:
            await websocket.close()
        except Exception as exc:
            logger.debug("%s: websocket.close() failed: %s", label, exc)


@app.websocket("/api/profiles/{profile_id}/cdp")
async def cdp_proxy(websocket: WebSocket, profile_id: str):
    """Proxy WebSocket frames between external tools and Chrome's CDP."""
    if not await _check_websocket_origin(websocket):
        return

    running = browser_mgr.running.get(profile_id)
    if not running:
        await websocket.close(code=4004, reason="Profile not running")
        return

    await websocket.accept()

    # Get browser-level CDP WebSocket URL from Chrome
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://127.0.0.1:{running.cdp_port}/json/version", timeout=5
            )
            ws_url = resp.json()["webSocketDebuggerUrl"]
    except Exception as exc:
        logger.error("CDP_CONNECT_FAILED: failed to get WS URL for %s: %s", profile_id, exc)
        await websocket.close(code=4005, reason="CDP not available")
        return

    await _proxy_cdp_websocket(websocket, ws_url, f"CDP proxy [{profile_id}]")


@app.websocket("/api/profiles/{profile_id}/cdp/devtools/{path:path}")
async def cdp_page_proxy(websocket: WebSocket, profile_id: str, path: str):
    """Proxy page-specific CDP WebSocket connections (e.g. /devtools/page/GUID)."""
    if not await _check_websocket_origin(websocket):
        return

    running = browser_mgr.running.get(profile_id)
    if not running:
        await websocket.close(code=4004, reason="Profile not running")
        return

    await websocket.accept()

    target_url = f"ws://127.0.0.1:{running.cdp_port}/devtools/{path}"
    await _proxy_cdp_websocket(websocket, target_url, f"CDP page proxy [{profile_id}]")


# ── Static Frontend ───────────────────────────────────────────────────────────

# Serve React build. Must be AFTER API routes so /api/* isn't caught by the SPA.
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="CloakBrowser Manager Backend")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
