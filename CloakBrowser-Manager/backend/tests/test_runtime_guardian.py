import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend import database as db
from backend.runtime_guardian import start_runtime_guardian, stop_runtime_guardian, run_lightweight_check

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

@pytest.mark.asyncio
async def test_run_lightweight_check_dead_process():
    # Setup profile
    profile = db.create_profile(name="TestDead")
    profile_id = profile["id"]

    browser_mgr = MagicMock()
    # Mocking running dictionary in browser manager (browser not in running)
    browser_mgr.running = {}

    res = await run_lightweight_check(profile_id, browser_mgr)
    assert res["status"] == "dead"
    assert "Browser is not running" in res["message"]

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_run_lightweight_check_critical_ip_change(mock_get):
    profile = db.create_profile(
        name="TestCritical",
        proxy="http://1.2.3.4:8080",
        proxy_mode="static_residential",
        expected_exit_ip="1.2.3.4",
        allow_ip_rotation=False
    )
    profile_id = profile["id"]

    # Mock browser manager running profile
    running_prof = MagicMock()
    running_prof.pid = 9999
    browser_mgr = MagicMock()
    browser_mgr.running = {profile_id: running_prof}

    # Mock os.kill to return process alive
    with patch("os.kill") as mock_kill:
        mock_kill.return_value = None

        # Mock IP API to return rotated IP (5.6.7.8 instead of expected 1.2.3.4)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "query": "5.6.7.8",
            "countryCode": "US",
            "as": "AS123"
        }
        mock_get.return_value = mock_response

        res = await run_lightweight_check(profile_id, browser_mgr)
        assert res["status"] == "critical"
        assert res["risk_level"] == "critical"
        assert res["policy_report"]["error_code"] == "PROXY_EXIT_IP_CHANGED"

@pytest.mark.asyncio
async def test_start_stop_guardian_lifecycle():
    profile = db.create_profile(
        name="TestLifecycle",
        runtime_guardian_enabled=True
    )
    profile_id = profile["id"]

    browser_mgr = MagicMock()
    
    # Start guardian
    start_runtime_guardian(profile_id, browser_mgr)
    
    # Check status
    updated = db.get_profile(profile_id)
    assert updated["runtime_guardian_status"] == "monitoring"
    assert updated["runtime_risk_level"] == "normal"

    # Stop guardian
    stop_runtime_guardian(profile_id)
    updated_stopped = db.get_profile(profile_id)
    assert updated_stopped["runtime_guardian_status"] == "idle"


def test_generate_runtime_report():
    import json
    from backend.runtime_guardian import generate_runtime_report

    # Test Case 1: Healthy Profile
    profile_healthy = db.create_profile(
        name="TestHealthyReport",
        runtime_guardian_status="healthy",
        last_runtime_check_at="2026-06-02T12:00:00Z",
        last_runtime_check_result=json.dumps({
            "status": "healthy",
            "risk_level": "normal",
            "proxy_check": {
                "status_code": "PROXY_OK",
                "latency_ms": 120
            }
        })
    )
    report = generate_runtime_report(profile_healthy)
    assert report["status"] == "healthy"
    assert report["score"] == 100
    assert report["checks"]["proxy"] == "pass"
    assert not report["blocking_issues"]

    # Test Case 2: Critical Profile
    profile_critical = db.create_profile(
        name="TestCriticalReport",
        runtime_guardian_status="stopped_by_guardian",
        last_runtime_check_at="2026-06-02T12:05:00Z",
        last_runtime_check_result=json.dumps({
            "status": "critical",
            "risk_level": "critical",
            "error_code": "PROXY_EXIT_IP_CHANGED",
            "message": "Proxy exit IP changed"
        })
    )
    report_crit = generate_runtime_report(profile_critical)
    assert report_crit["status"] == "critical"
    assert report_crit["score"] == 45
    assert report_crit["checks"]["proxy"] == "failed"
    assert "PROXY_EXIT_IP_CHANGED" in report_crit["blocking_issues"]
    assert report_crit["action_taken"] == "stop_profile"


def test_get_runtime_report_api():
    import json
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)

    profile = db.create_profile(
        name="TestApiReport",
        runtime_guardian_status="warning",
        last_runtime_check_at="2026-06-02T12:10:00Z",
        last_runtime_check_result=json.dumps({
            "status": "warning",
            "risk_level": "warning",
            "error_code": "TLS_CHECK_UNAVAILABLE",
            "message": "TLS check is unavailable"
        })
    )

    response = client.get(f"/api/profiles/{profile['id']}/runtime-report")
    assert response.status_code == 200
    data = response.json()
    assert data["profile_id"] == profile["id"]
    assert data["status"] == "warning"
    assert data["score"] == 80
    assert "TLS_CHECK_UNAVAILABLE" in data["warnings"]

