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

---

## 3. Portable Profile Package & Fingerprint Lock

### 3.1 Portable Profile Package là gì?
**Portable Profile Package** (định dạng `.cbprofile`) là giải pháp chuẩn hóa để chuyển giao toàn bộ trạng thái hoạt động của một profile trình duyệt giữa các thiết bị vật lý hoặc các môi trường khác nhau mà vẫn đảm bảo tính kế thừa tuyệt đối. 

Không chỉ đơn thuần sao lưu tài khoản, gói dữ liệu này bao gồm:
* **Thông tin Session/Cookies**: Cookies, `localStorage`, `sessionStorage`, `IndexedDB`, `Service Worker data`, dữ liệu `Cache` cần thiết, và các tùy chọn `Preferences`.
* **Cấu hình Fingerprint Core**: Cấu hình profile, `fingerprint_seed`, cấu hình giả lập Canvas, WebGL, Font danh sách, múi giờ (timezone), ngôn ngữ (locale), `user-agent`, độ phân giải màn hình (`screen size`), cùng metadata phiên bản trình duyệt (`browser version metadata`).

### 3.2 Vì sao không chỉ export cookies?
Export/Import mỗi cookie là **không đủ** để duy trì trạng thái đăng nhập hoặc độ tin cậy của tài khoản trên các nền tảng lớn (Facebook, Google, Amazon).
* Nhiều website hiện đại lưu trữ trạng thái đăng nhập và session token trong `localStorage` hoặc `IndexedDB`.
* Nếu chỉ chuyển giao cookies mà thay đổi hoàn toàn vân tay trình duyệt (`fingerprint`), hệ thống bảo mật của website sẽ lập tức phát hiện sự bất thường (mâu thuẫn giữa cookies cũ và cấu hình thiết bị mới), dẫn đến xác minh danh tính (checkpoint, khóa tài khoản).
* Định dạng `.cbprofile` đảm bảo **đồng bộ cả dữ liệu phiên hoạt động và vân tay số trình duyệt**.

### 3.3 Phân quyền Export/Import
* **Staff (Nhân viên thường)**: **KHÔNG** được phép thực hiện Export hoặc Import profile package để ngăn ngừa rủi ro rò rỉ dữ liệu tài nguyên của doanh nghiệp.
* **Admin**: Được phép Export và Import các profile package giữa các máy.
* **Super Admin**: Được phép sử dụng toàn bộ tính năng và các công cụ nâng cao (Advanced Tools).

### 3.4 Quy trình Export Profile
1. Đảm bảo profile cần xuất đang ở trạng thái **Dừng (Stopped)**. 
   > [!WARNING]
   > Hệ thống sẽ chặn hoàn toàn và báo lỗi nếu bạn cố gắng export một profile đang chạy (`running`).
2. Chọn profile mong muốn từ danh sách và click **Export Profile**.
3. Nhập mật khẩu bảo vệ (**Passphrase**) để mã hóa gói dữ liệu an toàn bằng thuật toán AES.
4. Tùy chọn gán bảo mật: Theo mặc định, ứng dụng sẽ **không xuất mật khẩu proxy** kèm theo gói để bảo vệ tài nguyên mạng của doanh nghiệp (có thể bật thủ công nếu cần thiết).
5. Nhấn **Export** và lưu trữ file `.cbprofile` thu được vào nơi an toàn.

> [!CAUTION]
> File `.cbprofile` chứa toàn bộ session đăng nhập đang hoạt động của tài khoản. Tuyệt đối không gửi file này qua các kênh chat công cộng không an toàn hoặc chia sẻ cho người không có thẩm quyền.

### 3.5 Quy trình Import Profile
1. Khởi động ứng dụng trên máy tính mới hoặc trong thư mục App Data Folder sạch.
2. Di chuyển đến mục **Import Profile**.
3. Chọn file `.cbprofile` cần nhập và nhập chính xác **Passphrase** bảo vệ.
4. Lựa chọn chế độ import:
   - **Import as new profile**: Tạo một profile hoàn toàn mới có ID mới kế thừa cấu hình gốc.
   - **Overwrite existing profile**: Ghi đè trực tiếp lên một profile hiện tại (Profile đích bắt buộc phải đang ở trạng thái **Stopped**).
5. Nhấn **Import** để hoàn tất phục hồi.
6. Tiến hành **Launch profile** để kiểm tra tính toàn vẹn của phiên hoạt động.

### 3.6 Fingerprint Lock (Khóa Vân tay trình duyệt)
Tính năng **Fingerprint Locked = ON** (mặc định kích hoạt) giúp cố định hoàn toàn danh tính kỹ thuật số của profile trình duyệt, ngăn chặn các hành vi vô tình làm thay đổi cấu hình gốc.

* **Khi Fingerprint Lock đang bật**, các thông số sau sẽ **bị khóa cứng** và không thể sửa đổi:
  - `fingerprint_seed`, canvas config/seed, WebGL vendor/renderer, font list, `user-agent`, screen size, `hardwareConcurrency`, `deviceMemory`, audio fingerprint, và browser version lock.
* **Đổi Proxy an toàn**: Khi bạn tiến hành thay đổi Proxy của profile, hệ thống **chỉ cập nhật cấu hình proxy**, hoàn toàn không tác động đến các core fingerprint nêu trên. Ứng dụng sẽ hiển thị thông báo rõ ràng:
  `Proxy changed. Fingerprint unchanged.`

### 3.7 Cơ chế ghi đè dữ liệu khi tắt Profile
Khi bạn khởi chạy, sử dụng profile trên máy mới và **Dừng (Stop)** trình duyệt:
* **Các thành phần ĐƯỢC cập nhật & lưu trữ**: Cookies mới phát sinh, bộ nhớ `localStorage`/`sessionStorage` mới, `IndexedDB`, `Service Worker`, cache web, site settings và extension data.
* **Các thông số KHÔNG bao giờ bị thay đổi**: Toàn bộ core fingerprint (canvas, font, WebGL, UA, screen, hardware info,...) được giữ nguyên tuyệt đối để bảo toàn vân tay trình duyệt.
* **Tự động lưu**: Nếu tính năng `session_auto_save = true`, timestamp `last_session_save_at` sẽ tự động được ghi nhận.

### 3.8 Hướng dẫn Giả lập 2 Máy (Local Simulation Test)
Để kiểm thử tính năng Portable Profile Package mà không cần 2 máy vật lý thật, bạn có thể sử dụng biến môi trường `APP_DATA_DIR` để khởi chạy 2 phiên bản độc lập trên cùng 1 máy tính:

* **Mở Máy A (Môi trường A)**:
  ```bash
  cd CloakBrowser-Manager
  APP_DATA_DIR="$HOME/Desktop/cbtest-machine-a" npm run desktop:dev
  ```
* **Mở Máy B (Môi trường B)**:
  ```bash
  cd CloakBrowser-Manager
  APP_DATA_DIR="$HOME/Desktop/cbtest-machine-b" npm run desktop:dev
  ```

**Quy trình kiểm thử:**
1. Trên ứng dụng **Máy A**: Tạo một profile trình duyệt (ví dụ: `Test-Machine-A`), bật Fingerprint Locked. Khởi chạy và truy cập một vài website để tạo dữ liệu cookies/session, sau đó dừng profile.
2. Thực hiện **Export** profile đó thành file `Test-Machine-A.cbprofile` ra ngoài Desktop. Đóng hoàn toàn app Máy A.
3. Trên ứng dụng **Máy B**: Ứng dụng sẽ mở ra hoàn toàn trống trơn (không chứa dữ liệu của Máy A). Tiến hành **Import** file `.cbprofile` từ Desktop.
4. Khởi chạy profile vừa import trên Máy B, xác nhận trạng thái đăng nhập (session/cookies) và kiểm tra các thông số vân tay trên các trang check fingerprint hoàn toàn trùng khớp với Máy A.

---

## 4. Bảng mã lỗi Hệ thống & Hướng dẫn xử lý (System Error Codes)

| Mã lỗi (Error Code) | Ý nghĩa / Nguyên nhân | Hướng dẫn khắc phục cụ thể |
| :--- | :--- | :--- |
| `PROFILE_RUNNING_EXPORT_DENIED` | Cố gắng export một profile đang ở trạng thái hoạt động (`starting` hoặc `running`). | Tiến hành nhấn nút **Dừng (Stop)** profile trước khi export. |
| `PROFILE_RUNNING_IMPORT_DENIED` | Cố gắng import ghi đè (`overwrite`) vào một profile đang chạy. | Dừng profile đích đang chạy trước khi thực hiện ghi đè. |
| `PROFILE_PACKAGE_INVALID` | File `.cbprofile` tải lên không đúng định dạng zip hoặc bị thiếu file cấu hình quan trọng (`metadata.json`). | Kiểm tra lại tệp tin được chọn, đảm bảo tệp tin được sinh ra từ tính năng Export của CloakBrowser. |
| `PROFILE_PACKAGE_CHECKSUM_FAILED` | File package bị can thiệp thay đổi cấu trúc hoặc bị hỏng trong quá trình truyền tải (lỗi hash checksum). | Hãy thực hiện export lại tệp tin từ máy gốc và chuyển giao lại qua đường truyền an toàn hơn. |
| `PROFILE_PACKAGE_DECRYPT_FAILED` | Giải mã thất bại do nhập sai **Passphrase** bảo vệ. | Hãy nhập chính xác mật khẩu bảo vệ đã thiết lập khi export tệp tin. |
| `BROWSER_VERSION_MISMATCH` | Phiên bản CloakBrowser trên máy nhập khác biệt lớn so với máy xuất, gây rủi ro lệch vân tay. | Cài đặt phiên bản CloakBrowser tương thích hoặc nhấn xác nhận bỏ qua cảnh báo nếu tin tưởng. |
| `FINGERPRINT_LOCKED` | Cố gắng thay đổi các trường vân tay cốt lõi khi profile đang ở chế độ khóa (`Fingerprint Locked = ON`). | Chỉ tài khoản có quyền Admin/Super Admin mới được phép mở khóa hoặc thực hiện tái tạo vân tay (`regenerate`). |
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

## 5. Quy định An toàn thông tin (Security Notes)
* **Tuyệt đối không lưu cookies hoặc dữ liệu localStorage vào logs hệ thống** để tránh lộ lọt thông tin tài khoản người dùng.
* **Không lưu mật khẩu proxy và passphrase giải mã** dưới dạng plain-text vào database hay logs.
* **Chặn hoàn toàn** hành vi xuất/nhập/ghi đè các profile đang ở trạng thái hoạt động (`running`) để tránh tranh chấp ghi file gây lỗi cấu trúc trình duyệt.
* Các tệp tin `.cbprofile` xuất ra phải được lưu trữ ở các phân vùng được mã hóa và chuyển giao qua các kênh kết nối có bảo mật (SSL/TLS, SFTP hoặc ổ cứng di động mã hóa).

---

## 6. Checklist trước khi Phát hành (Pre-release Checklist)

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

## 7. Phụ lục: Docker & Môi trường ảo (Chỉ dành cho Dev / Debug)

> [!IMPORTANT]
> Hướng dẫn chạy bằng Docker bên dưới chỉ phục vụ mục đích **phát triển (development), kiểm thử (testing), hoặc debug hệ thống**. Đây KHÔNG phải là luồng vận hành chính dành cho người dùng cuối của ứng dụng.

### 7.1 Hạn chế của luồng Docker / VNC / noVNC
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
