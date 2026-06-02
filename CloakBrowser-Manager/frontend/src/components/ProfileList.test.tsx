import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProfileList } from "./ProfileList";
import type { Profile } from "../lib/api";

const mockProfiles: Profile[] = [
  {
    id: "p1",
    name: "Profile Healthy",
    fingerprint_seed: 12345,
    proxy: "http://1.2.3.4:8080",
    proxy_id: null,
    timezone: "UTC",
    locale: "en-US",
    platform: "windows",
    user_agent: "Mozilla/5.0 ...",
    screen_width: 1920,
    screen_height: 1080,
    gpu_vendor: "Google",
    gpu_renderer: "ANGLE",
    hardware_concurrency: 4,
    humanize: false,
    human_preset: "default",
    headless: false,
    geoip: false,
    clipboard_sync: true,
    auto_launch: false,
    color_scheme: null,
    launch_args: [],
    notes: null,
    user_data_dir: "/fake/dir",
    created_at: "2026-06-02",
    updated_at: "2026-06-02",
    tags: [],
    status: "stopped",
    vnc_ws_port: null,
    cdp_url: null,
    last_launched: null,
    fingerprint_locked: true,
    session_auto_save: true,
    auto_sync_timezone_with_proxy: false,
    auto_sync_locale_with_proxy: false,
    auto_sync_geolocation_with_proxy: false,
    last_fingerprint_change_at: null,
    last_session_save_at: null,
    last_proxy_change_at: null,
    verification_status: "verified",
    runtime_guardian_enabled: true,
    runtime_guardian_status: "healthy",
    runtime_risk_level: "normal",
    last_runtime_check_at: "2026-06-02T12:00:00Z",
    last_runtime_check_result: {
      proxy_check: { status_code: "PROXY_OK" }
    }
  },
  {
    id: "p2",
    name: "Profile Critical Mismatch",
    fingerprint_seed: 12345,
    proxy: "http://1.2.3.4:8080",
    proxy_id: null,
    timezone: "UTC",
    locale: "en-US",
    platform: "windows",
    user_agent: "Mozilla/5.0 ...",
    screen_width: 1920,
    screen_height: 1080,
    gpu_vendor: "Google",
    gpu_renderer: "ANGLE",
    hardware_concurrency: 4,
    humanize: false,
    human_preset: "default",
    headless: false,
    geoip: false,
    clipboard_sync: true,
    auto_launch: false,
    color_scheme: null,
    launch_args: [],
    notes: null,
    user_data_dir: "/fake/dir",
    created_at: "2026-06-02",
    updated_at: "2026-06-02",
    tags: [],
    status: "stopped",
    vnc_ws_port: null,
    cdp_url: null,
    last_launched: null,
    fingerprint_locked: true,
    session_auto_save: true,
    auto_sync_timezone_with_proxy: false,
    auto_sync_locale_with_proxy: false,
    auto_sync_geolocation_with_proxy: false,
    last_fingerprint_change_at: null,
    last_session_save_at: null,
    last_proxy_change_at: null,
    verification_status: "verified",
    runtime_guardian_enabled: true,
    runtime_guardian_status: "critical",
    runtime_risk_level: "critical",
    last_runtime_check_at: "2026-06-02T12:00:00Z",
    last_runtime_check_result: {
      error_code: "FINGERPRINT_UA_MISMATCH",
      message: "Fingerprint User-Agent mismatch detected."
    }
  }
];

describe("ProfileList UI alerts and override handling", () => {
  it("renders status badges correctly for healthy profiles", () => {
    render(
      <ProfileList
        profiles={mockProfiles}
        selectedId={null}
        onSelect={() => {}}
        onNew={() => {}}
        onLaunch={async () => {}}
        onStop={async () => {}}
        onView={() => {}}
        onEdit={() => {}}
        onLogs={() => {}}
        onExportClick={() => {}}
        onImportClick={() => {}}
      />
    );

    // Verify badges are rendered
    expect(screen.getByText("Proxy: Connected")).toBeDefined();
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
    expect(screen.getByText("Guardian: Healthy")).toBeDefined();
    expect(screen.getAllByText("Locked").length).toBeGreaterThan(0);
  });

  it("renders critical alert banners and disables the launch button when critical risk detected", () => {
    const { container } = render(
      <ProfileList
        profiles={mockProfiles}
        selectedId={null}
        onSelect={() => {}}
        onNew={() => {}}
        onLaunch={async () => {}}
        onStop={async () => {}}
        onView={() => {}}
        onEdit={() => {}}
        onLogs={() => {}}
        onExportClick={() => {}}
        onImportClick={() => {}}
      />
    );

    // Verify critical alert banner text is displayed
    expect(screen.getByText("Fingerprint không khớp cấu hình đã khóa.")).toBeDefined();

    // Verify "View Report" button is rendered
    expect(screen.getByText("View Report")).toBeDefined();

    // Verify Launch button is disabled for p2
    const launchButton = container.querySelector("#btn-launch-p2");
    expect(launchButton).toBeDefined();
    expect(launchButton?.hasAttribute("disabled")).toBe(true);
  });
});
