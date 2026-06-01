import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from backend.proxy_checker import check_proxy

@pytest.mark.asyncio
async def test_check_proxy_success():
    proxy_record = {
        "type": "http",
        "host": "127.0.0.1",
        "port": 8080,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ip": "1.2.3.4"}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("backend.proxy_checker.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        
        result = await check_proxy(proxy_record)
        
        assert result["status_code"] == "PROXY_OK"
        assert result["last_ip"] == "1.2.3.4"
        assert isinstance(result["latency_ms"], int)

@pytest.mark.asyncio
async def test_check_proxy_timeout():
    proxy_record = {
        "type": "socks5",
        "host": "10.0.0.1",
        "port": 1080,
    }

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("Timeout")

    with patch("backend.proxy_checker.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        
        result = await check_proxy(proxy_record)
        
        assert result["status_code"] == "PROXY_TIMEOUT"
        assert result["last_ip"] is None
        assert result["latency_ms"] is None

@pytest.mark.asyncio
async def test_check_proxy_auth_failed():
    proxy_record = {
        "type": "http",
        "host": "127.0.0.1",
        "port": 8080,
        "username": "bad",
        "password": "pwd"
    }

    mock_response = AsyncMock()
    mock_response.status_code = 407

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("backend.proxy_checker.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        
        result = await check_proxy(proxy_record)
        
        assert result["status_code"] == "PROXY_AUTH_FAILED"

@pytest.mark.asyncio
async def test_check_proxy_connection_failed():
    proxy_record = {
        "type": "http",
        "host": "invalid.local",
        "port": 80,
    }

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with patch("backend.proxy_checker.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        
        result = await check_proxy(proxy_record)
        
        assert result["status_code"] == "PROXY_CONNECTION_FAILED"
