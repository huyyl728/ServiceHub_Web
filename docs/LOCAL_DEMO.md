# ServiceHub – dữ liệu demo chỉ trên máy cá nhân

Dùng khi cần trình diễn tài khoản và chức năng đặt lịch. **Không dùng trên Render, hosting, mạng LAN công khai hoặc production.**

## Chạy demo

Mở Terminal tại gốc dự án:

```sh
python3 scripts/local_demo.py
```

Sau khi script khởi tạo, vào `http://127.0.0.1:8001`. Script tự sinh **3 Customer, 3 Owner, 1 Admin, 3 cơ sở và 6 dịch vụ** trên database độc lập `.local-demo/servicehub-demo.db`. Để xem email/mật khẩu riêng tư, mở file `.local-demo/credentials.json` **trên chính máy của bạn**. Không gửi file này cho người khác hoặc lên GitHub.

Chạy lại lệnh trên không sinh thêm tài khoản hoặc thay đổi mật khẩu. Dừng server bằng `Control + C`.

Nếu cổng 8001 đang được dùng:

```sh
python3 scripts/local_demo.py --port 8002
```

Nếu chỉ cần chuẩn bị dữ liệu, chưa chạy server:

```sh
python3 scripts/local_demo.py --setup-only
```

## Admin trong database thường (không phải demo)

Nếu đang chạy bằng `python3 server.py`, cấu hình Admin riêng bằng:

```sh
python3 scripts/setup_admin.py --email admin@servicehub.local
```

Script lưu mật khẩu mới tại `.env.admin` và cấu hình `.env` (chỉ máy local). Xem `docs/ADMIN_SETUP.md`. Đừng gửi file chứa mật khẩu lên chat, GitHub hoặc nơi công khai.

**Quan trọng:** Admin local trong `servicehub.db`, tài khoản của Docker Volume, tài khoản Render, và tài khoản ở `.local-demo/servicehub-demo.db` là **những database khác nhau**. Tạo tài khoản ở database này không tự làm nó xuất hiện ở database khác.

## Bảo vệ dữ liệu

- Không xóa `servicehub.db` hay Docker Volume để “sửa lỗi” đăng nhập: có thể mất lịch sử người dùng.
- Tài khoản demo cũ đã bị vô hiệu hóa; mật khẩu mới được sinh ngẫu nhiên, không khôi phục mật khẩu cũ.
- Mọi file `.local-demo/` và `.env*` (trừ `.env.example`) nằm trong `.gitignore`.
- Không chạy script trên máy chủ public; nó tự giới hạn địa chỉ `127.0.0.1`.
- Chạy `python3 scripts/run_checks.py` để kiểm tra backend và JavaScript.
