import datetime
import pytest
from unittest.mock import MagicMock
from backend import database as db
from backend.profile_verifier import can_launch_profile

@pytest.fixture(autouse=True)
def init_in_memory_db():
    db.init_db()
    yield

def test_can_launch_profile_no_verification_required():
    profile = {
        "id": "123",
        "require_verification_before_use": False,
        "verification_status": "unverified",
    }
    allowed, err = can_launch_profile(profile, "user")
    assert allowed is True
    assert err is None

def test_can_launch_profile_unverified():
    profile = {
        "id": "123",
        "require_verification_before_use": True,
        "verification_status": "unverified",
    }
    allowed, err = can_launch_profile(profile, "user")
    assert allowed is False
    assert err == "LAUNCH_BLOCKED_VERIFICATION_REQUIRED"

def test_can_launch_profile_failed():
    profile = {
        "id": "123",
        "require_verification_before_use": True,
        "verification_status": "failed",
    }
    allowed, err = can_launch_profile(profile, "user")
    assert allowed is False
    assert err == "PROFILE_VERIFICATION_FAILED"

def test_can_launch_profile_expired():
    profile = {
        "id": "123",
        "require_verification_before_use": True,
        "verification_status": "expired",
    }
    allowed, err = can_launch_profile(profile, "user")
    assert allowed is False
    assert err == "PROFILE_VERIFICATION_EXPIRED"

def test_can_launch_profile_warning_non_admin():
    profile = {
        "id": "123",
        "require_verification_before_use": True,
        "verification_status": "warning",
    }
    allowed, err = can_launch_profile(profile, "user")
    assert allowed is False
    assert err == "LAUNCH_BLOCKED_VERIFICATION_REQUIRED"

def test_can_launch_profile_warning_admin():
    profile = {
        "id": "123",
        "require_verification_before_use": True,
        "verification_status": "warning",
    }
    allowed, err = can_launch_profile(profile, "admin")
    assert allowed is True
    assert err is None

    allowed, err = can_launch_profile(profile, "super_admin")
    assert allowed is True
    assert err is None

def test_can_launch_profile_verified_not_expired():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    profile = {
        "id": "123",
        "require_verification_before_use": True,
        "verification_status": "verified",
        "last_verified_at": now,
        "verification_expires_minutes": 60,
    }
    allowed, err = can_launch_profile(profile, "user")
    assert allowed is True
    assert err is None

def test_can_launch_profile_verified_expired():
    # Setup profile in database to verify updates
    p = db.create_profile(
        name="TestExpired",
        verification_status="verified",
        last_verified_at=(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=70)).isoformat(),
        require_verification_before_use=True,
        verification_expires_minutes=60
    )
    
    allowed, err = can_launch_profile(p, "user")
    assert allowed is False
    assert err == "PROFILE_VERIFICATION_EXPIRED"

    # Verify database status changed to expired
    updated = db.get_profile(p["id"])
    assert updated["verification_status"] == "expired"
