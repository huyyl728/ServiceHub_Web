# ServiceHub – demo tích hợp trong ứng dụng

Chỉ dùng trên máy cá nhân qua localhost. Không bật trên Docker, Render, hosting, LAN công khai, production; không đưa server demo qua reverse proxy hoặc tunnel.

## Một lệnh chạy

Tại gốc repo:

```sh
python3 server.py --local-demo
```

Hoặc `./start-mac.command --local-demo`. Mặc định dùng cổng 8000; `.env` có thể đặt cổng 8001. Luôn mở địa chỉ được Terminal thông báo sau khi khởi động thành công. Nếu cổng đã dùng:

```sh
python3 server.py --local-demo --port 8002
```

Không cần chạy script seed/setup riêng. Lần đầu tạo **1 Admin, 3 Customer, 3 Owner, 3 cơ sở và 6 dịch vụ**, dùng ảnh SVG đã có trong repo. Các Owner đã được duyệt và mỗi người có một cơ sở. Mọi tài khoản dùng form Email/Mật khẩu hiện có.

Email và mật khẩu riêng của mỗi tài khoản nằm tại `.local-demo/credentials.json`. Mở file đó bằng trình soạn thảo trên máy; không copy lên chat, issue, log hoặc GitHub. Không có mật khẩu dùng chung, không in mật khẩu ra Terminal, không có endpoint web cung cấp mật khẩu. Mật khẩu trong SQLite được băm như tài khoản thường.

## Chạy bằng nút Run hoặc lệnh thông thường

Trong `.env` riêng trên máy (không commit):

```dotenv
SERVICEHUB_ENV=local-demo
SERVICEHUB_HOST=127.0.0.1
SERVICEHUB_PORT=8001
```

Sau đó chạy `python3 server.py`, nút Run của trình soạn thảo, hoặc `./start-mac.command`. Biến môi trường của tiến trình ưu tiên hơn `.env`; `--port` ưu tiên hơn cấu hình cổng. Không đặt `SERVICEHUB_DB_PATH` cho demo. Cấu hình Admin thường nếu có được bỏ qua ở demo và không được sao chép vào DB demo.

Để về chế độ thường, bỏ dòng `SERVICEHUB_ENV=local-demo` và bỏ cờ `--local-demo`. Chế độ thường dùng database/config Admin riêng; xem [ADMIN_SETUP.md](ADMIN_SETUP.md). `SERVICEHUB_ENV=production python3 server.py` có thể ghi đè `.env`, nhưng tuyệt đối không kèm `--local-demo`.

## Giữ dữ liệu và chuyển từ PR #43

- DB demo: `.local-demo/servicehub-demo.db`; thông tin đăng nhập: `.local-demo/credentials.json`.
- Chạy lại giữ nguyên mật khẩu, phiên đăng nhập, lịch đặt và thay đổi cơ sở; không tự khôi phục quyền hoặc mở lại tài khoản bị khóa.
- Dữ liệu đúng định dạng do `scripts/local_demo.py` của PR #43 đã tạo được dùng lại trực tiếp tại cùng thư mục. Script cũ đã được loại bỏ; dùng lệnh trên.
- DB thường `servicehub.db`, Docker volume và Render độc lập với DB demo. Chế độ thường cũng từ chối DB có dấu nhận diện demo, kể cả khi bị sao chép sang đường dẫn khác.
- `.local-demo/` bị loại khỏi Git và Docker build context. Trên macOS/Linux, thư mục là `0700`, DB và file mật khẩu là `0600`. Trên Windows, kiểm tra thêm quyền truy cập thư mục của tài khoản hệ điều hành.
- Server chỉ bind `127.0.0.1`, từ chối cấu hình host public, môi trường production/staging hoặc hosting được nhận diện. Request với Host/Origin ngoài localhost hoặc header chuyển tiếp proxy bị từ chối. Các kiểm tra này không thay thế yêu cầu tuyệt đối không triển khai/chuyển tiếp demo lên Internet.

## Khi khởi động báo lỗi

- **Cổng bận:** chọn `--port 8002` (hoặc cổng trống khác); không cần tắt tiến trình không rõ nguồn gốc. Server kiểm tra cổng trước khi tạo dữ liệu.
- **DB/file mật khẩu thiếu, sai định dạng hoặc không khớp:** server dừng, không ghi đè để “sửa”. Dừng mọi tiến trình demo, sao lưu cả `.local-demo/` vào nơi riêng tư và kiểm tra. Không xóa DB thật hay Docker volume.
- **Quyền file quá rộng:** trên macOS/Linux, sau khi xác minh file thuộc về bạn, dùng `chmod 700 .local-demo` và `chmod 600 .local-demo/credentials.json .local-demo/servicehub-demo.db`.
- **Khóa khởi tạo còn lại sau khi tiến trình bị dừng đột ngột:** xác nhận không còn tiến trình demo đang khởi tạo rồi dùng `rmdir .local-demo/.startup-lock`. Nếu còn dữ liệu khởi tạo dang dở, xử lý như trường hợp không khớp ở trên.
- Nếu không cần giữ dữ liệu demo cũ, dừng server và đổi tên cả thư mục `.local-demo/` sang một nơi sao lưu riêng **bên ngoài repo**, rồi chạy lại để tạo bộ mới. Không có thao tác tự reset dữ liệu.

## Kiểm thử

```sh
python3 scripts/run_checks.py
```

Bộ kiểm thử dùng SQLite tạm, cưỡng chế chế độ test để không kế thừa demo từ `.env`. Kiểm tra đủ 7 lần đăng nhập, phân quyền Admin/Customer/Owner, đặt/xác nhận lịch, khởi động lại, quyền file, bảo vệ DB thường, các cấu hình bị từ chối và JavaScript. Node.js chỉ cần cho kiểm thử JavaScript.
