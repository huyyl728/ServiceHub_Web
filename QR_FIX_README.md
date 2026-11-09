# ServiceHub – Sửa lỗi nút Tạo QR

## Các vấn đề đã sửa

1. Python trước đây không tự nạp `.env`: chạy `python3 server.py` bỏ qua ngân hàng và vô hiệu hóa QR. Bản này đọc `.env` đặt cạnh `server.py` một cách an toàn và không ghi đè biến môi trường hiện có.
2. Giao diện trước đây chỉ nói “Chưa cấu hình”, nay hiển thị cụ thể tên biến thiếu/sai. Không hiển thị bí mật trong thông báo lỗi.
3. Tách việc tải lịch sử QR khỏi việc kiểm tra cấu hình để lỗi một phần không khóa toàn bộ màn hình.
4. Báo lỗi rõ khi ảnh Quick Link VietQR không tải được; yêu cầu vẫn ở trạng thái chờ.
5. Thêm bài kiểm thử xác minh `.env` được nạp khi chạy Python.

## Chạy trên MacBook

1. Giải nén, mở Terminal trong thư mục `ServiceHub_fullstack`.
2. `cp .env.example .env` nếu chưa có `.env`. Điền mã BIN, số tài khoản, tên thụ hưởng **trong file `.env` riêng trên MacBook**, bật `SERVICEHUB_ENABLE_BANK_QR=1` nếu bạn có quyền dùng tài khoản đó. Với VietinBank, BIN là `970415`.
3. Kiểm tra `SERVICEHUB_PORT=8001`, sau đó chạy `python3 server.py`.
4. Mở `http://127.0.0.1:8001` → Đăng nhập → Tài khoản → Tạo mã QR.
5. Nếu lỗi, đọc dòng `VietQR not configured:` trong Terminal hoặc thông báo ở khu vực QR trên web.

**Lưu ý:** QR có thể dẫn đến chuyển tiền thật nếu bạn điền tài khoản thật. Không chuyển tiền khi thử; tạo QR không xác nhận đã thanh toán.
