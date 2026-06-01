# TÀI LIỆU PHÁT TRIỂN TOOL BROWSER PROFILE NỘI BỘ DỰA TRÊN CLOAKBROWSER

## 1. Mục tiêu dự án

Xây dựng một tool nội bộ để quản lý nhiều browser profile độc lập dựa trên CloakBrowser và CloakBrowser Manager.

Tool này dùng cho mục đích nội bộ như:

- Quản lý nhiều môi trường trình duyệt riêng biệt.
- Gắn proxy riêng cho từng profile.
- Lưu session/cookie/localStorage/cache theo từng profile.
- Mở/tắt/restart profile từ giao diện web.
- Theo dõi trạng thái profile, proxy, browser process.
- Ghi log lỗi rõ ràng để debug.
- Hỗ trợ automation nội bộ qua CDP/Playwright khi cần.
- Backup/restore dữ liệu profile.

## 2. Nguyên tắc phạm vi

### 2.1. Làm trong phạm vi

Dự án chỉ phục vụ nội bộ, không bán SaaS, không đóng gói thương mại, không cung cấp cho khách hàng bên thứ ba.

Các chức năng trong phạm vi:

- Fork và tùy chỉnh CloakBrowser Manager.
- Chạy self-hosted bằng Docker.
- Thêm UI tiếng Việt nếu cần.
- Thêm logging, test, backup, dashboard.
- Thêm proxy checker, health check, activity log.
- Thêm giới hạn tài nguyên để tránh quá tải máy chủ.
- Có thể nâng SQLite lên PostgreSQL nếu số lượng profile/log lớn.

### 2.2. Không làm trong phạm vi

Không xây dựng tính năng phục vụ cho việc lạm dụng nền tảng, spam, gian lận, vượt kiểm duyệt, đánh cắp tài khoản, hoặc né hệ thống bảo mật của bên thứ ba.

Không bán lại binary/app như một sản phẩm thương mại nếu chưa xử lý đầy đủ vấn đề giấy phép.

Không expose app trực tiếp ra internet khi chưa có HTTPS, auth, firewall và backup.

## 3. Đánh giá nền tảng CloakBrowser

### 3.1. CloakBrowser là gì?

CloakBrowser là phần lõi browser engine dựa trên Chromium, có tùy chỉnh ở tầng browser để tạo môi trường trình duyệt riêng biệt và phù hợp cho browser automation/profile isolation.

### 3.2. CloakBrowser Manager là gì?

CloakBrowser Manager là web app quản lý profile cho CloakBrowser. Đây là phần nên dùng làm nền cho dự án nội bộ.

Các thành phần chính:

- Web UI quản lý profile.
- Backend API.
- Browser launcher.
- Proxy config theo profile.
- Session/profile data riêng theo profile.
- noVNC để thao tác browser qua giao diện web.
- CDP endpoint để kết nối automation.
- Docker để triển khai nhanh.

### 3.3. Kết luận lựa chọn

Không nên code app từ đầu ngay.

Lộ trình hợp lý:

1. Chạy app gốc CloakBrowser Manager để test.
2. Fork repo.
3. Thêm log/test/dashboard/proxy checker/backup.
4. Chỉ code UI riêng nếu UI gốc quá khó sửa hoặc workflow nội bộ quá khác.

## 4. Kiến trúc tổng thể

```text
Người dùng nội bộ
   ↓
Web UI React
   ↓
Backend FastAPI
   ↓
Profile Service ───── Database
   ↓
Browser Launcher
   ↓
CloakBrowser Instance
   ↓
noVNC Viewer / CDP Automation
   ↓
Logs / Health Check / Backup
```

## 5. Công nghệ đề xuất

| Layer | Giai đoạn đầu | Giai đoạn ổn định | Lý do |
|---|---|---|---|
| Browser engine | CloakBrowser | CloakBrowser | Không build browser engine từ đầu |
| App base | CloakBrowser Manager | Fork CloakBrowser Manager | Có sẵn profile/proxy/session/noVNC/CDP |
| Backend | FastAPI | FastAPI | Giữ theo repo gốc, dễ mở rộng |
| Frontend | React + Tailwind | React + TypeScript + Tailwind | Dễ chỉnh UI nội bộ |
| Database | SQLite | PostgreSQL | SQLite đủ MVP, PostgreSQL tốt hơn khi nhiều log/profile |
| Deploy | Docker Compose | Docker Compose | Dễ chạy nội bộ |
| Viewer | noVNC | noVNC | Có sẵn trong manager |
| Automation | CDP/Playwright | CDP/Playwright | Kết nối browser đang chạy |
| Logging | Python logging JSON | Loki/ELK/Sentry tùy nhu cầu | Debug lỗi production |
| Monitoring | Basic dashboard | Prometheus/Grafana | Theo dõi RAM/CPU/crash |
| Reverse proxy | Caddy/Nginx | Caddy/Nginx + HTTPS | An toàn khi truy cập từ xa |

## 6. Roadmap 3 giai đoạn

# Giai đoạn 1 — Chạy được MVP nội bộ

## 6.1. Mục tiêu

Chạy được CloakBrowser Manager, tạo profile, launch browser, gắn proxy, lưu session, thao tác qua noVNC.

## 6.2. Việc cần làm

1. Clone hoặc fork repo CloakBrowser Manager.
2. Chạy bằng Docker Compose.
3. Cấu hình thư mục data persistent.
4. Tạo profile thử nghiệm.
5. Gắn proxy thử nghiệm.
6. Launch profile.
7. Kiểm tra session sau restart.
8. Kiểm tra noVNC.
9. Kiểm tra CDP connection.
10. Ghi lại lỗi phát sinh.

## 6.3. Checklist test giai đoạn 1

| Chức năng | Test case | Kết quả mong muốn |
|---|---|---|
| Profile create | Tạo profile mới | Profile xuất hiện trong danh sách |
| Profile update | Sửa tên/proxy/fingerprint config | Dữ liệu cập nhật đúng |
| Profile delete | Xóa profile | Profile bị xóa khỏi UI và DB |
| Browser launch | Bấm Launch | Browser mở được |
| Browser stop | Bấm Stop | Browser process tắt sạch |
| Restart session | Tắt/mở lại profile | Cookie/session còn nếu profile persistent |
| Proxy valid | Gắn proxy đúng | Browser đi qua proxy |
| Proxy invalid | Gắn proxy sai | App báo lỗi rõ |
| noVNC | Mở viewer | Thao tác browser được |
| CDP | Connect bằng script test | Kết nối thành công |

## 6.4. Output giai đoạn 1

Một bản chạy nội bộ ổn định ở mức MVP:

```text
Docker → Web UI → Profile → Launch → noVNC/CDP → Session persistent
```

# Giai đoạn 2 — Thêm log, test, dashboard

## 6.5. Mục tiêu

Khi lỗi xảy ra, biết lỗi nằm ở profile, proxy, browser, noVNC, CDP, database hay storage.

## 6.6. Module cần bổ sung

| Module | Mục đích |
|---|---|
| Error Logger | Ghi lỗi có cấu trúc |
| Activity Log | Lưu lịch sử thao tác user |
| Profile Status | running/stopped/failed/crashed |
| Proxy Checker | Check proxy sống/chết, auth, latency |
| Browser Health Check | Kiểm tra process browser còn sống |
| CDP Health Check | Kiểm tra automation endpoint |
| VNC Health Check | Kiểm tra viewer |
| Storage Checker | Kiểm tra dung lượng ổ cứng |
| Backup Service | Backup DB và profile folder |
| Test Runner | Chạy test từng chức năng |

## 6.7. Trạng thái profile đề xuất

```text
created
starting
running
stopping
stopped
failed
crashed
proxy_error
storage_error
```

## 6.8. Error code đề xuất

| Error code | Ý nghĩa |
|---|---|
| PROFILE_CREATE_FAILED | Tạo profile lỗi |
| PROFILE_UPDATE_FAILED | Sửa profile lỗi |
| PROFILE_DELETE_FAILED | Xóa profile lỗi |
| PROFILE_DATA_MISSING | Mất folder dữ liệu profile |
| PROFILE_LOCKED | Profile đang chạy nên không cho sửa/xóa |
| PROXY_AUTH_FAILED | Sai user/pass proxy |
| PROXY_TIMEOUT | Proxy timeout |
| PROXY_CONNECTION_FAILED | Không kết nối được proxy |
| BROWSER_START_FAILED | Browser không mở |
| BROWSER_CRASHED | Browser crash khi đang chạy |
| BROWSER_STOP_FAILED | Không stop được browser |
| CDP_CONNECT_FAILED | Không kết nối được CDP |
| VNC_CONNECT_FAILED | Không mở được viewer |
| DB_WRITE_FAILED | Lỗi ghi database |
| DB_READ_FAILED | Lỗi đọc database |
| STORAGE_FULL | Hết dung lượng ổ cứng |
| BACKUP_FAILED | Backup lỗi |
| RESTORE_FAILED | Restore lỗi |

## 6.9. Mẫu log chuẩn

```json
{
  "timestamp": "2026-05-30T20:00:00+07:00",
  "level": "error",
  "module": "browser_launcher",
  "profile_id": "profile_001",
  "user_id": "internal_admin",
  "action": "launch_profile",
  "status": "failed",
  "error_code": "BROWSER_START_FAILED",
  "message": "Browser process exited before CDP was ready",
  "duration_ms": 4280,
  "metadata": {
    "proxy_id": "proxy_001",
    "browser_version": "cloakbrowser_current",
    "host": "internal-server-01"
  }
}
```

## 6.10. Dashboard cần có

| Widget | Nội dung |
|---|---|
| Tổng profile | Tổng số profile trong DB |
| Profile đang chạy | Số profile running |
| Profile lỗi | Số profile failed/crashed |
| Proxy lỗi | Số proxy timeout/auth failed |
| RAM/CPU | Tài nguyên máy chủ |
| Disk usage | Dung lượng thư mục profile |
| Browser crash rate | Tỷ lệ crash |
| Launch success rate | Tỷ lệ mở browser thành công |
| Log gần nhất | 20 lỗi gần nhất |

# Giai đoạn 3 — Bản nội bộ dùng lâu dài

## 6.11. Mục tiêu

Tool ổn định, dễ bảo trì, có backup, không mất dữ liệu, có khả năng mở rộng cho team nội bộ.

## 6.12. Nâng cấp đề xuất

| Hạng mục | Khi nào cần | Đề xuất |
|---|---|---|
| PostgreSQL | Nhiều profile/log/user | Chuyển từ SQLite sang PostgreSQL |
| User role | Nhiều người dùng | Admin/Operator/Viewer |
| Queue | Nhiều task chạy nền | Celery/RQ/Redis |
| Monitoring | Chạy 24/7 | Prometheus/Grafana hoặc dashboard riêng |
| Log storage | Nhiều log | Loki/ELK hoặc PostgreSQL partition |
| Backup tự động | Dùng lâu dài | Backup hằng ngày |
| Reverse proxy | Truy cập từ xa | Caddy/Nginx + HTTPS |
| Resource limit | Nhiều browser chạy song song | Giới hạn max running profiles |

## 7. Module chi tiết

# 7.1. Profile Management

## Chức năng

- Tạo profile.
- Sửa profile.
- Xóa profile.
- Clone profile.
- Tìm kiếm profile.
- Gắn tag/folder.
- Gắn proxy.
- Xem trạng thái running/stopped/failed.

## Field đề xuất

| Field | Kiểu dữ liệu | Ghi chú |
|---|---|---|
| id | string/uuid | ID profile |
| name | string | Tên profile |
| group_id | string/null | Nhóm profile |
| proxy_id | string/null | Proxy gắn với profile |
| fingerprint_seed | string | Seed fingerprint |
| timezone | string | Timezone profile |
| locale | string | Locale profile |
| platform | string | Windows/macOS/Linux |
| screen_width | int | Width |
| screen_height | int | Height |
| status | string | running/stopped/failed |
| data_path | string | Folder profile |
| created_at | datetime | Ngày tạo |
| updated_at | datetime | Ngày sửa |
| last_launched_at | datetime/null | Lần mở gần nhất |

# 7.2. Browser Launcher

## Chức năng

- Launch browser theo profile.
- Stop browser.
- Restart browser.
- Kiểm tra process còn sống.
- Ghi log launch duration.
- Ghi log crash.

## Luồng launch

```text
User bấm Launch
   ↓
Backend kiểm tra profile tồn tại
   ↓
Kiểm tra profile chưa running
   ↓
Kiểm tra proxy nếu có
   ↓
Kiểm tra storage path
   ↓
Start CloakBrowser process
   ↓
Wait CDP ready
   ↓
Wait noVNC ready
   ↓
Update status = running
   ↓
Trả về viewer URL/CDP endpoint
```

## Luồng stop

```text
User bấm Stop
   ↓
Backend tìm browser process
   ↓
Gửi stop signal
   ↓
Wait graceful shutdown
   ↓
Nếu timeout thì force kill
   ↓
Update status = stopped
   ↓
Ghi log
```

# 7.3. Proxy Manager

## Chức năng

- Thêm proxy.
- Sửa proxy.
- Xóa proxy.
- Gắn proxy vào profile.
- Check proxy.
- Hiển thị IP/country/latency/status.

## Field đề xuất

| Field | Kiểu dữ liệu | Ghi chú |
|---|---|---|
| id | uuid | ID proxy |
| name | string | Tên proxy |
| type | enum | http/https/socks5 |
| host | string | Host/IP |
| port | int | Port |
| username | string/null | Username |
| password | encrypted string/null | Password mã hóa |
| country | string/null | Quốc gia detect được |
| last_ip | string/null | IP detect được |
| latency_ms | int/null | Độ trễ |
| status | string | active/failed/timeout/auth_failed |
| last_checked_at | datetime/null | Lần check gần nhất |

## Test proxy

```text
Input proxy
   ↓
Check connection
   ↓
Check auth
   ↓
Get exit IP
   ↓
Measure latency
   ↓
Save status
```

# 7.4. noVNC Viewer

## Chức năng

- Mở browser trong giao diện web.
- Hiển thị trạng thái kết nối.
- Báo lỗi khi viewer không kết nối được.

## Lỗi thường gặp

| Lỗi | Nguyên nhân |
|---|---|
| VNC_CONNECT_FAILED | noVNC service chưa sẵn sàng |
| BROWSER_NOT_RUNNING | Profile chưa launch |
| VIEWER_TIMEOUT | Browser process treo |

# 7.5. CDP Automation

## Chức năng

- Cung cấp CDP endpoint cho profile đang chạy.
- Cho phép script nội bộ kết nối bằng Playwright/Puppeteer.
- Log lỗi connect.

## Nguyên tắc

- Chỉ automation trong phạm vi được phép.
- Không hard-code credential nhạy cảm trong script.
- Log script run để biết profile nào được điều khiển.

# 7.6. Backup/Restore

## Dữ liệu cần backup

- Database.
- Profile data folder.
- Proxy config.
- App config.
- Log quan trọng.

## Lịch backup đề xuất

| Loại backup | Tần suất | Lưu giữ |
|---|---|---|
| DB backup | Hằng ngày | 14 ngày |
| Profile folder backup | Hằng ngày hoặc 2 ngày/lần | 7 bản gần nhất |
| Full backup | Hằng tuần | 4 tuần |

## Quy tắc restore

1. Stop toàn bộ running profiles.
2. Backup trạng thái hiện tại trước khi restore.
3. Restore DB.
4. Restore profile folder.
5. Chạy integrity check.
6. Launch test 1 profile.
7. Ghi log restore.

## 8. Database schema đề xuất

# 8.1. Bảng users

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'admin',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

# 8.2. Bảng profiles

```sql
CREATE TABLE profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  group_id TEXT,
  proxy_id TEXT,
  fingerprint_seed TEXT,
  timezone TEXT,
  locale TEXT,
  platform TEXT,
  screen_width INTEGER,
  screen_height INTEGER,
  status TEXT NOT NULL DEFAULT 'stopped',
  data_path TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  last_launched_at TIMESTAMP
);
```

# 8.3. Bảng proxies

```sql
CREATE TABLE proxies (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  host TEXT NOT NULL,
  port INTEGER NOT NULL,
  username TEXT,
  password_encrypted TEXT,
  country TEXT,
  last_ip TEXT,
  latency_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'unknown',
  last_checked_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

# 8.4. Bảng activity_logs

```sql
CREATE TABLE activity_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  profile_id TEXT,
  module TEXT NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT,
  metadata_json TEXT,
  created_at TIMESTAMP NOT NULL
);
```

# 8.5. Bảng error_logs

```sql
CREATE TABLE error_logs (
  id TEXT PRIMARY KEY,
  level TEXT NOT NULL,
  module TEXT NOT NULL,
  profile_id TEXT,
  proxy_id TEXT,
  action TEXT,
  error_code TEXT NOT NULL,
  message TEXT NOT NULL,
  stack_trace TEXT,
  metadata_json TEXT,
  created_at TIMESTAMP NOT NULL
);
```

# 8.6. Bảng browser_processes

```sql
CREATE TABLE browser_processes (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  pid INTEGER,
  cdp_endpoint TEXT,
  vnc_url TEXT,
  status TEXT NOT NULL,
  started_at TIMESTAMP,
  stopped_at TIMESTAMP,
  crash_reason TEXT
);
```

## 9. API nội bộ đề xuất

# 9.1. Profile API

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | /api/profiles | Danh sách profile |
| POST | /api/profiles | Tạo profile |
| GET | /api/profiles/{id} | Chi tiết profile |
| PUT | /api/profiles/{id} | Sửa profile |
| DELETE | /api/profiles/{id} | Xóa profile |
| POST | /api/profiles/{id}/launch | Launch profile |
| POST | /api/profiles/{id}/stop | Stop profile |
| POST | /api/profiles/{id}/restart | Restart profile |
| POST | /api/profiles/{id}/clone | Clone profile |
| GET | /api/profiles/{id}/logs | Log theo profile |

# 9.2. Proxy API

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | /api/proxies | Danh sách proxy |
| POST | /api/proxies | Thêm proxy |
| PUT | /api/proxies/{id} | Sửa proxy |
| DELETE | /api/proxies/{id} | Xóa proxy |
| POST | /api/proxies/{id}/check | Check proxy |
| POST | /api/proxies/bulk-check | Check nhiều proxy |

# 9.3. Dashboard API

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | /api/dashboard/summary | Tổng quan hệ thống |
| GET | /api/dashboard/resources | CPU/RAM/Disk |
| GET | /api/dashboard/errors | Lỗi gần nhất |
| GET | /api/dashboard/profile-status | Trạng thái profile |

# 9.4. Logs API

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | /api/logs/activity | Activity logs |
| GET | /api/logs/errors | Error logs |
| GET | /api/logs/errors/{id} | Chi tiết lỗi |

# 9.5. Backup API

| Method | Endpoint | Chức năng |
|---|---|---|
| POST | /api/backups | Tạo backup |
| GET | /api/backups | Danh sách backup |
| POST | /api/backups/{id}/restore | Restore backup |

## 10. UI cần có

# 10.1. Sidebar

- Dashboard
- Profiles
- Proxies
- Browser Sessions
- Logs
- Backups
- Settings

# 10.2. Dashboard

Thông tin cần hiển thị:

- Tổng số profile.
- Profile đang chạy.
- Profile lỗi.
- Proxy lỗi.
- RAM/CPU/Disk.
- Lỗi gần nhất.
- Nút “Stop all profiles”.

# 10.3. Trang Profiles

Cột đề xuất:

- Tên profile.
- Group/tag.
- Proxy.
- Trạng thái.
- Lần mở gần nhất.
- Nút Launch.
- Nút Stop.
- Nút View.
- Nút Edit.
- Nút Logs.

# 10.4. Trang Proxy

Cột đề xuất:

- Tên proxy.
- Type.
- Host.
- Country.
- IP.
- Latency.
- Status.
- Last checked.
- Check button.

# 10.5. Trang Logs

Filter cần có:

- Theo profile.
- Theo proxy.
- Theo module.
- Theo error code.
- Theo level.
- Theo thời gian.

# 10.6. Trang Settings

Các setting đề xuất:

- Max running profiles.
- Default profile path.
- Log level.
- Backup path.
- Backup schedule.
- Auth token/user config.
- Reverse proxy base URL.

## 11. Test plan chi tiết

# 11.1. Unit test

| Module | Test |
|---|---|
| Profile service | create/update/delete/clone |
| Proxy service | parse/check/save status |
| Launcher service | build command/start/stop |
| Logger service | log format/error code |
| Backup service | create/restore/integrity check |

# 11.2. Integration test

| Flow | Test |
|---|---|
| Create → Launch → Stop | Profile chạy được và dừng được |
| Proxy valid | Browser dùng đúng proxy |
| Proxy invalid | App báo proxy error |
| Restart profile | Session còn sau restart |
| CDP connect | Playwright connect được |
| noVNC view | Mở viewer được |
| Backup restore | Restore xong profile vẫn launch được |

# 11.3. Failure test

| Trường hợp lỗi | Kết quả mong muốn |
|---|---|
| Proxy chết | status = proxy_error, log PROXY_TIMEOUT |
| Sai proxy password | log PROXY_AUTH_FAILED |
| Browser crash | status = crashed, log BROWSER_CRASHED |
| Hết disk | log STORAGE_FULL, không launch thêm |
| DB lỗi | log DB_WRITE_FAILED |
| noVNC lỗi | log VNC_CONNECT_FAILED |
| CDP lỗi | log CDP_CONNECT_FAILED |

# 11.4. Performance test

| Test | Mục tiêu |
|---|---|
| Launch 1 profile | Ghi launch time baseline |
| Launch 5 profile | Kiểm tra RAM/CPU |
| Launch 10 profile | Xác định giới hạn máy |
| Stop all | Dừng sạch toàn bộ process |
| Long run 8 giờ | Kiểm tra memory leak/crash |

## 12. Deployment nội bộ

# 12.1. Kiến trúc deploy đơn giản

```text
Internal User
   ↓
Caddy/Nginx HTTPS
   ↓
Docker Compose
   ├── cloakbrowser-manager
   ├── database
   ├── logs
   └── backups
```

# 12.2. Biến môi trường đề xuất

```env
APP_ENV=internal
APP_HOST=0.0.0.0
APP_PORT=8080
AUTH_ENABLED=true
AUTH_TOKEN=change_me
DATA_PATH=/data
LOG_LEVEL=INFO
MAX_RUNNING_PROFILES=5
BACKUP_PATH=/backups
BACKUP_RETENTION_DAYS=14
DATABASE_URL=sqlite:////data/app.db
```

Nếu chuyển sang PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@postgres:5432/cloak_internal
```

# 12.3. Docker Compose mẫu định hướng

```yaml
services:
  app:
    image: cloakhq/cloakbrowser-manager:latest
    container_name: cloakbrowser-manager
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
      - ./logs:/logs
      - ./backups:/backups
    environment:
      - AUTH_ENABLED=true
      - AUTH_TOKEN=change_me
      - DATA_PATH=/data
      - LOG_LEVEL=INFO
      - MAX_RUNNING_PROFILES=5
    restart: unless-stopped
```

Sau khi fork và tùy chỉnh, nên build image riêng:

```yaml
services:
  app:
    build: .
    container_name: internal-browser-tool
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
      - ./logs:/logs
      - ./backups:/backups
    env_file:
      - .env
    restart: unless-stopped
```

## 13. Bảo mật nội bộ

Checklist bảo mật tối thiểu:

- Không public app trực tiếp ra internet.
- Nếu truy cập từ xa, bắt buộc dùng HTTPS.
- Dùng VPN hoặc whitelist IP.
- Đổi token/password mặc định.
- Không lưu proxy password dạng plain text nếu có thể.
- Backup dữ liệu định kỳ.
- Không commit `.env` lên Git.
- Không hard-code credential trong source code.
- Log không được in password/token đầy đủ.
- Có nút stop toàn bộ browser khi cần khẩn cấp.

## 14. Quy trình phát triển

# 14.1. Branch strategy

```text
main        = bản ổn định đang chạy nội bộ
staging     = bản test trước khi deploy
feature/*   = tính năng mới
fix/*       = sửa lỗi
```

# 14.2. Quy trình làm tính năng

```text
Tạo issue
   ↓
Tạo branch feature
   ↓
Code
   ↓
Unit test
   ↓
Integration test
   ↓
Review thủ công
   ↓
Merge staging
   ↓
Test trên staging
   ↓
Merge main
   ↓
Deploy nội bộ
```

# 14.3. Quy trình xử lý lỗi

```text
User gặp lỗi
   ↓
Xem error_logs
   ↓
Xem activity_logs theo profile_id
   ↓
Xác định module lỗi
   ↓
Reproduce lỗi trên staging
   ↓
Fix
   ↓
Test case mới
   ↓
Deploy
```

## 15. Thứ tự ưu tiên phát triển

# Sprint 1 — Chạy gốc và test lõi

- Run Docker.
- Test create/edit/delete profile.
- Test launch/stop/restart.
- Test proxy.
- Test session persistence.
- Test noVNC.
- Test CDP.

# Sprint 2 — Logging cơ bản

- Thêm structured logs.
- Thêm error code.
- Lưu activity log.
- Lưu browser launch/stop log.
- Trang Logs cơ bản.

# Sprint 3 — Proxy checker + profile status

- Check proxy đơn lẻ.
- Check nhiều proxy.
- Lưu latency/IP/country/status.
- Hiển thị trạng thái profile rõ ràng.

# Sprint 4 — Dashboard + resource guard

- Dashboard tổng quan.
- CPU/RAM/Disk.
- Max running profiles.
- Stop all profiles.
- Crash watcher.

# Sprint 5 — Backup/restore

- Backup DB.
- Backup profile folder.
- Restore test.
- Lịch backup tự động.

# Sprint 6 — Tối ưu UI nội bộ

- Việt hóa giao diện.
- Group/tag profile.
- Search/filter.
- Profile detail page.
- Error detail page.

## 16. Tiêu chí hoàn thành dự án

Dự án được xem là hoàn thành bản nội bộ khi đạt các tiêu chí sau:

| Nhóm | Tiêu chí |
|---|---|
| Profile | Tạo/sửa/xóa/clone ổn định |
| Browser | Launch/stop/restart ổn định |
| Session | Cookie/localStorage/cache còn sau restart |
| Proxy | Proxy đúng/sai đều xử lý rõ |
| Logs | Lỗi có error code, module, profile_id |
| Dashboard | Xem được trạng thái hệ thống |
| Backup | Backup/restore thành công |
| Security | Có auth, không public trần ra internet |
| Resource | Có giới hạn số profile chạy song song |
| Documentation | Có hướng dẫn cài đặt/vận hành/debug |

## 17. Rủi ro chính

| Rủi ro | Tác động | Cách xử lý |
|---|---|---|
| Repo gốc còn alpha | Có bug bất ngờ | Test kỹ trước khi dùng thật |
| Browser crash | Mất phiên làm việc | Health check + crash log |
| Proxy chết | Profile không hoạt động | Proxy checker + status rõ |
| Hết RAM | Máy treo | Max running profiles |
| Hết disk | Mất dữ liệu/session lỗi | Disk monitor + backup |
| SQLite quá tải | App chậm/lỗi lock DB | Chuyển PostgreSQL |
| Không backup | Mất profile | Backup tự động |
| Expose app không HTTPS | Rủi ro token/session | Dùng VPN/HTTPS/whitelist IP |

## 18. Mental model triển khai

Không coi CloakBrowser Manager là sản phẩm final.

Coi nó là:

```text
Engine + khung app sẵn có
```

Tool nội bộ của mình là:

```text
Fork Manager
+ Logging
+ Test
+ Dashboard
+ Proxy checker
+ Backup
+ Resource guard
+ UI tiếng Việt
```

Thứ tự đúng:

```text
Chạy được → Đo lỗi được → Debug được → Backup được → Dùng lâu dài được
```

Không nên bắt đầu bằng việc làm UI đẹp. UI đẹp nhưng browser/proxy/session lỗi thì dự án không có giá trị.

## 19. Kết luận kỹ thuật

Với mục tiêu nội bộ, không cần xây app từ đầu.

Nên dùng CloakBrowser Manager làm base, sau đó fork và phát triển thêm các lớp cần thiết:

1. Logging.
2. Error tracking.
3. Proxy checker.
4. Health check.
5. Dashboard.
6. Backup/restore.
7. Resource limit.
8. UI nội bộ/tiếng Việt.

Đây là hướng nhanh nhất, ít rủi ro nhất và tiết kiệm chi phí dev nhất.

