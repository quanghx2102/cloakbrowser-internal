"""Pydantic models for profile CRUD operations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProfileCreate(BaseModel):
    name: str
    fingerprint_seed: int | None = None  # random if not set
    proxy: str | None = None  # "http://user:pass@host:port" or null
    proxy_id: str | None = None  # Reference to proxy table
    timezone: str | None = None  # "America/New_York"
    locale: str | None = None  # "en-US"
    platform: Literal["windows", "macos", "linux"] = "windows"
    user_agent: str | None = None
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool = False
    human_preset: Literal["default", "careful"] = "default"
    headless: bool = False
    geoip: bool = False
    clipboard_sync: bool = True
    auto_launch: bool = False
    color_scheme: Literal["light", "dark", "no-preference"] | None = None
    launch_args: list[str] = Field(default_factory=list)
    notes: str | None = None
    tags: list[TagCreate] | None = None
    fingerprint_locked: bool = True
    session_auto_save: bool = True
    auto_sync_timezone_with_proxy: bool = False
    auto_sync_locale_with_proxy: bool = False
    auto_sync_geolocation_with_proxy: bool = False
    proxy_mode: Literal["static_residential", "sticky_residential", "rotating", "datacenter_static"] = "static_residential"
    expected_exit_ip: str | None = None
    expected_country: str | None = None
    expected_asn: str | None = None
    allow_ip_rotation: bool = False
    allowed_rotation_scope: Literal["same_ip", "same_country", "same_asn"] = "same_ip"
    proxy_sticky_session_ttl_minutes: int | None = None
    verification_expires_on_proxy_change: bool = True
    verification_status: Literal["unverified", "checking", "verified", "warning", "failed", "expired"] = "unverified"
    last_verified_at: str | None = None
    last_verification_result: str | None = None
    require_verification_before_use: bool = True
    verification_expires_minutes: int = 60
    runtime_guardian_enabled: bool = True
    runtime_guardian_status: Literal["idle", "monitoring", "healthy", "warning", "critical", "stopped_by_guardian"] = "idle"
    runtime_risk_level: Literal["normal", "warning", "critical"] = "normal"
    last_runtime_check_at: str | None = None
    last_runtime_check_result: str | None = None
    runtime_check_interval_seconds: int = 60
    deep_check_interval_minutes: int = 10
    runtime_action_on_critical: Literal["stop_profile", "warn_only"] = "stop_profile"
    last_runtime_issue: str | None = None
    last_runtime_message: str | None = None




class ProfileUpdate(BaseModel):
    name: str | None = None
    fingerprint_seed: int | None = None
    proxy: str | None = Field(default=None)
    proxy_id: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    locale: str | None = Field(default=None)
    platform: Literal["windows", "macos", "linux"] | None = None
    user_agent: str | None = Field(default=None)
    screen_width: int | None = None
    screen_height: int | None = None
    gpu_vendor: str | None = Field(default=None)
    gpu_renderer: str | None = Field(default=None)
    hardware_concurrency: int | None = Field(default=None)
    humanize: bool | None = None
    human_preset: Literal["default", "careful"] | None = None
    headless: bool | None = None
    geoip: bool | None = None
    clipboard_sync: bool | None = None
    auto_launch: bool | None = None
    color_scheme: Literal["light", "dark", "no-preference"] | None = Field(default=None)
    launch_args: list[str] | None = None
    notes: str | None = Field(default=None)
    tags: list[TagCreate] | None = None
    fingerprint_locked: bool | None = None
    session_auto_save: bool | None = None
    auto_sync_timezone_with_proxy: bool | None = None
    auto_sync_locale_with_proxy: bool | None = None
    auto_sync_geolocation_with_proxy: bool | None = None
    proxy_mode: Literal["static_residential", "sticky_residential", "rotating", "datacenter_static"] | None = None
    expected_exit_ip: str | None = Field(default=None)
    expected_country: str | None = Field(default=None)
    expected_asn: str | None = Field(default=None)
    allow_ip_rotation: bool | None = None
    allowed_rotation_scope: Literal["same_ip", "same_country", "same_asn"] | None = None
    proxy_sticky_session_ttl_minutes: int | None = Field(default=None)
    verification_expires_on_proxy_change: bool | None = None
    verification_status: Literal["unverified", "checking", "verified", "warning", "failed", "expired"] | None = None
    last_verified_at: str | None = Field(default=None)
    last_verification_result: str | None = Field(default=None)
    require_verification_before_use: bool | None = None
    verification_expires_minutes: int | None = None
    runtime_guardian_enabled: bool | None = None
    runtime_guardian_status: Literal["idle", "monitoring", "healthy", "warning", "critical", "stopped_by_guardian"] | None = None
    runtime_risk_level: Literal["normal", "warning", "critical"] | None = None
    last_runtime_check_at: str | None = Field(default=None)
    last_runtime_check_result: str | None = Field(default=None)
    runtime_check_interval_seconds: int | None = None
    deep_check_interval_minutes: int | None = None
    runtime_action_on_critical: Literal["stop_profile", "warn_only"] | None = None
    last_runtime_issue: str | None = Field(default=None)
    last_runtime_message: str | None = Field(default=None)




class TagCreate(BaseModel):
    tag: str
    color: str | None = None  # hex color


class TagResponse(BaseModel):
    tag: str
    color: str | None = None


class ProfileResponse(BaseModel):
    id: str
    name: str
    fingerprint_seed: int
    proxy: str | None = None
    proxy_id: str | None = None
    timezone: str | None = None
    locale: str | None = None
    platform: str = "windows"
    user_agent: str | None = None
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool = False
    human_preset: str = "default"
    headless: bool = False
    geoip: bool = False
    clipboard_sync: bool = True
    auto_launch: bool = False
    fingerprint_locked: bool = True
    session_auto_save: bool = True
    auto_sync_timezone_with_proxy: bool = False
    auto_sync_locale_with_proxy: bool = False
    auto_sync_geolocation_with_proxy: bool = False
    last_fingerprint_change_at: str | None = None
    last_session_save_at: str | None = None
    last_proxy_change_at: str | None = None
    proxy_mode: str = "static_residential"
    expected_exit_ip: str | None = None
    expected_country: str | None = None
    expected_asn: str | None = None
    allow_ip_rotation: bool = False
    allowed_rotation_scope: str = "same_ip"
    proxy_sticky_session_ttl_minutes: int | None = None
    verification_expires_on_proxy_change: bool = True
    verification_status: str = "unverified"
    last_verified_at: str | None = None
    last_verification_result: str | None = None
    require_verification_before_use: bool = True
    verification_expires_minutes: int = 60
    runtime_guardian_enabled: bool = True
    runtime_guardian_status: str = "idle"
    runtime_risk_level: str = "normal"
    last_runtime_check_at: str | None = None
    last_runtime_check_result: str | None = None
    runtime_check_interval_seconds: int = 60
    deep_check_interval_minutes: int = 10
    runtime_action_on_critical: str = "stop_profile"
    last_runtime_issue: str | None = None
    last_runtime_message: str | None = None



    @field_validator("clipboard_sync", mode="before")
    @classmethod
    def coerce_clipboard_sync(cls, v: object) -> bool:
        return v if v is not None else True

    color_scheme: str | None = None
    launch_args: list[str] = []
    notes: str | None = None
    user_data_dir: str
    created_at: str
    updated_at: str
    tags: list[TagResponse] = []
    status: str = "stopped"  # "starting" | "running" | "stopping" | "stopped" | "failed" | "crashed"
    vnc_ws_port: int | None = None
    cdp_url: str | None = None
    last_launched: str | None = None


class LaunchResponse(BaseModel):
    profile_id: str
    status: str = "running"
    vnc_ws_port: int | None = None
    display: str | None = None
    cdp_url: str | None = None


class StatusResponse(BaseModel):
    running_count: int
    binary_version: str
    profiles_total: int
    is_desktop: bool = False


class ProfileStatusResponse(BaseModel):
    status: str  # "starting" | "running" | "stopping" | "stopped" | "failed" | "crashed"
    vnc_ws_port: int | None = None
    display: str | None = None
    cdp_url: str | None = None


class ClipboardRequest(BaseModel):
    text: str = Field(max_length=1_048_576)  # 1MB max


class LoginRequest(BaseModel):
    token: str


class ProxyCreate(BaseModel):
    name: str
    type: Literal["http", "socks5"] = "http"
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    status: Literal["active", "inactive"] = "active"
    timezone: str | None = None
    locale: str | None = None


class ProxyUpdate(BaseModel):
    name: str | None = None
    type: Literal["http", "socks5"] | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
    status: Literal["active", "inactive"] | None = None
    timezone: str | None = Field(default=None)
    locale: str | None = Field(default=None)


class ProxyResponse(BaseModel):
    id: str
    name: str
    type: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    status: str
    latency_ms: int | None = None
    last_ip: str | None = None
    last_checked_at: str | None = None
    timezone: str | None = None
    locale: str | None = None
    created_at: str
    updated_at: str


class ProxyCheckResult(BaseModel):
    status_code: str
    proxy: ProxyResponse

class LogEntryModel(BaseModel):
    id: str
    timestamp: str
    level: str
    module: str
    action: str
    status: str
    error_code: str | None = None
    message: str | None = None
    profile_id: str | None = None
    proxy_id: str | None = None
    duration_ms: int | None = None

class DashboardSummary(BaseModel):
    total_profiles: int
    running_profiles: int
    stopped_profiles: int
    failed_profiles: int
    total_proxies: int
    ok_proxies: int
    failed_proxies: int
    recent_errors: list[LogEntryModel]
    max_running_profiles: int


class BackupResponse(BaseModel):
    filename: str
    path: str
    size_bytes: int
    created_at: str

class BackupCreateResponse(BaseModel):
    ok: bool
    backup_path: str

class ProfileBackupResponse(BaseModel):
    ok: bool
    backup_path: str
    metadata: dict[str, Any]

class RestoreRequest(BaseModel):
    backup_filename: str

class ProfileRestoreRequest(BaseModel):
    backup_filename: str

class RestoreResponse(BaseModel):
    ok: bool
    message: str


class RuntimeReportChecks(BaseModel):
    proxy: Literal["pass", "warning", "failed"]
    fingerprint: Literal["pass", "warning", "failed"]
    headers: Literal["pass", "warning", "failed"]
    session: Literal["pass", "warning", "failed"]


class RuntimeReportResponse(BaseModel):
    profile_id: str
    status: str
    score: int
    checked_at: str | None = None
    checks: RuntimeReportChecks
    blocking_issues: list[str]
    warnings: list[str]
    action_taken: str


class OverrideWarningRequest(BaseModel):
    reason: str


class BatchDeleteRequest(BaseModel):
    ids: list[str]



