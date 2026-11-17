# ServiceHub — Chế độ Local Demo

## 1. Yêu cầu và khởi chạy nhanh

Cần Python 3.10 trở lên và trình duyệt. Không cần cài thư viện, npm hay Docker.

Clone repository và mở Terminal tại thư mục ServiceHub_Web.

**macOS/Linux:**

```bash
python3 scripts/start_demo.py
```

**Windows (PowerShell):**

```powershell
py -3 scripts/start_demo.py
```

Nếu không có lệnh `py` nhưng có `python`, dùng `python scripts/start_demo.py`.

Có thể dùng `./start-mac.command` trên macOS hoặc mở `start-windows.bat` trên Windows. Truy cập URL được in trong Terminal (mặc định http://127.0.0.1:8001). Ctrl+C để dừng.

## 2. Dữ liệu và đăng nhập

Lần đầu script tự tạo .env với mật khẩu Admin ngẫu nhiên, gọi chính schema/migration và hàm seed demo của server.py để tạo database servicehub.db, 1 Admin, 3 Customer, 3 Owner, 3 cơ sở và 6 dịch vụ. Không cần chạy setup_admin.py.

- Admin: thông tin cả email và mật khẩu nằm trong file .env.
- Customer và Owner: thông tin đăng nhập nằm trong .local-demo/main-credentials.json.
- Mở file trên máy cá nhân; không gửi mật khẩu lên chat hoặc commit các file này.
- Khi khởi chạy lại, script dùng database và cấu hình demo hiện có, không đặt lại mật khẩu hay xóa lịch đặt/đánh giá.

Mỗi clone mới có một database demo độc lập với mật khẩu riêng. Đây không phải đồng bộ database giữa nhiều máy; dữ liệu phát sinh trên một máy không tự xuất hiện trên máy khác.

## 3. Xử lý lỗi

- Cổng đang bận: dừng tiến trình ServiceHub cũ hoặc chạy `python3 scripts/start_demo.py --port 8002` (Windows: thay python3 bằng py -3).
- Có .env cấu hình không phải demo, database không có dấu demo tích hợp, hoặc thiếu file cấu hình tương ứng: script dừng thay vì ghi đè dữ liệu. Giữ nguyên thư mục hiện tại và dùng một bản clone sạch; nếu có bản sao lưu demo thì khôi phục cả database lẫn cấu hình phù hợp.
- Có biến SERVICEHUB_* ghi đè cấu hình: mở terminal local không có các biến ghi đè đó.
- Chỉ khởi tạo/kiểm tra, không mở server: thêm `--setup-only`.
- Nếu trước đây chạy `scripts/local_demo.py`, đó là demo độc lập cũ trong .local-demo/servicehub-demo.db. Script mới không di chuyển hoặc ghi đè database cũ.

## 4. Kiểm thử

```bash
python3 scripts/run_checks.py
```

Bộ test tự kiểm tra trên bản sao mã nguồn trong thư mục tạm, không xóa database local.

## 5. Bảo mật và triển khai

- Demo chỉ chạy trên 127.0.0.1, không dùng proxy/tunnel công khai; cơ chế bảo vệ demo của server.py vẫn được áp dụng.
- Không commit .env, .env.admin, .local-demo, database hoặc uploads riêng tư.
- Trên Windows, quyền truy cập file phụ thuộc ACL hệ điều hành; giữ thư mục clone trong tài khoản cá nhân, không đặt trong thư mục dùng chung.
- Production/Render tiếp tục dùng lệnh khởi động server.py, database riêng và SERVICEHUB_LOCAL_DEMO=0; không dùng script start_demo.py.

Xem [cấu hình Admin riêng](ADMIN_SETUP.md) nếu cần khởi tạo tài khoản quản trị cho môi trường thường, không phải demo.
