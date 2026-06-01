import io
import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from backend import database as db
from backend import main


def test_toggle_fingerprint_lock_endpoint(app_client: TestClient):
    """Test toggle fingerprint lock API endpoint."""
    profile = db.create_profile(name="Lock Toggle Profile", fingerprint_seed=123)
    pid = profile["id"]
    assert bool(profile["fingerprint_locked"]) is True

    # Toggle to False
    resp = app_client.patch(
        f"/api/profiles/{pid}/fingerprint-lock",
        json={"fingerprint_locked": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fingerprint_locked"] is False

    # Check DB directly
    db_profile = db.get_profile(pid)
    assert db_profile["fingerprint_locked"] == 0 or db_profile["fingerprint_locked"] is False


def test_export_package_endpoint_permission(app_client: TestClient):
    """Test export package API admin role guard."""
    profile = db.create_profile(name="Perm Profile")
    pid = profile["id"]

    # Non-admin request
    resp = app_client.post(
        f"/api/profiles/{pid}/export-package",
        json={"passphrase": None, "include_proxy_secret": False},
        headers={"x-user-role": "user"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "EXPORT_DENIED_PERMISSION"


def test_export_package_endpoint_success(app_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Test successful export package API endpoint and desktop vs file download response."""
    profile = db.create_profile(name="Export Success")
    pid = profile["id"]

    # Mock browser_mgr status
    monkeypatch.setattr(main.browser_mgr, "statuses", {pid: "stopped"})

    # 1. Test standard file response (non-desktop mode)
    monkeypatch.setattr(main.browser_mgr, "is_desktop", False)
    resp = app_client.post(
        f"/api/profiles/{pid}/export-package",
        json={"passphrase": "mypass", "include_proxy_secret": True},
        headers={"x-user-role": "admin"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert len(resp.content) > 0

    # 2. Test desktop mode JSON path response
    monkeypatch.setattr(main.browser_mgr, "is_desktop", True)
    resp = app_client.post(
        f"/api/profiles/{pid}/export-package",
        json={"passphrase": "mypass", "include_proxy_secret": True},
        headers={"x-user-role": "admin"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "export_path" in data
    assert data["export_path"].endswith(f"profile_{pid}.cbprofile")


def test_get_profile_packages_endpoint(app_client: TestClient):
    """Test listing profile packages endpoint."""
    from backend.database import DATA_DIR
    exports_dir = DATA_DIR / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a dummy .cbprofile file
    dummy_file = exports_dir / "profile_dummy.cbprofile"
    dummy_file.write_text("dummypackage", encoding="utf-8")

    resp = app_client.get("/api/profile-packages")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(x["filename"] == "profile_dummy.cbprofile" for x in data)


def test_import_package_endpoint_permission(app_client: TestClient):
    """Test import package API admin role guard."""
    dummy_file_bytes = b"dummycontent"

    # Non-admin request
    resp = app_client.post(
        "/api/profiles/import-package",
        files={"file": ("test.cbprofile", dummy_file_bytes, "application/octet-stream")},
        data={"passphrase": "somepass", "mode": "new_profile"},
        headers={"x-user-role": "user"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "IMPORT_DENIED_PERMISSION"


def test_import_package_endpoint_success(app_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Test import package endpoint successfully imports via form data."""
    # 1. Create a dummy stopped profile first and export it to a file
    profile = db.create_profile(name="To Import", fingerprint_seed=777)
    pid = profile["id"]
    monkeypatch.setattr(main.browser_mgr, "statuses", {pid: "stopped"})
    monkeypatch.setattr(main.browser_mgr, "is_desktop", True)

    resp_export = app_client.post(
        f"/api/profiles/{pid}/export-package",
        json={"passphrase": "securephrase", "include_proxy_secret": False},
        headers={"x-user-role": "admin"},
    )
    assert resp_export.status_code == 200
    export_path = resp_export.json()["export_path"]

    # 2. Read the exported file bytes
    with open(export_path, "rb") as f:
        file_bytes = f.read()

    # 3. Post to import-package
    resp_import = app_client.post(
        "/api/profiles/import-package",
        files={"file": ("profile.cbprofile", file_bytes, "application/octet-stream")},
        data={"passphrase": "securephrase", "mode": "new_profile"},
        headers={"x-user-role": "admin"},
    )
    assert resp_import.status_code == 200
    import_data = resp_import.json()
    assert import_data["status"] == "PROFILE_PACKAGE_IMPORTED"
    new_pid = import_data["profile_id"]

    # Validate db entry
    new_profile = db.get_profile(new_pid)
    assert new_profile["name"] == "To Import"
    assert new_profile["fingerprint_seed"] == 777
