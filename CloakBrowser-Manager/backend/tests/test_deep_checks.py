import pytest
import os
import sqlite3
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend import database as db
from backend.runtime_guardian import run_deep_check, _guardian_loop

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

@pytest.mark.asyncio
@patch("os.path.exists")
@patch("httpx.AsyncClient.get")
async def test_deep_check_session_corruption(mock_get, mock_exists):
    # Setup profile
    profile = db.create_profile(
        name="TestCorrupt"
    )
    profile_id = profile["id"]

    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET user_data_dir = ? WHERE id = ?", ("/fake/dir/corrupt", profile_id))
        conn.commit()

    browser_mgr = MagicMock()
    running_prof = MagicMock()
    running_prof.pid = 1234
    browser_mgr.running = {profile_id: running_prof}

    # Mock os.kill to return process alive
    with patch("os.kill") as mock_kill:
        mock_kill.return_value = None
        # Mock user_data_dir exists but mock path validation failure
        mock_exists.return_value = False

        res = await run_deep_check(profile_id, browser_mgr)
        assert res["status"] == "critical"
        assert res["error_code"] == "SESSION_DATA_CORRUPTED"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_deep_check_healthy_and_mismatch(mock_get, tmp_path):
    # Setup a mock user_data_dir with empty cookies DB
    ud_dir = tmp_path / "user_data"
    ud_dir.mkdir()
    net_dir = ud_dir / "Default" / "Network"
    net_dir.mkdir(parents=True)
    cookies_db = net_dir / "Cookies"
    
    # Create valid SQLite DB
    conn = sqlite3.connect(str(cookies_db))
    conn.execute("CREATE TABLE cookies (name TEXT)")
    conn.commit()
    conn.close()

    profile = db.create_profile(
        name="TestHealthy",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        platform="windows",
        screen_width=1920,
        screen_height=1080,
        timezone="America/New_York",
        locale="en-US",
        gpu_vendor="Google Inc. (NVIDIA)",
        gpu_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        fingerprint_locked=True
    )
    profile_id = profile["id"]

    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET user_data_dir = ? WHERE id = ?", (str(ud_dir), profile_id))
        conn.commit()

    browser_mgr = MagicMock()
    running_prof = MagicMock()
    running_prof.pid = 1234
    running_prof.cdp_port = 5105
    browser_mgr.running = {profile_id: running_prof}

    # Mock os.kill to return process alive
    with patch("os.kill") as mock_kill:
        mock_kill.return_value = None

        # 1. Mock CDP /json/list response returning a page target
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = [
            {
                "type": "page",
                "webSocketDebuggerUrl": "ws://127.0.0.1:5105/devtools/page/abc"
            }
        ]

        # Mock TLS check success response
        mock_tls_resp = MagicMock()
        mock_tls_resp.status_code = 200

        mock_get.side_effect = [mock_list_resp, mock_tls_resp]

        # Mock websockets connect
        mock_ws = AsyncMock()
        # Mock receiving evaluation payload
        evaluated_val = {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "platform": "Win32",
            "screenWidth": 1920,
            "screenHeight": 1080,
            "timezone": "America/New_York",
            "locale": "en-US",
            "canvasHash": "12345",
            "webglVendor": "Google Inc. (NVIDIA)",
            "webglRenderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "fontHash": "mock-font-hash"
        }
        mock_ws.recv = AsyncMock(return_value=json.dumps({
            "result": {
                "result": {
                    "value": json.dumps(evaluated_val)
                }
            }
        }))

        mock_ws_ctx = MagicMock()
        mock_ws_ctx.__aenter__ = AsyncMock(return_value=mock_ws)

        with patch("websockets.connect", return_value=mock_ws_ctx):
            res = await run_deep_check(profile_id, browser_mgr)
            assert res["status"] == "healthy"
            assert res["risk_level"] == "normal"

        # 2. Test Mismatch: Mock websockets evaluated val with wrong user-agent
        evaluated_val_wrong = evaluated_val.copy()
        evaluated_val_wrong["userAgent"] = "Mismatched UA 1.0"
        
        # Reset side effects
        mock_get.side_effect = [mock_list_resp, mock_tls_resp]
        
        mock_ws_wrong = AsyncMock()
        mock_ws_wrong.recv = AsyncMock(return_value=json.dumps({
            "result": {
                "result": {
                    "value": json.dumps(evaluated_val_wrong)
                }
            }
        }))
        mock_ws_ctx_wrong = MagicMock()
        mock_ws_ctx_wrong.__aenter__ = AsyncMock(return_value=mock_ws_wrong)

        with patch("websockets.connect", return_value=mock_ws_ctx_wrong):
            res = await run_deep_check(profile_id, browser_mgr)
            assert res["status"] == "critical"
            assert res["error_code"] == "FINGERPRINT_UA_MISMATCH"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_deep_check_tls_unavailable(mock_get, tmp_path):
    ud_dir = tmp_path / "user_data"
    ud_dir.mkdir()
    net_dir = ud_dir / "Default" / "Network"
    net_dir.mkdir(parents=True)
    cookies_db = net_dir / "Cookies"
    
    conn = sqlite3.connect(str(cookies_db))
    conn.execute("CREATE TABLE cookies (name TEXT)")
    conn.commit()
    conn.close()

    profile = db.create_profile(
        name="TestTLSWarn"
    )
    profile_id = profile["id"]

    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET user_data_dir = ? WHERE id = ?", (str(ud_dir), profile_id))
        conn.commit()

    browser_mgr = MagicMock()
    running_prof = MagicMock()
    running_prof.pid = 1234
    running_prof.cdp_port = 5105
    browser_mgr.running = {profile_id: running_prof}

    with patch("os.kill") as mock_kill:
        mock_kill.return_value = None

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = []

        # Mock TLS check endpoint timeout/exception
        mock_get.side_effect = [mock_list_resp, Exception("TLS Service Timeout")]

        res = await run_deep_check(profile_id, browser_mgr)
        assert res["status"] == "warning"
        assert res["error_code"] == "TLS_CHECK_UNAVAILABLE"
