import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient
from backend import main
from backend.browser_manager import RunningProfile

def test_resource_limit_reached(app_client: TestClient):
    # Set limit to 2 running profiles
    with patch.dict(os.environ, {"MAX_RUNNING_PROFILES": "2"}):
        create = app_client.post("/api/profiles", json={"name": "P3"})
        pid = create.json()["id"]

        # Mock browser_mgr.statuses to simulate 2 profiles already running/starting
        main.browser_mgr.statuses = {
            "p1": "running",
            "p2": "starting",
        }

        # Clear any existing running dict to isolate test
        main.browser_mgr.running.clear()

        # Try to launch P3
        resp = app_client.post(f"/api/profiles/{pid}/launch")
        
        # Should fail with 409 Conflict (since limit is reached)
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error_code"] == "RESOURCE_LIMIT_REACHED"
        assert "Maximum running profiles limit" in data["detail"]["message"]

        # Verify that an error log was inserted in the database
        recent_errors = main.db.get_recent_errors(limit=5)
        has_limit_log = any(
            err.get("error_code") == "RESOURCE_LIMIT_REACHED"
            for err in recent_errors
        )
        assert has_limit_log, "RESOURCE_LIMIT_REACHED error was not logged to DB"

        # Cleanup statuses
        main.browser_mgr.statuses.clear()

def test_resource_limit_not_reached(app_client: TestClient):
    # Set limit to 2 running profiles
    with patch.dict(os.environ, {"MAX_RUNNING_PROFILES": "2"}):
        create = app_client.post("/api/profiles", json={"name": "P2"})
        pid = create.json()["id"]

        # Mock browser_mgr.statuses to simulate 1 profile running (under limit)
        main.browser_mgr.statuses = {
            "p1": "running",
        }
        main.browser_mgr.running.clear()

        # Mock the browser launch to avoid starting Playwright context
        mock_running = MagicMock(spec=RunningProfile)
        mock_running.ws_port = 6100
        mock_running.display = 100
        main.browser_mgr.launch = AsyncMock(return_value=mock_running)

        # Try to launch P2
        resp = app_client.post(f"/api/profiles/{pid}/launch")
        
        # Should succeed or at least bypass the limit check and try to launch (we mock launch to succeed)
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

        # Cleanup statuses & mock restore
        main.browser_mgr.statuses.clear()
        import importlib
        importlib.reload(main)
