from __future__ import annotations
from typing import Any


def evaluate_proxy_policy(profile: dict[str, Any], current_proxy_result: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluates the proxy policy for a given profile based on current proxy check result.
    
    Returns a dict with 'status', 'error_code', 'message', and optional 'verification_expired'.
    """
    # 1. Check if proxy is connected successfully
    status_code = current_proxy_result.get("status_code")
    if status_code != "PROXY_OK":
        if status_code == "PROXY_AUTH_FAILED":
            return {
                "status": "critical",
                "error_code": "PROXY_AUTH_FAILED",
                "message": "Proxy authentication failed"
            }
        return {
            "status": "critical",
            "error_code": "PROXY_CONNECTION_FAILED",
            "message": f"Proxy connection failed with status: {status_code}"
        }

    current_ip = current_proxy_result.get("last_ip")
    current_country = current_proxy_result.get("country")
    current_asn = current_proxy_result.get("asn")

    expected_ip = profile.get("expected_exit_ip")
    expected_country = profile.get("expected_country")
    expected_asn = profile.get("expected_asn")

    # If expected_exit_ip is not set yet, it means the profile is not yet initialized / verified.
    # We allow it to pass but it should be verified/initialized.
    if not expected_ip:
        return {"status": "healthy"}

    allow_ip_rotation = bool(profile.get("allow_ip_rotation", False))
    allowed_rotation_scope = profile.get("allowed_rotation_scope", "same_ip")

    # If IP has not changed, it is always healthy
    if current_ip == expected_ip:
        return {"status": "healthy"}

    # IP has changed here!
    if not allow_ip_rotation:
        return {
            "status": "critical",
            "error_code": "PROXY_EXIT_IP_CHANGED",
            "message": f"Proxy exit IP changed from {expected_ip} to {current_ip} on static residential policy"
        }

    # IP rotation is allowed, check the scope
    if allowed_rotation_scope == "same_ip":
        # IP is allowed to rotate, but scope is restricted to same_ip which is a contradiction,
        # so treat as critical IP change.
        return {
            "status": "critical",
            "error_code": "PROXY_EXIT_IP_CHANGED",
            "message": f"Proxy exit IP changed from {expected_ip} to {current_ip} under same_ip constraint"
        }

    elif allowed_rotation_scope == "same_country":
        if expected_country and current_country != expected_country:
            return {
                "status": "critical",
                "error_code": "PROXY_COUNTRY_MISMATCH",
                "message": f"Proxy exit country changed from {expected_country} to {current_country}"
            }
        return {
            "status": "warning",
            "error_code": "PROXY_IP_ROTATED",
            "message": f"Proxy IP rotated within same country: {current_ip}",
            "verification_expired": True
        }

    elif allowed_rotation_scope == "same_asn":
        # Must match country as well as ASN
        if expected_country and current_country != expected_country:
            return {
                "status": "critical",
                "error_code": "PROXY_COUNTRY_MISMATCH",
                "message": f"Proxy exit country changed from {expected_country} to {current_country}"
            }
        if expected_asn and current_asn != expected_asn:
            return {
                "status": "critical",
                "error_code": "PROXY_ASN_MISMATCH",
                "message": f"Proxy ASN changed from {expected_asn} to {current_asn}"
            }
        return {
            "status": "warning",
            "error_code": "PROXY_IP_ROTATED",
            "message": f"Proxy IP rotated within same ASN: {current_ip}",
            "verification_expired": True
        }

    return {"status": "healthy"}


def can_launch_profile(profile: dict[str, Any], user_role: str) -> tuple[bool, str | None]:
    """
    Determines if a profile can be launched based on its verification status,
    expiration, and user role.
    
    Returns:
        (allowed: bool, error_code: str | None)
    """
    require_verification = bool(profile.get("require_verification_before_use", True))
    if not require_verification:
        return True, None

    status = profile.get("verification_status", "unverified")

    if status == "verified":
        last_verified_at = profile.get("last_verified_at")
        expires_minutes = profile.get("verification_expires_minutes", 60)
        if last_verified_at:
            import datetime
            try:
                verified_time = datetime.datetime.fromisoformat(last_verified_at)
                if verified_time.tzinfo is None:
                    now = datetime.datetime.now()
                else:
                    now = datetime.datetime.now(datetime.timezone.utc)
                elapsed = (now - verified_time).total_seconds() / 60.0
                if elapsed > expires_minutes:
                    from backend.database import update_profile
                    update_profile(profile["id"], verification_status="expired")
                    return False, "PROFILE_VERIFICATION_EXPIRED"
            except Exception:
                from backend.database import update_profile
                update_profile(profile["id"], verification_status="expired")
                return False, "PROFILE_VERIFICATION_EXPIRED"

    if status == "expired":
        return False, "PROFILE_VERIFICATION_EXPIRED"
    elif status in ("failed", "unverified"):
        return False, "PROFILE_VERIFICATION_FAILED" if status == "failed" else "LAUNCH_BLOCKED_VERIFICATION_REQUIRED"
    elif status == "warning":
        if user_role.lower() in ("admin", "super_admin"):
            return True, None
        else:
            return False, "LAUNCH_BLOCKED_VERIFICATION_REQUIRED"
    elif status == "checking":
        return False, "LAUNCH_BLOCKED_VERIFICATION_REQUIRED"

    return True, None

    return True, None


async def verify_profile_prelaunch(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Executes the full suite of pre-launch verification checks.
    """
    import time
    import httpx
    import os
    import sqlite3
    from pathlib import Path
    from backend.database import get_proxy

    errors = []
    warnings = []
    details = {
        "proxy": {"status": "skipped", "message": "No proxy configured"},
        "headers": {"status": "skipped"},
        "tls": {"status": "skipped"},
        "session": {"status": "passed"}
    }

    # 1. Resolve proxy settings
    proxy_url = None
    proxy_record = None
    if profile.get("proxy_id"):
        proxy_record = get_proxy(profile["proxy_id"])
    elif profile.get("proxy"):
        # Parse legacy string format "http://user:pass@host:port"
        from urllib.parse import urlparse
        try:
            parsed = urlparse(profile["proxy"])
            proxy_record = {
                "type": parsed.scheme or "http",
                "host": parsed.hostname,
                "port": parsed.port,
                "username": parsed.username,
                "password": parsed.password
            }
        except Exception:
            pass

    if proxy_record:
        ptype = proxy_record.get("type", "http")
        host = proxy_record["host"]
        port = proxy_record["port"]
        user = proxy_record.get("username")
        pwd = proxy_record.get("password")
        if user and pwd:
            proxy_url = f"{ptype}://{user}:{pwd}@{host}:{port}"
        else:
            proxy_url = f"{ptype}://{host}:{port}"

    # A. Proxy Check
    if proxy_url:
        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
                response = await client.get("http://ip-api.com/json/")
                if response.status_code == 407:
                    errors.append("PROXY_AUTH_FAILED")
                    details["proxy"] = {"status": "failed", "message": "Proxy authentication failed"}
                else:
                    response.raise_for_status()
                    data = response.json()
                    if data.get("status") == "success":
                        latency = int((time.monotonic() - start_time) * 1000)
                        current_ip = data.get("query")
                        current_country = data.get("countryCode")
                        current_asn = data.get("as")
                        details["proxy"] = {
                            "status": "passed",
                            "ip": current_ip,
                            "country": current_country,
                            "asn": current_asn,
                            "latency_ms": latency
                        }
                        # Compare Country Policy if static or expected is set
                        expected_country = profile.get("expected_country")
                        if expected_country and current_country != expected_country:
                            errors.append("PROXY_COUNTRY_MISMATCH")
                    else:
                        errors.append("PROXY_CONNECTION_FAILED")
                        details["proxy"] = {"status": "failed", "message": "Failed to retrieve GeoIP metadata"}
        except httpx.TimeoutException:
            errors.append("PROXY_CONNECTION_FAILED")
            details["proxy"] = {"status": "failed", "message": "Proxy connection timed out"}
        except Exception as e:
            errors.append("PROXY_CONNECTION_FAILED")
            details["proxy"] = {"status": "failed", "message": f"Proxy connection error: {e}"}

    # B. Header Check & C. Fingerprint Consistency Check
    if not errors:  # Only check headers if proxy is working or not set
        client_options = {}
        if proxy_url:
            client_options["proxy"] = proxy_url

        try:
            # Set profile's user-agent as requesting header to let httpbin echo it back
            headers = {}
            if profile.get("user_agent"):
                headers["User-Agent"] = profile["user_agent"]
            if profile.get("locale"):
                headers["Accept-Language"] = profile["locale"]

            async with httpx.AsyncClient(headers=headers, timeout=10.0, **client_options) as client:
                response = await client.get("https://httpbin.org/headers")
                response.raise_for_status()
                echoed_headers = response.json().get("headers", {})

                # Check UA consistency
                sent_ua = profile.get("user_agent")
                echoed_ua = echoed_headers.get("User-Agent")
                if sent_ua and echoed_ua and sent_ua != echoed_ua:
                    warnings.append("FINGERPRINT_UA_MISMATCH")
                    details["headers"]["ua_status"] = "warning"
                else:
                    details["headers"]["ua_status"] = "passed"

                # Check Locale consistency
                sent_locale = profile.get("locale")
                echoed_lang = echoed_headers.get("Accept-Language")
                if sent_locale and echoed_lang and sent_locale not in echoed_lang:
                    warnings.append("HEADERS_MISMATCH")
                    details["headers"]["locale_status"] = "warning"
                else:
                    details["headers"]["locale_status"] = "passed"

                details["headers"]["status"] = "passed"
        except Exception as e:
            warnings.append("HEADERS_MISMATCH")
            details["headers"] = {"status": "warning", "message": f"Failed to check headers: {e}"}

    # D. TLS/HTTP2 Check
    if not errors:
        client_options = {}
        if proxy_url:
            client_options["proxy"] = proxy_url

        try:
            async with httpx.AsyncClient(timeout=10.0, **client_options) as client:
                response = await client.get("https://tls.peet.ws/api/all")
                response.raise_for_status()
                details["tls"] = {"status": "passed", "data": response.json()}
        except Exception:
            warnings.append("TLS_CHECK_UNAVAILABLE")
            details["tls"] = {"status": "warning", "message": "TLS checker service is unavailable"}

    # E. Session Runtime Check
    user_data_dir = profile.get("user_data_dir")
    if user_data_dir:
        # Check folder structure
        p_dir = Path(user_data_dir)
        if p_dir.exists():
            # If cookies file exists, verify database integrity
            cookies_file = p_dir / "Default" / "Network" / "Cookies"
            if not cookies_file.exists():
                # Older Chromium profiles keep it directly in Default or profile root
                cookies_file = p_dir / "Default" / "Cookies"
            if not cookies_file.exists():
                cookies_file = p_dir / "Cookies"

            if cookies_file.exists():
                try:
                    conn = sqlite3.connect(str(cookies_file))
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    res = cursor.fetchone()
                    conn.close()
                    if not res or res[0] != "ok":
                        errors.append("SESSION_DATA_CORRUPTED")
                        details["session"] = {"status": "failed", "message": "Cookies database integrity check failed"}
                except Exception:
                    errors.append("SESSION_DATA_CORRUPTED")
                    details["session"] = {"status": "failed", "message": "Failed to open Cookies database"}

    # Evaluate final status
    status = "verified"
    if errors:
        status = "failed"
    elif warnings:
        status = "warning"

    import datetime
    return {
        "status": status,
        "last_verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "errors": errors,
        "warnings": warnings,
        "details": details
    }
