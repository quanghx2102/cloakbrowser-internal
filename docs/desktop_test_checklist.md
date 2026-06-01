# CHECKLIST KIỂM THỬ ỨNG DỤNG DESKTOP (E2E TESTING CHECKLIST)
*Tài liệu kiểm thử tích hợp toàn diện từ đầu đến cuối cho CloakBrowser Manager*

Tài liệu này cung cấp danh sách các bước kiểm thử tích hợp thực tế (E2E) nhằm đảm bảo ứng dụng hoạt động ổn định trên môi trường Desktop của người dùng cuối.

---

## PHẦN 1: KIỂM THỬ MÔI TRƯỜNG PHÁT TRIỂN & BUILD (PHASE 1-2)

### 1.1 Khởi động Chế độ Dev (`npm run desktop:dev`)
- [ ] **Bước 1**: Đảm bảo thư mục `binaries` chứa file chạy `cloakbrowser` (hoặc `cloakbrowser.exe` trên Windows).
- [ ] **Bước 2**: Chạy lệnh `npm run desktop:dev` ở root directory.
- [ ] **Bước 3**: Xác nhận Vite Dev Server khởi động thành công trên cổng `5173`.
- [ ] **Bước 4**: Xác nhận FastAPI Backend khởi động thành công (port scan tự động chọn cổng trống, thường là `8080`).
- [ ] **Bước 5**: Cửa sổ ứng dụng Electron tự động hiển thị, tải đúng giao diện và kết nối được với API backend.

### 1.2 Đóng gói Ứng dụng Sản phẩm (`npm run desktop:dist`)
- [ ] **Bước 1**: Chạy lệnh `npm run desktop:dist`.
- [ ] **Bước 2**: Xác nhận React build tĩnh kết xuất vào thư mục `frontend/dist/`.
- [ ] **Bước 3**: Xác nhận PyInstaller compile thành công backend độc lập vào `backend/dist/`.
- [ ] **Bước 4**: Xác nhận `electron-builder` hoàn tất đóng gói và tạo file cài đặt (`.dmg` trên macOS hoặc `.exe` trên Windows) trong thư mục `release/1.0.0/`.

---

## PHẦN 2: KIỂM THỬ KHỞI ĐỘNG & VÒNG ĐỜI (PHASE 3)

### 2.1 Tự động phát hiện & Kiểm tra Cổng API (Port Binding)
- [ ] **Bước 1**: Khởi động app khi cổng `8080` đang bị chiếm bởi một dịch vụ khác.
- [ ] **Bước 2**: Xác nhận module `find-free-port` tự động phát hiện cổng bị chiếm và cấp phát một cổng mới (ví dụ: `8081`).
- [ ] **Bước 3**: Xác nhận ứng dụng Electron tự động chuyển query parameter kết nối sang cổng mới (`?api_port=8081`) và hoạt động bình thường.

### 2.2 Trình tìm kiếm & Giải quyết Đường dẫn Binary (Binary Resolver)
- [ ] **Bước 1**: Xóa tạm thời file chạy `cloakbrowser` ra khỏi thư mục `binaries` và không set biến môi trường.
- [ ] **Bước 2**: Khởi động ứng dụng.
- [ ] **Bước 3**: Xác nhận hộp thoại thông báo lỗi hiển thị rõ ràng: `"Không tìm thấy CloakBrowser Binary"`.
- [ ] **Bước 4**: Trả lại file chạy vào thư mục `binaries` và khởi chạy lại. Xác nhận app khởi động thành công không báo lỗi.

---

## PHẦN 3: KIỂM THỬ QUẢN LÝ HỒ SƠ & PROXY (PHASE 4)

### 3.1 Thêm, Sửa, Xóa Profile & Proxy
- [ ] **Bước 1**: Vào menu Proxy, thêm một proxy mới (HTTP/SOCKS5) và nhấn nút **Check**. Xác nhận IP và latency hiển thị chính xác.
- [ ] **Bước 2**: Tạo mới một Profile, gắn proxy vừa tạo, kích hoạt tính năng **GeoIP**.
- [ ] **Bước 3**: Thay đổi cấu hình Profile (đổi tên, đổi độ phân giải màn hình ảo). Xác nhận dữ liệu cập nhật lưu thành công vào SQLite DB.

### 3.2 Tự động Đồng bộ Timezone & Locale từ Proxy
- [ ] **Bước 1**: Sử dụng một proxy thuộc quốc gia khác (ví dụ: Mỹ hoặc Singapore).
- [ ] **Bước 2**: Nhấn Check proxy để lấy múi giờ và ngôn ngữ địa phương tự động.
- [ ] **Bước 3**: Khởi chạy Profile gắn proxy này.
- [ ] **Bước 4**: Vào các trang check như [IPHey](https://iphey.com) hoặc [CreepJS](https://abrahamjuliot.github.io/creepjs/). Xác nhận múi giờ của trình duyệt và ngôn ngữ hiển thị tự động khớp chính xác với quốc gia của proxy mà không cần thiết lập thủ công.

---

## PHẦN 4: KIỂM THỬ KHỞI CHẠY TRÌNH DUYỆT NATIVE (PHASE 5-6)

### 4.1 Khởi chạy Native Window (Launch Profile)
- [ ] **Bước 1**: Nhấn nút **Khởi chạy (Launch)** trên một profile.
- [ ] **Bước 2**: Xác nhận trạng thái hiển thị trên giao diện chuyển từ `stopped` -> `starting` -> `running`.
- [ ] **Bước 3**: Xác nhận **cửa sổ trình duyệt CloakBrowser thật** xuất hiện trực tiếp trên màn hình máy tính (Native Window), không thông qua noVNC ảo.
- [ ] **Bước 4**: Kiểm tra trong Task Manager / Activity Monitor, xác nhận có tiến trình Chromium chạy độc lập tương ứng với PID được ghi nhận ở backend.

### 4.2 Giám sát Tiến trình & Xử lý Crash (Crash Watcher)
- [ ] **Bước 1**: Đang chạy 1 profile, giả lập crash bằng cách tắt cửa sổ trình duyệt đó thủ công hoặc dùng lệnh `kill -9 <PID>` trực tiếp trên hệ điều hành.
- [ ] **Bước 2**: Xác nhận crash watcher của backend phát hiện tiến trình đã chết trong vòng 3 giây.
- [ ] **Bước 3**: Xác nhận trạng thái profile trên giao diện tự động chuyển về `stopped` hoặc báo lỗi phù hợp.

### 4.3 Dừng mềm & Force Kill khi Tắt Profile (Stop/Restart)
- [ ] **Bước 1**: Nhấn nút **Dừng (Stop)** trên một profile đang hoạt động.
- [ ] **Bước 2**: Xác nhận tiến trình đóng lại mềm dẻo (graceful close) và giải phóng hoàn toàn các file khóa SQLite/Chromium.
- [ ] **Bước 3**: Giả lập kịch bản trình duyệt bị treo (không phản hồi lệnh close). Xác nhận sau 5 giây, backend tự động thực thi lệnh `SIGKILL` dựa trên PID đã lưu trữ để tắt hẳn tiến trình treo.
- [ ] **Bước 4**: Nhấn nút **Khởi động lại (Restart)**. Xác nhận profile tắt đi gọn gàng và tự khởi chạy lại cửa sổ mới sau 1 giây.

---

## PHẦN 5: THOÁT ỨNG DỤNG & DỌN DẸP (PHASE 7)

### 5.1 Xử lý khi có Profile đang chạy khi đóng App
- [ ] **Bước 1**: Đang có 1 hoặc nhiều profile trình duyệt đang hoạt động, nhấn đóng ứng dụng Electron bằng nút đóng (`X`) hoặc `Cmd+Q` / `Alt+F4`.
- [ ] **Bước 2**: Xác nhận hộp thoại cảnh báo hiển thị với 3 lựa chọn:
  1. *Đóng tất cả và thoát*: Tắt toàn bộ profile đang chạy và thoát app.
  2. *Giữ trình duyệt tiếp tục chạy và thoát*: Giữ nguyên cửa sổ trình duyệt chạy độc lập, chỉ tắt backend/app quản lý.
  3. *Hủy bỏ*: Giữ nguyên ứng dụng hoạt động.
- [ ] **Bước 3**: Chọn lựa chọn 1. Xác nhận toàn bộ cửa sổ trình duyệt đóng lại đồng thời và Electron tắt an toàn.
- [ ] **Bước 4**: Mở lại ứng dụng. Chọn lựa chọn 2. Xác nhận app Electron đóng đi, các cửa sổ trình duyệt vẫn tiếp tục hoạt động độc lập bình thường.
