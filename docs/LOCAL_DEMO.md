# ServiceHub — Chế độ Local Demo

## 1. Yêu cầu và khởi chạy nhanh

Cần Python 3.10 trở lên và trình duyệt. Không cần cài thư viện, npm hay Docker.

Clone repository và mở Terminal tại thư mục ServiceHub_Web.

**macOS/Linux:**

```bash
python3 server.py
```

**Windows (PowerShell):**

```powershell
py -3 server.py
```

Nếu không có lệnh `py` nhưng có `python`, dùng `python server.py`.

Có thể dùng `./start-mac.command` trên macOS hoặc mở `start-windows.bat` trên Windows. Truy cập URL được in trong Terminal (mặc định http://127.0.0.1:8001). Ctrl+C để dừng.

## 2. Dữ liệu và đăng nhập

Khi chạy server.py từ bản clone sạch, chưa có .env, database, cấu hình Admin hoặc biến SERVICEHUB_* ghi đè, server tự tạo .env với tài khoản Admin mẫu cố định, gọi chính schema/migration và hàm seed demo của server.py để tạo database servicehub.db, 1 Admin, 3 Customer, 3 Owner, 3 cơ sở và 6 dịch vụ. Không cần chạy setup_admin.py.

- Admin mặc định cho mọi bản clone sạch: `admin@servicehub.local` / `ServiceHub-Local-2026!`. Đây là tài khoản mẫu công khai chỉ dành cho demo localhost; giá trị cũng được tạo trong `.env`.
- Customer và Owner: thông tin đăng nhập nằm trong .local-demo/main-credentials.json.
- Mở file trên máy cá nhân; không gửi mật khẩu lên chat hoặc commit các file này.
- Khi khởi chạy lại, server dùng database và cấu hình demo hiện có, không đặt lại mật khẩu hay xóa lịch đặt/đánh giá.

Mỗi clone mới có database demo độc lập và dùng cùng thông tin đăng nhập Admin mẫu; mật khẩu Customer/Owner vẫn riêng theo bản clone. Đây không phải đồng bộ database giữa nhiều máy; dữ liệu phát sinh trên một máy không tự xuất hiện trên máy khác.

### Chuyển bản demo đã clone từ PR cũ sang tài khoản chung

Dừng server, sao lưu `.env` và `servicehub.db` trên máy. Nếu đang dùng database demo tích hợp và muốn chuyển sang Admin mặc định, chỉnh đúng hai biến Admin trong `.env` (giữ `SERVICEHUB_LOCAL_DEMO=1`, `SERVICEHUB_HOST=127.0.0.1` và các cấu hình khác):

```dotenv
SERVICEHUB_ADMIN_EMAIL=admin@servicehub.local
SERVICEHUB_ADMIN_PASSWORD=ServiceHub-Local-2026!
```

Chạy lại `server.py`. Nếu Admin đang có cùng email, hệ thống cập nhật hash mật khẩu và thu hồi phiên cũ, giữ nguyên lịch đặt và dữ liệu. Không tự ghi đè `.env` tùy chỉnh của các máy đã cấu hình. Không thực hiện bước này trên database thật hoặc môi trường triển khai.

## 3. Xử lý lỗi

- Cổng đang bận: dừng tiến trình ServiceHub cũ hoặc chạy `python3 server.py --port 8002` (Windows: thay python3 bằng py -3).
- Có .env hoặc database hiện hữu: server không tự tạo lại cấu hình demo; khởi chạy theo cấu hình hiện tại. Nếu database demo thiếu cấu hình phù hợp, cơ chế bảo vệ của server từ chối khởi động. Giữ nguyên thư mục và khôi phục bản sao lưu hoặc dùng clone sạch nếu muốn dữ liệu mẫu mới.
- Có biến SERVICEHUB_* ghi đè cấu hình: server ưu tiên biến môi trường và không tự bật demo.
- Chỉ khởi tạo/kiểm tra, không mở server: thêm `--setup-only`.
- Nếu trước đây chạy `scripts/local_demo.py`, đó là demo độc lập cũ trong .local-demo/servicehub-demo.db. Server không di chuyển hoặc ghi đè database demo độc lập cũ.

## 4. Kiểm thử

```bash
python3 scripts/run_checks.py
```

Bộ test tự kiểm tra trên bản sao mã nguồn trong thư mục tạm, không xóa database local.

## 5. Bảo mật và triển khai

- Demo chỉ chạy trên 127.0.0.1, không dùng proxy/tunnel công khai; cơ chế bảo vệ demo của server.py vẫn được áp dụng.
- Không commit .env, .env.admin, .local-demo, database hoặc uploads riêng tư.
- Trên Windows, quyền truy cập file phụ thuộc ACL hệ điều hành; giữ thư mục clone trong tài khoản cá nhân, không đặt trong thư mục dùng chung.
- Production/Render tiếp tục dùng lệnh khởi động server.py, database riêng, mật khẩu Admin riêng tư và SERVICEHUB_LOCAL_DEMO=0. Server từ chối mật khẩu Admin mẫu bên ngoài demo local và từ chối database đã chứa Admin mẫu kể cả khi seed demo chưa hoàn tất.

Xem [cấu hình Admin riêng](ADMIN_SETUP.md) nếu cần khởi tạo tài khoản quản trị cho môi trường thường, không phải demo.
