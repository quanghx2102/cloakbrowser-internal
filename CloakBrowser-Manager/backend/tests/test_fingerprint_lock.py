"""Unit tests for browser profile Fingerprint and Identity Lock behaviors."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from backend import main
from backend.browser_manager import RunningProfile


def test_create_profile_with_fingerprint_lock_default(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={"name": "LockByDefault"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["fingerprint_locked"] is True
    assert data["session_auto_save"] is True
    assert data["auto_sync_timezone_with_proxy"] is False
    assert data["auto_sync_locale_with_proxy"] is False
    assert data["auto_sync_geolocation_with_proxy"] is False


def test_modify_core_field_when_locked_rejected(app_client: TestClient):
    # 1. Create a profile (locked by default)
    create = app_client.post("/api/profiles", json={"name": "LockedProfile"})
    pid = create.json()["id"]

    # 2. Try to change fingerprint_seed while fingerprint_locked=True (should be rejected with 400)
    resp = app_client.put(f"/api/profiles/{pid}", json={"fingerprint_seed": 999})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "FINGERPRINT_LOCKED"


def test_unlock_requires_admin_role(app_client: TestClient):
    # 1. Create profile (locked by default)
    create = app_client.post("/api/profiles", json={"name": "UnlockTest"})
    pid = create.json()["id"]

    # 2. Try to unlock as a regular user (should be rejected with 403)
    resp = app_client.put(f"/api/profiles/{pid}", json={"fingerprint_locked": False}, headers={"X-User-Role": "user"})
    assert resp.status_code == 403

    # 3. Unlock as an admin (should succeed)
    resp = app_client.put(f"/api/profiles/{pid}", json={"fingerprint_locked": False}, headers={"X-User-Role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["fingerprint_locked"] is False

    # 4. Now modify core fields while unlocked (should succeed)
    resp = app_client.put(f"/api/profiles/{pid}", json={"fingerprint_seed": 999})
    assert resp.status_code == 200
    assert resp.json()["fingerprint_seed"] == 999


def test_proxy_change_events(app_client: TestClient):
    # 1. Create profile (locked by default)
    create = app_client.post("/api/profiles", json={"name": "ProxyTest"})
    pid = create.json()["id"]

    # 2. Change proxy
    resp = app_client.put(f"/api/profiles/{pid}", json={"proxy": "http://host:8080"})
    assert resp.status_code == 200
    assert resp.json()["proxy"] == "http://host:8080"
    # Core fingerprint is unchanged
    assert resp.json()["fingerprint_locked"] is True


def test_regenerate_fingerprint_endpoint_security(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "RegenTest"})
    pid = create.json()["id"]
    original_seed = create.json()["fingerprint_seed"]

    # 1. Regular user cannot regenerate fingerprint
    resp = app_client.post(f"/api/profiles/{pid}/regenerate-fingerprint", headers={"X-User-Role": "user"})
    assert resp.status_code == 403

    # 2. Admin can regenerate fingerprint
    resp = app_client.post(f"/api/profiles/{pid}/regenerate-fingerprint", headers={"X-User-Role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["fingerprint_seed"] != original_seed
    assert resp.json()["last_fingerprint_change_at"] is not None


def test_session_auto_save_timestamp_on_stop(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "StopSaveTest", "session_auto_save": True})
    pid = create.json()["id"]

    # Inject mock running profile
    mock_running = MagicMock(spec=RunningProfile)
    mock_running.display = 100
    mock_running.cdp_port = 5100
    mock_running.context = AsyncMock()
    mock_running.pid = None
    main.browser_mgr.running[pid] = mock_running

    # Mock stop_vnc so it doesn't try to run subprocess shell commands
    main.browser_mgr.vnc.stop_vnc = AsyncMock()

    resp = app_client.post(f"/api/profiles/{pid}/stop")
    assert resp.status_code == 200

    # Get updated profile and check last_session_save_at is updated
    updated = app_client.get(f"/api/profiles/{pid}").json()
    assert updated["last_session_save_at"] is not None
