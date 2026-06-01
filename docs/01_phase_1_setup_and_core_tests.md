# PHASE 1 — Setup Và Kiểm Tra Lõi CloakBrowser Manager

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

## Mục tiêu Phase 1

Chạy được bản gốc CloakBrowser Manager và xác nhận các chức năng lõi hoạt động:

- Chạy Docker thành công.
- Tạo/sửa/xóa profile.
- Launch/stop/restart browser.
- Kiểm tra session còn sau restart.
- Gắn proxy và test proxy.
- Mở browser qua noVNC.
- Kết nối CDP bằng Playwright/Puppeteer.

## Output cuối Phase 1

Một bản CloakBrowser Manager chạy nội bộ ổn định ở mức MVP.

```text
Docker → Web UI → Profile → Launch Browser → noVNC/CDP → Session Persistent
```

---

# TASK 1.1 — Clone/Fork Repo Và Chạy Docker

## Mục tiêu

Clone hoặc fork CloakBrowser Manager, chạy được app bằng Docker Compose trên máy local/server nội bộ.

## Yêu cầu

- Clone/fork repo.
- Kiểm tra file Docker/Docker Compose có sẵn.
- Chạy app thành công.
- Xác định port truy cập UI.
- Xác định thư mục lưu data/profile.
- Ghi lại command setup.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Docker build/run | Container chạy không lỗi |
| Mở UI | Truy cập được giao diện web |
| Restart container | Dữ liệu không mất nếu đã mount volume |
| Xem logs container | Không có lỗi nghiêm trọng |

## Prompt copy cho AI/dev

```text
Bạn là senior full-stack/devops engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tôi đang build tool nội bộ dựa trên CloakBrowser Manager. Đây không phải sản phẩm thương mại. Mục tiêu hiện tại là chạy được app gốc bằng Docker để kiểm tra lõi.

Task:
TASK 1.1 — Clone/Fork repo và chạy Docker.

Yêu cầu:
1. Kiểm tra cấu trúc repo hiện tại.
2. Xác định cách chạy bằng Docker/Docker Compose.
3. Kiểm tra port UI, thư mục data, thư mục profile.
4. Nếu cần, tạo file .env mẫu.
5. Không thay đổi business logic.
6. Trả về command chạy từng dòng rõ ràng.
7. Trả về checklist kiểm tra sau khi chạy.

Output cần trả:
- Các file cần tạo/sửa nếu có.
- Command setup.
- Cách mở UI.
- Cách xem log.
- Cách restart container.
- Test case xác nhận thành công.
```

---

# TASK 1.2 — Kiểm Tra Profile Create/Edit/Delete

## Mục tiêu

Xác nhận app gốc tạo, sửa, xóa profile hoạt động đúng.

## Yêu cầu

- Tạo profile mới.
- Sửa thông tin profile.
- Xóa profile.
- Kiểm tra dữ liệu có lưu vào database không.
- Kiểm tra folder profile có được tạo/xóa đúng không.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Tạo profile có tên hợp lệ | Profile xuất hiện trong danh sách |
| Sửa tên profile | UI và DB cập nhật đúng |
| Xóa profile | Profile không còn trong UI |
| Tạo profile thiếu tên | Báo lỗi rõ |
| Kiểm tra data path | Có thư mục profile tương ứng |

## Prompt copy cho AI/dev

```text
Bạn là senior backend/full-stack engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tôi đang kiểm tra CloakBrowser Manager để dùng làm tool nội bộ. Hiện tại chỉ cần xác nhận chức năng quản lý profile gốc hoạt động đúng.

Task:
TASK 1.2 — Kiểm tra Profile Create/Edit/Delete.

Yêu cầu:
1. Đọc code hiện tại liên quan đến profile management.
2. Xác định API tạo/sửa/xóa profile.
3. Xác định database/table lưu profile.
4. Xác định profile data folder được tạo ở đâu.
5. Không viết lại UI nếu chưa cần.
6. Nếu phát hiện lỗi nhỏ, đề xuất fix tối thiểu.
7. Trả về checklist test thủ công.

Output cần trả:
- API liên quan.
- File backend/frontend liên quan.
- Luồng create/edit/delete profile.
- Test case.
- Lỗi/rủi ro nếu có.
- Đề xuất fix tối thiểu nếu cần.
```

---

# TASK 1.3 — Kiểm Tra Launch/Stop Browser

## Mục tiêu

Xác nhận profile launch được browser, stop được browser và process tắt sạch.

## Yêu cầu

- Launch một profile.
- Kiểm tra browser process.
- Stop profile.
- Kiểm tra process đã tắt.
- Ghi nhận lỗi nếu browser không mở.
- Ghi nhận thời gian launch.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Launch profile | Browser chạy được |
| Stop profile | Browser process tắt |
| Launch profile đang chạy | Không tạo process trùng |
| Stop profile chưa chạy | Báo trạng thái hợp lý |
| Browser lỗi khi launch | Có log lỗi rõ |

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer có kinh nghiệm process management.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Dự án dùng CloakBrowser Manager làm base cho tool nội bộ. Tôi cần kiểm tra chức năng launch/stop browser theo từng profile.

Task:
TASK 1.3 — Kiểm tra Launch/Stop Browser.

Yêu cầu:
1. Đọc code liên quan đến browser launcher.
2. Xác định command/process dùng để launch CloakBrowser.
3. Xác định cách app lưu trạng thái running/stopped.
4. Kiểm tra có chống launch trùng profile không.
5. Kiểm tra stop có kill process sạch không.
6. Đề xuất log tối thiểu cho launch/stop.
7. Không refactor lớn.

Output cần trả:
- File liên quan.
- Luồng launch browser.
- Luồng stop browser.
- Cách kiểm tra process.
- Test case.
- Lỗi/rủi ro phát hiện.
- Fix nhỏ nếu cần.
```

---

# TASK 1.4 — Kiểm Tra Session Persistence

## Mục tiêu

Kiểm tra cookie/localStorage/cache có còn sau khi tắt/mở lại profile không.

## Yêu cầu

- Mở profile.
- Truy cập một website test nội bộ/được phép.
- Lưu cookie/localStorage.
- Stop browser.
- Launch lại profile.
- Kiểm tra session còn hay mất.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Lưu cookie | Cookie còn sau restart |
| Lưu localStorage | localStorage còn sau restart |
| Stop/start profile | Dữ liệu profile không mất |
| Xóa profile | Dữ liệu profile bị xóa nếu logic yêu cầu |

## Prompt copy cho AI/dev

```text
Bạn là senior QA/backend engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tôi đang kiểm tra CloakBrowser Manager để dùng nội bộ. Cần xác nhận profile data persistent hoạt động đúng.

Task:
TASK 1.4 — Kiểm tra Session Persistence.

Yêu cầu:
1. Xác định folder lưu dữ liệu browser profile.
2. Tạo kịch bản test cookie/localStorage/cache.
3. Launch profile, tạo dữ liệu session, stop, launch lại.
4. Kiểm tra dữ liệu còn hay mất.
5. Nếu session mất, tìm nguyên nhân từ data path/volume/browser args.
6. Không sửa code nếu chưa xác định lỗi.

Output cần trả:
- Vị trí profile data folder.
- Cách test cookie/localStorage.
- Kết quả mong muốn.
- Nguyên nhân có thể nếu session mất.
- Đề xuất fix nếu cần.
```

---

# TASK 1.5 — Kiểm Tra Proxy Theo Profile

## Mục tiêu

Xác nhận mỗi profile có thể gắn proxy riêng và browser đi qua proxy đó.

## Yêu cầu

- Gắn proxy hợp lệ vào profile.
- Launch profile.
- Kiểm tra IP exit.
- Test proxy sai auth.
- Test proxy timeout.
- Ghi nhận lỗi proxy.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Proxy đúng | Browser đi qua proxy |
| Proxy sai username/password | Báo lỗi auth |
| Proxy chết | Báo timeout/connection failed |
| Không proxy | Browser chạy direct hoặc theo config mặc định |
| Đổi proxy | Profile dùng proxy mới sau restart |

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer có kinh nghiệm proxy/network debugging.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ dựa trên CloakBrowser Manager cần gắn proxy riêng cho từng profile. Tôi cần kiểm tra chức năng proxy hiện tại.

Task:
TASK 1.5 — Kiểm tra Proxy theo profile.

Yêu cầu:
1. Đọc code phần proxy config.
2. Xác định proxy được truyền vào browser bằng cách nào.
3. Kiểm tra HTTP/SOCKS5 nếu repo hỗ trợ.
4. Test proxy hợp lệ, proxy sai auth, proxy timeout.
5. Đề xuất error code tối thiểu cho lỗi proxy.
6. Không thêm proxy checker hoàn chỉnh ở task này.

Output cần trả:
- File liên quan.
- Format proxy hiện tại.
- Cách gắn proxy vào profile.
- Test case.
- Error code đề xuất.
- Rủi ro/lỗi nếu có.
```

---

# TASK 1.6 — Kiểm Tra noVNC Viewer

## Mục tiêu

Xác nhận có thể mở và thao tác browser qua noVNC trong web UI.

## Yêu cầu

- Launch profile.
- Mở viewer.
- Kiểm tra thao tác chuột/bàn phím.
- Kiểm tra viewer lỗi khi profile chưa chạy.
- Kiểm tra viewer lỗi khi browser crash.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Profile running | Viewer mở được |
| Profile stopped | Báo profile chưa chạy |
| Browser crash | Viewer báo lỗi/không treo UI |
| Nhiều profile | Viewer đúng profile |

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
CloakBrowser Manager dùng noVNC để xem browser trong web UI. Tôi cần kiểm tra viewer hoạt động ổn định cho tool nội bộ.

Task:
TASK 1.6 — Kiểm tra noVNC Viewer.

Yêu cầu:
1. Đọc code liên quan đến noVNC/viewer.
2. Xác định viewer URL được tạo như thế nào.
3. Test viewer với profile running.
4. Test viewer với profile stopped.
5. Test viewer khi browser crash.
6. Đề xuất log lỗi VNC_CONNECT_FAILED nếu cần.
7. Không đổi UI lớn.

Output cần trả:
- File frontend/backend liên quan.
- Luồng mở viewer.
- Test case.
- Lỗi/rủi ro.
- Fix tối thiểu nếu cần.
```

---

# TASK 1.7 — Kiểm Tra CDP/Playwright Connection

## Mục tiêu

Xác nhận có thể kết nối vào profile đang chạy bằng CDP endpoint.

## Yêu cầu

- Launch profile.
- Lấy CDP endpoint.
- Kết nối bằng Playwright.
- Mở page test.
- Đóng kết nối mà không làm crash browser.

## Test case

| Test | Kết quả mong muốn |
|---|---|
| Profile running | CDP connect được |
| Profile stopped | CDP báo không available |
| Kết nối nhiều lần | Không crash browser |
| CDP lỗi | Có log rõ |

## Prompt copy cho AI/dev

```text
Bạn là senior automation engineer có kinh nghiệm Playwright/CDP.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ dựa trên CloakBrowser Manager cần hỗ trợ automation qua CDP cho profile đang chạy.

Task:
TASK 1.7 — Kiểm tra CDP/Playwright Connection.

Yêu cầu:
1. Xác định CDP endpoint của profile lấy ở đâu.
2. Viết script test Playwright connect qua CDP.
3. Test profile running và stopped.
4. Đảm bảo script disconnect không làm browser crash.
5. Đề xuất log CDP_CONNECT_FAILED nếu cần.
6. Không viết automation workflow phức tạp ở task này.

Output cần trả:
- Cách lấy CDP endpoint.
- Script test tối thiểu.
- Test case.
- Lỗi/rủi ro.
- Fix tối thiểu nếu cần.
```

---

# TASK 1.8 — Tổng Kết Phase 1 Và Quyết Định Fork

## Mục tiêu

Tổng hợp kết quả test Phase 1 và quyết định có fork để phát triển tiếp hay không.

## Yêu cầu

- Liệt kê chức năng đã pass/fail.
- Liệt kê lỗi nghiêm trọng.
- Liệt kê lỗi có thể fix.
- Đánh giá có đủ làm base không.
- Tạo backlog cho Phase 2.

## Prompt copy cho AI/dev

```text
Bạn là technical lead.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tôi đã test các chức năng lõi của CloakBrowser Manager ở Phase 1. Cần tổng kết để quyết định fork và phát triển Phase 2.

Task:
TASK 1.8 — Tổng kết Phase 1 và quyết định fork.

Input:
Tôi sẽ cung cấp kết quả test từng task.

Yêu cầu:
1. Tổng hợp pass/fail theo từng chức năng.
2. Phân loại lỗi: blocker, major, minor.
3. Đề xuất có nên fork repo để phát triển tiếp không.
4. Tạo backlog Phase 2 theo thứ tự ưu tiên.
5. Không viết code trong task này.

Output cần trả:
- Bảng pass/fail.
- Bảng lỗi.
- Quyết định kỹ thuật.
- Backlog Phase 2.
- Rủi ro còn lại.
```
