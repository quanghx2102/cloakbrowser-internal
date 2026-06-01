# HƯỚNG DẪN VẬN HÀNH BẢN DESKTOP (RUNBOOK)
*Dự án phát triển công cụ quản lý hồ sơ trình duyệt CloakBrowser*

---

## 1. Tổng quan Kiến trúc Desktop
Ứng dụng CloakBrowser Manager hoạt động như một ứng dụng Desktop hoàn chỉnh, bao gồm:
* **UI Frontend**: React (Vite) đóng gói dạng Static assets và được load trực tiếp trong cửa sổ Electron.
* **Backend**: FastAPI (Python) được khởi động tự động khi mở app Electron (ở chế độ development qua `uvicorn`, ở chế độ production thông qua backend binary được compile bằng `PyInstaller`).
* **Trình duyệt Native**: Khi chạy profile, app mở cửa sổ trình duyệt **CloakBrowser Native thật** trực tiếp trên màn hình của người dùng thay vì chạy trong container noVNC ảo.

---

## 2. Cách Chạy Phát triển (Development Workflow)

Để khởi động toàn bộ hệ thống ở chế độ dev:
1. Đảm bảo bạn đã cài đặt các dependency của Electron ở thư mục gốc:
   ```bash
   npm install
   ```
2. Đảm bảo môi trường Python ảo `.venv` đã được tạo và cài đặt đầy đủ các package cần thiết:
   ```bash
   # Tạo môi trường ảo (nếu chưa có)
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Cài đặt các package bắt buộc
   pip install -r backend/requirements.txt
   ```
3. Đặt file chạy của **CloakBrowser** (`cloakbrowser` trên macOS/Linux hoặc `cloakbrowser.exe` trên Windows) vào thư mục `binaries` ở thư mục gốc hoặc chỉ định thông qua biến môi trường `CLOAK_BROWSER_BINARY_PATH`.
4. Khởi chạy ứng dụng:
   ```bash
   npm run desktop:dev
   ```
   *Lệnh này sẽ đồng thời start Vite dev server, biên dịch TypeScript cho main process của Electron và khởi động ứng dụng Electron.*

---

## 3. Cách Đóng gói & Phát hành (Production Build)

Khi cần đóng gói ứng dụng để bàn giao cho người dùng cuối:
1. **Build toàn bộ các thành phần**:
   ```bash
   npm run desktop:build
   ```
   *Script này sẽ biên dịch React UI sang file tĩnh, đóng gói FastAPI backend thành file chạy độc lập (.exe hoặc binary) thông qua PyInstaller, và biên dịch file chạy chính của Electron.*
2. **Đóng gói Installer (DMG/NSIS)**:
   ```bash
   npm run desktop:dist
   ```
   *Tạo gói cài đặt tự động tại thư mục `release/1.0.0/`.*

---

## 4. Quản lý Hồ sơ & Proxy trên Desktop

### 4.1 Tạo Hồ sơ (Profile CRUD)
* Mở giao diện ứng dụng -> Vào mục **Hồ sơ trình duyệt (Profiles)**.
* Chọn **Thêm hồ sơ (Create Profile)** -> Thiết lập tên, seed fingerprint (platform macOS, Windows, Linux), độ phân giải màn hình ảo và lưu lại.
* Dữ liệu cấu hình được lưu trực tiếp tại database SQLite nội bộ đặt tại đường dẫn dữ liệu người dùng (`Application Support` hoặc `AppData`).

### 4.2 Gắn Proxy & Tự động đồng bộ Timezone/Locale
* Vào menu **Proxy** -> Chọn **Thêm proxy** để cấu hình proxy mới (hỗ trợ HTTP, SOCKS5).
* Nhấn **Kiểm tra (Check)** để kiểm tra tốc độ phản hồi và IP.
* Khi bật tính năng **GeoIP** trong cấu hình Profile, hệ thống sẽ tự động phân giải quốc gia, múi giờ (Timezone) và ngôn ngữ (Locale) dựa trên proxy được gắn để áp dụng trực tiếp cho cửa sổ trình duyệt CloakBrowser native khi mở, giúp tăng điểm trust tối đa.

---

## 5. Khởi chạy & Đóng Trình duyệt (Native Window Workflow)

* **Khởi chạy (Launch)**: Nhấn nút **Khởi chạy (Launch)** trên UI. 
  - Backend sẽ tự động kiểm tra sự tồn tại của file chạy `cloakbrowser`.
  - Khởi tạo Chromium persistent context thực tế dưới màn hình host.
  - Tiến trình sẽ tự động lấy PID để giám sát thời gian thực.
* **Dừng (Stop)**: Nhấn nút **Dừng (Stop)**.
  - Hệ thống sẽ gọi lệnh đóng Context của Playwright một cách mềm dẻo (graceful close).
  - Nếu trình duyệt không phản hồi sau 5 giây, hệ thống sẽ tự động dùng PID thực thi `SIGKILL` để giải phóng bộ nhớ triệt để, tránh các tiến trình chạy ngầm (zombie chromium processes).
* **Đóng tất cả khẩn cấp**: Click **Dừng tất cả** trên Dashboard để quét dọn toàn bộ các profile đang chạy.

---

## 6. Sao lưu & Phục hồi dữ liệu (Backup & Restore)

Mọi dữ liệu của ứng dụng bao gồm SQLite DB và profile cookies/sessions đều nằm hoàn toàn cục bộ trên máy của bạn tại thư mục ứng dụng chuẩn (`Application Support/CloakInternalTool` hoặc `AppData\Roaming\CloakInternalTool`).

### 6.1 Sao lưu Database
* **Web API**: `POST http://localhost:<port>/api/backups`
* Dữ liệu SQLite lưu trữ cấu hình sẽ được backup tự động vào thư mục con `backups/database/`.

### 6.2 Sao lưu Thư mục Profile (Cookies, Storage, Cache)
> [!WARNING]
> Không thực hiện sao lưu khi profile đó đang ở trạng thái hoạt động (`starting` / `running`).
* Trên giao diện, chọn nút **Sao lưu (Backup)** bên cạnh profile tương ứng.
* Hệ thống sẽ zip toàn bộ thư mục dữ liệu của profile đó và lưu trữ vào thư mục `backups/profiles/`.

### 6.3 Phục hồi (Restore)
* Để khôi phục một profile cũ, chỉ cần chọn file zip sao lưu tương ứng trong Settings/API và click **Restore**. Hệ thống sẽ giải nén và ghi đè an toàn vào thư mục `profiles/` cục bộ.

---

## 7. Các Lỗi Thường Gặp trên Bản Desktop & Cách Xử Lý

| Hiện tượng | Nguyên nhân | Cách xử lý |
| :--- | :--- | :--- |
| **Không tìm thấy CloakBrowser Binary** | Chưa cấu hình hoặc chưa đặt file chạy `cloakbrowser` đúng vị trí. | Đảm bảo file chạy đã được copy vào thư mục `binaries` ở thư mục gốc của app hoặc set biến môi trường `CLOAK_BROWSER_BINARY_PATH` trỏ tới file chạy thật. |
| **Lỗi khởi động Backend** | Thiếu dependency Python ở máy dev hoặc file chạy PyInstaller backend bị lỗi/chặn bởi Antivirus. | 1. Chạy `pip install -r backend/requirements.txt` trong môi trường ảo.<br>2. Thêm thư mục dữ liệu app vào danh sách loại trừ của Windows Defender / Antivirus. |
| **Không giải phóng được Profile cũ** | SQLite database hoặc file `SingletonLock` bị khóa do app tắt đột ngột trước đó. | Mở app lại, hệ thống sẽ tự động thực hiện tiến trình `cleanup_stale` để xóa các file Lock dư thừa và tắt các Chromium chạy ngầm. |
