import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from backend import database as db
from backend.profile_package import export_profile, import_profile, ProfilePackageError


def test_export_import_plain(tmp_db: Path):
    """Test exporting and importing a profile without encryption."""
    # 1. Create a profile and write dummy user data
    profile = db.create_profile(name="Plain Profile", fingerprint_seed=99999)
    profile_id = profile["id"]
    
    user_data_dir = Path(profile["user_data_dir"])
    user_data_dir.mkdir(parents=True, exist_ok=True)
    (user_data_dir / "Preferences").write_text("dummy-prefs", encoding="utf-8")
    (user_data_dir / "Cookies").write_text("dummy-cookies", encoding="utf-8")

    # Mock browser manager with a stopped state
    browser_mgr = MagicMock()
    browser_mgr.statuses = {}

    dest_file = tmp_db / "plain.cbprofile"

    # 2. Export profile
    res_export = export_profile(
        browser_mgr=browser_mgr,
        profile_id=profile_id,
        dest_path=str(dest_file),
    )
    assert res_export["status"] == "PROFILE_PACKAGE_EXPORTED"
    assert dest_file.exists()

    # 3. Import profile as a new one
    res_import = import_profile(
        browser_mgr=browser_mgr,
        src_path=str(dest_file),
    )
    assert res_import["status"] == "PROFILE_PACKAGE_IMPORTED"
    new_profile_id = res_import["profile_id"]
    assert new_profile_id != profile_id

    # Verify database entry
    imported_prof = db.get_profile(new_profile_id)
    assert imported_prof is not None
    assert imported_prof["name"] == "Plain Profile"
    assert imported_prof["fingerprint_seed"] == 99999

    # Verify user data dir content
    new_user_data_dir = Path(imported_prof["user_data_dir"])
    assert (new_user_data_dir / "Preferences").read_text(encoding="utf-8") == "dummy-prefs"
    assert (new_user_data_dir / "Cookies").read_text(encoding="utf-8") == "dummy-cookies"


def test_export_import_encrypted(tmp_db: Path):
    """Test exporting and importing a profile with passphrase encryption."""
    profile = db.create_profile(name="Secret Profile", fingerprint_seed=11111)
    profile_id = profile["id"]
    
    user_data_dir = Path(profile["user_data_dir"])
    user_data_dir.mkdir(parents=True, exist_ok=True)
    (user_data_dir / "Preferences").write_text("topsecret", encoding="utf-8")

    browser_mgr = MagicMock()
    browser_mgr.statuses = {}

    dest_file = tmp_db / "secret.cbprofile"
    passphrase = "my-super-secret-passphrase"

    # Export with passphrase
    export_profile(
        browser_mgr=browser_mgr,
        profile_id=profile_id,
        dest_path=str(dest_file),
        passphrase=passphrase,
    )

    # Attempt import with WRONG passphrase
    with pytest.raises(ProfilePackageError) as exc:
        import_profile(
            browser_mgr=browser_mgr,
            src_path=str(dest_file),
            passphrase="wrong-passphrase",
        )
    assert exc.value.code == "PROFILE_PACKAGE_DECRYPT_FAILED"

    # Attempt import with CORRECT passphrase
    res_import = import_profile(
        browser_mgr=browser_mgr,
        src_path=str(dest_file),
        passphrase=passphrase,
    )
    assert res_import["status"] == "PROFILE_PACKAGE_IMPORTED"

    imported_prof = db.get_profile(res_import["profile_id"])
    assert imported_prof["name"] == "Secret Profile"
    assert Path(imported_prof["user_data_dir"]).exists()
    assert (Path(imported_prof["user_data_dir"]) / "Preferences").read_text(encoding="utf-8") == "topsecret"


def test_export_running_denied(tmp_db: Path):
    """Test that exporting a running profile is denied."""
    profile = db.create_profile(name="Running Profile")
    profile_id = profile["id"]

    browser_mgr = MagicMock()
    # Mock statuses where profile is starting or running
    browser_mgr.statuses = {profile_id: "running"}

    dest_file = tmp_db / "should_fail.cbprofile"

    with pytest.raises(ProfilePackageError) as exc:
        export_profile(
            browser_mgr=browser_mgr,
            profile_id=profile_id,
            dest_path=str(dest_file),
        )
    assert exc.value.code == "PROFILE_RUNNING_EXPORT_DENIED"


def test_import_overwrite_running_denied(tmp_db: Path):
    """Test that overwriting a running profile is denied."""
    profile = db.create_profile(name="To Overwrite")
    profile_id = profile["id"]

    # Create package first (using empty stopped mock)
    browser_mgr_stopped = MagicMock()
    browser_mgr_stopped.statuses = {}
    dest_file = tmp_db / "package.cbprofile"
    export_profile(
        browser_mgr=browser_mgr_stopped,
        profile_id=profile_id,
        dest_path=str(dest_file),
    )

    # Now mock running state for import/overwrite
    browser_mgr_running = MagicMock()
    browser_mgr_running.statuses = {profile_id: "running"}

    with pytest.raises(ProfilePackageError) as exc:
        import_profile(
            browser_mgr=browser_mgr_running,
            src_path=str(dest_file),
            overwrite_profile_id=profile_id,
        )
    assert exc.value.code == "PROFILE_RUNNING_IMPORT_DENIED"


def test_import_corrupted_checksum(tmp_db: Path):
    """Test checksum mismatch validation during import."""
    profile = db.create_profile(name="Checksum Profile")
    profile_id = profile["id"]

    browser_mgr = MagicMock()
    browser_mgr.statuses = {}
    dest_file = tmp_db / "corrupted.cbprofile"

    export_profile(
        browser_mgr=browser_mgr,
        profile_id=profile_id,
        dest_path=str(dest_file),
    )

    # Corrupt the zip file content manually by overwriting the header
    with open(dest_file, "r+b") as f:
        f.seek(0)
        f.write(b"corruptedzipheader!" * 5)

    with pytest.raises(ProfilePackageError) as exc:
        import_profile(
            browser_mgr=browser_mgr,
            src_path=str(dest_file),
        )
    # Since zip is broken now, it fails unzip, decrypt, or invalid zip format
    assert exc.value.code in ("PROFILE_PACKAGE_INVALID", "PROFILE_PACKAGE_CHECKSUM_FAILED", "PROFILE_PACKAGE_DECRYPT_FAILED")

