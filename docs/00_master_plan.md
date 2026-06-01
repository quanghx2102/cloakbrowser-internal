# MASTER PLAN — Tool Browser Profile Nội Bộ Dựa Trên CloakBrowser

## Source repo bắt buộc

Repo chính cần bám theo:

- CloakBrowser engine: https://github.com/CloakHQ/CloakBrowser
- CloakBrowser Manager nếu cần phần app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager

Nguyên tắc:

- Luôn đọc cấu trúc repo hiện tại trước khi đề xuất sửa.
- Không tự thiết kế app từ đầu nếu repo gốc đã có chức năng tương ứng.
- Không tự đổi stack công nghệ nếu chưa có lý do kỹ thuật rõ ràng.
- Ưu tiên fork/chỉnh trên CloakBrowser Manager.
- CloakBrowser là native window, CloakBrowser Manager là app quản lý profile/UI/backend.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.

## 1. Mục tiêu dự án

Xây dựng một tool nội bộ dựa trên CloakBrowser Manager để quản lý nhiều browser profile riêng biệt.

Dự án phục vụ nội bộ, không thương mại hóa, không bán SaaS, không đóng gói lại cho khách hàng bên thứ ba.

## 2. Định hướng kỹ thuật

Không code app từ đầu ngay.

Hướng đi đề xuất:

```text
Dùng CloakBrowser Manager gốc
→ Chạy thử lõi
→ Fork repo
→ Thêm logging, proxy checker, dashboard, backup
→ Tối ưu UI nội bộ nếu cần
```

## 3. Stack công nghệ đề xuất

| Layer              | Công nghệ                   |
| ------------------ | --------------------------- |
| Browser Engine     | CloakBrowser                |
| App base           | CloakBrowser Manager        |
| Backend            | FastAPI                     |
| Frontend           | React + Tailwind            |
| Database ban đầu   | SQLite                      |
| Database lâu dài   | PostgreSQL                  |
| Deploy             | Docker Compose              |
| Viewer             | noVNC                       |
| Automation         | CDP / Playwright            |
| Logging            | JSON structured logs        |
| Monitoring sau này | Grafana / Loki / Prometheus |

## 4. Phân chia Phase

| Phase   | Mục tiêu                                    |
| ------- | ------------------------------------------- |
| Phase 1 | Chạy được lõi CloakBrowser Manager          |
| Phase 2 | Làm thành tool nội bộ dùng được hằng ngày   |
| Phase 3 | Làm tool ổn định, backup được, dùng lâu dài |

## 5. Nguyên tắc làm việc với AI/dev

Không giao toàn bộ tài liệu dài một lần.

Mỗi lần chỉ giao 1 task theo format:

```text
Bối cảnh dự án:
Mục tiêu task:
File cần kiểm tra/sửa:
Yêu cầu backend:
Yêu cầu frontend:
Logging cần có:
Test case:
Điều kiện hoàn thành:
Không làm ngoài phạm vi:
```

## 6. Quy tắc quan trọng

- Không sửa nhiều module trong một task nếu không cần.
- Luôn yêu cầu AI/dev đọc code hiện tại trước khi sửa.
- Luôn yêu cầu trả về danh sách file đã sửa.
- Luôn yêu cầu test case sau khi sửa.
- Mỗi task phải có log lỗi nếu liên quan đến backend/browser/proxy/storage.
- Ưu tiên ổn định hơn UI đẹp.
- Không expose app ra internet nếu chưa có HTTPS/auth/firewall.

## 7. Mental model

```text
CloakBrowser = browser engine
CloakBrowser Manager = app base
Tool nội bộ = fork Manager + log + test + proxy checker + dashboard + backup
```

Thứ tự đúng:

```text
Chạy được → Đo lỗi được → Debug được → Backup được → Dùng lâu dài được
```
