import pytest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch
from backend.browser_manager import BrowserManager, RunningProfile

@pytest.mark.asyncio
async def test_crash_watcher_detects_dead_process():
    mgr = BrowserManager()
    
    # 1. Create a mocked running profile
    profile_id = "test_profile"
    mock_context = MagicMock()
    mock_running = RunningProfile(
        profile_id=profile_id,
        context=mock_context,
        display=100,
        ws_port=6100,
        cdp_port=5100,
        pid=99999, # Dummy pid
    )
    
    mgr.running[profile_id] = mock_running
    mgr.statuses[profile_id] = "running"
    
    # 2. Mock os.kill to raise OSError (indicating process is dead)
    # Mock log_error to trace BROWSER_CRASHED logging
    with patch("os.kill", side_effect=OSError()), \
         patch("backend.browser_manager.log_error") as mock_log_error, \
         patch.object(mgr.vnc, "stop_vnc", new_callable=AsyncMock) as mock_stop_vnc:
        
        # We call _handle_crash directly to simulate what the watcher loop does when process dies
        await mgr._handle_crash(profile_id, mock_running)
        
        # Verify the manager state
        assert profile_id not in mgr.running
        assert mgr.statuses[profile_id] == "crashed"
        
        # Verify VNC is stopped
        mock_stop_vnc.assert_called_once_with(100)
        
        # Verify error log is registered
        mock_log_error.assert_called_once_with(
            module="browser_manager",
            action="crash_watcher",
            error_code="BROWSER_CRASHED",
            message="Browser process (PID 99999) for profile test_profile crashed or was killed abnormally.",
            profile_id=profile_id
        )
