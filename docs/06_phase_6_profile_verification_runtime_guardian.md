# PHASE 6 — Profile Verification Gate & Runtime Guardian

> Mục tiêu Phase 6: nâng cấp hệ thống từ “mở profile được” thành “chỉ cho dùng profile khi profile đang an toàn”.  
> Backend là bộ não kiểm tra. Electron UI là nơi hiển thị trạng thái, cảnh báo và hành động xử lý.

---

## 0. Kết luận kỹ thuật

Hướng nâng cấp đúng:

```text
Static/Sticky Residential Proxy
+ Fingerprint Locked
+ Pre-launch Verification Gate
+ Runtime Guardian khi profile đang chạy
+ Alert rõ trên từng profile
+ Auto stop khi lỗi Critical
```

Không nên dùng proxy xoay 60s/lần cho profile dài hạn.

Luồng chuẩn:

```text
User bấm Launch
→ Backend chạy Pre-launch Verification
→ Nếu PASS thì mở CloakBrowser native window
→ Runtime Guardian bắt đầu giám sát
→ Nếu có lỗi Critical thì cảnh báo + stop profile
→ UI cập nhật trạng thái từng profile liên tục
```

---

## 1. Nguyên tắc bắt buộc

- Backend là nơi quyết định profile pass/fail.
- Không dùng noVNC làm luồng mặc định.
- Không fallback sang Chrome/Chromium thường.
- Không log cookie value, localStorage content, proxy password, token.
- Fingerprint Config không được tự thay đổi khi đổi proxy.
- Cookies/session/localStorage/IndexedDB mới vẫn phải được lưu khi stop/dừng profile.
- Nếu profile dùng proxy tĩnh mà IP đổi bất thường → Critical.
- Nếu chưa verified hoặc verification expired → không cho Launch.
- Admin chỉ được override Warning, không override Critical mặc định.
- Docker chỉ là dev/debug, không phải workflow chính của desktop app.

---

## 2. Proxy policy khuyến nghị

Với profile dùng lâu dài:

```json
{
  "proxy_mode": "static_residential",
  "allow_ip_rotation": false,
  "fingerprint_locked": true,
  "session_auto_save": true,
  "require_verification_before_use": true,
  "runtime_guardian_enabled": true,
  "runtime_check_interval_seconds": 60,
  "deep_check_interval_minutes": 10,
  "runtime_action_on_critical": "stop_profile",
  "verification_expires_on_proxy_change": true
}
```

Thứ tự ưu tiên proxy:

| Ưu tiên | Loại proxy | Ghi chú |
|---|---|---|
| 1 | Static Residential / Proxy tĩnh dân cư | Tốt nhất cho profile dài hạn |
| 2 | Sticky Residential TTL dài | Dùng được nếu IP giữ đủ lâu |
| 3 | Datacenter tĩnh | Chỉ nên dùng test/dev/profile phụ |
| 4 | Rotating proxy | Không khuyến nghị cho profile giữ session lâu |

---

## 3. Website/công cụ kiểm tra được phép dùng trong Phase 6

Để tránh tự suy diễn hoặc viết check mơ hồ, Phase 6 chỉ nên dùng các nhóm công cụ sau.

### 3.1 Công cụ kiểm tra IP / Proxy / ASN

Ưu tiên:

```text
https://ipinfo.io/
https://ipinfo.io/developers/ipinfo-api
https://httpbin.org/ip
```

Dùng để lấy:

```text
current exit IP
country
region/city nếu có
ASN/ISP nếu API trả về
proxy status
```

Quy tắc:

```text
- IPinfo dùng để lấy IP country/ASN.
- httpbin /ip dùng để kiểm tra IP hiện tại đơn giản.
- Không dùng dữ liệu IP để thay đổi fingerprint.
- Nếu proxy static mà current IP khác expected_exit_ip → Critical.
```

### 3.2 Công cụ kiểm tra headers

Ưu tiên:

```text
https://httpbin.org/headers
https://httpbin.org/user-agent
https://httpbin.org/get
```

Dùng để kiểm tra:

```text
User-Agent
Accept-Language
headers browser gửi ra ngoài
origin IP
```

Quy tắc:

```text
- User-Agent trong headers phải khớp user_agent đã lưu trong profile config.
- Accept-Language phải khớp locale/language policy.
- Nếu header mismatch nghiêm trọng → Warning hoặc Critical theo policy.
```

### 3.3 Công cụ kiểm tra browser fingerprint/privacy surface

Ưu tiên manual hoặc semi-automated report:

```text
https://browserleaks.com/
https://browserleaks.com/webrtc
https://browserleaks.com/canvas
https://browserleaks.com/webgl
```

Dùng để kiểm tra:

```text
WebRTC leak
Canvas fingerprint
WebGL vendor/renderer
font/browser surface nếu cần
geolocation/timezone nếu cần
```

Quy tắc:

```text
- Dùng BrowserLeaks để đối chiếu trong quá trình dev/test.
- Không phụ thuộc hoàn toàn vào website ngoài cho quyết định production.
- Với production, nên lưu runtime hash do hệ thống tự thu thập hoặc dùng checker nội bộ.
```

### 3.4 Công cụ kiểm tra TLS / HTTP2 / network fingerprint

Ưu tiên:

```text
https://tls.peet.ws/
https://tls.peet.ws/api/all
```

Dùng để kiểm tra:

```text
TLS fingerprint
JA3/JA4 nếu có
HTTP/2 fingerprint
request details
headers phía server nhận được
```

Quy tắc:

```text
- TLS check nên là Warning nếu endpoint unavailable.
- Không fail cứng chỉ vì TLS checker ngoài không truy cập được.
- Nếu sau này có checker nội bộ, ưu tiên checker nội bộ hơn website ngoài.
```

### 3.5 Checker nội bộ khuyến nghị

Về lâu dài nên có endpoint riêng:

```text
https://checker.your-domain.com/profile-check
```

Hoặc khi dev:

```text
http://127.0.0.1:<port>/profile-check
```

Checker nội bộ nên ghi nhận:

```text
IP
country/ASN
headers
User-Agent
Accept-Language
TLS/HTTP2 nếu server hỗ trợ
request timestamp
profile_check_id
```

Quy tắc:

```text
- Checker nội bộ là nguồn đáng tin nhất.
- Website ngoài chỉ dùng dev/test/manual validation.
- Không gửi cookie/localStorage/proxy password tới checker.
```

---

## 4. Dữ liệu nào được thay đổi và không được thay đổi

### 4.1 Khi đổi proxy

Được thay đổi:

```text
proxy_id
proxy_host
proxy_port
proxy_type
proxy_username/password trong storage bảo mật nếu có
proxy_status
proxy_latency
expected_exit_ip sau khi verify lại
expected_country/ASN sau khi verify lại
last_proxy_change_at
```

Không được tự thay đổi:

```text
fingerprint_seed
canvas config/hash
WebGL vendor/renderer/config
font config/hash
user-agent
screen size
hardwareConcurrency
deviceMemory
audio fingerprint
browser version lock
```

Rule:

```text
Proxy changed
→ Fingerprint unchanged
→ verification_status=expired
→ cần Verify lại trước khi Launch
```

### 4.2 Khi stop/dừng profile sau khi sử dụng

Được lưu/cập nhật:

```text
cookies mới
localStorage mới
sessionStorage mới
IndexedDB mới
Service Worker data
cache cần thiết
site settings
extension storage nếu browser/profile có sử dụng
last_session_save_at
```

Không được tự thay đổi:

```text
fingerprint_seed
canvas config/hash
WebGL config/hash
font config/hash
user-agent
screen size
hardware info
audio fingerprint
browser version lock
```

Rule:

```text
Session Runtime Data được lưu.
Fingerprint Config không được tự ghi đè.
```

---

## 5. Quy ước trạng thái task

```text
Not Started = chưa làm
Ready = đủ điều kiện bắt đầu
In Progress = đang làm
Blocked = bị chặn
Needs Fix = đã làm nhưng test fail
Done = hoàn thành và test pass
```

---

## 6. Task table

| Task | Tên task | Status | Mục tiêu |
|---|---|---|---|
| 6.1 | Proxy Policy Engine | Ready | Chuẩn hóa policy proxy cho từng profile |
| 6.2 | Verification Status & Launch Gate | Not Started | Chặn Launch nếu profile chưa an toàn |
| 6.3 | Pre-launch Verification Checks | Not Started | Kiểm tra trước khi mở profile |
| 6.4 | Runtime Guardian Lightweight Checks | Not Started | Giám sát liên tục proxy/process/IP |
| 6.5 | Runtime Guardian Deep Checks | Not Started | Kiểm tra định kỳ fingerprint/header/session |
| 6.6 | Runtime Alert UI per Profile | Not Started | Badge/banner cảnh báo rõ từng profile |
| 6.7 | OS Notification từ Electron | Not Started | Cảnh báo khi user không nhìn dashboard |
| 6.8 | Critical Action & Auto Stop | Not Started | Dừng profile khi lỗi nghiêm trọng |
| 6.9 | Runtime Report & Audit Log | Not Started | Lưu báo cáo, lịch sử lỗi |
| 6.10 | Proxy Change Re-verification | Not Started | Đổi proxy thì verification expired |
| 6.11 | Admin Override Policy | Not Started | Admin override Warning, không override Critical |
| 6.12 | Cookie/Session Save Integrity | Not Started | Đảm bảo stop profile vẫn lưu cookies/session mới |
| 6.13 | System Test Phase 6 | Not Started | Test đầy đủ phase 6 |

---

# TASK 6.1 — Proxy Policy Engine

**Status:** Ready

## Mục tiêu

Mỗi profile cần có policy proxy rõ ràng để backend biết khi nào IP/proxy thay đổi là bình thường, khi nào là lỗi Critical.

## Field cần thêm

```json
{
  "proxy_mode": "static_residential | sticky_residential | rotating | datacenter_static",
  "expected_exit_ip": null,
  "expected_country": null,
  "expected_asn": null,
  "allow_ip_rotation": false,
  "allowed_rotation_scope": "same_ip | same_country | same_asn",
  "proxy_sticky_session_ttl_minutes": null,
  "verification_expires_on_proxy_change": true
}
```

## Message prompt

```text
Bạn là senior backend engineer.

Task:
TASK 6.1 — Thêm Proxy Policy Engine cho từng profile.

Yêu cầu:
1. Thêm các field proxy policy vào profile/database:
   - proxy_mode
   - expected_exit_ip
   - expected_country
   - expected_asn
   - allow_ip_rotation
   - allowed_rotation_scope
   - proxy_sticky_session_ttl_minutes
   - verification_expires_on_proxy_change
2. Default cho profile thật:
   - proxy_mode=static_residential
   - allow_ip_rotation=false
   - verification_expires_on_proxy_change=true
3. Khi verify lần đầu thành công, lưu expected_exit_ip, expected_country, expected_asn.
4. Tạo helper evaluate_proxy_policy(profile, current_proxy_result).
5. Dữ liệu current_proxy_result nên lấy từ:
   - IPinfo API nếu có token
   - httpbin /ip nếu chỉ cần IP
   - checker nội bộ nếu đã có
6. Nếu IP đổi ngoài policy, trả Critical.
7. Nếu proxy rotating được phép đổi trong cùng country/ASN, trả Warning và set verification expired.
8. Không thay đổi fingerprint config khi proxy thay đổi.
9. Không log proxy password.

Output:
- File đã sửa.
- Database migration nếu có.
- Proxy policy schema.
- evaluate_proxy_policy logic.
- Test cases pass/fail.
```

---

# TASK 6.2 — Verification Status & Launch Gate

**Status:** Not Started

## Mục tiêu

Profile phải được xác minh trước khi sử dụng.

## Field cần thêm

```json
{
  "verification_status": "unverified | checking | verified | warning | failed | expired",
  "last_verified_at": null,
  "last_verification_result": null,
  "require_verification_before_use": true,
  "verification_expires_minutes": 60
}
```

## Message prompt

```text
Bạn là senior full-stack engineer.

Task:
TASK 6.2 — Thêm Verification Status & Launch Gate.

Mục tiêu:
Nếu profile chưa verified hoặc verification đã expired, profile không được Launch.

Yêu cầu backend:
1. Thêm fields:
   - verification_status
   - last_verified_at
   - last_verification_result
   - require_verification_before_use
   - verification_expires_minutes
2. Tạo helper can_launch_profile(profile, user_role).
3. Nếu require_verification_before_use=true:
   - verified chưa hết hạn → allow
   - warning → chỉ admin/super_admin có thể override
   - failed/unverified/expired → block
4. Nếu launch bị chặn, trả lỗi:
   - LAUNCH_BLOCKED_VERIFICATION_REQUIRED
   - PROFILE_VERIFICATION_EXPIRED
   - PROFILE_VERIFICATION_FAILED
5. Ghi audit log khi launch bị chặn.

Yêu cầu frontend:
1. Disable Launch button nếu không đủ điều kiện.
2. Hiển thị badge:
   - Verified
   - Warning
   - Failed
   - Unverified
   - Expired
3. Hiển thị nút Verify Profile / Re-Verify.

Output:
- File đã sửa.
- API/logic can_launch_profile.
- UI badge.
- Test cases pass/fail.
```

---

# TASK 6.3 — Pre-launch Verification Checks

**Status:** Not Started

## Mục tiêu

Kiểm tra profile trước khi mở.

## Website/công cụ được dùng

```text
Proxy/IP:
- https://ipinfo.io/
- https://httpbin.org/ip

Headers:
- https://httpbin.org/headers
- https://httpbin.org/user-agent
- https://httpbin.org/get

Browser surface manual/semi-auto:
- https://browserleaks.com/
- https://browserleaks.com/webrtc
- https://browserleaks.com/canvas
- https://browserleaks.com/webgl

TLS/HTTP2:
- https://tls.peet.ws/
- https://tls.peet.ws/api/all

Ưu tiên lâu dài:
- checker nội bộ
```

## Message prompt

```text
Bạn là senior backend QA/security engineer.

Task:
TASK 6.3 — Thêm Pre-launch Verification Checks.

Yêu cầu:
1. Tạo module backend/profile_verifier.py.
2. Tạo API:
   POST /api/profiles/{profile_id}/verify
   GET /api/profiles/{profile_id}/verification-report
3. Khi user bấm Verify Profile, chạy các nhóm check:

A. Proxy check:
- proxy alive
- auth OK
- current exit IP
- country/ASN
- latency
Nguồn dữ liệu được phép:
- IPinfo API
- httpbin /ip
- checker nội bộ

B. Header check:
- User-Agent
- Accept-Language
- origin IP
Nguồn dữ liệu được phép:
- httpbin /headers
- httpbin /user-agent
- httpbin /get
- checker nội bộ

C. Fingerprint consistency check:
- so sánh stored fingerprint config với runtime values nếu hệ thống thu thập được
- canvas hash
- WebGL vendor/renderer
- font hash/profile
- user-agent
- screen size
- timezone
- locale/language

D. TLS/HTTP2 check:
- dùng tls.peet.ws/api/all hoặc checker nội bộ
- nếu endpoint unavailable, trả Warning TLS_CHECK_UNAVAILABLE, không fail cứng mặc định

E. Session runtime check:
- user_data_dir tồn tại
- Cookies DB tồn tại nếu profile đã dùng
- Local Storage/IndexedDB folder không lỗi

4. Nếu PASS:
   - verification_status=verified
   - lưu last_verified_at
   - lưu last_verification_result
5. Nếu Warning:
   - verification_status=warning
   - lưu warning list
6. Nếu Fail:
   - verification_status=failed
   - lưu blocking issues
7. Không log cookie value/localStorage/proxy password.
8. Không tự nghĩ thêm website ngoài danh sách nếu chưa được duyệt.

Error codes:
- PROFILE_VERIFICATION_STARTED
- PROFILE_VERIFICATION_PASSED
- PROFILE_VERIFICATION_WARNING
- PROFILE_VERIFICATION_FAILED
- PROXY_CONNECTION_FAILED
- PROXY_AUTH_FAILED
- PROXY_COUNTRY_MISMATCH
- FINGERPRINT_CANVAS_MISMATCH
- FINGERPRINT_WEBGL_MISMATCH
- FINGERPRINT_FONT_MISMATCH
- FINGERPRINT_UA_MISMATCH
- HEADERS_MISMATCH
- TLS_CHECK_UNAVAILABLE
- SESSION_DATA_CORRUPTED

Output:
- File đã sửa/tạo.
- Website/tool nào được dùng cho từng check.
- Verification report schema.
- API endpoints.
- Test cases pass/fail.
```

---

# TASK 6.4 — Runtime Guardian Lightweight Checks

**Status:** Not Started

## Mục tiêu

Trong lúc profile đang chạy, backend kiểm tra định kỳ các lỗi nhanh.

## Lightweight checks

Chạy mỗi 30–60 giây:

```text
profile process còn sống không
browser còn phản hồi không
proxy còn connect được không
current exit IP có đổi không
latency có quá cao không
proxy policy có bị vi phạm không
```

## Message prompt

```text
Bạn là senior backend engineer.

Task:
TASK 6.4 — Thêm Runtime Guardian Lightweight Checks.

Yêu cầu:
1. Tạo module backend/runtime_guardian.py.
2. Thêm fields:
   - runtime_guardian_enabled boolean default true
   - runtime_guardian_status idle/monitoring/healthy/warning/critical/stopped_by_guardian
   - runtime_risk_level normal/warning/critical
   - last_runtime_check_at
   - last_runtime_check_result JSON
   - runtime_check_interval_seconds default 60
3. Khi profile launch thành công, start guardian task cho profile đó.
4. Khi profile stop, stop guardian task.
5. Không tạo nhiều guardian task trùng cho cùng profile.
6. Lightweight check mỗi runtime_check_interval_seconds:
   - process alive
   - proxy connect
   - exit IP
   - latency
   - proxy policy
7. Nguồn dữ liệu được phép:
   - IPinfo API
   - httpbin /ip
   - checker nội bộ
8. Nếu phát hiện issue, cập nhật database và audit log.
9. Nếu Critical, chuyển sang Task 6.8 xử lý stop profile.
10. Không log proxy password.

API:
- GET /api/profiles/{profile_id}/runtime-status
- GET /api/profiles/runtime-status
- POST /api/profiles/{profile_id}/runtime-guardian/check-now

Output:
- File đã sửa/tạo.
- Guardian task lifecycle.
- API endpoints.
- Test cases pass/fail.
```

---

# TASK 6.5 — Runtime Guardian Deep Checks

**Status:** Not Started

## Mục tiêu

Kiểm tra sâu định kỳ, ít hơn lightweight check để không làm nặng hệ thống.

## Deep checks

Chạy mỗi 5–15 phút:

```text
user-agent
headers
Accept-Language
Sec-CH-UA nếu lấy được qua checker
timezone
locale
canvas hash
WebGL vendor/renderer
font hash
audio hash nếu có
browser version
session data health
TLS/network checker
```

## Message prompt

```text
Bạn là senior backend QA/security engineer.

Task:
TASK 6.5 — Thêm Runtime Guardian Deep Checks.

Yêu cầu:
1. Thêm field deep_check_interval_minutes default 10.
2. Deep check chạy định kỳ khi profile đang running.
3. So sánh runtime fingerprint với locked fingerprint config:
   - user-agent
   - platform
   - screen
   - timezone
   - locale
   - canvas hash
   - WebGL vendor/renderer
   - font hash
   - audio hash nếu có
   - browser version
4. Nguồn kiểm tra được phép:
   - BrowserLeaks cho manual/semi-auto dev check
   - httpbin cho headers
   - tls.peet.ws/api/all cho TLS/HTTP2
   - checker nội bộ nếu có
5. Nếu fingerprint_locked=true và mismatch core fingerprint → Critical.
6. Nếu TLS/internal checker unavailable → Warning, không fail cứng mặc định.
7. Session data health:
   - user_data_dir tồn tại
   - Cookies DB không lỗi
   - Local Storage/IndexedDB folder không lỗi
8. Không log cookie/localStorage content.
9. Không tự nghĩ thêm website ngoài danh sách nếu chưa được duyệt.

Error codes:
- FINGERPRINT_CANVAS_MISMATCH
- FINGERPRINT_WEBGL_MISMATCH
- FINGERPRINT_FONT_MISMATCH
- FINGERPRINT_UA_MISMATCH
- HEADERS_MISMATCH_CRITICAL
- TLS_CHECK_UNAVAILABLE
- SESSION_DATA_CORRUPTED
- BROWSER_VERSION_WARNING

Output:
- File đã sửa.
- Deep check flow.
- Website/tool nào được dùng cho từng check.
- Severity mapping.
- Test cases pass/fail.
```

---

# TASK 6.6 — Runtime Alert UI per Profile

**Status:** Not Started

## Mục tiêu

Người dùng phải thấy cảnh báo rõ ngay trên từng profile.

## Message prompt

```text
Bạn là senior frontend engineer.

Task:
TASK 6.6 — Thêm Runtime Alert UI per Profile.

Yêu cầu:
1. Trong ProfileList/ProfileCard, thêm badge:
   - Proxy Status
   - Verification Status
   - Runtime Guardian Status
   - Fingerprint Locked
   - Last Check
2. Nếu profile có Critical:
   - hiển thị banner đỏ trên card profile
   - disable Launch
   - hiển thị nút View Report
3. Nếu profile Warning:
   - hiển thị banner vàng
   - admin có thể override nếu policy cho phép
4. Polling mỗi 5 giây:
   - GET /api/profiles/runtime-status
   - cập nhật UI realtime
5. Thêm toast/modal khi có critical mới.
6. Hiển thị message dễ hiểu:
   - “Proxy đã mất kết nối. Profile đã được dừng để đảm bảo an toàn.”
   - “IP proxy đã thay đổi ngoài chính sách.”
   - “Fingerprint không khớp cấu hình đã khóa.”
   - “Kết quả xác minh đã hết hạn. Vui lòng Verify lại profile.”
   - “Session đã được lưu sau khi dừng profile.”

Output:
- File đã sửa.
- Components mới nếu có.
- Badge logic.
- Polling logic.
- Test cases pass/fail.
```

---

# TASK 6.7 — OS Notification từ Electron

**Status:** Not Started

## Mục tiêu

Nếu người dùng không nhìn dashboard, vẫn nhận được cảnh báo hệ điều hành.

## Message prompt

```text
Bạn là senior Electron engineer.

Task:
TASK 6.7 — Thêm OS Notification từ Electron cho cảnh báo Critical.

Yêu cầu:
1. Thêm IPC function:
   showRuntimeNotification({ title, body, profileId, severity })
2. Khi frontend nhận critical issue mới:
   - gọi Electron notification
3. Notification examples:
   - title: “Profile stopped for safety”
   - body: “Proxy IP changed unexpectedly”
4. Chỉ bắn notification khi:
   - severity=critical
   - issue mới, không spam lặp lại mỗi polling
5. Nếu app không chạy desktop mode, bỏ qua notification.

Output:
- File đã sửa.
- IPC API.
- Notification logic.
- Anti-spam logic.
- Test cases pass/fail.
```

---

# TASK 6.8 — Critical Action & Auto Stop

**Status:** Not Started

## Mục tiêu

Lỗi Critical thì không để tiếp tục sử dụng profile.

## Message prompt

```text
Bạn là senior backend engineer.

Task:
TASK 6.8 — Critical Action & Auto Stop.

Yêu cầu:
1. Thêm field:
   - runtime_action_on_critical: stop_profile | warn_only
2. Default:
   - stop_profile
3. Nếu Runtime Guardian phát hiện Critical:
   - runtime_guardian_status=critical
   - runtime_risk_level=critical
   - ghi last_runtime_issue
   - ghi last_runtime_message
   - ghi audit log RUNTIME_GUARDIAN_CRITICAL
4. Nếu runtime_action_on_critical=stop_profile:
   - graceful stop profile
   - đảm bảo cookies/session runtime data được flush/lưu nếu có thể
   - update status stopped_by_guardian
   - cập nhật last_session_save_at nếu session_auto_save=true
   - ghi audit log PROFILE_STOPPED_BY_GUARDIAN
5. Nếu warn_only:
   - không stop
   - UI phải hiển thị cảnh báo đỏ
6. Critical mặc định không override.

Critical errors:
- PROXY_CONNECTION_FAILED
- PROXY_AUTH_FAILED
- PROXY_EXIT_IP_CHANGED
- PROXY_COUNTRY_MISMATCH
- FINGERPRINT_CANVAS_MISMATCH
- FINGERPRINT_WEBGL_MISMATCH
- FINGERPRINT_FONT_MISMATCH
- FINGERPRINT_UA_MISMATCH
- HEADERS_MISMATCH_CRITICAL
- BROWSER_PROCESS_CRASHED
- SESSION_DATA_CORRUPTED

Output:
- File đã sửa.
- Critical handling flow.
- Stop flow integration.
- Audit events.
- Test cases pass/fail.
```

---

# TASK 6.9 — Runtime Report & Audit Log

**Status:** Not Started

## Mục tiêu

Mỗi cảnh báo phải có báo cáo rõ ràng để xem lại.

## Message prompt

```text
Bạn là senior backend/frontend engineer.

Task:
TASK 6.9 — Runtime Report & Audit Log.

Yêu cầu backend:
1. Lưu last_runtime_check_result JSON.
2. Tạo API:
   GET /api/profiles/{profile_id}/runtime-report
3. Report schema:
   {
     "profile_id": "abc",
     "status": "critical",
     "score": 45,
     "checked_at": "...",
     "checks": {
       "proxy": "failed",
       "fingerprint": "pass",
       "headers": "warning",
       "session": "pass"
     },
     "blocking_issues": ["PROXY_EXIT_IP_CHANGED"],
     "warnings": ["PROXY_LATENCY_HIGH"],
     "action_taken": "stop_profile"
   }
4. Ghi audit log cho:
   - PROFILE_VERIFICATION_STARTED
   - PROFILE_VERIFICATION_PASSED
   - PROFILE_VERIFICATION_WARNING
   - PROFILE_VERIFICATION_FAILED
   - RUNTIME_GUARDIAN_STARTED
   - RUNTIME_GUARDIAN_WARNING
   - RUNTIME_GUARDIAN_CRITICAL
   - PROFILE_STOPPED_BY_GUARDIAN
   - SESSION_SAVED_ON_STOP
   - ADMIN_OVERRIDE_VERIFICATION_WARNING
5. Không log secret.

Yêu cầu frontend:
1. Thêm View Report modal.
2. Hiển thị:
   - overall status
   - score
   - last check time
   - blocking issues
   - warnings
   - action taken
3. Dịch message lỗi sang câu dễ hiểu cho user.

Output:
- File đã sửa.
- Report schema.
- API endpoint.
- UI modal.
- Test cases pass/fail.
```

---

# TASK 6.10 — Proxy Change Re-verification

**Status:** Not Started

## Mục tiêu

Khi proxy thay đổi, profile không được dùng tiếp nếu chưa verify lại.

## Message prompt

```text
Bạn là senior backend/frontend engineer.

Task:
TASK 6.10 — Proxy Change Re-verification.

Yêu cầu:
1. Khi đổi proxy của profile:
   - update Network Config
   - không regenerate fingerprint
   - ghi audit log PROXY_CHANGED
   - ghi audit log FINGERPRINT_UNCHANGED_AFTER_PROXY_CHANGE
2. Nếu verification_expires_on_proxy_change=true:
   - set verification_status=expired
   - set runtime_guardian_status=idle nếu profile stopped
   - UI hiển thị “Proxy changed. Re-verification required.”
3. Nếu profile đang running và proxy đổi runtime:
   - evaluate proxy policy
   - nếu ngoài policy → Critical
   - nếu trong policy nhưng cần reverify → Warning + verification expired
4. Disable Launch nếu verification expired.
5. Không thay đổi:
   - canvas
   - WebGL
   - fonts
   - user-agent
   - screen
   - hardwareConcurrency
   - deviceMemory
   - audio fingerprint
   - fingerprint_seed

Output:
- File đã sửa.
- Proxy update flow.
- Verification expired flow.
- UI message.
- Test cases pass/fail.
```

---

# TASK 6.11 — Admin Override Policy

**Status:** Not Started

## Mục tiêu

Chỉ cho override Warning có kiểm soát. Critical không override mặc định.

## Message prompt

```text
Bạn là senior full-stack engineer.

Task:
TASK 6.11 — Admin Override Policy.

Yêu cầu:
1. Thêm rule:
   - regular user: không override warning/critical
   - admin: override warning
   - super_admin: override warning, critical chỉ khi config đặc biệt cho phép
2. Critical mặc định không override.
3. Khi admin override warning:
   - yêu cầu nhập reason
   - ghi audit log ADMIN_OVERRIDE_VERIFICATION_WARNING
4. UI:
   - User thường không thấy nút Override
   - Admin thấy Override Warning
   - Critical chỉ hiện Fix Required / View Report
5. API:
   POST /api/profiles/{profile_id}/override-warning
   Body: { reason: string }

Output:
- File đã sửa.
- Permission rules.
- UI rules.
- API endpoint.
- Audit log.
- Test cases pass/fail.
```

---

# TASK 6.12 — Cookie/Session Save Integrity

**Status:** Not Started

## Mục tiêu

Đảm bảo khi dừng profile, cookies/session mới vẫn được lưu, nhưng fingerprint config không bị thay đổi.

## Message prompt

```text
Bạn là senior backend QA engineer.

Task:
TASK 6.12 — Cookie/Session Save Integrity.

Mục tiêu:
Khi stop/dừng profile sau khi sử dụng, hệ thống phải giữ cookies/session/localStorage/IndexedDB mới nhất. Nhưng không được tự thay đổi Fingerprint Config.

Yêu cầu:
1. Khi Stop profile:
   - graceful stop trước
   - chờ browser flush dữ liệu nếu có thể
   - cập nhật last_session_save_at nếu session_auto_save=true
   - ghi audit log SESSION_SAVED_ON_STOP
2. Không được ghi đè:
   - fingerprint_seed
   - canvas config/hash
   - WebGL config/hash
   - font config/hash
   - user-agent
   - screen
   - hardware info
3. Test:
   - Launch profile
   - tạo cookie/localStorage test bằng một trang test nội bộ hoặc local page
   - Stop profile
   - Launch lại
   - kiểm tra cookie/localStorage vẫn còn
   - kiểm tra fingerprint config không đổi
4. Nếu profile bị Runtime Guardian stop do Critical:
   - vẫn cố gắng graceful stop
   - vẫn ghi last_session_save_at nếu lưu thành công
5. Không log cookie/localStorage content.

Output:
- File đã sửa.
- Stop/save flow.
- Test cases pass/fail.
```

---

# TASK 6.13 — System Test Phase 6

**Status:** Not Started

## Mục tiêu

Test toàn bộ tính năng Phase 6 trước khi dùng nội bộ.

## Message prompt

```text
Bạn là senior QA engineer.

Task:
TASK 6.13 — System Test Phase 6.

Yêu cầu:
Chạy test toàn bộ Phase 6:

1. Pre-launch Gate:
- Profile mới chưa verify → Launch bị chặn.
- Verify PASS → Launch được.
- Verify FAIL → Launch bị chặn.

2. Proxy Policy:
- static_residential IP giữ nguyên → OK.
- static_residential IP đổi → Critical.
- rotating allow_ip_rotation=true cùng country → Warning + verification expired.
- rotating đổi country → Critical.

3. Runtime Guardian:
- Launch profile → guardian starts.
- Stop profile → guardian stops.
- Proxy die khi đang chạy → Critical + stop profile.
- Browser process crash → Critical/stopped.

4. Fingerprint Lock:
- Đổi proxy → fingerprint unchanged.
- Canvas/WebGL/font mismatch → Critical.

5. Cookie/Session Save:
- Dùng profile tạo cookies/localStorage test.
- Stop profile.
- Launch lại.
- cookies/localStorage vẫn còn.
- fingerprint config không đổi.

6. UI Alerts:
- Badge đúng màu.
- Banner đỏ khi Critical.
- Launch disabled khi failed/expired/critical.
- View Report đúng.
- OS notification chỉ bắn khi critical mới.

7. Permissions:
- User thường không override.
- Admin override warning được.
- Critical không override mặc định.

8. Security:
- Không log cookie value.
- Không log localStorage content.
- Không log proxy password/token.

Output:
- Pass/fail table.
- Bug list theo Blocker/Major/Minor.
- File cần sửa nếu fail.
- Kết luận:
  - Phase 6 Ready
  - Needs Fix
  - Blocked
```

---

## 7. Thứ tự triển khai khuyến nghị

Không làm tất cả cùng lúc.

```text
6.1 Proxy Policy Engine
6.2 Verification Status & Launch Gate
6.3 Pre-launch Verification Checks
6.6 Runtime Alert UI cơ bản
6.4 Runtime Guardian Lightweight Checks
6.8 Critical Action & Auto Stop
6.9 Runtime Report & Audit Log
6.10 Proxy Change Re-verification
6.11 Admin Override Policy
6.12 Cookie/Session Save Integrity
6.5 Runtime Guardian Deep Checks
6.7 OS Notification
6.13 System Test
```

Lý do:

```text
Làm Gate + Proxy Policy trước để chặn rủi ro lớn.
Làm Runtime Guardian nhẹ trước để phát hiện proxy chết/IP đổi.
Deep fingerprint check làm sau vì phức tạp hơn.
Cookie/session save integrity phải được test riêng để tránh mất session khi stop.
```

---

## 8. Điều kiện Phase 6 hoàn thành

```text
Profile chưa verified thì không launch được
Verify profile pass thì launch được
Proxy static mà IP đổi thì Critical
Runtime Guardian phát hiện proxy lỗi khi đang dùng
Lỗi Critical thì profile bị stop hoặc cảnh báo đỏ theo policy
UI hiện badge/banners rõ trên từng profile
OS notification hoạt động khi có critical mới
Đổi proxy không đổi fingerprint
Đổi proxy làm verification expired
Stop profile vẫn lưu cookies/session mới
Stop profile không làm đổi fingerprint config
View Report xem được lý do lỗi
Admin chỉ override Warning
Không log secret
System test pass
```

---

## 9. Kết luận

Phase 6 biến app từ “profile manager” thành “profile safety system”.

Cấu hình vận hành khuyến nghị:

```text
Proxy: Static Residential / Sticky Residential TTL dài
Fingerprint Locked: ON
Session Auto Save: ON
Require Verification Before Use: ON
Runtime Guardian: ON
Critical Action: Stop Profile
Proxy Change: Verification Expired
Admin: Override Warning có lý do
```

Backend kiểm tra, database lưu trạng thái, Electron UI hiển thị cảnh báo rõ ràng cho từng profile.
