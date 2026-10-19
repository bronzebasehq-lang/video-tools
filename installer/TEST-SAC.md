# TEST SAC — SIVO Installer (Phase 3)

> **Mục đích:** xác nhận installer + app SIVO chạy được khi Smart App Control (SAC) đang BẬT.
> **Nguyên tắc:** KHÔNG tắt SAC. KHÔNG tắt bảo mật. Nếu test nào FAIL → dừng, chụp ảnh, báo Rio — không tự tìm cách vòng qua.
> **Người test:** Minh, trên máy Windows của Minh, SAC bật.

## 0. Trước khi test: xác nhận SAC đang BẬT

1. Mở **Settings** → **Privacy & security** → **Windows Security** → **App & browser control**.
2. Bạn sẽ thấy mục **Smart App Control**. Nó phải hiện **On**.
3. Nếu nó hiện **Off** → báo Rio trước khi test (không tự bật/tắt gì — chỉ báo).

## 1. Test 1 — Double-click installer

1. Double-click file **`SIVO-Setup.exe`** (file installer Rio giao).
2. **Bạn sẽ thấy gì:** có thể hiện cửa sổ SmartScreen màu xanh: *"Windows protected your PC"* + *"Microsoft Defender SmartScreen prevented an unrecognized app from starting"*.
   - Đây là **BÌNH THƯỜNG** (installer chưa có chữ ký) — **KHÔNG phải FAIL.**
   - Bấm **"More info"** → bấm **"Run anyway"**.
3. Tiếp theo hiện màn hình chọn thư mục cài (mặc định `%LOCALAPPDATA%\Programs\SIVO`). Giữ nguyên → bấm **Install**.
4. Bạn sẽ thấy thanh tiến trình chạy (giải nén + cài Python lặng lẽ). Chờ tới màn hình **Finish**.
5. Bấm **Finish** (để tick "Run SIVO" — app sẽ tự mở).

| Kết quả | Nghĩa |
|---|---|
| Cài xong tới Finish | **PASS** |
| Hiện thông báo **Smart App Control chặn**, **KHÔNG có nút "Run anyway"** | **FAIL** — chụp ảnh toàn màn hình gửi Rio, dừng test |

## 2. Test 2 — Mở app

1. Nếu app chưa tự mở sau Finish: double-click shortcut **SIVO** trên Desktop.
2. **Bạn sẽ thấy gì:** cửa sổ **"SIVO — Script In, Video Out"** với 4 mục (ô script, chọn template, tên kênh, nút Render). **KHÔNG có cửa sổ đen (terminal) nào hiện.**

| Kết quả | Nghĩa |
|---|---|
| Cửa sổ GUI mở bình thường | **PASS** |
| SAC chặn (báo tên file nào đó bị chặn, vd `pythonw.exe` / `node.exe` / `chrome-headless-shell.exe`) | **FAIL** — chụp ảnh (ghi rõ tên file bị chặn) gửi Rio |

## 3. Test 3 — Giọng SAPI (voice)

1. Trong GUI, để nguyên script mẫu (hoặc dán script của bạn, 1 câu/dòng) → bấm **Render**.
2. **Bạn sẽ thấy gì:** dòng trạng thái đổi thành **"Reading voice…"** (đang đọc giọng), sau đó chuyển thành **"Building visuals…"** (đang dựng hình).
3. Chuyển từ "Reading voice…" sang "Building visuals…" = giọng đã tạo xong.

| Kết quả | Nghĩa |
|---|---|
| Chuyển sang "Building visuals…" | **PASS** |
| Hiện lỗi *"Voice could not be created…"* | **FAIL** — chụp ảnh lỗi gửi Rio |

## 4. Test 4 — Render video

1. Tiếp tục chờ (không bấm gì). Thanh tiến trình chạy.
2. **Bạn sẽ thấy gì:** trạng thái đổi thành **"Done!"** + nút **"Open video"** sáng lên + dòng *"Saved to: …\sivo.mp4"*.

| Kết quả | Nghĩa |
|---|---|
| "Done!" + mở được video | **PASS** |
| SAC chặn (báo `node.exe` / `chrome-headless-shell.exe` / `ffmpeg.exe` bị chặn) hoặc render crash | **FAIL** — chụp ảnh gửi Rio |

## 5. Test 5 — Full flow với script + brand của bạn

1. Bấm **"Open video"** → video mở ra. Kiểm tra: **nghe được giọng**, **thấy chữ**, **thấy badge tên kênh của bạn ở trên** (nếu bạn đã nhập tên kênh ở mục 3).
2. Dán script mới của bạn + nhập tên kênh của bạn → bấm **Render** → chờ "Done!" → mở video → kiểm tra video có đúng như mong muốn không.

| Kết quả | Nghĩa |
|---|---|
| Video coi được, có giọng, có badge tên kênh | **PASS** |
| Bất kỳ bước nào chặn / lỗi | **FAIL** — ghi rõ bước nào + chụp ảnh |

## Phân biệt SmartScreen vs SAC (quan trọng)

| Hiện tượng | Là gì | Xử lý |
|---|---|---|
| Cửa sổ xanh *"Windows protected your PC"* + có nút **"Run anyway"** | **SmartScreen** (cảnh báo app chưa có chữ ký) | BÌNH THƯỜNG. Bấm "Run anyway", tiếp tục test. |
| Thông báo **Smart App Control đã chặn** + **KHÔNG có nút "Run anyway"** | **SAC chặn cứng** | **FAIL.** Chụp ảnh, dừng test, báo Rio. |

## Báo lại cho Rio (sau khi test xong hoặc khi gặp FAIL đầu tiên)

1. Test nào PASS / FAIL (ghi theo số: Test 1…5).
2. Nếu FAIL: ở test nào + chụp ảnh thông báo (quan trọng nhất: **tên file nào bị chặn**).
3. Thời gian: cài mất bao lâu? Render video 60s mất bao lâu?
4. Video có đúng như mong muốn không (giọng, chữ, badge)?

## Gỡ cài đặt (nếu muốn)

Settings → Apps → Installed apps → **SIVO** → Uninstall. Hoặc Start Menu → SIVO → Uninstall SIVO.
