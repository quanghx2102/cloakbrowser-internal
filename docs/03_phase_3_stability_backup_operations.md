# PHASE 3 — Ổn Định, Backup, Resource Guard Và Vận Hành Lâu Dài

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

## Mục tiêu Phase 3

Làm tool nội bộ đủ ổn định để dùng lâu dài:

- Backup/restore.
- Giới hạn tài nguyên.
- Crash watcher.
- Stop all profiles.
- UI tiếng Việt.
- Tài liệu vận hành.
- Chuẩn bị nâng SQLite lên PostgreSQL nếu cần.

## Output cuối Phase 3

Một tool nội bộ có thể vận hành lâu dài, ít rủi ro mất dữ liệu, dễ debug, dễ bảo trì.

```text
Stable Internal Tool = Backup + Resource Guard + Monitoring + Vietnamese UI + Runbook
```

---

# TASK 3.1 — Backup Database

## Mục tiêu

Backup database định kỳ để tránh mất dữ liệu profile/proxy/log.

## Yêu cầu

- Tạo backup database thủ công.
- Lưu file backup vào thư mục backups.
- Đặt tên file có timestamp.
- Có API/UI tạo backup.
- Có danh sách backup.
- Không backup khi đang ghi dữ liệu quan trọng nếu có rủi ro.

## Prompt copy cho AI/dev

```text
Bạn là senior backend/devops engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần backup database để tránh mất dữ liệu profile/proxy/log. Hiện app có thể đang dùng SQLite hoặc PostgreSQL tùy cấu hình.

Task:
TASK 3.1 — Backup Database.

Yêu cầu:
1. Xác định database hiện tại là SQLite hay PostgreSQL.
2. Tạo service backup database.
3. File backup phải có timestamp.
4. Lưu vào BACKUP_PATH.
5. API tạo backup thủ công.
6. API list backups.
7. Ghi activity log khi backup thành công.
8. Ghi error log BACKUP_FAILED khi lỗi.
9. Không đụng logic browser.

Output cần trả:
- File đã sửa.
- Cách backup SQLite/PostgreSQL.
- API mới.
- Test case.
- Cách restore thủ công nếu cần.
```

---

# TASK 3.2 — Backup Profile Folder

## Mục tiêu

Backup dữ liệu profile folder gồm cookie/session/cache/localStorage.

## Yêu cầu

- Backup thư mục profile data.
- Có thể nén thành zip/tar.gz.
- Không backup profile đang running nếu có nguy cơ hỏng dữ liệu.
- Có cảnh báo nếu còn profile đang chạy.
- Lưu metadata backup.

## Prompt copy cho AI/dev

```text
Bạn là senior backend/devops engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần backup profile folder vì đây là nơi lưu session/cookie/localStorage/cache của từng browser profile.

Task:
TASK 3.2 — Backup Profile Folder.

Yêu cầu:
1. Xác định DATA_PATH/profile folder hiện tại.
2. Tạo chức năng backup profile folder.
3. Nếu có profile đang running, cảnh báo hoặc yêu cầu stop trước khi backup.
4. Nén backup thành file có timestamp.
5. Lưu metadata: created_at, size, type, status.
6. Ghi BACKUP_FAILED nếu lỗi.
7. Không làm restore ở task này.

Output cần trả:
- File đã sửa.
- Luồng backup.
- Cách xử lý profile đang running.
- Test case.
- Rủi ro dữ liệu.
```

---

# TASK 3.3 — Restore Test

## Mục tiêu

Khôi phục database/profile folder từ backup và kiểm tra profile launch được.

## Yêu cầu

- Có quy trình restore an toàn.
- Stop tất cả profile trước khi restore.
- Backup trạng thái hiện tại trước khi restore.
- Restore DB.
- Restore profile folder.
- Chạy integrity check.
- Launch test 1 profile.

## Prompt copy cho AI/dev

```text
Bạn là senior backend/devops engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ đã có backup database và profile folder. Cần xây dựng restore process an toàn.

Task:
TASK 3.3 — Restore Test.

Yêu cầu:
1. Thiết kế quy trình restore an toàn.
2. Stop all profiles trước khi restore.
3. Tạo safety backup trước khi restore.
4. Restore database.
5. Restore profile folder.
6. Chạy integrity check.
7. Launch test một profile sau restore.
8. Ghi activity log RESTORE_COMPLETED.
9. Ghi error log RESTORE_FAILED nếu lỗi.

Output cần trả:
- File đã sửa nếu có.
- Restore flow.
- API/command restore.
- Test case.
- Cảnh báo rủi ro.
```

---

# TASK 3.4 — Resource Limit / Max Running Profiles

## Mục tiêu

Giới hạn số profile chạy cùng lúc để tránh full RAM/CPU.

## Yêu cầu

- Config MAX_RUNNING_PROFILES.
- Trước khi launch, kiểm tra số profile đang running.
- Nếu vượt giới hạn, không cho launch.
- Log RESOURCE_LIMIT_REACHED.
- Hiển thị thông báo rõ trên UI.

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer có kinh nghiệm resource control.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Mỗi browser profile tốn RAM/CPU. Tool nội bộ cần giới hạn số profile chạy đồng thời để tránh treo server.

Task:
TASK 3.4 — Resource Limit / Max Running Profiles.

Yêu cầu:
1. Thêm config MAX_RUNNING_PROFILES.
2. Trước khi launch profile, đếm số profile running/starting.
3. Nếu vượt giới hạn, không launch.
4. Trả message rõ cho frontend.
5. Ghi error/activity log RESOURCE_LIMIT_REACHED.
6. Hiển thị trên dashboard số profile running / max allowed.

Output cần trả:
- File đã sửa.
- Config mới.
- Logic kiểm tra trước launch.
- UI thay đổi nếu có.
- Test case.
```

---

# TASK 3.5 — Stop All Profiles

## Mục tiêu

Có nút dừng toàn bộ profile đang chạy để xử lý khẩn cấp.

## Yêu cầu

- API stop all.
- UI button có confirm.
- Stop từng profile an toàn.
- Ghi log từng profile stop thành công/lỗi.
- Trả summary kết quả.

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
Tool nội bộ cần nút Stop All Profiles để dừng toàn bộ browser khi máy quá tải hoặc cần backup/restore.

Task:
TASK 3.5 — Stop All Profiles.

Yêu cầu:
1. Tạo API stop all profiles.
2. Chỉ stop profile đang running/starting nếu phù hợp.
3. Stop từng profile theo logic stop hiện có.
4. Ghi log cho từng profile.
5. Trả summary: total, stopped, failed.
6. Frontend có nút Stop All Profiles trên Dashboard.
7. UI phải có confirm trước khi chạy.

Output cần trả:
- File đã sửa.
- API.
- UI.
- Response mẫu.
- Test case.
```

---

# TASK 3.6 — Crash Watcher

## Mục tiêu

Phát hiện browser process crash và cập nhật status profile.

## Yêu cầu

- Theo dõi process browser đang chạy.
- Nếu process chết bất thường, set status = crashed.
- Ghi error log BROWSER_CRASHED.
- Dashboard hiển thị profile crashed.
- Không auto restart mặc định nếu chưa có yêu cầu.

## Prompt copy cho AI/dev

```text
Bạn là senior backend engineer có kinh nghiệm process monitoring.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ cần biết khi browser profile crash, thay vì UI vẫn hiển thị running sai.

Task:
TASK 3.6 — Crash Watcher.

Yêu cầu:
1. Xác định nơi lưu pid/process của browser profile.
2. Tạo watcher kiểm tra process còn sống.
3. Nếu process chết bất thường, cập nhật status = crashed.
4. Ghi error log BROWSER_CRASHED.
5. Dashboard/list profile phải hiển thị crashed.
6. Không auto restart ở task này.

Output cần trả:
- File đã sửa.
- Watcher flow.
- Chu kỳ check đề xuất.
- Test case bằng cách kill process.
- Rủi ro/performance.
```

---

# TASK 3.7 — UI Tiếng Việt Và Tối Ưu Workflow Nội Bộ

## Mục tiêu

Việt hóa UI và làm workflow dễ dùng cho team nội bộ.

## Yêu cầu

- Việt hóa menu chính.
- Việt hóa nút/action chính.
- Việt hóa error message quan trọng.
- Không đổi tên biến/code internal nếu không cần.
- Giữ layout gọn.
- Ưu tiên rõ ràng hơn đẹp.

## Gợi ý menu

| English | Vietnamese |
|---|---|
| Dashboard | Tổng quan |
| Profiles | Hồ sơ trình duyệt |
| Proxies | Proxy |
| Logs | Nhật ký |
| Backups | Sao lưu |
| Settings | Cài đặt |

## Prompt copy cho AI/dev

```text
Bạn là senior frontend engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ đã có chức năng chính. Bây giờ cần Việt hóa UI để team dễ dùng. Không cần thiết kế lại toàn bộ.

Task:
TASK 3.7 — UI tiếng Việt và tối ưu workflow nội bộ.

Yêu cầu:
1. Việt hóa menu, button, title, empty state, error message chính.
2. Không đổi tên biến/API nếu không cần.
3. Không refactor frontend lớn.
4. Giữ layout hiện tại nếu vẫn dùng được.
5. Ưu tiên rõ ràng, dễ thao tác.
6. Các thuật ngữ kỹ thuật có thể giữ tiếng Anh nếu dịch gây khó hiểu, ví dụ CDP, proxy, profile.

Output cần trả:
- File đã sửa.
- Danh sách text đã Việt hóa.
- Screenshot/mô tả UI nếu có.
- Test case UI.
```

---

# TASK 3.8 — Tài Liệu Vận Hành Nội Bộ

## Mục tiêu

Tạo tài liệu cho người vận hành biết cách chạy, backup, restore, debug lỗi.

## Tài liệu cần có

- Cách start/stop app.
- Cách xem logs.
- Cách tạo profile.
- Cách gắn proxy.
- Cách check proxy.
- Cách backup.
- Cách restore.
- Cách xử lý lỗi phổ biến.
- Cách update app.

## Prompt copy cho AI/dev

```text
Bạn là technical writer kiêm senior engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ đã có các chức năng chính. Cần tài liệu vận hành ngắn gọn để team dùng và debug.

Task:
TASK 3.8 — Tài liệu vận hành nội bộ.

Yêu cầu:
Tạo file RUNBOOK.md gồm:
1. Cách start app.
2. Cách stop app.
3. Cách restart app.
4. Cách xem container logs.
5. Cách tạo profile.
6. Cách gắn proxy.
7. Cách check proxy.
8. Cách launch/stop profile.
9. Cách backup database/profile folder.
10. Cách restore.
11. Bảng lỗi phổ biến và cách xử lý.
12. Checklist trước khi update app.

Format:
- Ngắn gọn.
- Có command từng dòng riêng.
- Có checklist.
- Không viết dài dòng.

Output cần trả:
- File RUNBOOK.md hoàn chỉnh.
```

---

# TASK 3.9 — Đánh Giá Có Cần Chuyển SQLite Sang PostgreSQL Không

## Mục tiêu

Quyết định khi nào nên chuyển DB từ SQLite sang PostgreSQL.

## Tiêu chí đánh giá

| Dấu hiệu | Hành động |
|---|---|
| Ít profile, ít user | Giữ SQLite |
| Nhiều log, hay bị DB locked | Cân nhắc PostgreSQL |
| Nhiều user nội bộ | PostgreSQL |
| Cần query logs/dashboard nhiều | PostgreSQL |
| Chạy 24/7 ổn định | PostgreSQL tốt hơn |

## Prompt copy cho AI/dev

```text
Bạn là senior backend/database engineer.

Bối cảnh bắt buộc:
- Dự án này phát triển tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile nên kiểm tra nếu cần UI/backend: https://github.com/CloakHQ/CloakBrowser-Manager
- Không code app từ đầu nếu CloakBrowser Manager đã có chức năng tương ứng.
- Luôn đọc code/cấu trúc repo hiện tại trước khi sửa.
- Chỉ làm đúng task được giao, không tự ý mở rộng scope.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.


Bối cảnh:
Tool nội bộ hiện có thể đang dùng SQLite. Cần đánh giá có nên chuyển sang PostgreSQL không.

Task:
TASK 3.9 — Đánh giá chuyển SQLite sang PostgreSQL.

Yêu cầu:
1. Kiểm tra schema hiện tại.
2. Kiểm tra lượng profile/log/user dự kiến.
3. Nêu rủi ro SQLite: DB lock, backup, concurrent writes.
4. Đề xuất giữ SQLite hay chuyển PostgreSQL.
5. Nếu chuyển, đề xuất migration plan từng bước.
6. Không thực hiện migration trong task này trừ khi được yêu cầu.

Output cần trả:
- Đánh giá hiện trạng.
- Khi nào giữ SQLite.
- Khi nào chuyển PostgreSQL.
- Migration plan nếu cần.
- Rủi ro.
```
