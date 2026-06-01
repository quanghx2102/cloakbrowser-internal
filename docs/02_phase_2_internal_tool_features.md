# PHASE 2 — Phát Triển Tool Nội Bộ Dùng Được Hằng Ngày

## Source repo bắt buộc

Repo chính cần bám theo:

- CloakBrowser engine: https://github.com/CloakHQ/CloakBrowser
- CloakBrowser Manager nếu cần phần app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager

Nguyên tắc:
- Luôn đọc cấu trúc repo hiện tại trước khi đề xuất sửa.
- Không tự thiết kế app từ đầu nếu repo gốc đã có chức năng tương ứng.
- Không tự đổi stack công nghệ nếu chưa có lý do kỹ thuật rõ ràng.
- Ưu tiên fork/chỉnh trên CloakBrowser Manager.
- CloakBrowser là browser engine, CloakBrowser Manager là app quản lý profile/UI/backend.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.

## Mục tiêu Phase 2

Fork CloakBrowser Manager và thêm các chức năng cần thiết để dùng nội bộ ổn định hơn:

- Profile list/create/edit/delete rõ ràng hơn.
- Launch/stop/restart ổn định hơn.
- Proxy manager.
- Proxy checker.
- Logging/error tracking.
- Activity log.
- Dashboard cơ bản.

## Output cuối Phase 2

Một tool nội bộ có thể dùng hằng ngày với khả năng debug lỗi rõ ràng.

```text
Profile Management + Browser Control + Proxy Checker + Logs + Dashboard
```

---

# TASK 2.1 — Chuẩn Hóa Profile List

## Mục tiêu

Làm trang danh sách profile dễ dùng hơn cho nội bộ.

## Yêu cầu

- Hiển thị danh sách profile.
- Có trạng thái running/stopped/failed.
- Hiển thị proxy đang gắn.
- Có nút Launch/Stop/View/Edit/Logs.
- Có search theo tên.
- Có filter theo status.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Có profile | Hiển thị đúng danh sách |
| Không có profile | Empty state rõ ràng |
| Search | Lọc đúng profile |
| Filter status | Lọc đúng trạng thái |
| Nút action | Gọi đúng API |

## Prompt copy cho AI/dev

```text
Bạn là senior React/FastAPI full-stack engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tôi đã fork CloakBrowser Manager để làm tool nội bộ. Phase 1 đã xác nhận lõi chạy được. Bây giờ cần cải thiện trang danh sách profile.

Task:
TASK 2.1 — Chuẩn hóa Profile List.

Yêu cầu:
1. Đọc code hiện tại của trang profile list.
2. Không viết lại toàn bộ app.
3. Hiển thị các cột: name, status, proxy, last launched, actions.
4. Thêm search theo tên profile nếu chưa có.
5. Thêm filter theo status nếu chưa có.
6. Nút action gồm Launch, Stop, View, Edit, Logs.
7. Trạng thái profile phải dễ nhìn.
8. Không đụng logic launch/stop nếu không cần.

Output cần trả:
- File đã sửa.
- Mô tả thay đổi.
- Test case.
- Cách kiểm tra UI.
```

---

# TASK 2.2 — Create/Edit/Delete Profile Hoàn Chỉnh

## Mục tiêu

Chuẩn hóa flow tạo, sửa, xóa profile.

## Yêu cầu

- Form tạo profile.
- Form sửa profile.
- Validate tên profile.
- Chọn proxy nếu có.
- Chọn timezone/locale/platform nếu hệ thống hỗ trợ.
- Không cho xóa profile đang running.
- Toast/error message rõ ràng.

## Logging

| Event | Error code |
|---|---|
| Tạo thành công | PROFILE_CREATED |
| Tạo lỗi | PROFILE_CREATE_FAILED |
| Sửa thành công | PROFILE_UPDATED |
| Sửa lỗi | PROFILE_UPDATE_FAILED |
| Xóa thành công | PROFILE_DELETED |
| Xóa lỗi | PROFILE_DELETE_FAILED |
| Xóa profile đang chạy | PROFILE_LOCKED |

## Prompt copy cho AI/dev

```text
Bạn là senior full-stack engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ dựa trên CloakBrowser Manager cần flow Create/Edit/Delete profile ổn định và có log lỗi rõ.

Task:
TASK 2.2 — Create/Edit/Delete Profile hoàn chỉnh.

Yêu cầu backend:
1. Validate name không rỗng.
2. Không cho xóa profile đang running.
3. Tạo/sửa/xóa phải ghi activity log.
4. Khi lỗi phải ghi error log với error_code.
5. Không làm thay đổi browser engine.

Yêu cầu frontend:
1. Có modal/form tạo profile.
2. Có modal/form sửa profile.
3. Có confirm khi xóa profile.
4. Hiển thị toast success/error.
5. UI rõ ràng, không cần quá đẹp.

Logging:
- PROFILE_CREATED
- PROFILE_CREATE_FAILED
- PROFILE_UPDATED
- PROFILE_UPDATE_FAILED
- PROFILE_DELETED
- PROFILE_DELETE_FAILED
- PROFILE_LOCKED

Output cần trả:
- File đã sửa.
- API liên quan.
- Logic validate.
- Test case.
- Cách test thủ công.
```

---

# TASK 2.3 — Launch/Stop/Restart Profile Có Trạng Thái Rõ Ràng

## Mục tiêu

Chuẩn hóa trạng thái browser profile và tránh lỗi process trùng.

## Yêu cầu

- Status: starting/running/stopping/stopped/failed/crashed.
- Không cho launch profile đang running.
- Stop phải tắt process sạch.
- Restart = stop rồi launch lại.
- Ghi duration khi launch.
- Ghi lỗi nếu browser crash.

## Logging

| Event | Error code |
|---|---|
| Launch thành công | BROWSER_STARTED |
| Launch lỗi | BROWSER_START_FAILED |
| Stop thành công | BROWSER_STOPPED |
| Stop lỗi | BROWSER_STOP_FAILED |
| Browser crash | BROWSER_CRASHED |
| Launch trùng | PROFILE_ALREADY_RUNNING |

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer có kinh nghiệm quản lý process.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần launch/stop/restart browser profile ổn định. Không được tạo process trùng cho cùng một profile.

Task:
TASK 2.3 — Launch/Stop/Restart Profile có trạng thái rõ ràng.

Yêu cầu:
1. Đọc logic launcher hiện tại.
2. Thêm/chuẩn hóa status: starting, running, stopping, stopped, failed, crashed.
3. Không cho launch profile đang running/starting.
4. Stop phải graceful trước, force kill nếu timeout.
5. Restart = stop hoàn tất rồi launch lại.
6. Ghi duration_ms khi launch.
7. Ghi activity log và error log.
8. Không refactor lớn nếu chưa cần.

Logging:
- BROWSER_STARTED
- BROWSER_START_FAILED
- BROWSER_STOPPED
- BROWSER_STOP_FAILED
- BROWSER_CRASHED
- PROFILE_ALREADY_RUNNING

Output cần trả:
- File đã sửa.
- Luồng launch/stop/restart.
- Cách chống process trùng.
- Test case.
- Cách kiểm tra bằng process list/log.
```

---

# TASK 2.4 — Proxy Manager

## Mục tiêu

Tạo trang quản lý proxy nội bộ.

## Yêu cầu

- Thêm/sửa/xóa proxy.
- Hỗ trợ type: HTTP/HTTPS/SOCKS5 nếu backend hiện có hỗ trợ.
- Lưu host, port, username, password.
- Không hiển thị password đầy đủ trên UI.
- Gắn proxy vào profile.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Thêm proxy | Proxy lưu vào DB |
| Sửa proxy | Dữ liệu cập nhật |
| Xóa proxy | Proxy bị xóa nếu không bị ràng buộc |
| Gắn proxy profile | Profile lưu proxy_id |
| Password | Không lộ full password trên UI/log |

## Prompt copy cho AI/dev

```text
Bạn là senior full-stack engineer có kinh nghiệm proxy management.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần trang Proxy Manager để thêm/sửa/xóa proxy và gắn proxy vào profile.

Task:
TASK 2.4 — Proxy Manager.

Yêu cầu backend:
1. Tạo hoặc chuẩn hóa model/table proxy nếu cần.
2. API list/create/update/delete proxy.
3. Không log password proxy dạng plain text.
4. Password nếu lưu DB nên mã hóa hoặc ít nhất mask khi trả về frontend.
5. Cho phép profile tham chiếu proxy_id.

Yêu cầu frontend:
1. Trang danh sách proxy.
2. Form thêm/sửa proxy.
3. Confirm khi xóa.
4. Mask password.
5. Hiển thị type, host, port, status.

Không làm:
- Chưa cần bulk import proxy.
- Chưa cần proxy checker nâng cao ở task này.

Output cần trả:
- File đã sửa.
- DB/schema nếu có.
- API proxy.
- UI thay đổi.
- Test case.
```

---

# TASK 2.5 — Proxy Checker

## Mục tiêu

Kiểm tra proxy sống/chết, auth, latency và IP exit.

## Yêu cầu

- Check proxy đơn lẻ.
- Lưu status.
- Lưu latency.
- Lưu last_ip nếu lấy được.
- Báo lỗi proxy auth/timeout/connection failed.
- Có nút check trên UI.

## Logging

| Error code | Ý nghĩa |
|---|---|
| PROXY_OK | Proxy hoạt động |
| PROXY_AUTH_FAILED | Sai auth |
| PROXY_TIMEOUT | Timeout |
| PROXY_CONNECTION_FAILED | Không kết nối được |
| PROXY_CHECK_FAILED | Lỗi không xác định |

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer có kinh nghiệm network/proxy debugging.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần kiểm tra proxy trước khi gắn vào profile hoặc trước khi launch browser.

Task:
TASK 2.5 — Proxy Checker.

Yêu cầu:
1. Thêm endpoint check proxy đơn lẻ.
2. Kiểm tra connection, auth, timeout.
3. Đo latency_ms.
4. Lấy exit IP nếu có thể.
5. Lưu status, latency_ms, last_ip, last_checked_at.
6. Frontend có nút Check proxy.
7. Không log username/password đầy đủ.
8. Timeout phải có giới hạn rõ ràng.

Error code:
- PROXY_OK
- PROXY_AUTH_FAILED
- PROXY_TIMEOUT
- PROXY_CONNECTION_FAILED
- PROXY_CHECK_FAILED

Output cần trả:
- File đã sửa.
- Endpoint mới.
- Logic check proxy.
- UI thay đổi.
- Test case với proxy đúng/sai/timeout.
```

---

# TASK 2.6 — Structured Logging Và Error Tracking

## Mục tiêu

Mọi lỗi quan trọng phải có log rõ ràng: module, profile_id, action, error_code, message.

## Yêu cầu

- Tạo logger chuẩn JSON.
- Tạo bảng/file error_logs nếu cần.
- Tạo helper log_activity.
- Tạo helper log_error.
- Không log secret/password/token.
- Các module profile/browser/proxy dùng chung logger.

## Format log

```json
{
  "timestamp": "2026-05-30T20:00:00+07:00",
  "level": "error",
  "module": "browser_launcher",
  "profile_id": "profile_001",
  "action": "launch_profile",
  "status": "failed",
  "error_code": "BROWSER_START_FAILED",
  "message": "Browser process exited before CDP was ready",
  "duration_ms": 4280
}
```

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ hiện cần hệ thống logging chuẩn để debug lỗi profile/browser/proxy. Ưu tiên log có cấu trúc, dễ filter.

Task:
TASK 2.6 — Structured Logging và Error Tracking.

Yêu cầu:
1. Kiểm tra logging hiện tại.
2. Thiết kế helper log_activity và log_error.
3. Log cần có: timestamp, level, module, action, status, error_code, message, profile_id, proxy_id nếu có, duration_ms nếu có.
4. Không log password/token/secret.
5. Áp dụng logger vào profile create/update/delete, browser launch/stop, proxy check.
6. Nếu dùng DB, tạo bảng error_logs/activity_logs.
7. Nếu chưa dùng DB, ít nhất ghi JSON logs ra file.

Output cần trả:
- File đã sửa.
- Log schema.
- Helper functions.
- Những chỗ đã tích hợp log.
- Test case.
```

---

# TASK 2.7 — Activity Log

## Mục tiêu

Lưu lịch sử thao tác của user hoặc admin nội bộ.

## Yêu cầu

- Lưu khi tạo/sửa/xóa profile.
- Lưu khi launch/stop/restart.
- Lưu khi thêm/sửa/xóa proxy.
- Trang UI xem activity log.
- Filter theo profile/action/time.

## Prompt copy cho AI/dev

```text
Bạn là senior full-stack engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần Activity Log để biết ai/lúc nào đã thao tác gì với profile/proxy/browser.

Task:
TASK 2.7 — Activity Log.

Yêu cầu backend:
1. Tạo activity_logs nếu chưa có.
2. Ghi log cho profile create/update/delete.
3. Ghi log cho browser launch/stop/restart.
4. Ghi log cho proxy create/update/delete/check.
5. API list activity logs có filter action/profile_id/time.

Yêu cầu frontend:
1. Trang Activity Logs.
2. Hiển thị time, action, module, profile, status, message.
3. Filter cơ bản.

Không làm:
- Chưa cần audit permission phức tạp.
- Chưa cần export CSV ở task này.

Output cần trả:
- File đã sửa.
- API.
- UI.
- Test case.
```

---

# TASK 2.8 — Dashboard Cơ Bản

## Mục tiêu

Có dashboard để xem nhanh trạng thái hệ thống.

## Widget cần có

- Tổng số profile.
- Số profile running.
- Số profile stopped.
- Số profile failed/crashed.
- Số proxy OK.
- Số proxy lỗi.
- 10 lỗi gần nhất.
- Nút Stop All Profiles.

## Prompt copy cho AI/dev

```text
Bạn là senior full-stack engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần dashboard đơn giản để xem trạng thái profile/proxy/browser và lỗi gần nhất.

Task:
TASK 2.8 — Dashboard cơ bản.

Yêu cầu backend:
1. Tạo endpoint /api/dashboard/summary.
2. Trả về tổng profile, running, stopped, failed/crashed.
3. Trả về tổng proxy OK/lỗi.
4. Trả về danh sách lỗi gần nhất.
5. Endpoint stop all profiles nếu chưa có thì đề xuất/triển khai cẩn thận.

Yêu cầu frontend:
1. Trang Dashboard.
2. Cards thống kê.
3. Bảng lỗi gần nhất.
4. Nút Stop All Profiles có confirm.

Output cần trả:
- File đã sửa.
- API response mẫu.
- UI thay đổi.
- Test case.
```
