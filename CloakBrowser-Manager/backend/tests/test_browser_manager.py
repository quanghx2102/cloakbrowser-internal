"""Tests for browser_manager pure functions — proxy parsing, fingerprint args, profile defaults."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import socket
from unittest.mock import patch

from backend.browser_manager import (
    BASE_CDP_PORT,
    CDP_PORT_RANGE,
    _init_profile_defaults,
    _normalize_proxy,
    _validate_proxy,
    BrowserManager,
)


# ── _normalize_proxy ─────────────────────────────────────────────────────────


def test_normalize_already_http():
    assert _normalize_proxy("http://user:pass@host:8080") == "http://user:pass@host:8080"


def test_normalize_already_https():
    assert _normalize_proxy("https://host:443") == "https://host:443"


def test_normalize_already_socks5():
    assert _normalize_proxy("socks5://host:1080") == "socks5://host:1080"


def test_normalize_host_port_user_pass():
    assert _normalize_proxy("proxy.com:8080:myuser:mypass") == "http://myuser:mypass@proxy.com:8080"


def test_normalize_host_port_only():
    assert _normalize_proxy("proxy.com:8080") == "http://proxy.com:8080"


def test_normalize_three_parts():
    # 3 parts doesn't match any pattern — returned as-is
    assert _normalize_proxy("a:b:c") == "a:b:c"


def test_normalize_five_parts():
    # 5 parts doesn't match — returned as-is
    assert _normalize_proxy("a:b:c:d:e") == "a:b:c:d:e"


def test_normalize_empty_parts():
    # host:port:user:pass with empty parts
    result = _normalize_proxy(":8080:user:pass")
    assert result == "http://user:pass@:8080"


# ── _validate_proxy ──────────────────────────────────────────────────────────


def test_validate_valid_http():
    _validate_proxy("http://proxy.com:8080")  # should not raise


def test_validate_valid_socks5():
    _validate_proxy("socks5://proxy.com:1080")  # should not raise


def test_validate_valid_with_auth():
    _validate_proxy("http://user:pass@proxy.com:8080")  # should not raise


def test_validate_bad_scheme():
    with pytest.raises(ValueError, match="Invalid proxy scheme 'ftp'"):
        _validate_proxy("ftp://host:80")


def test_validate_no_hostname():
    with pytest.raises(ValueError, match="missing hostname"):
        _validate_proxy("http://:8080")


def test_validate_no_port():
    with pytest.raises(ValueError, match="missing port"):
        _validate_proxy("http://host")


# ── _build_fingerprint_args ──────────────────────────────────────────────────

# Use the BrowserManager instance to call the method
_mgr = BrowserManager()


def test_build_args_always_includes_base():
    args = _mgr._build_fingerprint_args({})
    assert "--disable-infobars" in args
    assert "--test-type" in args
    assert "--use-angle=swiftshader" in args


def test_build_args_seed():
    args = _mgr._build_fingerprint_args({"fingerprint_seed": 42})
    assert "--fingerprint=42" in args


def test_build_args_no_seed():
    args = _mgr._build_fingerprint_args({"fingerprint_seed": None})
    assert not any(a.startswith("--fingerprint=") for a in args)


def test_build_args_platform():
    args = _mgr._build_fingerprint_args({"platform": "macos"})
    assert "--fingerprint-platform=macos" in args


def test_build_args_gpu():
    args = _mgr._build_fingerprint_args({
        "gpu_vendor": "NVIDIA Corporation",
        "gpu_renderer": "NVIDIA GeForce RTX 3070",
    })
    assert "--fingerprint-gpu-vendor=NVIDIA Corporation" in args
    assert "--fingerprint-gpu-renderer=NVIDIA GeForce RTX 3070" in args


def test_build_args_hardware_concurrency():
    args = _mgr._build_fingerprint_args({"hardware_concurrency": 8})
    assert "--fingerprint-hardware-concurrency=8" in args


def test_build_args_screen():
    args = _mgr._build_fingerprint_args({"screen_width": 2560, "screen_height": 1440})
    assert "--fingerprint-screen-width=2560" in args
    assert "--fingerprint-screen-height=1440" in args


def test_build_args_empty_profile():
    args = _mgr._build_fingerprint_args({})
    # Only the 3 base args
    assert len(args) == 3


# ── launch_args appended to extra_args ────────────────────────────────────────


def test_launch_args_appended_to_fingerprint_args():
    """launch_args from profile should appear in the args list after fingerprint args."""
    profile = {
        "fingerprint_seed": 42,
        "platform": "windows",
        "launch_args": ["--load-extension=/tmp/ext", "--disable-features=Foo"],
    }
    args = _mgr._build_fingerprint_args(profile)
    args += profile.get("launch_args") or []
    assert "--load-extension=/tmp/ext" in args
    assert "--disable-features=Foo" in args
    # Fingerprint args still present
    assert "--fingerprint=42" in args


def test_launch_args_empty_no_effect():
    profile = {"launch_args": []}
    args = _mgr._build_fingerprint_args(profile)
    base_count = len(args)
    args += profile.get("launch_args") or []
    assert len(args) == base_count


def test_launch_args_none_no_effect():
    profile = {"launch_args": None}
    args = _mgr._build_fingerprint_args(profile)
    base_count = len(args)
    args += profile.get("launch_args") or []
    assert len(args) == base_count


# ── _allocate_cdp_port ───────────────────────────────────────────────────────


def test_allocate_cdp_port_returns_free_port():
    mgr = BrowserManager()
    port = mgr._allocate_cdp_port()
    assert BASE_CDP_PORT <= port < BASE_CDP_PORT + CDP_PORT_RANGE


def test_allocate_cdp_port_skips_occupied():
    mgr = BrowserManager()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", BASE_CDP_PORT))
        blocker.listen(1)
        port = mgr._allocate_cdp_port()
        assert port == BASE_CDP_PORT + 1


def test_allocate_cdp_port_advances_counter():
    mgr = BrowserManager()
    p1 = mgr._allocate_cdp_port()
    p2 = mgr._allocate_cdp_port()
    assert p2 == p1 + 1


def test_allocate_cdp_port_wraps_around():
    mgr = BrowserManager()
    mgr._next_cdp_port = BASE_CDP_PORT + CDP_PORT_RANGE - 1
    p1 = mgr._allocate_cdp_port()
    assert p1 == BASE_CDP_PORT + CDP_PORT_RANGE - 1
    p2 = mgr._allocate_cdp_port()
    assert p2 == BASE_CDP_PORT


def test_allocate_cdp_port_all_occupied_raises():
    mgr = BrowserManager()
    blockers = []
    try:
        for i in range(CDP_PORT_RANGE):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", BASE_CDP_PORT + i))
            s.listen(1)
            blockers.append(s)
        with pytest.raises(ValueError, match="No free CDP ports"):
            mgr._allocate_cdp_port()
    finally:
        for s in blockers:
            s.close()


# ── _init_profile_defaults ───────────────────────────────────────────────────


def test_init_creates_bookmarks(tmp_path: Path):
    _init_profile_defaults(tmp_path)
    bookmarks_path = tmp_path / "Default" / "Bookmarks"
    assert bookmarks_path.exists()
    data = json.loads(bookmarks_path.read_text())
    children = data["roots"]["bookmark_bar"]["children"]
    assert len(children) == 4  # 4 folders
    folder_names = {f["name"] for f in children}
    assert folder_names == {"Detection Tests", "Fingerprint", "Headers & TLS", "reCAPTCHA"}


def test_init_creates_preferences(tmp_path: Path):
    _init_profile_defaults(tmp_path)
    prefs_path = tmp_path / "Default" / "Preferences"
    assert prefs_path.exists()
    data = json.loads(prefs_path.read_text())
    assert "default_search_provider_data" in data
    assert "DuckDuckGo" in data["default_search_provider_data"]["template_url_data"]["short_name"]


def test_init_idempotent(tmp_path: Path):
    _init_profile_defaults(tmp_path)
    bookmarks_path = tmp_path / "Default" / "Bookmarks"
    original = bookmarks_path.read_text()

    # Write a sentinel to the file
    bookmarks_path.write_text("SENTINEL")

    # Second call should NOT overwrite (file already exists)
    _init_profile_defaults(tmp_path)
    assert bookmarks_path.read_text() == "SENTINEL"


# ── Desktop native launch tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_launch_already_running_raises_profile_already_running():
    mgr = BrowserManager()
    mgr.statuses["profile1"] = "running"
    
    with patch("backend.browser_manager.log_error") as mock_log_error:
        with pytest.raises(RuntimeError, match="Profile profile1 is already running"):
            await mgr.launch({"id": "profile1"})
        
        mock_log_error.assert_called_once_with(
            module="browser_manager",
            action="launch_profile",
            error_code="PROFILE_ALREADY_RUNNING",
            message="Profile profile1 is already running",
            profile_id="profile1"
        )


# ── Desktop native stop/restart tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_graceful_success():
    from backend.browser_manager import RunningProfile
    from unittest.mock import AsyncMock, MagicMock

    mgr = BrowserManager()
    mgr.is_desktop = True
    
    mock_context = AsyncMock()
    running = RunningProfile(
        profile_id="profile1",
        context=mock_context,
        display=None,
        ws_port=None,
        cdp_port=5100,
        pid=12345
    )
    mgr.running["profile1"] = running
    mgr.statuses["profile1"] = "running"

    with patch("os.kill") as mock_kill, patch("backend.browser_manager.log_activity") as mock_log:
        # First call to os.kill(12345, 0) returns True (alive)
        # Second call to check if dead returns OSError (dead)
        mock_kill.side_effect = [None, OSError("No process")]
        
        await mgr.stop("profile1")
        
        mock_context.close.assert_awaited_once()
        assert mgr.statuses["profile1"] == "stopped"
        
        # Check BROWSER_NATIVE_STOP_REQUESTED was logged
        mock_log.assert_any_call(
            module="browser_manager",
            action="stop_profile",
            status="BROWSER_NATIVE_STOP_REQUESTED",
            message="Stop requested for native profile profile1",
            profile_id="profile1"
        )
        # Check BROWSER_NATIVE_STOPPED was logged
        mock_log.assert_any_call(
            module="browser_manager",
            action="stop_profile",
            status="BROWSER_NATIVE_STOPPED",
            message="Successfully stopped native profile profile1",
            profile_id="profile1"
        )


@pytest.mark.asyncio
async def test_stop_process_non_existent():
    from backend.browser_manager import RunningProfile
    from unittest.mock import AsyncMock

    mgr = BrowserManager()
    mgr.is_desktop = True
    
    mock_context = AsyncMock()
    running = RunningProfile(
        profile_id="profile1",
        context=mock_context,
        display=None,
        ws_port=None,
        cdp_port=5100,
        pid=12345
    )
    mgr.running["profile1"] = running
    mgr.statuses["profile1"] = "running"

    with patch("os.kill") as mock_kill, patch("backend.browser_manager.log_activity") as mock_log:
        # os.kill(12345, 0) raises OSError (process does not exist)
        mock_kill.side_effect = OSError("ESRCH")
        
        await mgr.stop("profile1")
        
        # Context close should NOT be called because process is already dead
        mock_context.close.assert_not_called()
        assert mgr.statuses["profile1"] == "stopped"
        
        mock_log.assert_any_call(
            module="browser_manager",
            action="stop_profile",
            status="BROWSER_NATIVE_STOPPED",
            message="Process 12345 for profile profile1 is already dead.",
            profile_id="profile1"
        )


@pytest.mark.asyncio
async def test_stop_timeout_force_kill():
    from backend.browser_manager import RunningProfile
    from unittest.mock import AsyncMock
    import asyncio

    mgr = BrowserManager()
    mgr.is_desktop = True
    
    mock_context = AsyncMock()
    # Mock close() to timeout
    async def slow_close():
        await asyncio.sleep(10)
    mock_context.close.side_effect = slow_close

    running = RunningProfile(
        profile_id="profile1",
        context=mock_context,
        display=None,
        ws_port=None,
        cdp_port=5100,
        pid=12345
    )
    mgr.running["profile1"] = running
    mgr.statuses["profile1"] = "running"

    with patch("os.kill") as mock_kill, patch("backend.browser_manager.log_activity") as mock_log, patch("os.waitpid") as mock_waitpid:
        # First call to os.kill(12345, 0) returns alive
        # Second call to check if dead after graceful fails returns alive
        # Third call to kill(12345, 9) kills it
        # Fourth call to check if dead returns dead
        mock_kill.side_effect = [None, None, None, OSError("No process")]
        
        # Override the timeout logic locally for test speed
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            await mgr.stop("profile1")
            
        # Verify SIGKILL was sent
        mock_kill.assert_any_call(12345, 9)
        assert mgr.statuses["profile1"] == "stopped"
        
        # Verify BROWSER_NATIVE_FORCE_KILLED was logged
        mock_log.assert_any_call(
            module="browser_manager",
            action="stop_profile",
            status="BROWSER_NATIVE_FORCE_KILLED",
            message="Forcing kill on process 12345 for profile profile1",
            profile_id="profile1"
        )


@pytest.mark.asyncio
async def test_restart_flow():
    from unittest.mock import AsyncMock
    mgr = BrowserManager()
    mgr.is_desktop = True
    
    profile = {"id": "profile1", "name": "Profile 1"}
    
    with patch.object(mgr, "stop", new_callable=AsyncMock) as mock_stop, \
         patch.object(mgr, "launch", new_callable=AsyncMock) as mock_launch, \
         patch("backend.browser_manager.log_activity") as mock_log:
         
        await mgr.restart(profile)
        
        mock_stop.assert_awaited_once_with("profile1")
        mock_launch.assert_awaited_once_with(profile)
        
        mock_log.assert_any_call(
            module="browser_manager",
            action="restart_profile",
            status="BROWSER_NATIVE_RESTARTED",
            message="Successfully restarted native profile profile1",
            profile_id="profile1"
        )


@pytest.mark.asyncio
async def test_launch_permission_denied_raises_permission_error():
    import os
    from unittest.mock import MagicMock
    mgr = BrowserManager()
    mgr.is_desktop = True

    profile = {
        "id": "profile1",
        "name": "Profile 1",
        "user_data_dir": "/tmp/non-existent-user-data-dir"
    }

    # Set up mocks to simulate resolved but non-executable binary path
    with patch.dict(os.environ, {"CLOAK_BROWSER_BINARY_PATH": "/tmp/non-executable-bin"}), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_file", return_value=True), \
         patch("os.path.realpath", return_value="/tmp/non-executable-bin"), \
         patch("platform.system", return_value="Linux"), \
         patch("os.access", return_value=False), \
         patch("os.chmod", side_effect=OSError("Permission Denied")):
         
         with pytest.raises(PermissionError, match="CLOAK_BROWSER_BINARY_PERMISSION_DENIED"):
             await mgr.launch(profile)

