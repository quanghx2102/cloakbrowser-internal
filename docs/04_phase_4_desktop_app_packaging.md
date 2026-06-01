# PHASE 4 — Desktop App Final + Bundled Backend + CloakBrowser Native Window

> Bản cập nhật mới nhất: **nên làm App desktop riêng**, backend được đóng gói/chạy local bên trong app, và khi Run Profile phải mở **CloakBrowser native window thật**. noVNC không còn là luồng mặc định.

---

## 0. Kết luận kỹ thuật

### Nên làm App không?

**Có.** Nên làm App desktop nếu bạn muốn trải nghiệm như phần mềm thật:

- Click app là chạy.
- Không cần mở terminal.
- Không cần tự chạy Docker.
- Không cần nhớ `http://localhost:8080`.
- App tự start/stop backend local.
- App tự quản lý database, profile data, logs, config.
- Bấm Run Profile là mở **CloakBrowser native window**.

Điểm quan trọng:

```text
App desktop giúp vận hành tiện hơn.
CloakBrowser native window giúp profile chạy mượt hơn noVNC.
```

---

## 1. Source repo bắt buộc

- CloakBrowser engine: https://github.com/CloakHQ/CloakBrowser
- CloakBrowser Manager: https://github.com/CloakHQ/CloakBrowser-Manager

Nguyên tắc bắt buộc:

- Không dùng Chrome/Chromium thường làm browser core.
- Không fallback sang Playwright default Chromium.
- Browser core bắt buộc là **CloakBrowser binary**.
- Backend launcher dùng `CLOAK_BROWSER_BINARY_PATH`.
- Backend nên được bundle/chạy local bên trong desktop app.
- Docker chỉ dùng dev/test, không bắt buộc trong desktop final.
- noVNC chỉ là option phụ/debug, không phải luồng chính.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.

---

## 2. Kiến trúc chốt

```text
Electron Desktop App
   ↓
React UI đã build static
   ↓
FastAPI backend local/bundled
   ↓
SQLite database trong App Data
   ↓
Profile/Proxy/Logs services
   ↓
CLOAK_BROWSER_BINARY_PATH
   ↓
CloakBrowser native window thật
```

Không dùng luồng này làm mặc định:

```text
Profile → noVNC viewer
```

---

## 3. Quy ước trạng thái task

```text
Not Started = chưa làm
Ready = đã đủ điều kiện bắt đầu
In Progress = đang làm
Blocked = bị chặn
Needs Fix = đã làm nhưng test fail
Done = hoàn thành và test pass
```

---

## 4. Task table

| Task | Tên task                             | Trạng thái  | Phụ thuộc         | Mục tiêu                          |
| ---- | ------------------------------------ | ----------- | ----------------- | --------------------------------- |
| 4.1  | Chốt kiến trúc App desktop           | Ready       | Phase 2 chạy được | Xác nhận kiến trúc trước khi code |
| 4.2  | Tạo Electron workspace               | Not Started | 4.1               | Tạo vỏ app desktop                |
| 4.3  | Load React UI trong Electron         | Done        | 4.2               | Dùng lại UI Phase 2               |
| 4.4  | Bundle/start FastAPI backend local   | Done        | 4.3               | App tự chạy backend               |
| 4.5  | App Data Path chuẩn                  | Done        | 4.4               | Lưu DB/profile/log đúng nơi       |
| 4.6  | Detect/Configure CloakBrowser binary | Done        | 4.5               | Dùng đúng CloakBrowser binary     |
| 4.7  | Launch CloakBrowser native window    | Done        | 4.6               | Run Profile mở cửa sổ thật        |
| 4.8  | Stop/Restart native process          | Not Started | 4.7               | Quản lý PID/process sạch          |
| 4.9  | Loại noVNC khỏi luồng mặc định       | Not Started | 4.7               | noVNC chỉ còn option phụ          |
| 4.10 | Startup/Shutdown lifecycle           | Not Started | 4.4 + 4.8         | App start/quit sạch               |
| 4.11 | Desktop logging/error handling       | Not Started | 4.4 + 4.7         | Debug lỗi app/backend/browser     |
| 4.12 | Build installer macOS/Windows        | Not Started | 4.10 + 4.11       | Tạo .dmg/.exe                     |
| 4.13 | End-to-end test Phase 4              | Not Started | 4.12              | Test app final nội bộ             |

---

# TASK 4.1 — Chốt kiến trúc App desktop

**Status:** Ready  
**Depends on:** Phase 2 web app chạy được

## Mục tiêu

Chốt kiến trúc desktop app để tránh AI/dev tự làm lệch hướng.

## Yêu cầu

- Electron desktop app.
- React UI dùng lại từ Phase 2.
- FastAPI backend bundled hoặc chạy local child process.
- Browser core là CloakBrowser binary.
- Run Profile mở CloakBrowser native window.
- noVNC không còn là luồng mặc định.
- Docker chỉ dùng dev/test.

## Điều kiện hoàn thành

- Có sơ đồ kiến trúc.
- Có startup/shutdown flow.
- Có native launch flow.
- Có danh sách module cần sửa.

## Message prompt

```text
Bạn là senior technical lead kiêm desktop app architect.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 2 đã có web UI quản lý profile/proxy/log/dashboard.
- Bây giờ cần Phase 4 để đóng gói thành desktop app riêng.
- Kết luận kỹ thuật: nên làm App desktop riêng.
- Browser profile phải chạy bằng CloakBrowser native window thật.
- Không dùng noVNC làm luồng chính.
- Không dùng Chrome/Chromium thường.
- Không fallback sang Playwright default Chromium.
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.

Task:
TASK 4.1 — Chốt kiến trúc App Desktop.

Yêu cầu:
1. Đọc cấu trúc repo hiện tại.
2. Xác định frontend React build ra thư mục nào.
3. Xác định backend FastAPI start bằng command nào.
4. Đề xuất kiến trúc Electron + React UI + FastAPI local/bundled backend.
5. Backend phải launch CloakBrowser bằng native window qua CLOAK_BROWSER_BINARY_PATH.
6. noVNC chỉ giữ làm option phụ/debug.
7. Docker chỉ dùng dev/test.
8. Không code trong task này.

Output cần trả:
- Sơ đồ kiến trúc.
- Luồng app startup.
- Luồng app shutdown.
- Luồng Run Profile → CloakBrowser native window.
- Danh sách module/file dự kiến cần sửa.
- Rủi ro kỹ thuật.
- Test checklist.
```

---

# TASK 4.2 — Tạo Electron workspace

**Status:** Not Started  
**Depends on:** 4.1 Done

## Mục tiêu

Tạo vỏ app desktop tối thiểu.

## Yêu cầu

- Tạo thư mục `desktop/` hoặc cấu trúc tương đương.
- Cài Electron.
- Tạo Electron main process.
- Tạo BrowserWindow.
- Dev mode có thể load React dev server.
- Chưa sửa backend/browser launcher.

## Điều kiện hoàn thành

- Chạy được cửa sổ Electron.
- Có script `desktop:dev`.
- Không làm hỏng web/Docker mode.

## Message prompt

```text
Bạn là senior Electron engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 2 đã có React UI và FastAPI backend.
- Phase 4 cần tạo app desktop riêng.
- Dev mode có thể load React dev server.
- Chưa sửa browser launcher trong task này.

Task:
TASK 4.2 — Tạo Electron workspace.

Yêu cầu:
1. Đọc cấu trúc repo hiện tại.
2. Tạo workspace Electron tối thiểu.
3. Thêm dependency Electron.
4. Tạo Electron main process.
5. Tạo BrowserWindow.
6. Thêm script chạy desktop dev.
7. Không sửa logic profile/proxy/browser.
8. Không xóa Docker/web mode hiện tại.

Output cần trả:
- File đã tạo/sửa.
- Cấu trúc thư mục mới.
- Command cài package.
- Command chạy desktop dev.
- Cách kiểm tra cửa sổ Electron mở được.
- Test case.
```

---

# TASK 4.3 — Load React UI trong Electron

**Status:** Done  
**Depends on:** 4.2 Done

## Mục tiêu

Electron load được React UI đã build hoặc React dev server.

## Yêu cầu

- Dev mode load React dev server.
- Production mode load `dist/index.html`.
- Không viết lại UI.
- Sửa asset/routing nếu cần.

## Message prompt

```text
Bạn là senior frontend/Electron engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 2 đã có React UI.
- Phase 4 cần Electron load UI trực tiếp trong app desktop.
- Không viết lại UI từ đầu.

Task:
TASK 4.3 — Load React UI trong Electron.

Yêu cầu:
1. Xác định command build frontend hiện tại.
2. Xác định thư mục output Vite, thường là dist/.
3. Cấu hình Electron:
   - dev mode load React dev server
   - production mode load dist/index.html
4. Kiểm tra asset path/routing không lỗi.
5. Không sửa business logic UI nếu không cần.
6. Thêm script build desktop nếu cần.

Output cần trả:
- File đã sửa.
- Script build/chạy.
- Cách chạy dev.
- Cách chạy production preview.
- Test case.
```

---

# TASK 4.4 — Bundle/start FastAPI backend local

**Status:** Done  
**Depends on:** 4.3 Done

## Mục tiêu

App desktop chứa hoặc tự start backend local. User không cần chạy Docker/terminal.

## Yêu cầu

- Xác định command start FastAPI.
- Electron start backend như child process.
- Có thể dùng PyInstaller để build backend binary.
- Backend bind `127.0.0.1`.
- Electron health check backend trước khi load UI.
- Khi quit app, backend stop an toàn.

## Message prompt

```text
Bạn là senior desktop/backend engineer có kinh nghiệm Electron child_process, FastAPI và PyInstaller.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 2 đã có FastAPI backend.
- Desktop app final phải bundle backend hoặc tự start backend local.
- User không cần chạy Docker/terminal ở bản final.

Task:
TASK 4.4 — Bundle/start FastAPI backend local.

Yêu cầu:
1. Xác định command start backend hiện tại.
2. Tạo cách chạy backend local từ Electron main process.
3. Nếu phù hợp, cấu hình PyInstaller để build backend thành binary.
4. Backend chỉ bind 127.0.0.1.
5. Electron phải health check backend.
6. Nếu backend start fail, UI báo lỗi rõ.
7. Khi app quit, stop backend process.
8. Ghi backend stdout/stderr ra desktop log.
9. Không sửa logic profile/proxy/browser nếu không cần.

Output cần trả:
- File đã sửa.
- Command start backend.
- PyInstaller config nếu có.
- Logic start/stop backend.
- Health check flow.
- Test case.
```

---

# TASK 4.5 — App Data Path chuẩn

**Status:** Not Started  
**Depends on:** 4.4 Done

## Mục tiêu

Dữ liệu app lưu ở thư mục chuẩn của hệ điều hành, không phụ thuộc Docker `/data`.

## Path đề xuất

macOS:

```text
~/Library/Application Support/CloakInternalTool/
```

Windows:

```text
%APPDATA%\\CloakInternalTool\\
```

Bên trong:

```text
profiles/
database/
logs/
backups/
config/
browsers/
```

## Message prompt

```text
Bạn là senior desktop/backend engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 4 chạy như desktop app local.
- Không phụ thuộc Docker volume /data ở bản desktop final.
- Profile data, database, logs, backups phải lưu vào app data path chuẩn.

Task:
TASK 4.5 — App Data Path chuẩn.

Yêu cầu:
1. Xác định các path hiện tại backend đang dùng: database, profiles, logs, backups.
2. Thêm config APP_DATA_DIR.
3. Nếu chạy desktop mode:
   - macOS: ~/Library/Application Support/CloakInternalTool/
   - Windows: %APPDATA%/CloakInternalTool/
4. Tạo thư mục con: profiles, database, logs, backups, config, browsers.
5. Không làm mất data cũ.
6. Nếu cần migration path, đề xuất rõ.
7. Log path đang dùng khi app start.

Output cần trả:
- File đã sửa.
- Cách xác định app data path.
- Cấu trúc thư mục data.
- Migration note nếu có.
- Test case.
```

---

# TASK 4.6 — Detect/Configure CloakBrowser binary

**Status:** Done  
**Depends on:** 4.5 Done

## Mục tiêu

App biết đúng CloakBrowser binary nằm ở đâu.

## Yêu cầu

- Thêm `CLOAK_BROWSER_BINARY_PATH`.
- Detect OS/architecture nếu cần.
- Không dùng Chromium/Chrome thường.
- Nếu thiếu binary, báo lỗi `CLOAK_BROWSER_BINARY_NOT_FOUND`.
- Hỗ trợ binary từ bundled resources, app data `browsers/`, hoặc env/config local.

## Message prompt

```text
Bạn là senior desktop/backend engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 4 cần launch CloakBrowser native window thật.
- Browser core bắt buộc là CloakBrowser binary.
- Không dùng Chrome/Chromium thường.
- Không fallback sang Playwright default Chromium.

Task:
TASK 4.6 — Detect/Configure CloakBrowser binary.

Yêu cầu:
1. Thêm config CLOAK_BROWSER_BINARY_PATH.
2. Detect OS/architecture nếu cần.
3. Hỗ trợ binary path từ:
   - bundled resources
   - app data browsers folder
   - env/config local
4. Nếu không tìm thấy binary, trả lỗi CLOAK_BROWSER_BINARY_NOT_FOUND.
5. UI hiển thị lỗi dễ hiểu.
6. Backend launcher phải dùng path này.
7. Không hard-code path máy dev.
8. Không fallback sang Chrome/Chromium thường.

Output cần trả:
- File đã sửa.
- Cách detect OS/architecture.
- Cách set CLOAK_BROWSER_BINARY_PATH.
- Cách validate binary path.
- Error handling.
- Test case cho macOS/Windows nếu có.
```

---

# TASK 4.7 — Launch CloakBrowser native window theo profile

**Status:** Done  
**Depends on:** 4.6 Done

## Mục tiêu

User bấm Run/Launch Profile → mở **CloakBrowser native window thật**.

## Yêu cầu

- Backend gọi CloakBrowser binary bằng native process/subprocess.
- Mỗi profile dùng `user-data-dir` riêng.
- Dùng proxy/fingerprint config theo profile nếu hệ thống hiện có.
- Lưu PID/process_id.
- Không launch trùng cùng profile.
- Không dùng noVNC làm luồng chính.

## Error codes

```text
BROWSER_NATIVE_STARTED
BROWSER_NATIVE_START_FAILED
BROWSER_NATIVE_STOPPED
BROWSER_NATIVE_STOP_FAILED
CLOAK_BROWSER_BINARY_NOT_FOUND
PROFILE_ALREADY_RUNNING
```

## Message prompt

```text
Bạn là senior backend/process engineer có kinh nghiệm launch browser native process.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 2 đã có profile management.
- Phase 4 cần app desktop launch CloakBrowser bằng native window thật.
- Không dùng noVNC làm mặc định.
- Browser core bắt buộc dùng CLOAK_BROWSER_BINARY_PATH.
- Không dùng Chrome/Chromium thường.
- Mỗi profile phải có data folder riêng.

Task:
TASK 4.7 — Launch CloakBrowser Native Window theo profile.

Yêu cầu:
1. Đọc launcher hiện tại trong CloakBrowser Manager.
2. Xác định hiện tại browser được launch qua Docker/noVNC như thế nào.
3. Thêm chế độ desktop/native launch.
4. Khi desktop mode:
   - launch CloakBrowser binary bằng native process
   - mở cửa sổ thật
   - dùng profile data folder riêng
   - gắn proxy/fingerprint config theo profile nếu hệ thống đã có
5. Lưu PID/process handle.
6. Stop profile phải stop đúng process.
7. Không cho launch trùng cùng profile.
8. Không phá web/Docker mode nếu vẫn cần dev/test.
9. Ghi log/error code:
   - BROWSER_NATIVE_STARTED
   - BROWSER_NATIVE_START_FAILED
   - CLOAK_BROWSER_BINARY_NOT_FOUND
   - PROFILE_ALREADY_RUNNING

Output cần trả:
- File đã sửa.
- Luồng native launch.
- Browser command được dùng.
- Cách truyền user-data-dir.
- Cách truyền proxy/fingerprint config.
- Cách lưu PID.
- Test case.
```

---

# TASK 4.8 — Stop/Restart native process

**Status:** Not Started  
**Depends on:** 4.7 Done

## Mục tiêu

Stop/Restart đúng CloakBrowser process của profile.

## Yêu cầu

- Stop theo PID/process handle.
- Graceful stop trước.
- Force kill nếu timeout.
- Restart = stop xong rồi launch lại.
- Không để zombie process.

## Message prompt

```text
Bạn là senior backend/process engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Task trước đã launch CloakBrowser native window và lưu PID/process_id.
- Bây giờ cần stop/restart native profile process an toàn.

Task:
TASK 4.8 — Stop/Restart Native Profile Process.

Yêu cầu:
1. Stop profile bằng PID/process handle đã lưu.
2. Graceful stop trước.
3. Nếu timeout thì force kill.
4. Restart = stop hoàn tất rồi launch lại.
5. Nếu process không tồn tại, cập nhật status stopped/crashed hợp lý.
6. Không kill nhầm process của profile khác.
7. Ghi log:
   - BROWSER_NATIVE_STOPPED
   - BROWSER_NATIVE_STOP_FAILED
   - BROWSER_NATIVE_RESTARTED
8. Không để zombie process.

Output cần trả:
- File đã sửa.
- Stop flow.
- Restart flow.
- Cách kiểm tra process còn sống.
- Error handling.
- Test case.
```

---

# TASK 4.9 — Loại noVNC khỏi luồng mặc định

**Status:** Not Started  
**Depends on:** 4.7 Done

## Mục tiêu

Desktop mode dùng `Launch Native`, noVNC chỉ là option phụ/debug.

## Message prompt

```text
Bạn là senior full-stack engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 4 desktop app cần browser mở native window thật để đỡ lag.
- noVNC không còn là luồng mặc định.
- noVNC chỉ là option phụ cho remote/debug.
- Không xóa noVNC khỏi web/server mode nếu vẫn cần.

Task:
TASK 4.9 — Loại noVNC khỏi luồng mặc định.

Yêu cầu:
1. Đọc UI profile actions hiện tại.
2. Trong desktop mode, nút chính là Launch Native hoặc Mở CloakBrowser.
3. noVNC/Open Viewer chỉ hiển thị nếu viewer khả dụng.
4. Nếu app chạy web/server mode, có thể giữ behavior cũ.
5. Không làm đứt logic launch/stop hiện có.
6. UI phải phân biệt rõ Native Window khác Viewer.

Output cần trả:
- File đã sửa.
- UI thay đổi.
- Điều kiện hiển thị noVNC.
- Test case desktop mode.
- Test case web mode nếu còn giữ.
```

---

# TASK 4.10 — Desktop startup/shutdown lifecycle

**Status:** Not Started  
**Depends on:** 4.4 + 4.8 Done

## Mục tiêu

App tự start backend, quản lý process, và tắt sạch khi quit.

## Message prompt

```text
Bạn là senior desktop engineer có kinh nghiệm app lifecycle và process cleanup.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Desktop app tự start FastAPI backend local.
- Desktop app có thể launch nhiều CloakBrowser native windows.
- Khi app quit, cần xử lý backend/browser process an toàn.

Task:
TASK 4.10 — Desktop Startup/Shutdown Lifecycle.

Yêu cầu:
1. Startup flow:
   - ensure app data path
   - start backend
   - health check
   - load UI
2. Shutdown flow:
   - nếu có browser profile đang chạy, hỏi user:
     a. Stop all and quit
     b. Keep browsers running
     c. Cancel
3. Stop backend process khi app quit.
4. Không kill browser bừa nếu user chọn keep running.
5. Ghi desktop logs.
6. Không để zombie process.

Output cần trả:
- File đã sửa.
- Startup flow.
- Shutdown flow.
- Dialog behavior.
- Process cleanup logic.
- Test case.
```

---

# TASK 4.11 — Desktop logging/error handling

**Status:** Not Started  
**Depends on:** 4.4 + 4.7 Done

## Mục tiêu

Có log rõ khi app/backend/browser lỗi.

## Message prompt

```text
Bạn là senior desktop/backend engineer.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 4 cần desktop app có log rõ để debug khi app không mở, backend không start hoặc browser launch lỗi.

Task:
TASK 4.11 — Desktop Logging và Error Handling.

Yêu cầu:
1. Tạo desktop log file trong app data path.
2. Log Electron startup/shutdown.
3. Log backend stdout/stderr.
4. Log backend health check fail.
5. Log APP_DATA_DIR đang dùng.
6. Log CLOAK_BROWSER_BINARY_PATH đang dùng, nhưng không log secret.
7. Log native browser launch/stop/crash.
8. Không log password/proxy secret/token.
9. UI hiển thị lỗi dễ hiểu nếu backend không start hoặc thiếu CloakBrowser binary.
10. Giữ error code nhất quán.

Output cần trả:
- File đã sửa.
- Log path.
- Log format.
- Error codes mới nếu có.
- Test case.
```

---

# TASK 4.12 — Build desktop installer macOS/Windows

**Status:** Not Started  
**Depends on:** 4.10 + 4.11 Done

## Mục tiêu

Build app desktop thành file cài đặt/chạy riêng.

## Message prompt

```text
Bạn là senior release engineer có kinh nghiệm Electron Builder và PyInstaller.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 4 cần build desktop app cho macOS/Windows.
- Đây là app nội bộ, chưa cần auto-update phức tạp.
- App desktop final không bắt user chạy Docker.
- Backend local phải được bundle hoặc có binary đi kèm.
- CloakBrowser binary phải được cấu hình rõ.

Task:
TASK 4.12 — Build Desktop Installer macOS/Windows.

Yêu cầu:
1. Cấu hình electron-builder.
2. Build macOS .dmg.
3. Build Windows .exe nếu môi trường hỗ trợ.
4. Đảm bảo React UI được bundle.
5. Đảm bảo backend local được đóng gói hoặc có hướng dẫn build backend binary.
6. Đảm bảo CloakBrowser binary path được cấu hình rõ.
7. Không hard-code path máy dev.
8. Tạo scripts:
   - npm run desktop:dev
   - npm run desktop:build
   - npm run desktop:dist

Output cần trả:
- File đã sửa.
- Build config.
- Scripts mới.
- Command build từng dòng.
- Output file expected.
- Test checklist sau khi cài app.
```

---

# TASK 4.13 — End-to-end test Phase 4

**Status:** Not Started  
**Depends on:** 4.12 Done

## Mục tiêu

Test toàn bộ desktop app trước khi dùng nội bộ.

## Checklist

| Test                           | Expected result                 |
| ------------------------------ | ------------------------------- |
| Mở app desktop                 | App window mở được              |
| Backend auto start             | Health check OK                 |
| Dashboard load                 | UI gọi API được                 |
| Tạo profile                    | Profile lưu được                |
| Launch Native                  | CloakBrowser mở cửa sổ thật     |
| Stop profile                   | Browser window đóng đúng        |
| Restart profile                | Browser mở lại đúng profile     |
| Quit app khi browser đang chạy | App hỏi user                    |
| Log                            | Có desktop/backend/browser logs |
| Restart app                    | Data profile còn                |
| Thiếu CloakBrowser binary      | Báo lỗi rõ                      |
| Không có Docker                | App vẫn chạy                    |

## Message prompt

```text
Bạn là senior QA engineer cho desktop app.

Bối cảnh bắt buộc:
- Dự án là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Phase 4 đã thêm desktop app Electron, backend local và native CloakBrowser launch.
- Cần test end-to-end trước khi dùng nội bộ.

Task:
TASK 4.13 — End-to-End Test Phase 4.

Yêu cầu:
1. Tạo checklist test desktop app.
2. Test app startup.
3. Test backend auto start.
4. Test UI gọi API.
5. Test tạo/sửa/xóa profile.
6. Test Launch Native mở CloakBrowser window thật.
7. Test Stop đóng đúng process.
8. Test Restart profile.
9. Test app quit khi browser còn chạy.
10. Test restart app data còn.
11. Test thiếu CloakBrowser binary.
12. Test máy không chạy Docker.
13. Ghi lỗi theo blocker/major/minor.
14. Không code trong task này trừ khi được yêu cầu.

Output cần trả:
- Test checklist.
- Expected result.
- Actual result template.
- Cách reproduce lỗi.
- Bảng phân loại lỗi.
- Kết luận có thể dùng nội bộ chưa.
```

---

## 5. Prompt khởi động triển khai Phase 4

Dùng prompt này khi muốn AI/dev bắt đầu cập nhật code Phase 4 bằng bước nhỏ đầu tiên.

```text
Bạn là senior full-stack desktop engineer có kinh nghiệm Electron, React, FastAPI, Python process management và desktop packaging.

Bối cảnh bắt buộc:
- Dự án này là tool nội bộ dựa trên CloakBrowser.
- Repo engine chính: https://github.com/CloakHQ/CloakBrowser
- Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
- Dự án chỉ dùng nội bộ, không thương mại hóa, không SaaS.
- Phase 1 đã chạy/test lõi CloakBrowser Manager.
- Phase 2 đã có web UI nội bộ cho profile/proxy/log/dashboard.
- Phase 3 có thể làm sau hoặc song song cho backup/resource.
- Phase 4 cần đóng gói desktop app riêng.
- Kết luận kỹ thuật: nên làm App desktop.
- Backend nên được bundle hoặc tự chạy local bên trong app.
- Luồng chính phải là mở CloakBrowser bằng native window thật.
- Browser core bắt buộc là CloakBrowser binary qua CLOAK_BROWSER_BINARY_PATH.
- Không dùng Chrome/Chromium thường.
- Không dùng noVNC làm mặc định.
- Không bắt user chạy Docker ở desktop final.
- Không tự viết lại toàn bộ app nếu tận dụng được code hiện có.

Task:
Bắt đầu triển khai Phase 4 theo từng bước nhỏ.

Phạm vi lần này:
1. Tạo Electron desktop workspace.
2. Load React UI trong Electron ở dev mode.
3. Thêm script chạy desktop dev.
4. Chuẩn bị cấu trúc để sau này start FastAPI backend local.
5. Không sửa browser launcher ở task đầu tiên.
6. Không xóa Docker/web mode hiện tại.
7. Không refactor lớn.

Output cần trả:
- Danh sách file đã tạo/sửa.
- Nội dung code thay đổi.
- Command cài package.
- Command chạy desktop dev.
- Cách kiểm tra app desktop mở được.
- Lỗi/rủi ro còn lại.
- Task tiếp theo nên làm.
```

---

## 6. Prompt build/run sau khi cập nhật Phase 4

```text
Bạn là senior release/devops engineer.

Bối cảnh:
Dự án là tool nội bộ dựa trên CloakBrowser đã được cập nhật Phase 4 Desktop App.
Repo engine chính: https://github.com/CloakHQ/CloakBrowser
Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager

Task:
Hướng dẫn build và chạy lại sau khi cập nhật Phase 4.

Yêu cầu:
1. Kiểm tra package.json scripts hiện tại.
2. Hướng dẫn cài dependencies.
3. Hướng dẫn build frontend.
4. Hướng dẫn chạy Electron desktop dev.
5. Nếu backend local chưa auto-start, hướng dẫn chạy backend riêng.
6. Nếu backend đã auto-start, hướng dẫn kiểm tra health check.
7. Hướng dẫn cấu hình CLOAK_BROWSER_BINARY_PATH.
8. Hướng dẫn build installer nếu đã cấu hình.
9. Command phải viết từng dòng riêng.
10. Có phần troubleshooting lỗi thường gặp.

Output cần trả:
- Lệnh cài dependencies.
- Lệnh chạy backend nếu cần.
- Lệnh chạy desktop dev.
- Lệnh build desktop.
- Cách set CLOAK_BROWSER_BINARY_PATH.
- Cách kiểm tra app hoạt động.
- Cách xem log.
- Cách xử lý lỗi port/backend/build/binary missing.
```

---

## 7. Thứ tự triển khai khuyến nghị

```text
4.1 Chốt kiến trúc
4.2 Tạo Electron workspace
4.3 Load React UI trong Electron
4.4 Bundle/start FastAPI backend local
4.5 App data path chuẩn
4.6 Detect/Configure CloakBrowser binary
4.7 Launch CloakBrowser native window
4.8 Stop/Restart native process
4.9 Loại noVNC khỏi luồng mặc định
4.10 Startup/shutdown lifecycle
4.11 Desktop logging
4.12 Build installer
4.13 End-to-end test
```

## 8. Điều kiện hoàn thành Phase 4

```text
Mở app desktop được
Backend local auto-start được
UI gọi API được
Tạo/sửa/xóa profile được
CLOAK_BROWSER_BINARY_PATH được cấu hình đúng
Bấm Launch Native mở CloakBrowser cửa sổ thật
Stop profile đóng đúng process
Restart profile hoạt động
noVNC không còn là mặc định
Quit app không để zombie process
Không cần Docker ở bản desktop final
Log lỗi xem được
Installer build được
```

## 9. Kết luận

Phase 4 nên làm App desktop riêng, nhưng trọng tâm không phải chỉ có “vỏ Electron”.

Trọng tâm thật là:

```text
App tự chạy backend
App quản lý data local
App dùng đúng CloakBrowser binary
Run Profile mở CloakBrowser native window
Stop/Restart process sạch
Không phụ thuộc Docker/noVNC ở bản final
```
