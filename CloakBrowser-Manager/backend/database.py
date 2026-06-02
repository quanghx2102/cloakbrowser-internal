"""SQLite database operations for browser profiles."""

from __future__ import annotations

import datetime
import json
import random
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import os
import platform

def _get_default_data_dir() -> Path:
    env_dir = os.environ.get("APP_DATA_DIR") or os.environ.get("CLOAK_DATA_DIR")
    if env_dir:
        path_obj = Path(env_dir).resolve()
        print(f"[Lifecycle] FastAPI using APP_DATA_DIR: {path_obj}")
        return path_obj
        
    system = platform.system()
    if system == "Darwin":
        path_obj = Path.home() / "Library" / "Application Support" / "CloakInternalTool"
    elif system == "Windows":
        app_data = os.environ.get("APPDATA")
        if app_data:
            path_obj = Path(app_data) / "CloakInternalTool"
        else:
            path_obj = Path.home() / "AppData" / "Roaming" / "CloakInternalTool"
    else:
        path_obj = Path.home() / ".config" / "cloakinternaltool"
        
    print(f"[Lifecycle] FastAPI using default APP_DATA_DIR: {path_obj}")
    return path_obj

DATA_DIR = _get_default_data_dir()
DB_PATH = DATA_DIR / "database" / "profiles.db"
BACKUP_DIR = DATA_DIR / "backups"


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                fingerprint_seed INTEGER NOT NULL,
                proxy TEXT,
                timezone TEXT,
                locale TEXT,
                platform TEXT DEFAULT 'windows',
                user_agent TEXT,
                screen_width INTEGER DEFAULT 1920,
                screen_height INTEGER DEFAULT 1080,
                gpu_vendor TEXT,
                gpu_renderer TEXT,
                hardware_concurrency INTEGER,
                humanize BOOLEAN DEFAULT 0,
                human_preset TEXT DEFAULT 'default',
                headless BOOLEAN DEFAULT 0,
                geoip BOOLEAN DEFAULT 0,
                clipboard_sync BOOLEAN DEFAULT 1,
                auto_launch BOOLEAN DEFAULT 0,
                color_scheme TEXT,
                notes TEXT,
                user_data_dir TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_launched TEXT,
                fingerprint_locked BOOLEAN DEFAULT 1,
                session_auto_save BOOLEAN DEFAULT 1,
                auto_sync_timezone_with_proxy BOOLEAN DEFAULT 0,
                auto_sync_locale_with_proxy BOOLEAN DEFAULT 0,
                auto_sync_geolocation_with_proxy BOOLEAN DEFAULT 0,
                last_fingerprint_change_at TEXT,
                last_session_save_at TEXT,
                last_proxy_change_at TEXT,
                proxy_mode TEXT DEFAULT 'static_residential',
                expected_exit_ip TEXT,
                expected_country TEXT,
                expected_asn TEXT,
                allow_ip_rotation BOOLEAN DEFAULT 0,
                allowed_rotation_scope TEXT DEFAULT 'same_ip',
                proxy_sticky_session_ttl_minutes INTEGER,
                verification_expires_on_proxy_change BOOLEAN DEFAULT 1,
                verification_status TEXT DEFAULT 'unverified',
                last_verified_at TEXT,
                last_verification_result TEXT,
                require_verification_before_use BOOLEAN DEFAULT 1,
                verification_expires_minutes INTEGER DEFAULT 60,
                runtime_guardian_enabled BOOLEAN DEFAULT 1,
                runtime_guardian_status TEXT DEFAULT 'idle',
                runtime_risk_level TEXT DEFAULT 'normal',
                last_runtime_check_at TEXT,
                last_runtime_check_result TEXT,
                runtime_check_interval_seconds INTEGER DEFAULT 60,
                deep_check_interval_minutes INTEGER DEFAULT 10,
                runtime_action_on_critical TEXT DEFAULT 'stop_profile',
                last_runtime_issue TEXT,
                last_runtime_message TEXT
            );

            CREATE TABLE IF NOT EXISTS profile_tags (
                profile_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                color TEXT,
                PRIMARY KEY (profile_id, tag)
            );

            CREATE TABLE IF NOT EXISTS proxies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'http',
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT,
                password TEXT,
                status TEXT DEFAULT 'active',
                latency_ms INTEGER,
                last_ip TEXT,
                last_checked_at TEXT,
                timezone TEXT,
                locale TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                error_code TEXT,
                message TEXT,
                profile_id TEXT,
                proxy_id TEXT,
                duration_ms INTEGER
            );
        """)
        conn.commit()

    with get_db() as conn:
        # Migrations for existing databases
        cols = {row[1] for row in conn.execute("PRAGMA table_info(profiles)").fetchall()}
        if "clipboard_sync" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN clipboard_sync BOOLEAN DEFAULT 1")
            conn.commit()
        if "launch_args" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN launch_args TEXT DEFAULT '[]'")
            conn.commit()
        if "auto_launch" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN auto_launch BOOLEAN DEFAULT 0")
            conn.commit()
        if "last_launched" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_launched TEXT")
            conn.commit()
        if "proxy_id" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN proxy_id TEXT REFERENCES proxies(id) ON DELETE SET NULL")
            conn.commit()
        if "fingerprint_locked" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN fingerprint_locked BOOLEAN DEFAULT 1")
            conn.commit()
        if "session_auto_save" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN session_auto_save BOOLEAN DEFAULT 1")
            conn.commit()
        if "auto_sync_timezone_with_proxy" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN auto_sync_timezone_with_proxy BOOLEAN DEFAULT 0")
            conn.commit()
        if "auto_sync_locale_with_proxy" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN auto_sync_locale_with_proxy BOOLEAN DEFAULT 0")
            conn.commit()
        if "auto_sync_geolocation_with_proxy" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN auto_sync_geolocation_with_proxy BOOLEAN DEFAULT 0")
            conn.commit()
        if "last_fingerprint_change_at" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_fingerprint_change_at TEXT")
            conn.commit()
        if "last_session_save_at" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_session_save_at TEXT")
            conn.commit()
        if "last_proxy_change_at" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_proxy_change_at TEXT")
            conn.commit()
        if "proxy_mode" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN proxy_mode TEXT DEFAULT 'static_residential'")
            conn.commit()
        if "expected_exit_ip" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN expected_exit_ip TEXT")
            conn.commit()
        if "expected_country" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN expected_country TEXT")
            conn.commit()
        if "expected_asn" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN expected_asn TEXT")
            conn.commit()
        if "allow_ip_rotation" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN allow_ip_rotation BOOLEAN DEFAULT 0")
            conn.commit()
        if "allowed_rotation_scope" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN allowed_rotation_scope TEXT DEFAULT 'same_ip'")
            conn.commit()
        if "proxy_sticky_session_ttl_minutes" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN proxy_sticky_session_ttl_minutes INTEGER")
            conn.commit()
        if "verification_expires_on_proxy_change" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN verification_expires_on_proxy_change BOOLEAN DEFAULT 1")
            conn.commit()
        if "verification_status" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN verification_status TEXT DEFAULT 'unverified'")
            conn.commit()
        if "last_verified_at" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_verified_at TEXT")
            conn.commit()
        if "last_verification_result" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_verification_result TEXT")
            conn.commit()
        if "require_verification_before_use" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN require_verification_before_use BOOLEAN DEFAULT 1")
            conn.commit()
        if "verification_expires_minutes" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN verification_expires_minutes INTEGER DEFAULT 60")
            conn.commit()
        if "runtime_guardian_enabled" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN runtime_guardian_enabled BOOLEAN DEFAULT 1")
            conn.commit()
        if "runtime_guardian_status" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN runtime_guardian_status TEXT DEFAULT 'idle'")
            conn.commit()
        if "runtime_risk_level" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN runtime_risk_level TEXT DEFAULT 'normal'")
            conn.commit()
        if "last_runtime_check_at" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_runtime_check_at TEXT")
            conn.commit()
        if "last_runtime_check_result" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_runtime_check_result TEXT")
            conn.commit()
        if "runtime_check_interval_seconds" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN runtime_check_interval_seconds INTEGER DEFAULT 60")
            conn.commit()
        if "deep_check_interval_minutes" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN deep_check_interval_minutes INTEGER DEFAULT 10")
            conn.commit()
        if "runtime_action_on_critical" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN runtime_action_on_critical TEXT DEFAULT 'stop_profile'")
            conn.commit()
        if "last_runtime_issue" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_runtime_issue TEXT")
            conn.commit()
        if "last_runtime_message" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN last_runtime_message TEXT")
            conn.commit()
            
        proxy_cols = {row[1] for row in conn.execute("PRAGMA table_info(proxies)").fetchall()}
        if "latency_ms" not in proxy_cols:
            conn.execute("ALTER TABLE proxies ADD COLUMN latency_ms INTEGER")
            conn.execute("ALTER TABLE proxies ADD COLUMN last_ip TEXT")
            conn.execute("ALTER TABLE proxies ADD COLUMN last_checked_at TEXT")
            conn.commit()
        if "timezone" not in proxy_cols:
            conn.execute("ALTER TABLE proxies ADD COLUMN timezone TEXT")
            conn.execute("ALTER TABLE proxies ADD COLUMN locale TEXT")
            conn.commit()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def create_profile(
    name: str,
    fingerprint_seed: int | None = None,
    **fields: Any,
) -> dict[str, Any]:
    profile_id = str(uuid.uuid4())
    seed = fingerprint_seed if fingerprint_seed is not None else random.randint(10000, 99999)
    user_data_dir = str(DATA_DIR / "profiles" / profile_id)
    now = _now()
    tags = fields.pop("tags", None) or []

    with get_db() as conn:
        conn.execute(
            """INSERT INTO profiles (
                id, name, fingerprint_seed, proxy, proxy_id, timezone, locale, platform,
                user_agent, screen_width, screen_height, gpu_vendor, gpu_renderer,
                hardware_concurrency, humanize, human_preset, headless, geoip,
                clipboard_sync, auto_launch, color_scheme, launch_args, notes,
                user_data_dir, created_at, updated_at,
                fingerprint_locked, session_auto_save,
                auto_sync_timezone_with_proxy, auto_sync_locale_with_proxy, auto_sync_geolocation_with_proxy,
                last_fingerprint_change_at, last_session_save_at, last_proxy_change_at,
                proxy_mode, expected_exit_ip, expected_country, expected_asn,
                allow_ip_rotation, allowed_rotation_scope, proxy_sticky_session_ttl_minutes,
                verification_expires_on_proxy_change,
                verification_status, last_verified_at, last_verification_result,
                require_verification_before_use, verification_expires_minutes,
                 runtime_guardian_enabled, runtime_guardian_status, runtime_risk_level,
                 last_runtime_check_at, last_runtime_check_result, runtime_check_interval_seconds,
                 deep_check_interval_minutes,
                 runtime_action_on_critical, last_runtime_issue, last_runtime_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            , (
                profile_id, name, seed,
                fields.get("proxy"),
                fields.get("proxy_id"),
                fields.get("timezone"),
                fields.get("locale"),
                fields.get("platform", "windows"),
                fields.get("user_agent"),
                fields.get("screen_width", 1920),
                fields.get("screen_height", 1080),
                fields.get("gpu_vendor"),
                fields.get("gpu_renderer"),
                fields.get("hardware_concurrency"),
                fields.get("humanize", False),
                fields.get("human_preset", "default"),
                fields.get("headless", False),
                fields.get("geoip", False),
                fields.get("clipboard_sync", True),
                fields.get("auto_launch", False),
                fields.get("color_scheme"),
                json.dumps(fields.get("launch_args") or []),
                fields.get("notes"),
                user_data_dir, now, now,
                fields.get("fingerprint_locked", True),
                fields.get("session_auto_save", True),
                fields.get("auto_sync_timezone_with_proxy", False),
                fields.get("auto_sync_locale_with_proxy", False),
                fields.get("auto_sync_geolocation_with_proxy", False),
                now if fingerprint_seed is not None else None,
                None,
                now if (fields.get("proxy") or fields.get("proxy_id")) else None,
                fields.get("proxy_mode", "static_residential"),
                fields.get("expected_exit_ip"),
                fields.get("expected_country"),
                fields.get("expected_asn"),
                fields.get("allow_ip_rotation", False),
                fields.get("allowed_rotation_scope", "same_ip"),
                fields.get("proxy_sticky_session_ttl_minutes"),
                fields.get("verification_expires_on_proxy_change", True),
                fields.get("verification_status", "unverified"),
                fields.get("last_verified_at"),
                fields.get("last_verification_result"),
                fields.get("require_verification_before_use", True),
                fields.get("verification_expires_minutes", 60),
                fields.get("runtime_guardian_enabled", True),
                fields.get("runtime_guardian_status", "idle"),
                fields.get("runtime_risk_level", "normal"),
                fields.get("last_runtime_check_at"),
                fields.get("last_runtime_check_result"),
                fields.get("runtime_check_interval_seconds", 60),
                fields.get("deep_check_interval_minutes", 10),
                fields.get("runtime_action_on_critical", "stop_profile"),
                fields.get("last_runtime_issue"),
                fields.get("last_runtime_message"),
            ),
        )
        for t in tags:
            conn.execute(
                "INSERT INTO profile_tags (profile_id, tag, color) VALUES (?, ?, ?)",
                (profile_id, t["tag"], t.get("color")),
            )
        conn.commit()

    return get_profile(profile_id)  # type: ignore[return-value]


def get_profile(profile_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            return None
        profile = dict(row)
        profile["launch_args"] = json.loads(profile.get("launch_args") or "[]")
        tags = conn.execute(
            "SELECT tag, color FROM profile_tags WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        profile["tags"] = [dict(t) for t in tags]
        return profile


def list_profiles() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
        profiles = []
        for row in rows:
            profile = dict(row)
            profile["launch_args"] = json.loads(profile.get("launch_args") or "[]")
            tags = conn.execute(
                "SELECT tag, color FROM profile_tags WHERE profile_id = ?",
                (profile["id"],),
            ).fetchall()
            profile["tags"] = [dict(t) for t in tags]
            profiles.append(profile)
        return profiles


def update_profile(profile_id: str, **fields: Any) -> dict[str, Any] | None:
    existing = get_profile(profile_id)
    if not existing:
        return None

    tags = fields.pop("tags", None)

    # Only update fields that were explicitly provided
    update_cols = []
    update_vals = []
    # Pre-serialize launch_args to JSON before the generic update loop
    if "launch_args" in fields:
        fields["launch_args"] = json.dumps(fields["launch_args"] or [])

    now = _now()
    if "fingerprint_seed" in fields and fields["fingerprint_seed"] != existing.get("fingerprint_seed"):
        fields["last_fingerprint_change_at"] = now
    if ("proxy" in fields and fields["proxy"] != existing.get("proxy")) or ("proxy_id" in fields and fields["proxy_id"] != existing.get("proxy_id")):
        fields["last_proxy_change_at"] = now

    for col in (
        "name", "fingerprint_seed", "proxy", "proxy_id", "timezone", "locale", "platform",
        "user_agent", "screen_width", "screen_height", "gpu_vendor", "gpu_renderer",
        "hardware_concurrency", "humanize", "human_preset", "headless", "geoip",
        "clipboard_sync", "auto_launch", "color_scheme", "launch_args", "notes",
        "fingerprint_locked", "session_auto_save",
        "auto_sync_timezone_with_proxy", "auto_sync_locale_with_proxy", "auto_sync_geolocation_with_proxy",
        "last_fingerprint_change_at", "last_session_save_at", "last_proxy_change_at",
        "proxy_mode", "expected_exit_ip", "expected_country", "expected_asn",
        "allow_ip_rotation", "allowed_rotation_scope", "proxy_sticky_session_ttl_minutes",
        "verification_expires_on_proxy_change",
        "verification_status", "last_verified_at", "last_verification_result",
        "require_verification_before_use", "verification_expires_minutes",
        "runtime_guardian_enabled", "runtime_guardian_status", "runtime_risk_level",
        "last_runtime_check_at", "last_runtime_check_result", "runtime_check_interval_seconds",
        "deep_check_interval_minutes",
        "runtime_action_on_critical", "last_runtime_issue", "last_runtime_message",
    ):
        if col in fields:
            update_cols.append(f"{col} = ?")
            update_vals.append(fields[col])

    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(_now())
        update_vals.append(profile_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE profiles SET {', '.join(update_cols)} WHERE id = ?",
                update_vals,
            )
            conn.commit()

    if tags is not None:
        with get_db() as conn:
            conn.execute("DELETE FROM profile_tags WHERE profile_id = ?", (profile_id,))
            for t in tags:
                conn.execute(
                    "INSERT INTO profile_tags (profile_id, tag, color) VALUES (?, ?, ?)",
                    (profile_id, t["tag"], t.get("color")),
                )
            conn.commit()

    return get_profile(profile_id)


def delete_profile(profile_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()
        return cursor.rowcount > 0


def set_last_launched(profile_id: str) -> None:
    """Update last_launched timestamp for a profile when it is launched."""
    with get_db() as conn:
        conn.execute(
            "UPDATE profiles SET last_launched = ? WHERE id = ?",
            (_now(), profile_id),
        )
        conn.commit()


# ── Proxy Management ──────────────────────────────────────────────────────────

def create_proxy(
    name: str,
    host: str,
    port: int,
    **fields: Any,
) -> dict[str, Any]:
    proxy_id = str(uuid.uuid4())
    now = _now()
    
    with get_db() as conn:
        conn.execute(
            """INSERT INTO proxies (
                id, name, type, host, port, username, password, status, timezone, locale, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proxy_id, name,
                fields.get("type", "http"),
                host, port,
                fields.get("username"),
                fields.get("password"),
                fields.get("status", "active"),
                fields.get("timezone"),
                fields.get("locale"),
                now, now,
            ),
        )
        conn.commit()
    return get_proxy(proxy_id)  # type: ignore[return-value]


def get_proxy(proxy_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM proxies WHERE id = ?", (proxy_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def list_proxies() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM proxies ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def update_proxy(proxy_id: str, **fields: Any) -> dict[str, Any] | None:
    existing = get_proxy(proxy_id)
    if not existing:
        return None

    update_cols = []
    update_vals = []

    for col in (
        "name", "type", "host", "port", "username", "password", 
        "status", "latency_ms", "last_ip", "last_checked_at",
        "timezone", "locale"
    ):
        if col in fields:
            update_cols.append(f"{col} = ?")
            update_vals.append(fields[col])

    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(_now())
        update_vals.append(proxy_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE proxies SET {', '.join(update_cols)} WHERE id = ?",
                update_vals,
            )
            conn.commit()

    return get_proxy(proxy_id)


def delete_proxy(proxy_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
        conn.commit()
        return cursor.rowcount > 0


# ── Logging Management ────────────────────────────────────────────────────────

def insert_log(log_entry: dict[str, Any]) -> None:
    """Insert a structured log entry into the database."""
    # Ensure ID exists
    log_id = log_entry.get("id") or str(uuid.uuid4())
    
    with get_db() as conn:
        conn.execute(
            """INSERT INTO logs (
                id, timestamp, level, module, action, status, 
                error_code, message, profile_id, proxy_id, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_id,
                log_entry.get("timestamp", _now()),
                log_entry.get("level", "info"),
                log_entry.get("module", "unknown"),
                log_entry.get("action", "unknown"),
                log_entry.get("status", "unknown"),
                log_entry.get("error_code"),
                log_entry.get("message"),
                log_entry.get("profile_id"),
                log_entry.get("proxy_id"),
                log_entry.get("duration_ms"),
            )
        )
        conn.commit()

def get_recent_errors(limit: int = 10) -> list[dict[str, Any]]:
    """Fetch recent error logs from the database."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT 
                id, timestamp, level, module, action, status, 
                error_code, message, profile_id, proxy_id, duration_ms
               FROM logs 
               WHERE level = 'error' 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

# ── Backup Management ─────────────────────────────────────────────────────────

def backup_database() -> str:
    """Create a safe backup of the SQLite database."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"profiles_backup_{timestamp}.db"
    
    with get_db() as conn:
        bck = sqlite3.connect(str(backup_file))
        with bck:
            conn.backup(bck)
        bck.close()
    
    return str(backup_file)

def list_backups() -> list[dict[str, Any]]:
    """List all available database backups."""
    if not BACKUP_DIR.exists():
        return []
    
    backups = []
    for f in BACKUP_DIR.glob("profiles_backup_*.db"):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": stat.st_size,
            "created_at": datetime.datetime.fromtimestamp(stat.st_ctime, datetime.timezone.utc).isoformat()
        })
    
    # Sort by created_at descending
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups

def backup_profile(profile_id: str) -> dict[str, Any]:
    """Backup a specific profile's user data directory to a zip file."""
    profile = get_profile(profile_id)
    if not profile:
        raise ValueError(f"Profile {profile_id} not found")
        
    user_data_dir = Path(profile["user_data_dir"])
    if not user_data_dir.exists():
        raise ValueError(f"Profile data directory {user_data_dir} does not exist")
        
    profile_backup_dir = BACKUP_DIR / "profiles"
    profile_backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"profile_{profile_id}_{timestamp}"
    backup_path = profile_backup_dir / backup_name
    
    import shutil
    # shutil.make_archive returns the path to the created archive
    archive_path = shutil.make_archive(str(backup_path), 'zip', root_dir=str(user_data_dir.parent), base_dir=user_data_dir.name)
    
    stat = Path(archive_path).stat()
    return {
        "filename": Path(archive_path).name,
        "path": archive_path,
        "size_bytes": stat.st_size,
        "type": "profile_folder",
        "created_at": datetime.datetime.fromtimestamp(stat.st_ctime, datetime.timezone.utc).isoformat(),
        "status": "success"
    }

def restore_database(backup_filename: str) -> bool:
    """Restore the database from a backup file."""
    backup_path = BACKUP_DIR / backup_filename
    if not backup_path.exists():
        raise ValueError(f"Backup file {backup_filename} not found")
        
    # Create safety backup first
    backup_database()
    
    with get_db() as conn:
        source_conn = sqlite3.connect(str(backup_path))
        with source_conn:
            # Copy from source_conn (backup) to conn (current db)
            source_conn.backup(conn)
        source_conn.close()
    return True

def restore_profile(profile_id: str, backup_filename: str) -> bool:
    """Restore a profile folder from a zip backup."""
    backup_path = BACKUP_DIR / "profiles" / backup_filename
    if not backup_path.exists():
        raise ValueError(f"Backup file {backup_filename} not found")
        
    profile = get_profile(profile_id)
    if not profile:
        raise ValueError(f"Profile {profile_id} not found")
        
    user_data_dir = Path(profile["user_data_dir"])
    
    # Create safety backup first if user_data_dir exists
    if user_data_dir.exists():
        backup_profile(profile_id)
        
    import shutil
    # Remove existing directory to ensure clean restore
    if user_data_dir.exists():
        shutil.rmtree(user_data_dir)
        
    user_data_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(backup_path), str(user_data_dir.parent))
    
    return True
