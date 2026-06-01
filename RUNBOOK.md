# TÀI LIỆU VẬN HÀNH NỘI BỘ (RUNBOOK)
*Dự án phát triển tool nội bộ dựa trên CloakBrowser*

---

## 1. Cách start app
Chạy lệnh từ thư mục gốc chứa file `docker-compose.yml`:
```bash
docker compose up -d
```
Nếu có thay đổi code backend/frontend hoặc cần build lại image:
```bash
docker compose up -d --build
```

---

## 2. Cách stop app
Dừng container và giải phóng tài nguyên một cách an toàn:
```bash
docker compose down
```
Hoặc chỉ dừng chạy container nhưng giữ nguyên trạng thái để start lại nhanh:
```bash
docker compose stop
```

---

## 3. Cách restart app
Khởi động lại toàn bộ dịch vụ (Manager & Web UI):
```bash
docker compose restart
```

---

## 4. Cách xem container logs
Xem log thời gian thực của container quản lý profile:
```bash
docker logs -f cloak-manager
```
Hoặc xem logs qua docker compose:
```bash
docker compose logs -f manager
```

---

## 5. Cách tạo profile
- **Qua Web UI**: Truy cập `http://localhost:8080` -> Chọn **Hồ sơ trình duyệt** (Profiles) -> Click **Thêm hồ sơ** (Create Profile) -> Điền tên, cấu hình seed fingerprint và lưu lại.
- **Qua API**:
```bash
curl -X POST http://localhost:8080/api/profiles -H "Content-Type: application/json" -d '{"name": "Profile-Moi"}'
```

---

## 6. Cách gắn proxy
- **Qua Web UI**:
  1. Vào menu **Proxy** -> Chọn **Thêm proxy** để khai báo proxy trước (HTTP, SOCKS5).
  2. Vào menu **Hồ sơ trình duyệt** -> Click **Sửa** (Edit) trên profile cần gắn -> Chọn proxy mong muốn từ danh sách -> Click **Lưu**.
- **Qua API**:
```bash
curl -X PUT http://localhost:8080/api/profiles/<profile_id> -H "Content-Type: application/json" -d '{"proxy_id": "<proxy_id>"}'
```

---

## 7. Cách check proxy
- **Qua Web UI**: Truy cập menu **Proxy** -> Click nút **Kiểm tra** (Check) tại dòng proxy tương ứng để xem latency và IP mới nhất.
- **Qua API**:
```bash
curl -X POST http://localhost:8080/api/proxies/<proxy_id>/check
```

---

## 8. Cách launch/stop profile
- **Khởi chạy Profile (Launch)**:
  - **Web UI**: Click nút **Khởi chạy** (Launch) trên Profile tương ứng.
  - **API**:
  ```bash
  curl -X POST http://localhost:8080/api/profiles/<profile_id>/launch
  ```
- **Dừng Profile (Stop)**:
  - **Web UI**: Click nút **Dừng** (Stop) trên Profile đang chạy.
  - **API**:
  ```bash
  curl -X POST http://localhost:8080/api/profiles/<profile_id>/stop
  ```
- **Dừng toàn bộ Profile khẩn cấp (Stop All)**:
  - **Web UI**: Click nút **Dừng tất cả** trên **Tổng quan** (Dashboard).
  - **API**:
  ```bash
  curl -X POST http://localhost:8080/api/profiles/stop-all
  ```

---

## 9. Cách backup database/profile folder

### 9.1 Backup Database (Lưu trữ thông tin cấu hình, proxy, logs)
- **Qua Web UI**: Vào **Cài đặt** (Settings) -> Click **Tạo bản sao lưu Database**.
- **Qua API**:
```bash
curl -X POST http://localhost:8080/api/backups
```
- **Qua Terminal** (Thực thi trực tiếp trong container):
```bash
docker exec -it cloak-manager python -c "from backend.database import backup_database; backup_database()"
```
*Đường dẫn lưu file: `/data/backups/profiles_backup_<timestamp>.db`*

### 9.2 Backup Profile Folder (Lưu trữ cookies, sessions, cache của từng profile)
> [!WARNING]
> Không backup khi profile đang chạy (`running` / `starting`) để tránh xung đột hoặc hỏng dữ liệu (data corruption).

- **Qua Web UI**: Vào **Hồ sơ trình duyệt** -> Click **Sao lưu dữ liệu** bên cạnh profile cần backup.
- **Qua API**:
```bash
curl -X POST http://localhost:8080/api/profiles/<profile_id>/backup
```
- **Qua Terminal** (Thực thi trực tiếp trong container):
```bash
docker exec -it cloak-manager python -c "from backend.database import backup_profile; backup_profile('<profile_id>')"
```
*Đường dẫn lưu file: `/data/backups/profiles/profile_<profile_id>_<timestamp>.zip`*

---

## 10. Cách restore

> [!IMPORTANT]
> Bắt buộc dừng tất cả profile đang chạy (`Stop All`) trước khi tiến hành restore để tránh xung đột ghi dữ liệu.

### 10.1 Restore Database
- **Qua API**:
```bash
curl -X POST http://localhost:8080/api/backups/restore -H "Content-Type: application/json" -d '{"backup_filename": "<profiles_backup_timestamp.db>"}'
```
- **Thực hiện thủ công bằng dòng lệnh**:
```bash
# 1. Stop container để giải phóng khóa DB
docker compose down

# 2. Copy đè bản backup vào profiles.db (chú ý đường dẫn volume mount thực tế trên host)
cp ./data/backups/<profiles_backup_timestamp.db> ./data/profiles.db

# 3. Start lại ứng dụng
docker compose up -d
```

### 10.2 Restore Profile Folder
- **Qua API**:
```bash
curl -X POST http://localhost:8080/api/profiles/<profile_id>/restore -H "Content-Type: application/json" -d '{"backup_filename": "<profile_id_timestamp.zip>"}'
```
- **Thực hiện thủ công bằng dòng lệnh**:
```bash
# Giải nén đè file zip backup vào thư mục lưu trữ profile
unzip -o ./data/backups/profiles/<profile_id_timestamp.zip> -d ./data/profiles/
```

---

## 11. Bảng lỗi phổ biến và cách xử lý

| Mã lỗi / Hiện tượng | Nguyên nhân | Cách xử lý |
| :--- | :--- | :--- |
| `RESOURCE_LIMIT_REACHED` | Số profile chạy đồng thời vượt quá giới hạn RAM/CPU cho phép. | 1. Dừng bớt các profile không hoạt động.<br>2. Tăng biến `MAX_RUNNING_PROFILES` trong file cấu hình `.env` nếu tài nguyên phần cứng còn dư dả. |
| `PROFILE_LOCKED` | Cố tình xóa hoặc backup khi profile đang khởi chạy hoặc hoạt động. | Chờ profile chuyển sang trạng thái dừng hẳn hoặc click **Dừng** (Stop) rồi thực hiện lại. |
| `BACKUP_FAILED` / `RESTORE_FAILED` | Ổ đĩa đầy hoặc không có quyền ghi vào thư mục `/data`. | 1. Kiểm tra dung lượng đĩa trên server bằng `df -h`.<br>2. Phân quyền lại thư mục lưu trữ: `chmod -R 755 ./data`. |
| `PROXY_CHECK_FAILED` / Proxy báo đỏ | Proxy bị lỗi kết nối, bị chặn, hoặc cấu hình sai IP/Port/Credentials. | 1. Kiểm tra lại thông tin cấu hình proxy.<br>2. Chạy thử `curl -x socks5://user:pass@host:port https://google.com` từ terminal của server để debug. |
| Màn hình VNC đen / Mất kết nối | Tiến trình KasmVNC của profile bị crash hoặc xung đột cổng websocket. | 1. Click **Dừng** (Stop) profile rồi bấm **Khởi chạy** (Launch) lại.<br>2. Kiểm tra logs container để xem chi tiết lỗi crash. |
| Database bị khóa (database is locked) | SQLite bị ghi đồng thời quá nhiều luồng (concurrent writes). | Hệ thống đã kích hoạt chế độ WAL. Nếu vẫn gặp lỗi, hãy thực hiện restart container. Cân nhắc nâng cấp lên PostgreSQL nếu quy mô vận hành tăng cao. |

---

## 12. Checklist trước khi update app
Trước khi tiến hành nâng cấp hoặc cập nhật phiên bản mới của ứng dụng:

- [ ] **1. Thông báo bảo trì**: Lên lịch bảo trì và thông báo cho người dùng nội bộ để tránh gián đoạn công việc.
- [ ] **2. Dừng toàn bộ profiles**: Click nút **Dừng tất cả** trên Dashboard hoặc gọi API `/api/profiles/stop-all` để đưa toàn bộ trình duyệt về trạng thái off.
- [ ] **3. Sao lưu Database**: Thực hiện backup db hiện tại bằng API hoặc lưu bản copy vật lý file `profiles.db`.
- [ ] **4. Kiểm tra đĩa cứng**: Đảm bảo ổ đĩa của server còn trống tối thiểu 5GB để lưu trữ image docker mới và các file tạm trong quá trình build.
- [ ] **5. Pull code & Rebuild**:
  ```bash
  git pull origin main
  docker compose up -d --build
  ```
- [ ] **6. Kiểm tra log khởi động**: Xem logs để đảm bảo database migrations chạy thành công và không có exception nào xảy ra:
  ```bash
  docker compose logs -f manager
  ```
- [ ] **7. Kiểm thử dịch vụ**: Khởi chạy thử 1 profile, kiểm tra kết nối VNC và lướt web thử để xác nhận hệ thống vận hành bình thường sau update.
