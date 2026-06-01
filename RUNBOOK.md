# HƯỚNG DẪN VẬN HÀNH CLOAKBROWSER MANAGER (RUNBOOK)
*Tài liệu hướng dẫn vận hành chuẩn hóa cho phiên bản Desktop App*

---

## 1. Tổng quan Kiến trúc Desktop App

Ứng dụng **CloakBrowser Manager** được thiết kế dưới dạng một Desktop App hoàn chỉnh, tích hợp chặt chẽ giữa các thành phần cốt lõi:
* **UI Frontend (React / Vite)**: Đóng gói thành các static assets tĩnh, được tải trực tiếp trong cửa sổ Electron để đảm bảo hiệu năng và bảo mật tối đa.
* **Backend (FastAPI)**: Viết bằng Python, quản lý cơ sở dữ liệu SQLite, tiến trình (process control) và cấu hình proxy/fingerprint. Ở môi trường Dev, backend chạy qua `uvicorn`. Ở môi trường Production, backend được compile thành một binary chạy ngầm độc lập thông qua `PyInstaller`.
* **Trình duyệt Native**: Khi người dùng nhấn khởi chạy Profile, ứng dụng sẽ gọi trực tiếp file thực thi **CloakBrowser Native** thật trên máy vật lý của người dùng. Mỗi profile mở ra một cửa sổ trình duyệt độc lập trực tiếp dưới dạng native window trên Host OS (macOS/Windows) thay vì chạy trong container noVNC ảo.

---

## 2. Quy trình Vận hành chính (Desktop App Workflow)

### 2.1 Cách mở App
1. **Chạy File cài đặt/Ứng dụng**: 
   - Trên **macOS**: Chạy file `CloakBrowser Manager.app` trong thư mục Applications.
   - Trên **Windows**: Chạy file `CloakBrowser Manager.exe` hoặc phím tắt trên Desktop.
2. **Khởi động ngầm tự động**:
   - Khi Electron khởi chạy, nó sẽ tự động tìm kiếm cổng kết nối còn trống (bắt đầu quét từ cổng `8080`) để khởi động tiến trình FastAPI Backend ngầm.
   - Electron sẽ liên tục gửi request Health Check để xác nhận backend sẵn sàng hoạt động trước khi hiển thị giao diện UI chính.

### 2.2 Thiết lập ban đầu (Cấu hình CloakBrowser Binary trong Settings)
Lần đầu tiên khởi chạy ứng dụng, bạn cần chỉ định file chạy trình duyệt CloakBrowser để hệ thống có thể điều khiển:
1. Mở ứng dụng, di chuyển đến mục **Cài đặt (Settings)** từ menu điều hướng trái.
2. Tại mục **Đường dẫn CloakBrowser Binary (CloakBrowser Binary Path)**, nhấn nút **Chọn File (Browse)**.
3. Cửa sổ chọn file hệ thống sẽ hiện ra. Hãy trỏ trực tiếp đến file chạy `cloakbrowser` (trên macOS) hoặc `cloakbrowser.exe` (trên Windows).
4. Nhấn **Lưu cấu hình (Save)**. Đường dẫn này sẽ được mã hóa và lưu trữ trực tiếp vào file cấu hình `app-config.json` nằm trong thư mục App Data Path của hệ thống.

### 2.3 Cách tạo Profile
1. Vào trang **Hồ sơ trình duyệt (Profiles)** từ menu chính.
2. Chọn **Tạo Hồ sơ mới (Create Profile)**.
3. Thiết lập các thông số Fingerprint cho profile:
   - **Tên cấu hình**: Đặt tên dễ gợi nhớ.
   - **Hệ điều hành đích (Platform)**: macOS, Windows, Linux.
   - **Độ phân giải màn hình (Screen Resolution)**.
   - **Cấu hình Fingerprint nâng cao**: User-Agent, Canvas, WebGL, WebRTC, ClientRects,...
4. Nhấn **Lưu cấu hình (Save)**. Cấu hình profile được ghi trực tiếp vào cơ sở dữ liệu SQLite cục bộ (`cloakbrowser.db`).

### 2.4 Cách gắn Proxy & Đồng bộ GeoIP
1. Truy cập mục **Quản lý Proxy (Proxy Manager)** -> Chọn **Thêm Proxy (Add Proxy)**.
2. Nhập các thông tin cấu hình proxy hỗ trợ các giao thức phổ biến: **HTTP**, **HTTPS**, **SOCKS5**.
3. Nhấp nút **Kiểm tra (Check Proxy)** để xác định trạng thái kết nối, tốc độ phản hồi (Latency) và địa chỉ IP thực tế.
4. Khi gán Proxy này vào một Profile và kích hoạt tính năng **Đồng bộ Múi giờ / Ngôn ngữ (GeoIP Auto-sync)**:
   - Hệ thống sẽ tự động gửi truy vấn GeoIP để xác định múi giờ (Timezone) và ngôn ngữ hiển thị (Locale/Language) của Proxy.
   - Các thông số này sẽ tự động được áp dụng vào cấu hình trình duyệt khi khởi chạy, giúp Profile đạt độ trust tuyệt đối trên các trang check fingerprint (IPHey, CreepJS).

### 2.5 Cách Launch Native (Khởi chạy Trình duyệt Native)
1. Tại danh sách Hồ sơ, tìm profile cần mở và nhấp nút **Khởi chạy (Launch)**.
2. **Quy trình hoạt động ngầm**:
   - Backend đọc cấu hình lưu trữ từ file `app-config.json` để lấy đường dẫn file chạy CloakBrowser.
   - Backend khởi tạo một tiến trình độc lập (`subprocess`) trỏ tới thư mục dữ liệu tách biệt của profile đó (`--user-data-dir`), đồng thời cấu hình tham số Proxy, Fingerprint và các cờ tối ưu hóa chromium.
   - Trình duyệt CloakBrowser sẽ xuất hiện dưới dạng cửa sổ độc lập ngay trên màn hình máy tính của bạn.
   - Backend ghi nhận Process ID (PID) của tiến trình này vào SQLite database để theo dõi thời gian thực.

### 2.6 Cách Stop/Restart (Dừng & Khởi động lại)
* **Cách Dừng (Stop)**:
  1. Nhấp nút **Dừng (Stop)** trực tiếp trên giao diện quản lý ứng dụng, hoặc tắt thủ công cửa sổ trình duyệt CloakBrowser.
  2. Hệ thống sẽ gửi tín hiệu đóng an toàn (graceful shutdown) đến chromium context để lưu lại cookies, session và lịch sử duyệt web một cách toàn vẹn.
  3. **Cơ chế Fallback an toàn**: Nếu tiến trình không tự tắt sau **5 giây**, backend sẽ tự động gửi lệnh cưỡng chế tắt (`SIGKILL` trên macOS hoặc `taskkill` trên Windows) dựa trên PID được lưu trữ để giải phóng RAM triệt để và tránh tiến trình chạy ngầm (zombie process).
* **Cách Khởi động lại (Restart)**:
  1. Nhấp nút **Khởi động lại (Restart)** bên cạnh profile tương ứng.
  2. Hệ thống thực thi tuần tự quy trình Dừng (Stop) -> Chờ dọn dẹp tiến trình -> Tự động khởi chạy lại (Launch) an toàn.

### 2.7 Cách xem Logs hệ thống
Nếu gặp sự cố trong quá trình vận hành, hãy kiểm tra logs ở các file sau nằm trong thư mục dữ liệu App Data Path:
* **`app.log`**: Log của tiến trình Electron (giao diện, quản lý cửa sổ, khởi động ứng dụng).
* **`backend.log`**: Log chi tiết của FastAPI Backend (kết nối cơ sở dữ liệu, gọi API, kết quả chạy proxy).
* **`profiles/{profile_id}/session.log`**: Nhật ký hoạt động chi tiết của riêng profile đó khi khởi chạy trình duyệt native.

**Đường dẫn thư mục chứa Log chuẩn theo hệ điều hành:**
* **macOS**: `~/Library/Application Support/CloakBrowser-Manager/logs/`
* **Windows**: `%APPDATA%\CloakBrowser-Manager\logs\`

### 2.8 Cách Sao lưu & Phục hồi theo App Data Path
Tất cả dữ liệu cấu hình, cookies, session và bộ nhớ đệm của bạn đều được lưu trữ hoàn toàn cục bộ trên máy tính cá nhân tại thư mục **App Data Path**:
* **macOS**: `~/Library/Application Support/CloakBrowser-Manager/`
* **Windows**: `%APPDATA%\CloakBrowser-Manager\`

#### Quy trình Sao lưu (Backup):
1. Đảm bảo toàn bộ các profile trình duyệt đã được **Dừng (Stop)** hoàn toàn.
2. Tạo bản sao lưu thư mục **App Data Path** bằng cách copy hoặc nén zip thủ công:
   - Thư mục `profiles/` (chứa cookies, cache của các tài khoản).
   - File `cloakbrowser.db` (chứa toàn bộ danh sách profile, cấu hình fingerprint và proxy).
   - File `app-config.json` (chứa cấu hình đường dẫn binary và cài đặt ứng dụng).
3. Lưu trữ file nén tại một nơi an toàn (USB, Cloud cá nhân).

#### Quy trình Phục hồi (Restore):
1. Tắt hoàn toàn ứng dụng Electron CloakBrowser Manager.
2. Giải nén bản sao lưu đè trực tiếp lên thư mục App Data Path tương ứng với hệ điều hành của bạn.
3. Khởi động lại ứng dụng, toàn bộ cấu hình, tài khoản và session của bạn sẽ xuất hiện nguyên vẹn.

---

## 3. Phụ lục: Docker & Môi trường ảo (Chỉ dành cho Dev / Debug)

> [!IMPORTANT]
> Hướng dẫn chạy bằng Docker bên dưới chỉ phục vụ mục đích **phát triển (development), kiểm thử (testing), hoặc debug hệ thống**. Đây KHÔNG phải là luồng vận hành chính dành cho người dùng cuối của ứng dụng.

### 3.1 Hạn chế của luồng Docker / VNC / noVNC
* **Bị phát hiện fingerprint**: Việc giả lập màn hình thông qua VNC/noVNC hoặc chạy trong môi trường Headless Docker làm tăng tỷ lệ bị phát hiện bởi các thuật toán chống bot nâng cao (như CreepJS, Cloudflare).
* **Hiệu năng kém**: Đồ họa dựng hình trong container không hỗ trợ tăng tốc phần cứng tốt bằng chạy Native trực tiếp trên hệ điều hành của máy Host.
* **Thao tác phức tạp**: Phải mở thêm cổng VNC, cấu hình docker-compose và quản lý tài nguyên container phức tạp.

### 3.2 Cách chạy chế độ Debug Container
Nếu bạn thực sự cần thử nghiệm trong Docker container:
1. Đảm bảo đã cài đặt Docker và Docker Compose trên máy tính.
2. Khởi động container ảo bằng lệnh:
   ```bash
   docker compose up -d --build
   ```
3. Truy cập dashboard quản trị trên Web qua cổng mặc định `http://localhost:8080`.
4. Xem giao diện trình duyệt được truyền trực tuyến qua giao thức noVNC tại cổng `http://localhost:6080/vnc.html`.

---

## 4. Bảng mã lỗi Hệ thống & Hướng dẫn xử lý (System Error Codes)

| Mã lỗi (Error Code) | Ý nghĩa / Nguyên nhân | Hướng dẫn khắc phục cụ thể |
| :--- | :--- | :--- |
| `BACKEND_START_FAILED` | Electron không thể khởi chạy tiến trình FastAPI Backend (do thiếu thư viện Python, file binary bị hỏng hoặc Antivirus chặn). | 1. Trên máy dev: Chạy lại `pip install -r backend/requirements.txt` trong `.venv`. <br>2. Thêm file chạy backend vào danh sách loại trừ (Exclusion) của Windows Defender / Antivirus. |
| `BACKEND_HEALTH_CHECK_FAILED` | Backend đã khởi chạy nhưng không phản hồi request ping từ Electron (hết thời gian timeout 10 giây). | Kiểm tra logs `backend.log` để xem có lỗi kết nối SQLite database hoặc lỗi cấu hình mạng nội bộ hay không. |
| `PORT_CONFLICT` | Cổng mặc định `8080` (hoặc cổng cấu hình) đã bị chiếm bởi một ứng dụng khác trên máy tính. | Electron sẽ tự động quét và chuyển sang cổng trống tiếp theo (e.g. `8081`, `8082`). Nếu vẫn lỗi, hãy đóng bớt ứng dụng chạy ngầm hoặc thay đổi cấu hình cổng mặc định trong file cài đặt. |
| `CLOAK_BROWSER_BINARY_NOT_CONFIGURED` | Người dùng chưa cấu hình đường dẫn tới file chạy CloakBrowser trong Settings. | Truy cập trang **Cài đặt (Settings)**, nhấp chọn file chạy `cloakbrowser` / `cloakbrowser.exe` thực tế trên máy và lưu lại. |
| `CLOAK_BROWSER_BINARY_NOT_FOUND` | Đường dẫn file chạy CloakBrowser đã cấu hình nhưng file không tồn tại thực tế (do bị xóa, di chuyển hoặc đổi tên). | Kiểm tra lại vị trí file chạy trên ổ cứng, truy cập Settings để trỏ lại chính xác đường dẫn mới nhất. |
| `BROWSER_NATIVE_START_FAILED` | Không thể khởi chạy tiến trình trình duyệt native (lỗi phân quyền, tham số fingerprint không hợp lệ hoặc thiếu RAM). | Xem chi tiết log tại `profiles/{profile_id}/session.log`. Kiểm tra phân quyền truy cập file chạy và dung lượng RAM trống của máy Host. |
| `BROWSER_NATIVE_STOP_FAILED` | Gặp lỗi khi cố gắng dừng profile (tiến trình bị treo cứng, không phản hồi lệnh graceful close và lệnh SIGKILL thất bại). | Khởi động lại ứng dụng Electron hoặc tắt tiến trình Chromium ngầm thủ công bằng Task Manager (Windows) / Activity Monitor (macOS). |
| `PROFILE_ALREADY_RUNNING` | Cố gắng mở một profile đang ở trạng thái hoạt động (`starting` hoặc `running`). Một profile chỉ được chạy 1 session duy nhất tại 1 thời điểm. | Đợi profile khởi chạy xong, hoặc nhấn nút **Dừng (Stop)** trước khi kích hoạt chạy lại. Nếu profile bị kẹt ảo, hãy tắt app Electron để giải phóng lock file SQLite. |
| `APP_DATA_PATH_PERMISSION_DENIED` | Hệ điều hành từ chối quyền đọc/ghi vào thư mục App Data của người dùng. | Chạy ứng dụng dưới quyền Administrator (Windows) hoặc phân quyền ghi cho thư mục dữ liệu bằng lệnh `chmod -R 755` (macOS). |
| `ELECTRON_WINDOW_BLANK` | Cửa sổ Electron bị trắng xóa (do lỗi render giao diện React, file build tĩnh bị thiếu hoặc Vite server chưa khởi động ở chế độ Dev). | 1. Ở chế độ Dev: Đảm bảo Vite dev server đang chạy ổn định. <br>2. Ở chế độ Prod: Chạy `npm run desktop:build` để đóng gói lại các static assets trước khi mở app. |

---

## 5. Checklist Kiểm thử trước khi Phát hành (Pre-release Checklist)

Trước khi thực hiện đóng gói installer và phát hành phiên bản mới (Release), người phụ trách kiểm thử (QA/Tester) phải thực hiện đầy đủ các bước kiểm thử sau đây để đảm bảo độ ổn định tối đa:

### PHASE A: Kiểm thử Cài đặt & Khởi tạo ban đầu
- [ ] **Kiểm tra cài đặt mới (Clean Install)**: Cài đặt ứng dụng trên máy sạch (chưa từng cài đặt CloakBrowser trước đó). App phải khởi chạy thành công mà không có lỗi thiếu thư mục hay file cấu hình.
- [ ] **Kiểm tra phát hiện Binary**: Trạng thái hiển thị cảnh báo `CLOAK_BROWSER_BINARY_NOT_CONFIGURED` khi chưa trỏ binary.
- [ ] **Kiểm tra Cấu hình Settings**: Trỏ binary trong mục Settings -> Ứng dụng ghi nhận chính xác đường dẫn vào `app-config.json` -> Trạng thái cảnh báo biến mất.

### PHASE B: Kiểm thử Tính năng cốt lõi (Core Features)
- [ ] **Kiểm tra Tạo Profile**: Tạo mới profile với các hệ điều hành khác nhau (macOS, Windows). Đảm bảo lưu thành công vào SQLite.
- [ ] **Kiểm tra Kết nối Proxy**:
  - [ ] Thêm Proxy SOCKS5/HTTP hợp lệ -> Click Check -> Phải báo Connect thành công và hiển thị IP chính xác.
  - [ ] Thêm Proxy lỗi -> Click Check -> Phải hiển thị lỗi kết nối cụ thể.
- [ ] **Kiểm tra Đồng bộ GeoIP**: Bật GeoIP auto-sync trên profile -> Khởi chạy -> Kiểm tra múi giờ và ngôn ngữ trên trình duyệt thực tế phải khớp 100% với IP của Proxy.

### PHASE C: Kiểm thử Chu kỳ Sống của Trình duyệt (Lifecycle Management)
- [ ] **Kiểm tra Launch Native**: Click Launch -> Cửa sổ trình duyệt thực tế phải hiển thị mượt mà trên màn hình chính. Kiểm tra điểm trust trên CreepJS/IPHey phải đạt chất lượng cao.
- [ ] **Kiểm tra Ngăn chặn Concurrent Session**: Khi profile đang chạy, nút Launch phải bị vô hiệu hóa hoặc báo lỗi `PROFILE_ALREADY_RUNNING` nếu cố ý gọi API chạy song song.
- [ ] **Kiểm tra Stop & Giải phóng PID**:
  - [ ] Click Stop trên giao diện -> Cửa sổ trình duyệt native tự động đóng trong vòng 3 giây.
  - [ ] Kiểm tra Task Manager / Activity Monitor không còn tiến trình con `cloakbrowser` hay `chromium` nào chạy ngầm.
- [ ] **Kiểm tra Cưỡng chế SIGKILL (Fallback)**: Giả lập kẹt trình duyệt -> Nhấn Stop -> Sau 5 giây, tiến trình phải bị cưỡng chế tắt hoàn toàn.

### PHASE D: Kiểm thử Độ ổn định & Dữ liệu (Stability & Data Integrity)
- [ ] **Kiểm tra Xung đột Cổng (Port Conflict)**: Chạy một ứng dụng khác chiếm cổng `8080` trước -> Khởi chạy CloakBrowser Manager -> Ứng dụng phải tự động phát hiện và chuyển sang cổng tiếp theo (e.g. `8081`) mượt mà không bị crash.
- [ ] **Kiểm tra Backup & Restore**:
  - [ ] Thực hiện Backup một profile chứa sẵn lịch sử/cookie -> Tạo thành công file `.zip`.
  - [ ] Xóa profile đó đi -> Click Restore từ file `.zip` -> Mở lại profile -> Lịch sử, session đăng nhập phải được khôi phục nguyên vẹn.
- [ ] **Kiểm tra Crash Recovery**: Tắt đột ngột ứng dụng Electron khi profile đang hoạt động -> Mở lại app -> Hệ thống phải tự dọn dẹp lock file cũ, đồng bộ lại trạng thái profile về `stopped` để sẵn sàng sử dụng tiếp.

