"""Unit tests for proxy update flow and auto-sync timezone/locale/geolocation settings."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from backend import database as db


def test_proxy_update_flow_and_auto_sync(app_client: TestClient):
    # 1. Create a proxy
    proxy_resp = app_client.post(
        "/api/proxies",
        json={
            "name": "MockProxy",
            "host": "127.0.0.1",
            "port": 8080,
            "type": "http",
        }
    )
    assert proxy_resp.status_code == 201
    proxy_data = proxy_resp.json()
    proxy_id = proxy_data["id"]

    # Set timezone and locale on the proxy
    db.update_proxy(proxy_id, timezone="Europe/Paris", locale="fr-FR")

    # 2. Create a profile with auto-sync enabled
    profile_resp = app_client.post(
        "/api/profiles",
        json={
            "name": "ProxySyncTest",
            "auto_sync_timezone_with_proxy": True,
            "auto_sync_locale_with_proxy": True,
            "auto_sync_geolocation_with_proxy": True,
        }
    )
    assert profile_resp.status_code == 201
    profile_data = profile_resp.json()
    profile_id = profile_data["id"]

    # Record initial fingerprint configuration
    core_fields_before = {
        "fingerprint_seed": profile_data["fingerprint_seed"],
        "gpu_vendor": profile_data["gpu_vendor"],
        "gpu_renderer": profile_data["gpu_renderer"],
        "platform": profile_data["platform"],
        "user_agent": profile_data["user_agent"],
        "screen_width": profile_data["screen_width"],
        "screen_height": profile_data["screen_height"],
        "hardware_concurrency": profile_data["hardware_concurrency"],
    }

    # Verify that initial profile has default/null timezone and locale
    assert profile_data["timezone"] is None
    assert profile_data["locale"] is None
    assert profile_data["geoip"] is False

    # 3. Update the profile to use the new proxy
    update_resp = app_client.put(
        f"/api/profiles/{profile_id}",
        json={"proxy_id": proxy_id}
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()

    # 4. Compare fingerprint configuration before/after. Results must be unchanged.
    core_fields_after = {
        "fingerprint_seed": updated_data["fingerprint_seed"],
        "gpu_vendor": updated_data["gpu_vendor"],
        "gpu_renderer": updated_data["gpu_renderer"],
        "platform": updated_data["platform"],
        "user_agent": updated_data["user_agent"],
        "screen_width": updated_data["screen_width"],
        "screen_height": updated_data["screen_height"],
        "hardware_concurrency": updated_data["hardware_concurrency"],
    }
    assert core_fields_before == core_fields_after

    # 5. Check that timezone, locale, and geoip are correctly auto-synced
    assert updated_data["timezone"] == "Europe/Paris"
    assert updated_data["locale"] == "fr-FR"
    assert updated_data["geoip"] is True

    # 6. Verify audit logs (PROXY_CHANGED and FINGERPRINT_UNCHANGED_AFTER_PROXY_CHANGE)
    with db.get_db() as conn:
        logs = conn.execute(
            "SELECT status FROM logs WHERE profile_id = ? ORDER BY timestamp DESC",
            (profile_id,)
        ).fetchall()
        statuses = [row["status"] for row in logs]
        assert "PROXY_CHANGED" in statuses
        assert "FINGERPRINT_UNCHANGED_AFTER_PROXY_CHANGE" in statuses


def test_proxy_change_re_verification(app_client: TestClient):
    # 1. Create a proxy
    proxy_resp = app_client.post(
        "/api/proxies",
        json={
            "name": "NewMockProxy",
            "host": "127.0.0.1",
            "port": 9090,
            "type": "http",
        }
    )
    assert proxy_resp.status_code == 201
    proxy_data = proxy_resp.json()
    proxy_id = proxy_data["id"]

    # 2. Create a profile (stopped, verified)
    profile_resp = app_client.post(
        "/api/profiles",
        json={
            "name": "ReverifyTest",
            "verification_status": "verified",
            "runtime_guardian_status": "monitoring",
            "verification_expires_on_proxy_change": True,
        }
    )
    assert profile_resp.status_code == 201
    profile_id = profile_resp.json()["id"]

    # 3. Update the proxy of the stopped profile
    update_resp = app_client.put(
        f"/api/profiles/{profile_id}",
        json={"proxy_id": proxy_id}
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()

    # Check status: verification_status becomes expired, and runtime_guardian_status becomes idle
    assert updated_data["verification_status"] == "expired"
    assert updated_data["runtime_guardian_status"] == "idle"

