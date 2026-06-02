import pytest
import os
from starlette.testclient import TestClient
from backend import database as db

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

def test_override_warning_permission_rules(app_client: TestClient):
    # 1. Create a profile in warning state
    profile = db.create_profile(
        name="TestOverrideProfile",
        verification_status="warning"
    )
    profile_id = profile["id"]

    # Test Case 1: Regular User - Access Denied (403)
    user_resp = app_client.post(
        f"/api/profiles/{profile_id}/override-warning",
        json={"reason": "Need to launch for user"},
        headers={"X-User-Role": "user"}
    )
    assert user_resp.status_code == 403
    assert "Only admins or super_admins can override" in user_resp.json()["detail"]

    # Test Case 2: Admin - Allow warning override
    admin_resp = app_client.post(
        f"/api/profiles/{profile_id}/override-warning",
        json={"reason": "Verified proxy connection manually"},
        headers={"X-User-Role": "admin"}
    )
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert data["verification_status"] == "verified"
    
    # Verify Audit log in DB
    with db.get_db() as conn:
        log = conn.execute(
            "SELECT action, message FROM logs WHERE profile_id = ? ORDER BY timestamp DESC LIMIT 1",
            (profile_id,)
        ).fetchone()
        assert log["action"] == "ADMIN_OVERRIDE_VERIFICATION_WARNING"
        assert "Verified proxy connection manually" in log["message"]


def test_critical_override_rules(app_client: TestClient):
    # Create profile in critical state
    profile = db.create_profile(
        name="TestCritProfile",
        verification_status="failed"
    )
    profile_id = profile["id"]

    # Test Case 1: Admin attempts critical override - Blocked (403)
    admin_resp = app_client.post(
        f"/api/profiles/{profile_id}/override-warning",
        json={"reason": "Attempt crit override as admin"},
        headers={"X-User-Role": "admin"}
    )
    assert admin_resp.status_code == 403
    assert "Critical issues cannot be overridden by default" in admin_resp.json()["detail"]

    # Test Case 2: Super Admin attempts critical override without env config - Blocked (403)
    os.environ["ALLOW_CRITICAL_OVERRIDE"] = "false"
    super_resp = app_client.post(
        f"/api/profiles/{profile_id}/override-warning",
        json={"reason": "Attempt crit override without config"},
        headers={"X-User-Role": "super_admin"}
    )
    assert super_resp.status_code == 403

    # Test Case 3: Super Admin attempts critical override with env config enabled - Allowed (200)
    os.environ["ALLOW_CRITICAL_OVERRIDE"] = "true"
    super_ok_resp = app_client.post(
        f"/api/profiles/{profile_id}/override-warning",
        json={"reason": "Override critical under special settings"},
        headers={"X-User-Role": "super_admin"}
    )
    assert super_ok_resp.status_code == 200
    assert super_ok_resp.json()["verification_status"] == "verified"
