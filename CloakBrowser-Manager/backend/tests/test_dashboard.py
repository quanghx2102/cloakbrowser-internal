import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@patch("backend.main.db.list_profiles")
@patch("backend.main.browser_mgr.get_status")
@patch("backend.main.db.list_proxies")
@patch("backend.main.db.get_recent_errors")
def test_dashboard_summary(mock_recent_errors, mock_list_proxies, mock_get_status, mock_list_profiles):
    mock_list_profiles.return_value = [
        {"id": "p1"}, {"id": "p2"}, {"id": "p3"}, {"id": "p4"}
    ]
    
    def mock_status(pid):
        if pid == "p1": return {"status": "running"}
        if pid == "p2": return {"status": "starting"}
        if pid == "p3": return {"status": "stopped"}
        if pid == "p4": return {"status": "crashed"}
    mock_get_status.side_effect = mock_status
    
    mock_list_proxies.return_value = [
        {"id": "px1", "status": "active", "latency_ms": 100},
        {"id": "px2", "status": "active", "latency_ms": None, "last_checked_at": "2026-05-31"},
        {"id": "px3", "status": "inactive"}
    ]
    
    mock_recent_errors.return_value = [
        {"id": "log1", "timestamp": "...", "level": "error", "module": "test", "action": "fail", "status": "failed"}
    ]
    
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["total_profiles"] == 4
    assert data["running_profiles"] == 2
    assert data["stopped_profiles"] == 1
    assert data["failed_profiles"] == 1
    
    assert data["total_proxies"] == 3
    assert data["ok_proxies"] == 1
    assert data["failed_proxies"] == 1
    
    assert len(data["recent_errors"]) == 1
    assert data["max_running_profiles"] == 5

@patch("backend.main.browser_mgr.stop")
def test_stop_all_profiles(mock_stop):
    with patch.dict("backend.main.browser_mgr.statuses", {"p1": "running", "p2": "starting", "p3": "stopped"}):
        resp = client.post("/api/profiles/stop-all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["total"] == 2
        assert data["stopped"] == 2
        assert data["failed"] == 0
        assert mock_stop.call_count == 2
