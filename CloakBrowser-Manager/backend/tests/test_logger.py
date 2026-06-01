import json
import pytest
from unittest.mock import patch, MagicMock
from backend import logger_utils

def test_sanitize_message():
    # Regular message
    assert logger_utils._sanitize_message("Hello world") == "Hello world"
    
    # URL without password
    assert logger_utils._sanitize_message("http://127.0.0.1:8080") == "http://127.0.0.1:8080"
    
    # URL with password
    assert logger_utils._sanitize_message("http://user:secret123@127.0.0.1:8080") == "http://user:***@127.0.0.1:8080"
    assert logger_utils._sanitize_message("socks5://admin:mypass!@proxy.net:1080") == "socks5://admin:***@proxy.net:1080"

@patch("backend.logger_utils.db.insert_log")
@patch("backend.logger_utils.logger.info")
def test_log_activity(mock_logger_info, mock_insert_log):
    logger_utils.log_activity(
        module="test_module",
        action="test_action",
        status="success",
        message="Testing http://user:pass@1.2.3.4:80",
        profile_id="p1",
        duration_ms=150
    )
    
    # Verify DB call
    assert mock_insert_log.call_count == 1
    log_entry = mock_insert_log.call_args[0][0]
    
    assert log_entry["level"] == "info"
    assert log_entry["module"] == "test_module"
    assert log_entry["action"] == "test_action"
    assert log_entry["status"] == "success"
    assert log_entry["profile_id"] == "p1"
    assert log_entry["duration_ms"] == 150
    assert "timestamp" in log_entry
    assert log_entry["message"] == "Testing http://user:***@1.2.3.4:80"
    
    # Verify standard logger call
    assert mock_logger_info.call_count == 1
    logged_json = mock_logger_info.call_args[0][0]
    parsed_log = json.loads(logged_json)
    assert parsed_log["level"] == "info"
    assert parsed_log["message"] == "Testing http://user:***@1.2.3.4:80"

@patch("backend.logger_utils.db.insert_log")
@patch("backend.logger_utils.logger.error")
def test_log_error(mock_logger_error, mock_insert_log):
    logger_utils.log_error(
        module="test_module",
        action="test_action",
        error_code="ERR_123",
        message="Failure occurred",
        proxy_id="prox1"
    )
    
    # Verify DB call
    assert mock_insert_log.call_count == 1
    log_entry = mock_insert_log.call_args[0][0]
    
    assert log_entry["level"] == "error"
    assert log_entry["module"] == "test_module"
    assert log_entry["action"] == "test_action"
    assert log_entry["status"] == "failed"
    assert log_entry["error_code"] == "ERR_123"
    assert log_entry["proxy_id"] == "prox1"
    
    # Verify standard logger call
    assert mock_logger_error.call_count == 1
    logged_json = mock_logger_error.call_args[0][0]
    parsed_log = json.loads(logged_json)
    assert parsed_log["error_code"] == "ERR_123"
