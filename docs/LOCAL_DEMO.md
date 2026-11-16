# ServiceHub — Chế độ Local Demo

## 1. Cấu hình môi trường

Tạo file `.env` từ `.env.example`.

```dotenv
SERVICEHUB_HOST=127.0.0.1
SERVICEHUB_PORT=8000
SERVICEHUB_ADMIN_EMAIL=admin@servicehub.local
SERVICEHUB_ADMIN_PASSWORD=YOUR_PRIVATE_PASSWORD
SERVICEHUB_LOCAL_DEMO=1
```

Thay mật khẩu mẫu bằng mật khẩu riêng có tối thiểu 16 ký tự.

## 2. Khởi động dự án

```bash
python3 server.py
```

Hệ thống khởi tạo:

- 1 Admin cá nhân.
- 3 Customer demo.
- 3 Owner demo.
- 3 cơ sở mẫu.
- 6 dịch vụ mẫu.

Tất cả sử dụng chung database `servicehub.db`.

## 3. Thông tin đăng nhập

Tài khoản Admin được cấu hình trong `.env`.

Thông tin đăng nhập của sáu tài khoản demo nằm trong `.local-demo/main-credentials.json`.

## 4. Kiểm thử tự động

```bash
python3 scripts/run_checks.py
```

Bộ kiểm thử sử dụng database tạm thời, độc lập với database local.

## 5. Bảo mật và triển khai

- Không commit mật khẩu, file `.env` hoặc database cá nhân.
- Không triển khai database chứa tài khoản demo lên production.
- Không đưa server demo ra Internet bằng proxy hoặc tunnel.
- Production phải sử dụng database riêng và `SERVICEHUB_LOCAL_DEMO=0`.
- Giữ `SERVICEHUB_LOCAL_DEMO=1` khi tiếp tục sử dụng database demo local.
- Script `scripts/local_demo.py` là phương thức demo độc lập cũ; không cần chạy khi sử dụng chế độ tích hợp mới.
