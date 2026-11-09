# Ghi chú nâng cấp ServiceHub

## Tính năng mới
1. Nhấn ảnh hoặc tên dịch vụ để xem chi tiết cơ sở kinh doanh.
2. Trang chi tiết hiển thị giới thiệu, địa chỉ, số điện thoại, bản đồ, dịch vụ/thực đơn, giá và ảnh riêng.
3. Chương trình hội viên được gắn với từng cơ sở; người dùng cần đăng nhập để tham gia.
4. Đăng ký hội viên được lưu trong SQLite và chống đăng ký trùng bằng ràng buộc dữ liệu hiện có.
5. Danh sách hội viên/điểm tiếp tục hiển thị trong khu vực Tài khoản.

## Kiểm tra đã thực hiện
- `python3 -m py_compile server.py`
- `node --check static/js/app.js`
- Bộ kiểm thử hiện có: 7/7 kiểm thử đạt sau khi chạy server cục bộ.

## Chạy trên macOS
Giải nén ZIP, mở thư mục `ServiceHub_fullstack` bằng VS Code và chạy `python3 server.py`, sau đó mở `http://localhost:8000`.


## Nâng cấp quản lý hội viên theo từng cơ sở
- Chủ cơ sở có thể cấu hình tên chương trình, mô tả, quyền lợi, điểm tích lũy, bật/tắt đăng ký và tự động xác nhận lịch đặt của hội viên.
- Khi khách đã tham gia chương trình của đúng cơ sở, các lịch đặt mới của khách tại cơ sở đó sẽ tự động ở trạng thái `confirmed` nếu chủ cơ sở bật tùy chọn. Khách không phải hội viên vẫn theo quy trình chờ xác nhận.
- Database tự thêm cột `benefits` và `auto_approve_bookings` khi khởi động, không cần xóa database cũ.
