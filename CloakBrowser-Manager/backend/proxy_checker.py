import time
import httpx
import logging
from typing import Any, Optional
try:
    from .logger_utils import log_activity, log_error
except ImportError:
    from backend.logger_utils import log_activity, log_error

logger = logging.getLogger("ProxyChecker")

_COUNTRY_LOCALE_MAP = {
    "US": "en-US",
    "VN": "vi-VN",
    "GB": "en-GB",
    "DE": "de-DE",
    "FR": "fr-FR",
    "CA": "en-CA",
    "AU": "en-AU",
    "JP": "ja-JP",
    "KR": "ko-KR",
    "CN": "zh-CN",
    "RU": "ru-RU",
    "BR": "pt-BR",
    "IN": "hi-IN",
    "SG": "en-SG",
    "TH": "th-TH",
    "MY": "ms-MY",
    "ID": "id-ID",
    "PH": "en-PH",
    "UA": "uk-UA",
    "ES": "es-ES",
    "IT": "it-IT",
    "NL": "nl-NL",
    "PL": "pl-PL",
    "TR": "tr-TR",
    "TW": "zh-TW",
    "HK": "zh-HK",
}

def _map_country_to_locale(country_code: Optional[str]) -> str:
    if not country_code:
        return "en-US"
    code = country_code.upper()
    if code in _COUNTRY_LOCALE_MAP:
        return _COUNTRY_LOCALE_MAP[code]
    return f"{code.lower()}-{code}"


async def check_proxy(proxy_record: dict[str, Any]) -> dict[str, Any]:
    """
    Checks the proxy connection and returns the updated proxy dict along with a status code.
    Possible status codes:
    - PROXY_OK
    - PROXY_AUTH_FAILED
    - PROXY_TIMEOUT
    - PROXY_CONNECTION_FAILED
    - PROXY_CHECK_FAILED
    """
    ptype = proxy_record.get("type", "http")
    host = proxy_record["host"]
    port = proxy_record["port"]
    user = proxy_record.get("username")
    pwd = proxy_record.get("password")

    if user and pwd:
        proxy_url = f"{ptype}://{user}:{pwd}@{host}:{port}"
        masked_url = f"{ptype}://{user}:***@{host}:{port}"
    else:
        proxy_url = f"{ptype}://{host}:{port}"
        masked_url = proxy_url

    log_activity("proxy_checker", "check_proxy", "started", f"Checking proxy: {masked_url}", proxy_id=proxy_record.get("id"))

    status_code = "PROXY_CHECK_FAILED"
    latency_ms = None
    last_ip = None
    timezone = None
    locale = None
    country = None
    asn = None

    start_time = time.monotonic()
    
    # We will query ip-api.com/json/ to get the exit IP, timezone and country
    # We use a 10s timeout.
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
            response = await client.get("http://ip-api.com/json/")
            if response.status_code == 407:
                status_code = "PROXY_AUTH_FAILED"
            else:
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "success":
                    last_ip = data.get("query")
                    timezone = data.get("timezone")
                    country_code = data.get("countryCode")
                    country = country_code
                    asn = data.get("as")
                    locale = _map_country_to_locale(country_code)
                    
                    # If we get here, connection succeeded
                    end_time = time.monotonic()
                    latency_ms = int((end_time - start_time) * 1000)
                    status_code = "PROXY_OK"
                else:
                    # Fallback to ipify if ip-api.com failed but proxy is working
                    ip_response = await client.get("https://api.ipify.org?format=json")
                    ip_response.raise_for_status()
                    last_ip = ip_response.json().get("ip")
                    end_time = time.monotonic()
                    latency_ms = int((end_time - start_time) * 1000)
                    status_code = "PROXY_OK"
                
    except httpx.ProxyError as e:
        msg = str(e).lower()
        if "auth" in msg or "407" in msg:
            status_code = "PROXY_AUTH_FAILED"
        else:
            status_code = "PROXY_CONNECTION_FAILED"
        log_error("proxy_checker", "check_proxy", status_code, f"Proxy connection failed for {masked_url}: {e}", proxy_id=proxy_record.get("id"))
    except httpx.TimeoutException:
        status_code = "PROXY_TIMEOUT"
        log_error("proxy_checker", "check_proxy", status_code, f"Proxy timeout for {masked_url}", proxy_id=proxy_record.get("id"))
    except httpx.ConnectError as e:
        status_code = "PROXY_CONNECTION_FAILED"
        log_error("proxy_checker", "check_proxy", status_code, f"Proxy connection failed for {masked_url}: {e}", proxy_id=proxy_record.get("id"))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 407:
            status_code = "PROXY_AUTH_FAILED"
        else:
            status_code = "PROXY_CHECK_FAILED"
        log_error("proxy_checker", "check_proxy", status_code, f"Proxy HTTP error for {masked_url}: {e}", proxy_id=proxy_record.get("id"))
    except Exception as e:
        status_code = "PROXY_CHECK_FAILED"
        log_error("proxy_checker", "check_proxy", status_code, f"Proxy unknown error for {masked_url}: {e}", proxy_id=proxy_record.get("id"))

    if status_code == "PROXY_OK":
        log_activity("proxy_checker", "check_proxy", "success", f"Proxy check successful for {masked_url}", proxy_id=proxy_record.get("id"), duration_ms=latency_ms)

    return {
        "status_code": status_code,
        "latency_ms": latency_ms,
        "last_ip": last_ip,
        "timezone": timezone,
        "locale": locale,
        "country": country,
        "asn": asn,
    }
