import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend import database as db
from backend.profile_verifier import verify_profile_prelaunch

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_verify_profile_prelaunch_success(mock_get):
    # Use standard MagicMock for response objects so json() does not return a coroutine
    mock_ip_api = MagicMock()
    mock_ip_api.status_code = 200
    mock_ip_api.json.return_value = {
        "status": "success",
        "query": "1.2.3.4",
        "countryCode": "US",
        "as": "AS123"
    }

    mock_headers = MagicMock()
    mock_headers.status_code = 200
    mock_headers.json.return_value = {
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
            "Accept-Language": "en-US"
        }
    }

    mock_tls = MagicMock()
    mock_tls.status_code = 200
    mock_tls.json.return_value = {"ja3": "abc"}

    # Mock the get call to return these responses sequentially
    mock_get.side_effect = [mock_ip_api, mock_headers, mock_tls]

    profile = db.create_profile(
        name="TestVerified",
        proxy="http://user:pass@1.2.3.4:8080",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        locale="en-US",
        expected_country="US"
    )

    report = await verify_profile_prelaunch(profile)
    assert report["status"] == "verified"
    assert not report["errors"]
    assert not report["warnings"]
    assert report["details"]["proxy"]["ip"] == "1.2.3.4"
    assert report["details"]["proxy"]["country"] == "US"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_verify_profile_prelaunch_country_mismatch(mock_get):
    mock_ip_api = MagicMock()
    mock_ip_api.status_code = 200
    mock_ip_api.json.return_value = {
        "status": "success",
        "query": "1.2.3.4",
        "countryCode": "CA",
        "as": "AS123"
    }

    mock_get.side_effect = [mock_ip_api]

    profile = db.create_profile(
        name="TestMismatch",
        proxy="http://1.2.3.4:8080",
        expected_country="US"
    )

    report = await verify_profile_prelaunch(profile)
    assert report["status"] == "failed"
    assert "PROXY_COUNTRY_MISMATCH" in report["errors"]

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_verify_profile_prelaunch_tls_warning(mock_get):
    mock_ip_api = MagicMock()
    mock_ip_api.status_code = 200
    mock_ip_api.json.return_value = {
        "status": "success",
        "query": "1.2.3.4",
        "countryCode": "US",
        "as": "AS123"
    }

    mock_headers = MagicMock()
    mock_headers.status_code = 200
    mock_headers.json.return_value = {
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
            "Accept-Language": "en-US"
        }
    }

    mock_get.side_effect = [mock_ip_api, mock_headers, Exception("TLS server down")]

    profile = db.create_profile(
        name="TestTLSWarning",
        proxy="http://1.2.3.4:8080",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        locale="en-US"
    )

    report = await verify_profile_prelaunch(profile)
    assert report["status"] == "warning"
    assert "TLS_CHECK_UNAVAILABLE" in report["warnings"]
