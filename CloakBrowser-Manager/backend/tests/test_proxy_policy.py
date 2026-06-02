from backend.profile_verifier import evaluate_proxy_policy

def test_static_residential_policy():
    # 1. Matching IP (healthy)
    profile = {
        "proxy_mode": "static_residential",
        "expected_exit_ip": "1.2.3.4",
        "expected_country": "US",
        "expected_asn": "AS123",
        "allow_ip_rotation": False,
    }
    result = {
        "status_code": "PROXY_OK",
        "last_ip": "1.2.3.4",
        "country": "US",
        "asn": "AS123",
    }
    eval_res = evaluate_proxy_policy(profile, result)
    assert eval_res["status"] == "healthy"

    # 2. Mismatched IP (critical)
    result_mismatch = {
        "status_code": "PROXY_OK",
        "last_ip": "5.6.7.8",
        "country": "US",
        "asn": "AS123",
    }
    eval_res = evaluate_proxy_policy(profile, result_mismatch)
    assert eval_res["status"] == "critical"
    assert eval_res["error_code"] == "PROXY_EXIT_IP_CHANGED"


def test_rotating_same_country_policy():
    profile = {
        "proxy_mode": "rotating",
        "expected_exit_ip": "1.2.3.4",
        "expected_country": "US",
        "expected_asn": "AS123",
        "allow_ip_rotation": True,
        "allowed_rotation_scope": "same_country",
    }

    # 1. IP changed but country matches (warning)
    result_rotated_ok = {
        "status_code": "PROXY_OK",
        "last_ip": "1.2.3.9",
        "country": "US",
        "asn": "AS999", # ASN difference allowed
    }
    eval_res = evaluate_proxy_policy(profile, result_rotated_ok)
    assert eval_res["status"] == "warning"
    assert eval_res["error_code"] == "PROXY_IP_ROTATED"
    assert eval_res.get("verification_expired") is True

    # 2. Country changed (critical)
    result_country_mismatch = {
        "status_code": "PROXY_OK",
        "last_ip": "9.9.9.9",
        "country": "CA",
        "asn": "AS123",
    }
    eval_res = evaluate_proxy_policy(profile, result_country_mismatch)
    assert eval_res["status"] == "critical"
    assert eval_res["error_code"] == "PROXY_COUNTRY_MISMATCH"


def test_rotating_same_asn_policy():
    profile = {
        "proxy_mode": "rotating",
        "expected_exit_ip": "1.2.3.4",
        "expected_country": "US",
        "expected_asn": "AS123",
        "allow_ip_rotation": True,
        "allowed_rotation_scope": "same_asn",
    }

    # 1. IP changed but same ASN & same Country (warning)
    result_ok = {
        "status_code": "PROXY_OK",
        "last_ip": "1.2.3.99",
        "country": "US",
        "asn": "AS123",
    }
    eval_res = evaluate_proxy_policy(profile, result_ok)
    assert eval_res["status"] == "warning"
    assert eval_res["error_code"] == "PROXY_IP_ROTATED"
    assert eval_res.get("verification_expired") is True

    # 2. ASN mismatch (critical)
    result_asn_mismatch = {
        "status_code": "PROXY_OK",
        "last_ip": "1.2.3.99",
        "country": "US",
        "asn": "AS999",
    }
    eval_res = evaluate_proxy_policy(profile, result_asn_mismatch)
    assert eval_res["status"] == "critical"
    assert eval_res["error_code"] == "PROXY_ASN_MISMATCH"


def test_proxy_connection_failures():
    profile = {
        "proxy_mode": "static_residential",
        "expected_exit_ip": "1.2.3.4",
    }

    # 1. Auth failed (critical)
    eval_res = evaluate_proxy_policy(profile, {"status_code": "PROXY_AUTH_FAILED"})
    assert eval_res["status"] == "critical"
    assert eval_res["error_code"] == "PROXY_AUTH_FAILED"

    # 2. Timeout / connection error (critical)
    eval_res = evaluate_proxy_policy(profile, {"status_code": "PROXY_TIMEOUT"})
    assert eval_res["status"] == "critical"
    assert eval_res["error_code"] == "PROXY_CONNECTION_FAILED"
