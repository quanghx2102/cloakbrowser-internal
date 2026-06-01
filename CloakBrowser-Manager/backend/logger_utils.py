from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

try:
    from . import database as db
except ImportError:
    import backend.database as db

logger = logging.getLogger("cloakbrowser.structured")

def _sanitize_message(message: str) -> str:
    """Basic sanitization to mask obvious passwords if they appear in URL format."""
    # We rely on proxy normalization masking in proxy_checker, but just in case
    import re
    # Mask pass in http://user:pass@host:port
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1***\3', message)

def _build_log_entry(
    level: str,
    module: str,
    action: str,
    status: str,
    message: str | None = None,
    error_code: str | None = None,
    profile_id: str | None = None,
    proxy_id: str | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    
    sanitized_msg = _sanitize_message(message) if message else None
    
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp": timestamp,
        "level": level,
        "module": module,
        "action": action,
        "status": status,
        "error_code": error_code,
        "message": sanitized_msg,
        "profile_id": profile_id,
        "proxy_id": proxy_id,
        "duration_ms": duration_ms,
    }

def log_activity(
    module: str,
    action: str,
    status: str,
    message: str | None = None,
    profile_id: str | None = None,
    proxy_id: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log an info-level activity event."""
    log_entry = _build_log_entry(
        level="info",
        module=module,
        action=action,
        status=status,
        message=message,
        profile_id=profile_id,
        proxy_id=proxy_id,
        duration_ms=duration_ms,
    )
    
    # Standard logging
    logger.info(json.dumps(log_entry))
    
    # DB persistence
    try:
        db.insert_log(log_entry)
    except Exception as e:
        logger.error(f"Failed to insert log to DB: {e}")

def log_error(
    module: str,
    action: str,
    error_code: str,
    message: str,
    profile_id: str | None = None,
    proxy_id: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log an error-level event."""
    log_entry = _build_log_entry(
        level="error",
        module=module,
        action=action,
        status="failed",
        error_code=error_code,
        message=message,
        profile_id=profile_id,
        proxy_id=proxy_id,
        duration_ms=duration_ms,
    )
    
    # Standard logging
    logger.error(json.dumps(log_entry))
    
    # DB persistence
    try:
        db.insert_log(log_entry)
    except Exception as e:
        logger.error(f"Failed to insert error log to DB: {e}")
