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

### 2.1 Cách cài đặt và mở App Electron
1. **Tải và cài đặt**:
   - **macOS**: Tải gói cài đặt `.dmg`, nhấp đúp và kéo biểu tượng `CloakBrowser Manager.app` vào thư mục `/Applications`.
   - **Windows**: Tải gói cài đặt `.exe` (Installer), nhấp đúp để cài đặt tự động lên máy tính.
2. **Khởi chạy ứng dụng**:
   - Nhấp đúp vào biểu tượng ứng dụng ở danh sách ứng dụng hoặc ngoài Desktop.
   - **Khởi động ngầm tự động**: Khi Electron khởi chạy, nó sẽ tự động tìm kiếm cổng kết nối còn trống (bắt đầu quét từ cổng `8080`) để khởi động tiến trình FastAPI Backend ngầm.
   - Electron sẽ liên tục gửi request Health Check để xác nhận backend sẵn sàng hoạt động trước khi hiển thị giao diện UI chính.

### 2.2 Lần đầu cấu hình CloakBrowser Binary trong Settings
Lần đầu tiên khởi chạy ứng dụng, bạn cần chỉ định file chạy trình duyệt CloakBrowser để hệ thống có thể điều khiển:
1. Mở ứng dụng, di chuyển đến mục **Cài đặt (Settings)** từ menu điều hướng bên trái.
2. Tại mục **Đường dẫn CloakBrowser Binary (CloakBrowser Binary Path)**, nhấn nút **Chọn File (Browse)**.
3. Giao diện File Dialog của Electron sẽ xuất hiện. Hãy trỏ trực tiếp đến file chạy `cloakbrowser` (trên macOS) hoặc `cloakbrowser.exe` (trên Windows).
4. Nhấn **Lưu cấu hình (Save)**. Đường dẫn này sẽ được xác thực định dạng và lưu trữ trực tiếp vào file cấu hình `app-config.json` nằm trong thư mục App Data Path của hệ thống.

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
4. Gán Proxy này vào Profile mong muốn:
   - Vào danh sách Profile -> Sửa Profile -> Chọn Proxy tương ứng.
5. Khi kích hoạt tính năng **Đồng bộ Múi giờ / Ngôn ngữ (GeoIP Auto-sync)**:
   - Hệ thống sẽ tự động gửi truy vấn GeoIP để xác định múi giờ (Timezone) và ngôn ngữ hiển thị (Locale/Language) của Proxy.
   - Các thông số này sẽ tự động được áp dụng vào cấu hình trình duyệt khi khởi chạy, giúp Profile đạt độ trust tuyệt đối trên các trang check fingerprint (IPHey, CreepJS).

### 2.5 Cách Launch Native (Khởi chạy Trình duyệt Native)
1. Tại danh sách Hồ sơ, tìm profile cần mở và nhấp nút **Khởi chạy (Launch)**.
2. **Quy trình hoạt động ngầm**:
   - Backend đọc cấu hình lưu trữ từ file `app-config.json` để lấy đường dẫn file chạy CloakBrowser.
   - Backend khởi tạo một tiến trình độc lập (`subprocess`) trỏ tới thư mục dữ liệu tách biệt của profile đó (`--user-data-dir`), đồng thời cấu hình tham số Proxy, Fingerprint và các cờ tối ưu hóa chromium.
   - Trình duyệt CloakBrowser sẽ xuất hiện dưới dạng cửa sổ độc lập ngay trên màn hình máy tính của bạn.
   - Backend ghi nhận Process ID (PID) của tiến trình này vào SQLite database để theo dõi thời gian thực.

### 2.6 Cách Stop/Restart profile (Dừng & Khởi động lại)
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

### 2.9 Cách Cập nhật ứng dụng (Update App)
1. **Cập nhật tự động (Auto-Update)**:
   - Khi khởi chạy, ứng dụng sẽ kiểm tra phiên bản mới trên máy chủ phát hành.
   - Nếu có phiên bản mới, ứng dụng sẽ tải về ngầm và hiển thị thông báo yêu cầu người dùng khởi động lại để hoàn tất cập nhật.
2. **Cập nhật thủ công**:
   - Tải file cài đặt `.dmg` hoặc `.exe` mới nhất từ trang chủ.
   - Tiến hành cài đặt đè lên phiên bản cũ. Toàn bộ cấu hình và dữ liệu profile cũ trong thư mục **App Data Path** được giữ nguyên hoàn toàn mà không bị ảnh hưởng.

### 2.10 Cách Đóng gói / Build Installer (.dmg / .exe)
Để đóng gói sản phẩm phục vụ phát hành, hãy chạy các script tương ứng trong thư mục dự án:
1. **Cài đặt thư viện phát triển**:
   ```bash
   npm install
   pip install -r backend/requirements.txt
   ```
2. **Build Frontend**:
   ```bash
   npm run build
   ```
3. **Build Backend sang dạng Binary độc lập (PyInstaller)**:
   ```bash
   npm run backend:build
   ```
4. **Build Installer cho Desktop App (Electron Builder)**:
   - **macOS** (tạo file `.dmg`):
     ```bash
     npm run desktop:build:mac
     ```
   - **Windows** (tạo file `.exe`):
     ```bash
     npm run desktop:build:win
     ```
   Sản phẩm đóng gói hoàn chỉnh sẽ nằm trong thư mục `dist/` để sẵn sàng phân phối.

---

## 3. Bảng mã lỗi Hệ thống & Hướng dẫn xử lý (System Error Codes)

| Mã lỗi (Error Code) | Ý nghĩa / Nguyên nhân | Hướng dẫn khắc phục cụ thể |
| :--- | :--- | :--- |
| `BACKEND_START_FAILED` | Electron không thể khởi chạy tiến trình FastAPI Backend (do thiếu thư viện Python, file binary bị hỏng hoặc Antivirus chặn). | 1. Trên máy dev: Chạy lại `pip install -r backend/requirements.txt` trong `.venv`. <br>2. Thêm file chạy backend vào danh sách loại trừ (Exclusion) của Windows Defender / Antivirus. |
| `BACKEND_HEALTH_CHECK_FAILED` | Backend đã khởi chạy nhưng không phản hồi request ping từ Electron (hết thời gian timeout 10 giây). | Kiểm tra logs `backend.log` để xem có lỗi kết nối SQLite database hoặc lỗi cấu hình mạng nội bộ hay không. |
| `PORT_CONFLICT` | Cổng mặc định `8080` (hoặc cổng cấu hình) đã bị chiếm bởi một ứng dụng khác trên máy tính. | Electron sẽ tự động quét và chuyển sang cổng trống tiếp theo (e.g. `8081`, `8082`). Nếu vẫn lỗi, hãy đóng bớt ứng dụng chạy ngầm hoặc thay đổi cấu hình cổng mặc định. |
| `CLOAK_BROWSER_BINARY_NOT_CONFIGURED` | Người dùng chưa cấu hình đường dẫn tới file chạy CloakBrowser trong Settings. | Truy cập trang **Cài đặt (Settings)**, nhấp chọn file chạy `cloakbrowser` / `cloakbrowser.exe` thực tế trên máy và lưu lại. |
| `CLOAK_BROWSER_BINARY_NOT_FOUND` | Đường dẫn file chạy CloakBrowser đã cấu hình nhưng file không tồn tại thực tế (do bị xóa, di chuyển hoặc đổi tên). | Kiểm tra lại vị trí file chạy trên ổ cứng, truy cập Settings để trỏ lại chính xác đường dẫn mới nhất. |
| `CLOAK_BROWSER_BINARY_INVALID` | File được chọn không phải là CloakBrowser binary hợp lệ hoặc bị lỗi cấu trúc, không thể thực thi. | Hãy tải lại bộ binary CloakBrowser chính xác cho hệ điều hành hiện tại (macOS Silicon/Intel, Windows x64/arm64) và chọn lại. |
| `BROWSER_NATIVE_START_FAILED` | Không thể khởi chạy tiến trình trình duyệt native (lỗi phân quyền, tham số fingerprint không hợp lệ hoặc thiếu RAM). | Xem chi tiết log tại `profiles/{profile_id}/session.log`. Kiểm tra phân quyền truy cập file chạy và dung lượng RAM trống của máy Host. |
| `BROWSER_NATIVE_STOP_FAILED` | Gặp lỗi khi cố gắng dừng profile (tiến trình bị treo cứng, không phản hồi lệnh graceful close và lệnh SIGKILL thất bại). | Khởi động lại ứng dụng Electron hoặc tắt tiến trình Chromium ngầm thủ công bằng Task Manager (Windows) / Activity Monitor (macOS). |
| `PROFILE_ALREADY_RUNNING` | Cố gắng mở một profile đang ở trạng thái hoạt động (`starting` hoặc `running`). Một profile chỉ được chạy 1 session duy nhất tại 1 thời điểm. | Đợi profile khởi chạy xong, hoặc nhấn nút **Dừng (Stop)** trước khi kích hoạt chạy lại. Nếu profile bị kẹt ảo, hãy tắt app Electron để giải phóng lock file SQLite. |
| `APP_DATA_PATH_PERMISSION_DENIED` | Hệ điều hành từ chối quyền đọc/ghi vào thư mục App Data của người dùng. | Chạy ứng dụng dưới quyền Administrator (Windows) hoặc phân quyền ghi cho thư mục dữ liệu bằng lệnh `chmod -R 755` (macOS). |
| `ELECTRON_WINDOW_BLANK` | Cửa sổ Electron bị trắng xóa (do lỗi render giao diện React, file build tĩnh bị thiếu hoặc Vite server chưa khởi động ở chế độ Dev). | 1. Ở chế độ Dev: Đảm bảo Vite dev server đang chạy ổn định. <br>2. Ở chế độ Prod: Chạy `npm run desktop:build` để đóng gói lại các static assets trước khi mở app. |

---

## 4. Checklist trước khi Phát hành (Pre-release Checklist)

Trước khi thực hiện đóng gói installer và phát hành phiên bản mới (Release), người phụ trách kiểm thử (QA/Tester) phải thực hiện đầy đủ checklist kiểm thử sau đây để đảm bảo ứng dụng vận hành đúng chuẩn Desktop App và không phụ thuộc Docker:

- [ ] **App mở được (Electron Launch)**: Mở ứng dụng mượt mà trên môi trường sạch không bị lỗi màn hình trắng (`ELECTRON_WINDOW_BLANK`).
- [ ] **Backend auto-start**: Khi mở app Electron, FastAPI Backend tự động được khởi chạy ngầm trên một cổng trống không bị lỗi `BACKEND_START_FAILED` hay `PORT_CONFLICT`.
- [ ] **Settings chọn binary**: Trang cài đặt mở được, cho phép chọn đường dẫn `cloakbrowser` binary cục bộ, xác thực thành công và lưu vào `app-config.json`.
- [ ] **Tạo profile**: Cho phép tạo và lưu cấu hình Profile mới vào SQLite thành công.
- [ ] **Launch native**: Kích hoạt profile mở ra cửa sổ trình duyệt thật trực tiếp trên màn hình máy tính Host OS, nhận chính xác tham số Fingerprint và Proxy.
- [ ] **Stop/Restart**: Nút Stop đóng hoàn toàn cửa sổ trình duyệt trong 3 giây. Nếu treo, cơ chế fallback SIGKILL dọn sạch tiến trình ngầm sau 5 giây. Restart tắt rồi mở lại an toàn.
- [ ] **Quit cleanup**: Khi tắt hoàn toàn ứng dụng Electron, tất cả tiến trình backend ngầm và trình duyệt đang mở đều được dọn dẹp sạch sẽ, không để lại tiến trình mồ côi (zombie processes).
- [ ] **Logs OK**: Thư mục App Data ghi nhận đầy đủ logs của Electron (`app.log`), Backend (`backend.log`) và Profile (`session.log`) chuẩn cấu trúc.
- [ ] **Build installer OK**: Biên dịch thành công gói installer `.dmg` trên macOS và `.exe` trên Windows bằng electron-builder.
- [ ] **Không cần Docker**: Toàn bộ hệ thống kiểm thử hoạt động hoàn chỉnh mà không cần cài đặt hoặc khởi chạy bất kỳ container Docker hay VNC/noVNC nào.

---

## 5. Phụ lục: Docker & Môi trường ảo (Chỉ dành cho Dev / Debug)

> [!IMPORTANT]
> Hướng dẫn chạy bằng Docker bên dưới chỉ phục vụ mục đích **phát triển (development), kiểm thử (testing), hoặc debug hệ thống**. Đây KHÔNG phải là luồng vận hành chính dành cho người dùng cuối của ứng dụng.

### 5.1 Hạn chế của luồng Docker / VNC / noVNC
* **Bị phát hiện fingerprint**: Việc giả lập màn hình thông qua VNC/noVNC hoặc chạy trong môi trường Headless Docker làm tăng tỷ lệ bị phát hiện bởi các thuật toán chống bot nâng cao (như CreepJS, Cloudflare).
* **Hiệu năng kém**: Đồ họa dựng hình trong container không hỗ trợ tăng tốc phần cứng tốt bằng chạy Native trực tiếp trên hệ điều hành của máy Host.
* **Thao tác phức tạp**: Phải mở thêm cổng VNC, cấu hình docker-compose và quản lý tài nguyên container phức tạp.

### 5.2 Cách chạy chế độ Debug Container
Nếu bạn thực sự cần thử nghiệm trong Docker container:
1. Đảm bảo đã cài đặt Docker và Docker Compose trên máy tính.
2. Khởi động container ảo bằng lệnh:
   ```bash
   docker compose up -d --build
   ```
3. Truy cập dashboard quản trị trên Web qua cổng mặc định `http://localhost:8080`.
4. Xem giao diện trình duyệt được truyền trực tuyến qua giao thức noVNC tại cổng `http://localhost:6080/vnc.html`.
