import pytest
import os
import json
import sqlite3
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch
from backend import database as db
from backend import main
from backend.browser_manager import BrowserManager, RunningProfile
from backend.runtime_guardian import _guardian_loop

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

@pytest.mark.asyncio
async def test_cookie_session_save_integrity_normal_stop():
    # 1. Create profile with fingerprint_locked=True and session_auto_save=True
    profile = db.create_profile(
        name="SaveIntegrityNormalStop",
        fingerprint_locked=True,
        session_auto_save=True,
        platform="windows",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        screen_width=1920,
        screen_height=1080,
        gpu_vendor="Google Inc.",
        gpu_renderer="ANGLE (Google, Vulkan 1.3, SwiftShader)"
    )
    profile_id = profile["id"]
    original_seed = profile["fingerprint_seed"]

    # 2. Mock Running Profile
    mgr = BrowserManager()
    mgr.is_desktop = True
    
    mock_context = AsyncMock()
    running = RunningProfile(
        profile_id=profile_id,
        context=mock_context,
        display=None,
        ws_port=None,
        cdp_port=5100,
        pid=98765
    )
    mgr.running[profile_id] = running
    mgr.statuses[profile_id] = "running"

    with patch("os.kill") as mock_kill:
        # Simulate process terminating on first check
        mock_kill.side_effect = OSError("No process")
        
        # Stop profile
        await mgr.stop(profile_id)

        # Verify state is stopped
        assert mgr.statuses[profile_id] == "stopped"

        # Verify profile database values
        updated = db.get_profile(profile_id)
        assert updated["last_session_save_at"] is not None
        
        # Verify fingerprint config is absolutely unchanged
        assert updated["fingerprint_seed"] == original_seed
        assert updated["platform"] == "windows"
        assert updated["user_agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        assert updated["screen_width"] == 1920
        assert updated["screen_height"] == 1080
        assert updated["gpu_vendor"] == "Google Inc."
        assert updated["gpu_renderer"] == "ANGLE (Google, Vulkan 1.3, SwiftShader)"

        # Check SESSION_SAVED_ON_STOP audit log
        with db.get_db() as conn:
            logs = conn.execute("SELECT * FROM logs WHERE profile_id = ? AND action = 'SESSION_SAVED_ON_STOP'", (profile_id,)).fetchall()
        assert len(logs) >= 1
        assert logs[0]["status"] == "success"

@pytest.mark.asyncio
@patch("backend.runtime_guardian.run_lightweight_check")
async def test_cookie_session_save_integrity_guardian_critical_stop(mock_check):
    # 1. Create a profile with default 'stop_profile' action and session_auto_save=True
    profile = db.create_profile(
        name="SaveIntegrityGuardianStop",
        runtime_action_on_critical="stop_profile",
        session_auto_save=True,
        fingerprint_locked=True,
        platform="macos",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        screen_width=1440,
        screen_height=900
    )
    profile_id = profile["id"]
    original_seed = profile["fingerprint_seed"]

    # 2. Setup mock lightweight check to return a critical status
    mock_check.return_value = {
        "status": "critical",
        "risk_level": "critical",
        "error_code": "PROXY_CONNECTION_FAILED",
        "message": "Proxy connection lost."
    }

    # 3. Setup mock browser manager to verify stop and graceful stop attempts
    browser_mgr = MagicMock()
    browser_mgr.stop = AsyncMock()

    # Mock sleep to complete instantly
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Run the guardian loop
        await _guardian_loop(profile_id, browser_mgr)

    # 4. Verify updates in the database
    updated = db.get_profile(profile_id)
    assert updated["runtime_guardian_status"] == "stopped_by_guardian"
    assert updated["runtime_risk_level"] == "critical"
    assert updated["last_session_save_at"] is not None
    
    # Verify fingerprint configs are unchanged
    assert updated["fingerprint_seed"] == original_seed
    assert updated["platform"] == "macos"
    assert updated["user_agent"] == "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    assert updated["screen_width"] == 1440
    assert updated["screen_height"] == 900

    # 5. Verify browser_mgr.stop was called gracefully
    browser_mgr.stop.assert_called_once_with(profile_id)

    # 6. Verify audit logs in SQLite database for SESSION_SAVED_ON_STOP
    with db.get_db() as conn:
        logs = conn.execute("SELECT * FROM logs WHERE profile_id = ? AND action = 'SESSION_SAVED_ON_STOP'", (profile_id,)).fetchall()
    assert len(logs) >= 1
