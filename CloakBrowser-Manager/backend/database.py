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
    env_dir = os.environ.get("CLOAK_DATA_DIR")
    if env_dir:
        return Path(env_dir)
        
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "CloakInternalTool"
    elif system == "Windows":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "CloakInternalTool"
        return Path.home() / "AppData" / "Roaming" / "CloakInternalTool"
    else:
        return Path.home() / ".config" / "cloakinternaltool"

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
                last_launched TEXT
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
                user_data_dir, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
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

    for col in (
        "name", "fingerprint_seed", "proxy", "proxy_id", "timezone", "locale", "platform",
        "user_agent", "screen_width", "screen_height", "gpu_vendor", "gpu_renderer",
        "hardware_concurrency", "humanize", "human_preset", "headless", "geoip",
        "clipboard_sync", "auto_launch", "color_scheme", "launch_args", "notes",
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
