import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend import database as db
from backend.runtime_guardian import _guardian_loop

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

@pytest.mark.asyncio
@patch("backend.runtime_guardian.run_lightweight_check")
async def test_critical_action_stop_profile(mock_check):
    # 1. Create a profile with default 'stop_profile' action and session_auto_save=True
    profile = db.create_profile(
        name="TestStopProfile",
        runtime_action_on_critical="stop_profile",
        session_auto_save=True
    )
    profile_id = profile["id"]

    # 2. Setup mock lightweight check to return a critical status
    mock_check.return_value = {
        "status": "critical",
        "risk_level": "critical",
        "error_code": "PROXY_CONNECTION_FAILED",
        "message": "Proxy connection lost."
    }

    # 3. Setup mock browser manager
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
    assert updated["last_runtime_issue"] == "PROXY_CONNECTION_FAILED"
    assert updated["last_runtime_message"] == "Proxy connection lost."
    assert updated["last_session_save_at"] is not None

    # 5. Verify browser_mgr.stop was called
    browser_mgr.stop.assert_called_once_with(profile_id)

    # 6. Verify audit logs in SQLite database for this profile_id
    with db.get_db() as conn:
        logs = conn.execute("SELECT * FROM logs WHERE profile_id = ?", (profile_id,)).fetchall()
    
    log_actions = [dict(log)["action"] for log in logs]
    assert "RUNTIME_GUARDIAN_CRITICAL" in log_actions
    assert "PROFILE_STOPPED_BY_GUARDIAN" in log_actions

@pytest.mark.asyncio
@patch("backend.runtime_guardian.run_lightweight_check")
async def test_critical_action_warn_only(mock_check):
    # 1. Create a profile with 'warn_only' action
    profile = db.create_profile(
        name="TestWarnOnly",
        runtime_action_on_critical="warn_only",
        session_auto_save=True
    )
    profile_id = profile["id"]

    # 2. Setup mock lightweight check to return critical status
    mock_check.return_value = {
        "status": "critical",
        "risk_level": "critical",
        "error_code": "FINGERPRINT_UA_MISMATCH",
        "message": "User-Agent mismatch detected."
    }

    # 3. Setup mock browser manager
    browser_mgr = MagicMock()
    browser_mgr.stop = AsyncMock()

    # To prevent infinite loop in 'warn_only' (since it does not break on critical),
    # we raise CancelledError on the second sleep call.
    sleep_count = 0
    async def mock_sleep(seconds):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count > 1:
            raise asyncio.CancelledError()

    with patch("asyncio.sleep", side_effect=mock_sleep):
        await _guardian_loop(profile_id, browser_mgr)

    # 4. Verify updates in the database: should be critical, NOT stopped_by_guardian
    updated = db.get_profile(profile_id)
    assert updated["runtime_guardian_status"] == "critical"
    assert updated["runtime_risk_level"] == "critical"
    assert updated["last_runtime_issue"] == "FINGERPRINT_UA_MISMATCH"
    assert updated["last_runtime_message"] == "User-Agent mismatch detected."
    assert updated["last_session_save_at"] is None  # Should not update session save time

    # 5. Verify browser_mgr.stop was NOT called
    browser_mgr.stop.assert_not_called()

    # 6. Verify audit logs: RUNTIME_GUARDIAN_CRITICAL is logged, PROFILE_STOPPED_BY_GUARDIAN is NOT logged for this profile_id
    with db.get_db() as conn:
        logs = conn.execute("SELECT * FROM logs WHERE profile_id = ?", (profile_id,)).fetchall()
    
    log_actions = [dict(log)["action"] for log in logs]
    assert "RUNTIME_GUARDIAN_CRITICAL" in log_actions
    assert "PROFILE_STOPPED_BY_GUARDIAN" not in log_actions
