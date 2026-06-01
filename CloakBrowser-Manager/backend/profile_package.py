import os
import json
import uuid
import shutil
import hashlib
import zipfile
import tempfile
import datetime
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.database import get_profile, get_proxy, create_profile, update_profile, get_db
from backend.logger_utils import log_activity, log_error

try:
    from cloakbrowser.config import CHROMIUM_VERSION
except ImportError:
    CHROMIUM_VERSION = "0.0.0-test"


class ProfilePackageError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _derive_fernet_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet key from a passphrase and a salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    import base64
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def _calculate_file_sha256(file_path: Path) -> str:
    """Calculate SHA256 of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _zip_dir(src_dir: Path, zip_file_path: Path):
    """Zip a directory recursively, preserving relative paths."""
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(src_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    rel_path = file_path.relative_to(src_dir)
                    zipf.write(file_path, rel_path)
                except Exception:
                    # Ignore temporary/locked files during zip
                    pass


def _unzip_file(zip_file_path: Path, dest_dir: Path):
    """Unzip a file into a destination directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_file_path, 'r') as zipf:
        zipf.extractall(dest_dir)


def export_profile(
    browser_mgr: Any,
    profile_id: str,
    dest_path: str,
    passphrase: Optional[str] = None,
    exported_by: str = "Admin",
    include_proxy_secret: bool = False,
) -> dict[str, Any]:
    """
    Export a profile into a .cbprofile package.
    """
    # 1. Verify running status
    status = browser_mgr.statuses.get(profile_id, "stopped")
    if status in ("starting", "running", "stopping"):
        log_error(
            module="profile_package",
            action="export",
            error_code="PROFILE_RUNNING_EXPORT_DENIED",
            message=f"Cannot export profile {profile_id} while it is {status}.",
            profile_id=profile_id,
        )
        raise ProfilePackageError("PROFILE_RUNNING_EXPORT_DENIED", "Cannot export a running profile.")

    # 2. Get profile & related config
    profile = get_profile(profile_id)
    if not profile:
        raise ProfilePackageError("PROFILE_PACKAGE_INVALID", "Profile not found in database.")

    proxy_data = None
    if profile.get("proxy_id"):
        proxy_data = get_proxy(profile["proxy_id"])
        if proxy_data and not include_proxy_secret:
            # Strip proxy password
            proxy_data = dict(proxy_data)
            proxy_data["password"] = None


    # 3. Setup temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        pkg_dir = temp_dir / "package"
        pkg_dir.mkdir()

        config_dir = pkg_dir / "config"
        config_dir.mkdir()

        profile_dir = pkg_dir / "profile"
        profile_dir.mkdir()

        # Serialize config files
        with open(config_dir / "profile.json", "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        fingerprint_fields = {
            "fingerprint_seed": profile.get("fingerprint_seed"),
            "platform": profile.get("platform"),
            "user_agent": profile.get("user_agent"),
            "screen_width": profile.get("screen_width"),
            "screen_height": profile.get("screen_height"),
            "gpu_vendor": profile.get("gpu_vendor"),
            "gpu_renderer": profile.get("gpu_renderer"),
            "hardware_concurrency": profile.get("hardware_concurrency"),
            "fingerprint_locked": profile.get("fingerprint_locked"),
        }
        with open(config_dir / "fingerprint.json", "w", encoding="utf-8") as f:
            json.dump(fingerprint_fields, f, indent=2, ensure_ascii=False)

        with open(config_dir / "proxy_ref.json", "w", encoding="utf-8") as f:
            json.dump(proxy_data, f, indent=2, ensure_ascii=False)

        browser_version_info = {
            "browser_family": "CloakBrowser",
            "browser_version": CHROMIUM_VERSION,
        }
        with open(config_dir / "browser_version.json", "w", encoding="utf-8") as f:
            json.dump(browser_version_info, f, indent=2, ensure_ascii=False)

        # Zip user data directory
        user_data_path = Path(profile["user_data_dir"])
        user_data_zip = profile_dir / "user_data_dir.zip"
        if user_data_path.exists():
            _zip_dir(user_data_path, user_data_zip)
        else:
            # Create an empty zip if user_data_dir doesn't exist
            with zipfile.ZipFile(user_data_zip, 'w') as empty_zip:
                pass

        # 4. Generate metadata.json
        metadata = {
            "package_version": "1.0",
            "profile_id": profile_id,
            "profile_name": profile.get("name"),
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "exported_by": exported_by,
            "browser_family": "CloakBrowser",
            "browser_version": CHROMIUM_VERSION,
            "includes": {
                "profile_data": True,
                "fingerprint_config": True,
                "proxy_config": proxy_data is not None,
                "cookies": True,
                "localStorage": True,
                "indexedDB": True
            }
        }
        with open(pkg_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 5. Validate checksums & write checksum.sha256
        checksums = {}
        for root, _, files in os.walk(pkg_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(pkg_dir)
                if rel_path.name == "checksum.sha256":
                    continue
                checksums[str(rel_path)] = _calculate_file_sha256(file_path)

        with open(pkg_dir / "checksum.sha256", "w", encoding="utf-8") as f:
            json.dump(checksums, f, indent=2, ensure_ascii=False)

        # Zip the package directory itself
        raw_zip_path = temp_dir / "package.zip"
        _zip_dir(pkg_dir, raw_zip_path)

        # 6. Encryption
        if passphrase:
            salt = os.urandom(16)
            key = _derive_fernet_key(passphrase, salt)
            fernet = Fernet(key)

            with open(raw_zip_path, "rb") as f:
                raw_bytes = f.read()

            encrypted_bytes = fernet.encrypt(raw_bytes)

            dest_path_p = Path(dest_path)
            dest_path_p.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path_p, "wb") as f:
                f.write(salt + encrypted_bytes)
        else:
            dest_path_p = Path(dest_path)
            dest_path_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raw_zip_path, dest_path_p)

    log_activity(
        module="profile_package",
        action="export",
        status="success",
        message="Profile package exported successfully",
        profile_id=profile_id,
    )
    return {
        "status": "PROFILE_PACKAGE_EXPORTED",
        "profile_id": profile_id,
        "dest_path": dest_path,
    }


def import_profile(
    browser_mgr: Any,
    src_path: str,
    passphrase: Optional[str] = None,
    overwrite_profile_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Import a profile from a .cbprofile package.
    """
    src_path_p = Path(src_path)
    if not src_path_p.exists():
        raise ProfilePackageError("PROFILE_PACKAGE_INVALID", "Source file does not exist.")

    # 1. Verify target running status if overwriting
    if overwrite_profile_id:
        status = browser_mgr.statuses.get(overwrite_profile_id, "stopped")
        if status in ("starting", "running", "stopping"):
            log_error(
                module="profile_package",
                action="import",
                error_code="PROFILE_RUNNING_IMPORT_DENIED",
                message=f"Cannot overwrite profile {overwrite_profile_id} while it is {status}.",
                profile_id=overwrite_profile_id,
            )
            raise ProfilePackageError("PROFILE_RUNNING_IMPORT_DENIED", "Cannot overwrite a running profile.")

    # 2. Decrypt & Unzip
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        pkg_zip = temp_dir / "package.zip"

        is_encrypted = False
        # Let's inspect the first few bytes. A ZIP file starts with b'PK\x03\x04'.
        with open(src_path_p, "rb") as f:
            header = f.read(4)

        if header != b'PK\x03\x04':
            is_encrypted = True

        if is_encrypted:
            if not passphrase:
                raise ProfilePackageError("PROFILE_PACKAGE_DECRYPT_FAILED", "Passphrase is required for encrypted package.")

            try:
                with open(src_path_p, "rb") as f:
                    file_bytes = f.read()

                salt = file_bytes[:16]
                encrypted_bytes = file_bytes[16:]

                key = _derive_fernet_key(passphrase, salt)
                fernet = Fernet(key)
                decrypted_bytes = fernet.decrypt(encrypted_bytes)

                with open(pkg_zip, "wb") as f:
                    f.write(decrypted_bytes)
            except Exception as e:
                log_error(
                    module="profile_package",
                    action="import",
                    error_code="PROFILE_PACKAGE_DECRYPT_FAILED",
                    message="Failed to decrypt the profile package.",
                )
                raise ProfilePackageError("PROFILE_PACKAGE_DECRYPT_FAILED", "Decryption failed or invalid passphrase.")
        else:
            shutil.copy2(src_path_p, pkg_zip)

        # Unzip structure
        pkg_dir = temp_dir / "package"
        pkg_dir.mkdir()
        try:
            _unzip_file(pkg_zip, pkg_dir)
        except Exception:
            raise ProfilePackageError("PROFILE_PACKAGE_INVALID", "Invalid zip format.")

        # 3. Check metadata and checksums
        meta_path = pkg_dir / "metadata.json"
        checksum_path = pkg_dir / "checksum.sha256"

        if not meta_path.exists() or not checksum_path.exists():
            raise ProfilePackageError("PROFILE_PACKAGE_INVALID", "Missing metadata or checksums in package.")

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        with open(checksum_path, "r", encoding="utf-8") as f:
            saved_checksums = json.load(f)

        # Validate checksums
        for rel_path_str, expected_sha in saved_checksums.items():
            full_path = pkg_dir / rel_path_str
            if not full_path.exists():
                raise ProfilePackageError("PROFILE_PACKAGE_CHECKSUM_FAILED", f"Missing file: {rel_path_str}")
            actual_sha = _calculate_file_sha256(full_path)
            if actual_sha != expected_sha:
                raise ProfilePackageError("PROFILE_PACKAGE_CHECKSUM_FAILED", f"Checksum mismatch for file: {rel_path_str}")

        # 4. Import configuration
        profile_json_path = pkg_dir / "config" / "profile.json"
        if not profile_json_path.exists():
            raise ProfilePackageError("PROFILE_PACKAGE_INVALID", "Missing profile configuration in package.")

        with open(profile_json_path, "r", encoding="utf-8") as f:
            imported_profile = json.load(f)

        # Generate target ID and directory
        if overwrite_profile_id:
            target_profile_id = overwrite_profile_id
            existing = get_profile(target_profile_id)
            if not existing:
                raise ProfilePackageError("PROFILE_PACKAGE_INVALID", f"Target profile {target_profile_id} not found to overwrite.")
            target_user_data_dir = Path(existing["user_data_dir"])
        else:
            target_profile_id = str(uuid.uuid4())
            from backend.database import DATA_DIR
            target_user_data_dir = DATA_DIR / "profiles" / target_profile_id

        # Extracted user data zip
        user_data_zip = pkg_dir / "profile" / "user_data_dir.zip"
        if target_user_data_dir.exists():
            shutil.rmtree(target_user_data_dir, ignore_errors=True)

        target_user_data_dir.mkdir(parents=True, exist_ok=True)
        if user_data_zip.exists():
            try:
                _unzip_file(user_data_zip, target_user_data_dir)
            except Exception:
                raise ProfilePackageError("PROFILE_PACKAGE_INVALID", "Failed to extract profile browser data.")

        # Re-save config metadata in DB
        fields_to_save = {
            "name": imported_profile.get("name", metadata.get("profile_name", "Imported Profile")),
            "fingerprint_seed": imported_profile.get("fingerprint_seed"),
            "proxy": imported_profile.get("proxy"),
            "proxy_id": imported_profile.get("proxy_id"),
            "timezone": imported_profile.get("timezone"),
            "locale": imported_profile.get("locale"),
            "platform": imported_profile.get("platform", "windows"),
            "user_agent": imported_profile.get("user_agent"),
            "screen_width": imported_profile.get("screen_width", 1920),
            "screen_height": imported_profile.get("screen_height", 1080),
            "gpu_vendor": imported_profile.get("gpu_vendor"),
            "gpu_renderer": imported_profile.get("gpu_renderer"),
            "hardware_concurrency": imported_profile.get("hardware_concurrency"),
            "humanize": imported_profile.get("humanize", False),
            "human_preset": imported_profile.get("human_preset", "default"),
            "headless": imported_profile.get("headless", False),
            "geoip": imported_profile.get("geoip", False),
            "clipboard_sync": imported_profile.get("clipboard_sync", True),
            "auto_launch": imported_profile.get("auto_launch", False),
            "color_scheme": imported_profile.get("color_scheme"),
            "launch_args": imported_profile.get("launch_args") or [],
            "notes": imported_profile.get("notes"),
            "tags": imported_profile.get("tags") or [],
            "fingerprint_locked": imported_profile.get("fingerprint_locked", True),
            "session_auto_save": imported_profile.get("session_auto_save", True),
            "auto_sync_timezone_with_proxy": imported_profile.get("auto_sync_timezone_with_proxy", False),
            "auto_sync_locale_with_proxy": imported_profile.get("auto_sync_locale_with_proxy", False),
            "auto_sync_geolocation_with_proxy": imported_profile.get("auto_sync_geolocation_with_proxy", False),
        }

        # Safe update/insert using DB
        if overwrite_profile_id:
            update_profile(target_profile_id, **fields_to_save)
        else:
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO profiles (
                        id, name, fingerprint_seed, proxy, proxy_id, timezone, locale, platform,
                        user_agent, screen_width, screen_height, gpu_vendor, gpu_renderer,
                        hardware_concurrency, humanize, human_preset, headless, geoip,
                        clipboard_sync, auto_launch, color_scheme, launch_args, notes,
                        user_data_dir, created_at, updated_at,
                        fingerprint_locked, session_auto_save,
                        auto_sync_timezone_with_proxy, auto_sync_locale_with_proxy, auto_sync_geolocation_with_proxy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        target_profile_id,
                        fields_to_save["name"],
                        fields_to_save["fingerprint_seed"],
                        fields_to_save["proxy"],
                        fields_to_save["proxy_id"],
                        fields_to_save["timezone"],
                        fields_to_save["locale"],
                        fields_to_save["platform"],
                        fields_to_save["user_agent"],
                        fields_to_save["screen_width"],
                        fields_to_save["screen_height"],
                        fields_to_save["gpu_vendor"],
                        fields_to_save["gpu_renderer"],
                        fields_to_save["hardware_concurrency"],
                        fields_to_save["humanize"],
                        fields_to_save["human_preset"],
                        fields_to_save["headless"],
                        fields_to_save["geoip"],
                        fields_to_save["clipboard_sync"],
                        fields_to_save["auto_launch"],
                        fields_to_save["color_scheme"],
                        json.dumps(fields_to_save["launch_args"]),
                        fields_to_save["notes"],
                        str(target_user_data_dir),
                        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        fields_to_save["fingerprint_locked"],
                        fields_to_save["session_auto_save"],
                        fields_to_save["auto_sync_timezone_with_proxy"],
                        fields_to_save["auto_sync_locale_with_proxy"],
                        fields_to_save["auto_sync_geolocation_with_proxy"],
                    )
                )
                # Re-add tags
                conn.execute("DELETE FROM profile_tags WHERE profile_id = ?", (target_profile_id,))
                for t in fields_to_save["tags"]:
                    conn.execute(
                        "INSERT INTO profile_tags (profile_id, tag, color) VALUES (?, ?, ?)",
                        (target_profile_id, t["tag"], t.get("color")),
                    )
                conn.commit()

    log_activity(
        module="profile_package",
        action="import",
        status="success",
        message="Profile package imported successfully",
        profile_id=target_profile_id,
    )
    return {
        "status": "PROFILE_PACKAGE_IMPORTED",
        "profile_id": target_profile_id,
    }
