# 05 — RUN APP & SYSTEM TEST

## Mục tiêu

Sau Phase 4, bước này dùng để:

```text
Build app
→ Start app
→ Kiểm tra backend auto-start
→ Kiểm tra UI gọi API
→ Test từng chức năng
→ Ghi pass/fail
→ Ghi log lỗi
→ Quay lại đúng task để fix
```

Không thêm tính năng mới trong bước này.

---

## Điều kiện trước khi test

| Điều kiện | Bắt buộc |
|---|---|
| Electron app đã có | Có |
| React UI load trong Electron | Có |
| Backend FastAPI local/bundled | Có |
| `CLOAK_BROWSER_BINARY_PATH` đã cấu hình | Có |
| CloakBrowser binary tồn tại | Có |
| App Data Path ghi được | Có |
| Logs hoạt động | Có |
| Docker không bắt buộc trong desktop final | Có |

---

## Test flow tổng thể

```text
RT.1 Preflight check
RT.2 Build app
RT.3 Start app
RT.4 Backend health check
RT.5 Profile CRUD
RT.6 Proxy Manager/Checker
RT.7 CloakBrowser Native Launch
RT.8 Stop/Restart native process
RT.9 noVNC default removal
RT.10 App shutdown cleanup
RT.11 Logs & error handling
RT.12 System test report
```

---

# RT.1 — Preflight Check

**Status:** Ready

## Mục tiêu

Kiểm tra môi trường trước khi chạy app.

## Checklist

- Kiểm tra Node/npm.
- Kiểm tra Python nếu backend chưa bundle.
- Kiểm tra scripts trong `package.json`.
- Kiểm tra `CLOAK_BROWSER_BINARY_PATH`.
- Kiểm tra CloakBrowser binary có tồn tại.
- Kiểm tra quyền ghi App Data Path.
- Kiểm tra port backend có bị chiếm không.

## Message prompt

```text
Bạn là senior QA/devops engineer.

Bối cảnh:
Dự án là desktop app nội bộ dựa trên CloakBrowser.
Repo engine chính: https://github.com/CloakHQ/CloakBrowser
Repo app quản lý profile: https://github.com/CloakHQ/CloakBrowser-Manager
Phase 4 đã phát triển Electron + React UI + FastAPI backend local + CloakBrowser native window.

Task:
RT.1 — Preflight Check.

Yêu cầu:
1. Kiểm tra Node/npm version.
2. Kiểm tra Python version nếu backend chưa bundle.
3. Kiểm tra package.json scripts.
4. Kiểm tra backend requirements.
5. Kiểm tra CLOAK_BROWSER_BINARY_PATH.
6. Kiểm tra CloakBrowser binary tồn tại và có quyền execute.
7. Kiểm tra App Data Path có quyền ghi.
8. Kiểm tra port backend.
9. Không sửa code nếu chưa cần, chỉ báo lỗi rõ.

Output:
- Preflight checklist.
- Command kiểm tra từng dòng.
- Expected result.
- Lỗi phát hiện nếu có.
- Cách fix đề xuất.
```

---

# RT.2 — Build App

**Status:** Not Started  
**Depends on:** RT.1 Pass

## Message prompt

```text
Bạn là senior release engineer.

Task:
RT.2 — Build App.

Yêu cầu:
1. Kiểm tra scripts hiện tại trong package.json.
2. Cài dependencies nếu cần.
3. Build React frontend.
4. Build backend nếu dùng PyInstaller.
5. Build Electron desktop app nếu đã cấu hình.
6. Không bỏ qua lỗi TypeScript.
7. Command phải viết từng dòng riêng.

Output:
- Command cài dependencies.
- Command build frontend.
- Command build backend.
- Command build desktop app.
- Build output path.
- Lỗi nếu có.
- Cách fix nếu build fail.
```

---

# RT.3 — Start App

**Status:** Not Started  
**Depends on:** RT.2 Pass

## Message prompt

```text
Bạn là senior desktop QA engineer.

Task:
RT.3 — Start App.

Yêu cầu:
1. Hướng dẫn chạy desktop app ở dev mode.
2. Nếu có installer/build output, hướng dẫn chạy bản build.
3. Xác nhận Electron window mở được.
4. Xác nhận UI không blank page.
5. Xác nhận console không có lỗi nghiêm trọng.
6. Nếu app không mở, đọc desktop logs và phân loại lỗi.

Output:
- Command chạy app.
- Cách mở app build.
- Expected result.
- Cách xem log Electron.
- Lỗi thường gặp và cách xử lý.
```

---

# RT.4 — Backend Auto-start & Health Check

**Status:** Not Started  
**Depends on:** RT.3 Pass

## Checklist

| Test | Expected |
|---|---|
| App mở | Backend auto-start |
| Health endpoint | Trả OK |
| UI gọi API | Không lỗi connection refused |
| App quit | Backend stop |

## Message prompt

```text
Bạn là senior backend/desktop QA engineer.

Task:
RT.4 — Backend Auto-start & Health Check.

Yêu cầu:
1. Mở app desktop.
2. Kiểm tra backend process có chạy không.
3. Gọi health endpoint.
4. Kiểm tra UI gọi API được.
5. Tắt app và kiểm tra backend process đã dừng.
6. Nếu backend fail, đọc stdout/stderr logs.
7. Phân loại lỗi: port conflict, missing dependency, permission, app data path, unknown.

Output:
- Cách kiểm tra backend process.
- Health endpoint result.
- Log path.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.5 — Profile CRUD Test

**Status:** Not Started  
**Depends on:** RT.4 Pass

## Checklist

| Test | Expected |
|---|---|
| Create profile | Profile xuất hiện |
| Edit profile | Dữ liệu cập nhật |
| Delete profile | Profile biến mất |
| Delete running profile | Bị chặn/cảnh báo |
| Restart app | Profile vẫn còn |

## Message prompt

```text
Bạn là senior QA engineer.

Task:
RT.5 — Profile CRUD Test.

Yêu cầu:
1. Tạo profile mới.
2. Sửa profile.
3. Xóa profile.
4. Test xóa profile đang running nếu có.
5. Restart app và kiểm tra profile còn.
6. Kiểm tra database/app data có lưu đúng.
7. Kiểm tra activity logs.

Output:
- Test cases.
- Expected result.
- Actual result template.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.6 — Proxy Manager & Proxy Checker Test

**Status:** Not Started  
**Depends on:** RT.5 Pass

## Checklist

| Test | Expected |
|---|---|
| Add proxy | Proxy lưu được |
| Edit proxy | Proxy cập nhật |
| Check valid proxy | Status OK |
| Check invalid proxy | Báo lỗi rõ |
| Assign proxy | Profile lưu proxy_id |
| Secret logging | Không lộ password/token |

## Message prompt

```text
Bạn là senior QA engineer có kinh nghiệm network/proxy debugging.

Task:
RT.6 — Proxy Manager & Proxy Checker Test.

Yêu cầu:
1. Thêm proxy mới.
2. Sửa proxy.
3. Gắn proxy vào profile.
4. Check proxy hợp lệ.
5. Check proxy sai auth/timeout nếu có dữ liệu test.
6. Đảm bảo không log proxy password/token.
7. Kiểm tra error codes:
   - PROXY_OK
   - PROXY_AUTH_FAILED
   - PROXY_TIMEOUT
   - PROXY_CONNECTION_FAILED

Output:
- Test checklist.
- Expected result.
- Actual result template.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.7 — CloakBrowser Native Launch Test

**Status:** Not Started  
**Depends on:** RT.5 Pass + `CLOAK_BROWSER_BINARY_PATH` configured

## Checklist

| Test | Expected |
|---|---|
| Binary path tồn tại | OK |
| Launch profile | CloakBrowser mở cửa sổ thật |
| Launch duplicate | Không tạo process trùng |
| User data dir riêng | Data nằm đúng folder |
| Status update | Profile chuyển running |
| Missing binary | Báo `CLOAK_BROWSER_BINARY_NOT_FOUND` |

## Message prompt

```text
Bạn là senior QA/process engineer.

Bối cảnh:
Desktop app phải launch profile bằng CloakBrowser native window thật. Không dùng noVNC làm luồng chính.

Task:
RT.7 — CloakBrowser Native Launch Test.

Yêu cầu:
1. Kiểm tra CLOAK_BROWSER_BINARY_PATH.
2. Kiểm tra binary tồn tại và có quyền execute.
3. Tạo hoặc chọn một profile test.
4. Bấm Launch Native/Run Profile.
5. Xác nhận CloakBrowser mở bằng cửa sổ thật trên OS.
6. Kiểm tra profile status = running.
7. Kiểm tra PID/process_id được lưu.
8. Test launch trùng cùng profile.
9. Test thiếu binary path để xem lỗi có rõ không.
10. Không dùng Chrome/Chromium thường.

Output:
- Test checklist.
- Browser command nếu log có.
- Expected result.
- Actual result template.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.8 — Stop/Restart Native Process Test

**Status:** Not Started  
**Depends on:** RT.7 Pass

## Message prompt

```text
Bạn là senior QA/process engineer.

Task:
RT.8 — Stop/Restart Native Process Test.

Yêu cầu:
1. Launch một profile native.
2. Stop profile và kiểm tra browser window đóng.
3. Kiểm tra PID không còn sống.
4. Restart profile và kiểm tra browser mở lại.
5. Kill process thủ công rồi kiểm tra app cập nhật status.
6. Kiểm tra logs:
   - BROWSER_NATIVE_STOPPED
   - BROWSER_NATIVE_STOP_FAILED
   - BROWSER_NATIVE_RESTARTED

Output:
- Test checklist.
- Expected result.
- Actual result.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.9 — noVNC Default Removal Test

**Status:** Not Started  
**Depends on:** RT.7 Pass

## Message prompt

```text
Bạn là senior QA/full-stack engineer.

Task:
RT.9 — noVNC Default Removal Test.

Yêu cầu:
1. Mở app desktop.
2. Bấm Run Profile.
3. Xác nhận app mở CloakBrowser native window, không mở noVNC viewer.
4. Kiểm tra UI không còn ưu tiên nút Open VNC.
5. Nếu còn noVNC, xác nhận nó chỉ là option phụ/debug.
6. Nếu desktop mode vẫn phụ thuộc noVNC, mark fail.

Output:
- Test checklist.
- Expected result.
- Actual result.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.10 — App Shutdown & Cleanup Test

**Status:** Not Started  
**Depends on:** RT.8 Pass

## Message prompt

```text
Bạn là senior desktop QA engineer.

Task:
RT.10 — App Shutdown & Cleanup Test.

Yêu cầu:
1. Test quit app khi không có profile running.
2. Test quit app khi có 1–3 profile running.
3. Kiểm tra dialog:
   - Stop all and quit
   - Keep browsers running
   - Cancel
4. Kiểm tra backend process sau khi quit.
5. Kiểm tra CloakBrowser process sau từng lựa chọn.
6. Kiểm tra không có zombie process.
7. Kiểm tra logs app quit.

Output:
- Test checklist.
- Expected result.
- Actual result.
- Process list sau khi quit.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.11 — Logs & Error Handling Test

**Status:** Not Started  
**Depends on:** RT.4 + RT.7 Pass

## Message prompt

```text
Bạn là senior QA engineer.

Task:
RT.11 — Logs & Error Handling Test.

Yêu cầu:
1. Kiểm tra log path.
2. Test backend startup log.
3. Test app data path log.
4. Test CLOAK_BROWSER_BINARY_PATH log.
5. Test missing binary error.
6. Test launch browser failed.
7. Test proxy error nếu có.
8. Đảm bảo không log password/token/proxy secret.
9. UI phải hiển thị lỗi dễ hiểu.

Output:
- Log files kiểm tra.
- Error cases.
- Expected result.
- Actual result.
- Pass/fail.
- Bug report nếu fail.
```

---

# RT.12 — System Test Report

**Status:** Not Started  
**Depends on:** RT.1 → RT.11 completed

## Message prompt

```text
Bạn là senior QA lead.

Task:
RT.12 — System Test Report.

Yêu cầu:
1. Tổng hợp pass/fail theo từng nhóm chức năng.
2. Phân loại lỗi:
   - Blocker
   - Major
   - Minor
3. Map lỗi về task cần fix:
   - Electron startup → Task 4.2/4.3
   - Backend auto-start → Task 4.4
   - App data path → Task 4.5
   - CloakBrowser binary → Task 4.6
   - Native launch → Task 4.7
   - Stop/restart process → Task 4.8
   - noVNC default → Task 4.9
   - Shutdown cleanup → Task 4.10
   - Logging → Task 4.11
   - Installer → Task 4.12
4. Đưa kết luận:
   - Ready for internal beta
   - Needs fixes
   - Blocked
5. Không code trong task này.

Output:
- System test report.
- Pass/fail table.
- Bug table.
- Fix priority.
- Release recommendation.
```

---

## Command mẫu

> Lệnh thực tế có thể khác tùy repo sau khi dev cập nhật. Luôn kiểm tra `package.json`.

```bash
npm install
```

```bash
npm run build
```

```bash
npm run desktop:dev
```

```bash
npm run desktop:build
```

```bash
npm run desktop:dist
```

macOS/Linux:

```bash
export CLOAK_BROWSER_BINARY_PATH="/absolute/path/to/CloakBrowser"
```

Windows PowerShell:

```powershell
$env:CLOAK_BROWSER_BINARY_PATH="C:\Path\To\CloakBrowser.exe"
```

---

## Tiêu chí app được xem là chạy được

```text
App desktop mở được
Backend auto-start được
UI gọi API được
Tạo/sửa/xóa profile được
Proxy manager/checker chạy được
CLOAK_BROWSER_BINARY_PATH đúng
Run Profile mở CloakBrowser native window thật
Stop/Restart profile đúng process
noVNC không còn mặc định
Quit app không để process rác
Logs ghi rõ lỗi
Không cần Docker ở bản desktop final
```
