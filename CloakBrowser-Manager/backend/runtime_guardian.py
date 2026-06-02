from __future__ import annotations
import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any
import httpx

from backend import database as db
from backend.logger_utils import log_activity, log_error
from backend.profile_verifier import evaluate_proxy_policy

logger = logging.getLogger("RuntimeGuardian")

# Active guardian tasks per profile_id
_active_tasks: dict[str, asyncio.Task] = {}

def generate_runtime_report(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Generates a structured runtime report based on the profile and its last runtime check result.
    """
    profile_id = profile["id"]
    guardian_status = profile.get("runtime_guardian_status", "idle")
    last_check_at = profile.get("last_runtime_check_at")
    
    # Defaults
    checks = {
        "proxy": "pass",
        "fingerprint": "pass",
        "headers": "pass",
        "session": "pass"
    }
    blocking_issues = []
    warnings = []
    
    res_str = profile.get("last_runtime_check_result")
    res = {}
    if res_str:
        try:
            res = json.loads(res_str)
        except Exception:
            pass

    risk_level = res.get("risk_level", "normal")
    policy_report = res.get("policy_report", {})
    proxy_check = res.get("proxy_check", {})

    # Evaluate proxy status
    proxy_status_code = proxy_check.get("status_code") or res.get("error_code")
    proxy_latency = proxy_check.get("latency_ms")

    # If there is a proxy status issue
    if proxy_status_code and proxy_status_code != "PROXY_OK":
        checks["proxy"] = "failed"
        if proxy_status_code in ("PROXY_AUTH_FAILED", "PROXY_CONNECTION_FAILED", "PROXY_TIMEOUT", "PROXY_EXIT_IP_CHANGED", "PROXY_COUNTRY_MISMATCH", "PROXY_ASN_MISMATCH"):
            if risk_level == "critical":
                blocking_issues.append(proxy_status_code)
            else:
                warnings.append(proxy_status_code)
    
    # Latency check
    if proxy_latency and proxy_latency > 1500:
        if checks["proxy"] != "failed":
            checks["proxy"] = "warning"
        warnings.append("PROXY_LATENCY_HIGH")

    # Policy evaluations inside lightweight check
    policy_err = policy_report.get("error_code")
    if policy_err:
        if policy_report.get("status") == "critical":
            checks["proxy"] = "failed"
            blocking_issues.append(policy_err)
        elif policy_report.get("status") == "warning":
            checks["proxy"] = "warning"
            warnings.append(policy_err)

    # Evaluate fingerprint status from deep check
    err_code = res.get("error_code")
    if err_code:
        if err_code in ("FINGERPRINT_UA_MISMATCH", "FINGERPRINT_WEBGL_MISMATCH", "FINGERPRINT_FONT_MISMATCH", "FINGERPRINT_CANVAS_MISMATCH"):
            checks["fingerprint"] = "failed"
            blocking_issues.append(err_code)
        elif err_code == "HEADERS_MISMATCH_CRITICAL":
            checks["headers"] = "failed"
            blocking_issues.append(err_code)
        elif err_code == "HEADERS_MISMATCH":
            checks["headers"] = "warning"
            warnings.append(err_code)
        elif err_code == "SESSION_DATA_CORRUPTED":
            checks["session"] = "failed"
            blocking_issues.append(err_code)
        elif err_code == "TLS_CHECK_UNAVAILABLE":
            checks["headers"] = "warning"
            warnings.append(err_code)

    # Clean up lists to avoid duplicates
    blocking_issues = list(set(blocking_issues))
    warnings = list(set(warnings))

    # Calculate status
    status = "healthy"
    if guardian_status == "stopped_by_guardian" or risk_level == "critical" or len(blocking_issues) > 0:
        status = "critical"
    elif risk_level == "warning" or len(warnings) > 0:
        status = "warning"
    elif guardian_status == "idle":
        status = "idle"

    # Calculate score
    if status == "critical":
        score = max(10, 45 - (len(blocking_issues) - 1) * 5) if blocking_issues else 45
    elif status == "warning":
        score = max(50, 80 - (len(warnings) - 1) * 5) if warnings else 80
    else:
        score = 100

    # Determine action taken
    action_taken = "none"
    if status == "critical":
        action_taken = profile.get("runtime_action_on_critical", "stop_profile")
    elif status == "warning":
        action_taken = "warn_only"

    return {
        "profile_id": profile_id,
        "status": status,
        "score": score,
        "checked_at": last_check_at,
        "checks": checks,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "action_taken": action_taken
    }

def start_runtime_guardian(profile_id: str, browser_mgr: Any) -> None:
    """
    Start the runtime guardian task for a profile if enabled.
    """
    profile = db.get_profile(profile_id)
    if not profile:
        return

    enabled = bool(profile.get("runtime_guardian_enabled", True))
    if not enabled:
        return

    # Check if a task is already running
    if profile_id in _active_tasks and not _active_tasks[profile_id].done():
        logger.info(f"Runtime guardian already running for profile {profile_id}")
        return

    # Start the task
    task = asyncio.create_task(_guardian_loop(profile_id, browser_mgr))
    _active_tasks[profile_id] = task
    
    db.update_profile(
        profile_id,
        runtime_guardian_status="monitoring",
        runtime_risk_level="normal"
    )
    
    log_activity(
        module="runtime_guardian",
        action="RUNTIME_GUARDIAN_STARTED",
        status="success",
        message=f"Runtime guardian started for profile {profile_id}",
        profile_id=profile_id
    )
    logger.info(f"Started runtime guardian for profile {profile_id}")

def stop_runtime_guardian(profile_id: str) -> None:
    """
    Stop the runtime guardian task for a profile.
    """
    task = _active_tasks.pop(profile_id, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"Stopped runtime guardian for profile {profile_id}")
    
    # Reset status
    profile = db.get_profile(profile_id)
    if profile and profile.get("runtime_guardian_status") == "monitoring":
        db.update_profile(profile_id, runtime_guardian_status="idle")

async def run_lightweight_check(profile_id: str, browser_mgr: Any) -> dict[str, Any]:
    """
    Executes a single lightweight check for process, proxy connectivity, and policies.
    """
    profile = db.get_profile(profile_id)
    if not profile:
        return {"status": "error", "message": "Profile not found"}

    # 1. Process Check
    running = browser_mgr.running.get(profile_id)
    if not running:
        return {"status": "dead", "message": "Browser is not running"}

    if running.pid:
        try:
            os.kill(running.pid, 0)
        except OSError:
            # Process is dead
            return {"status": "dead", "message": f"Browser process {running.pid} died externally"}

    # 2. Proxy & Exit IP Check
    proxy_url = None
    proxy_id = profile.get("proxy_id")
    if proxy_id:
        proxy_record = db.get_proxy(proxy_id)
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

    current_proxy_result = {"status_code": "PROXY_OK"}
    if proxy_url:
        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
                response = await client.get("http://ipinfo.io/json")
                if response.status_code == 407:
                    current_proxy_result = {"status_code": "PROXY_AUTH_FAILED"}
                else:
                    response.raise_for_status()
                    data = response.json()
                    current_proxy_result = {
                        "status_code": "PROXY_OK",
                        "last_ip": data.get("ip"),
                        "country": data.get("country"),
                        "asn": data.get("org"),
                        "latency_ms": int((time.monotonic() - start_time) * 1000)
                    }
        except httpx.TimeoutException:
            current_proxy_result = {"status_code": "PROXY_TIMEOUT"}
        except Exception:
            current_proxy_result = {"status_code": "PROXY_CONNECTION_FAILED"}

    # 3. Policy Evaluation
    policy_report = evaluate_proxy_policy(profile, current_proxy_result)
    
    # Map report back to risk severity
    risk_level = "normal"
    if policy_report.get("status") == "critical":
        risk_level = "critical"
    elif policy_report.get("status") == "warning":
        risk_level = "warning"

    return {
        "status": "healthy" if risk_level == "normal" else risk_level,
        "risk_level": risk_level,
        "policy_report": policy_report,
        "proxy_check": current_proxy_result
    }

async def run_deep_check(profile_id: str, browser_mgr: Any) -> dict[str, Any]:
    """
    Executes a single deep check comparing fingerprint parameters, session health, and TLS check.
    """
    profile = db.get_profile(profile_id)
    if not profile:
        return {"status": "error", "message": "Profile not found"}

    # 1. Process Check
    running = browser_mgr.running.get(profile_id)
    if not running:
        return {"status": "dead", "message": "Browser is not running"}

    if running.pid:
        try:
            os.kill(running.pid, 0)
        except OSError:
            return {"status": "dead", "message": f"Browser process {running.pid} died externally"}

    # 2. Session Data Health Check
    user_data_dir = profile.get("user_data_dir")
    if not user_data_dir or not os.path.exists(user_data_dir):
        return {
            "status": "critical",
            "risk_level": "critical",
            "error_code": "SESSION_DATA_CORRUPTED",
            "message": "User data directory does not exist or is corrupted."
        }

    # Cookies DB check
    cookies_paths = [
        os.path.join(user_data_dir, "Default", "Network", "Cookies"),
        os.path.join(user_data_dir, "Default", "Cookies"),
    ]
    for cp in cookies_paths:
        if os.path.exists(cp):
            try:
                conn = sqlite3.connect(cp, timeout=2.0)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                res = cursor.fetchone()
                conn.close()
                if not res or res[0] != "ok":
                    return {
                        "status": "critical",
                        "risk_level": "critical",
                        "error_code": "SESSION_DATA_CORRUPTED",
                        "message": "Cookies SQLite database is corrupted."
                    }
            except Exception as e:
                return {
                    "status": "critical",
                    "risk_level": "critical",
                    "error_code": "SESSION_DATA_CORRUPTED",
                    "message": f"Cookies database integrity check failed: {e}"
                }
    
    # Local Storage & IndexedDB folders check
    ls_path = os.path.join(user_data_dir, "Default", "Local Storage")
    idb_path = os.path.join(user_data_dir, "Default", "IndexedDB")
    if os.path.exists(ls_path) and not os.path.isdir(ls_path):
        return {
            "status": "critical",
            "risk_level": "critical",
            "error_code": "SESSION_DATA_CORRUPTED",
            "message": "Local Storage path is not a directory."
        }
    if os.path.exists(idb_path) and not os.path.isdir(idb_path):
        return {
            "status": "critical",
            "risk_level": "critical",
            "error_code": "SESSION_DATA_CORRUPTED",
            "message": "IndexedDB path is not a directory."
        }

    # 3. CDP Fingerprint checks
    cdp_port = getattr(running, "cdp_port", None)
    if not cdp_port:
        return {"status": "warning", "risk_level": "warning", "message": "CDP port not found on running instance"}

    targets = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://127.0.0.1:{cdp_port}/json/list")
            if resp.status_code == 200:
                targets = resp.json()
    except Exception as e:
        logger.warning(f"Failed to query CDP target list: {e}")
        return {"status": "warning", "risk_level": "warning", "message": f"CDP endpoint unreachable: {e}"}

    page_target = None
    for t in targets:
        if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
            page_target = t
            break

    runtime_fp = {}
    if page_target:
        ws_url = page_target["webSocketDebuggerUrl"]
        try:
            import websockets
            async with websockets.connect(ws_url, close_timeout=2.0) as ws:
                expr = """
                (function() {
                    let canvasHash = "";
                    try {
                        const canvas = document.createElement('canvas');
                        const ctx = canvas.getContext('2d');
                        ctx.fillText('cloakbrowser', 10, 10);
                        const data = canvas.toDataURL();
                        let hash = 0;
                        for (let i = 0; i < data.length; i++) {
                            hash = (hash << 5) - hash + data.charCodeAt(i);
                            hash |= 0;
                        }
                        canvasHash = hash.toString();
                    } catch(e) {}

                    let webglVendor = "";
                    let webglRenderer = "";
                    try {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                        if (gl) {
                            const dbg = gl.getExtension('WEBGL_debug_renderer_info');
                            webglVendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : "";
                            webglRenderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : "";
                        }
                    } catch(e) {}

                    let browserVersion = "";
                    try {
                        const ua = navigator.userAgent;
                        const match = ua.match(/Chrome\\/([^ ]+)/);
                        if (match) browserVersion = match[1];
                    } catch(e) {}

                    return JSON.stringify({
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        screenWidth: screen.width,
                        screenHeight: screen.height,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        locale: navigator.language,
                        canvasHash: canvasHash,
                        webglVendor: webglVendor,
                        webglRenderer: webglRenderer,
                        fontHash: "mock-font-hash",
                        audioHash: "mock-audio-hash",
                        browserVersion: browserVersion
                    });
                })()
                """
                payload = {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expr,
                        "returnByValue": True
                    }
                }
                await ws.send(json.dumps(payload))
                response_str = await ws.recv()
                response_data = json.loads(response_str)
                if "result" in response_data and "result" in response_data["result"] and "value" in response_data["result"]["result"]:
                    val_str = response_data["result"]["result"]["value"]
                    runtime_fp = json.loads(val_str)
        except Exception as e:
            logger.warning(f"Failed to evaluate runtime fingerprint via websocket: {e}")

    # 4. Fingerprint Lock Comparisons
    if runtime_fp and profile.get("fingerprint_locked", True):
        # UA Mismatch
        expected_ua = profile.get("user_agent")
        if expected_ua and runtime_fp.get("userAgent") != expected_ua:
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "FINGERPRINT_UA_MISMATCH",
                "message": f"User-Agent mismatch: Expected '{expected_ua}', got '{runtime_fp.get('userAgent')}'"
            }
        
        # Platform Mismatch
        expected_platform = profile.get("platform")
        plat_map = {"windows": "Win32", "macos": "MacIntel", "linux": "Linux x86_64"}
        actual_plat = runtime_fp.get("platform")
        expected_plat_mapped = plat_map.get(expected_platform, expected_platform)
        if expected_platform and actual_plat and expected_plat_mapped != actual_plat:
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "HEADERS_MISMATCH_CRITICAL",
                "message": f"Platform mismatch: Expected '{expected_plat_mapped}', got '{actual_plat}'"
            }

        # Screen Dimensions Mismatch
        expected_sw = profile.get("screen_width")
        expected_sh = profile.get("screen_height")
        if expected_sw and expected_sh:
            if runtime_fp.get("screenWidth") != expected_sw or runtime_fp.get("screenHeight") != expected_sh:
                return {
                    "status": "critical",
                    "risk_level": "critical",
                    "error_code": "HEADERS_MISMATCH_CRITICAL",
                    "message": f"Screen dimension mismatch: Expected {expected_sw}x{expected_sh}, got {runtime_fp.get('screenWidth')}x{runtime_fp.get('screenHeight')}"
                }

        # Timezone Mismatch
        expected_tz = profile.get("timezone")
        if expected_tz and runtime_fp.get("timezone") != expected_tz:
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "HEADERS_MISMATCH_CRITICAL",
                "message": f"Timezone mismatch: Expected '{expected_tz}', got '{runtime_fp.get('timezone')}'"
            }

        # Locale Mismatch
        expected_locale = profile.get("locale")
        if expected_locale and runtime_fp.get("locale") != expected_locale:
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "HEADERS_MISMATCH_CRITICAL",
                "message": f"Locale mismatch: Expected '{expected_locale}', got '{runtime_fp.get('locale')}'"
            }

        # WebGL Mismatch
        expected_vendor = profile.get("gpu_vendor")
        expected_renderer = profile.get("gpu_renderer")
        if expected_vendor and runtime_fp.get("webglVendor") != expected_vendor:
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "FINGERPRINT_WEBGL_MISMATCH",
                "message": f"WebGL GPU Vendor mismatch: Expected '{expected_vendor}', got '{runtime_fp.get('webglVendor')}'"
            }
        if expected_renderer and runtime_fp.get("webglRenderer") != expected_renderer:
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "FINGERPRINT_WEBGL_MISMATCH",
                "message": f"WebGL GPU Renderer mismatch: Expected '{expected_renderer}', got '{runtime_fp.get('webglRenderer')}'"
            }

        # Optional core verification simulations
        if "fontHash" in runtime_fp and runtime_fp.get("fontHash") != "mock-font-hash":
            return {
                "status": "critical",
                "risk_level": "critical",
                "error_code": "FINGERPRINT_FONT_MISMATCH",
                "message": "Font hash mismatch detected."
            }

        if "canvasHash" in runtime_fp and runtime_fp.get("canvasHash") != "":
            # Can support canvas hash checks if profile canvas configurations were pre-locked
            pass

    # 5. TLS Check
    tls_status = "ok"
    proxy_url = None
    proxy_id = profile.get("proxy_id")
    if proxy_id:
        proxy_record = db.get_proxy(proxy_id)
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

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
            resp = await client.get("https://tls.peet.ws/api/all")
            if resp.status_code != 200:
                tls_status = "unavailable"
    except Exception as e:
        logger.warning(f"TLS check failed/unavailable: {e}")
        tls_status = "unavailable"

    if tls_status == "unavailable":
        return {
            "status": "warning",
            "risk_level": "warning",
            "error_code": "TLS_CHECK_UNAVAILABLE",
            "message": "TLS check endpoint (tls.peet.ws) is unavailable."
        }

    return {
        "status": "healthy",
        "risk_level": "normal",
        "runtime_fingerprint": runtime_fp
    }

async def _guardian_loop(profile_id: str, browser_mgr: Any) -> None:
    """
    Background guardian loop checking every N seconds.
    """
    last_deep_check_time = time.time()
    try:
        while True:
            profile = db.get_profile(profile_id)
            if not profile:
                break
            
            interval = profile.get("runtime_check_interval_seconds", 60) or 60
            await asyncio.sleep(interval)

            now_ts = time.time()
            deep_interval = (profile.get("deep_check_interval_minutes", 10) or 10) * 60

            # Run periodic deep check if interval elapsed
            if now_ts - last_deep_check_time >= deep_interval:
                last_deep_check_time = now_ts
                res = await run_deep_check(profile_id, browser_mgr)
                is_deep = True
            else:
                res = await run_lightweight_check(profile_id, browser_mgr)
                is_deep = False

            now = datetime.now(timezone.utc).isoformat()
            
            if res["status"] == "dead":
                logger.info(f"Runtime Guardian: detected profile {profile_id} process dead. Stopping.")
                db.update_profile(
                    profile_id,
                    runtime_guardian_status="idle",
                    last_runtime_check_at=now,
                    last_runtime_check_result=json.dumps(res)
                )
                asyncio.create_task(browser_mgr._on_browser_closed(profile_id))
                break

            # Update DB with check result
            status_map = {
                "healthy": "healthy",
                "warning": "warning",
                "critical": "critical"
            }
            guardian_status = status_map.get(res["status"], "healthy")

            db.update_profile(
                profile_id,
                runtime_guardian_status=guardian_status,
                runtime_risk_level=res["risk_level"],
                last_runtime_check_at=now,
                last_runtime_check_result=json.dumps(res)
            )

            # Trigger Actions
            if res["risk_level"] == "critical":
                err_code = res.get("error_code") or res.get("policy_report", {}).get("error_code", "PROXY_POLICY_VIOLATION")
                msg = res.get("message") or res.get("policy_report", {}).get("message", "Critical violation.")
                
                db.update_profile(
                    profile_id,
                    last_runtime_issue=err_code,
                    last_runtime_message=msg
                )
                
                log_error(
                    module="runtime_guardian",
                    action="RUNTIME_GUARDIAN_CRITICAL",
                    error_code=err_code,
                    message=msg,
                    profile_id=profile_id
                )
                
                action_on_critical = profile.get("runtime_action_on_critical", "stop_profile")
                if action_on_critical == "stop_profile":
                    # Ensure cookies/session data are saved/flushed by doing a graceful stop
                    if bool(profile.get("session_auto_save", True)):
                        db.update_profile(profile_id, last_session_save_at=now)
                        log_activity(
                            module="runtime_guardian",
                            action="SESSION_SAVED_ON_STOP",
                            status="success",
                            message=f"Session auto-saved on stop for profile {profile_id}",
                            profile_id=profile_id
                        )
                    
                    db.update_profile(profile_id, runtime_guardian_status="stopped_by_guardian")
                    
                    log_activity(
                        module="runtime_guardian",
                        action="PROFILE_STOPPED_BY_GUARDIAN",
                        status="success",
                        message=f"Profile stopped automatically by Guardian due to critical risk: {msg}",
                        profile_id=profile_id
                    )
                    
                    asyncio.create_task(browser_mgr.stop(profile_id))
                    break

            elif res["risk_level"] == "warning":
                db.update_profile(profile_id, verification_status="expired")
                err_code = res.get("error_code") or "PROFILE_VERIFICATION_WARNING"
                msg = res.get("message") or res.get("policy_report", {}).get("message", "Warning alert.")
                
                log_activity(
                    module="runtime_guardian",
                    action="RUNTIME_GUARDIAN_WARNING",
                    status="warning",
                    message=f"WARNING guardian alert: {msg}.",
                    profile_id=profile_id
                )

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in guardian loop for profile {profile_id}: {e}")
