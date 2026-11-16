# S4R-08 — Báo cáo kiểm thử tích hợp và nghiệm thu Sprint 4

## 1. Mục tiêu

Kiểm thử toàn bộ luồng nghiệp vụ ServiceHub sau khi hoàn thiện Sprint 4, đảm bảo sự liên kết giữa Frontend, Backend và Database.

## 2. Phạm vi kiểm thử

- Đăng nhập và phân quyền Customer, Owner, Admin.
- Tìm kiếm dịch vụ.
- Đặt lịch không yêu cầu thanh toán.
- Xác nhận và hoàn thành lịch đặt.
- Viết và chỉnh sửa đánh giá.
- Hiển thị điểm sao và bình luận.
- Kiểm duyệt đánh giá.
- Thống kê chi tiết từng cơ sở.
- Kiểm thử hồi quy các chức năng hiện có.

## 3. Kết quả kiểm thử

| Mã   | Nội dung kiểm thử               | Kết quả |
| ---- | ------------------------------- | ------- |
| TC01 | Đăng nhập và xác thực           | PASS    |
| TC02 | Tìm kiếm dịch vụ                | PASS    |
| TC03 | Đặt lịch không thanh toán       | PASS    |
| TC04 | Owner xác nhận lịch đặt         | PASS    |
| TC05 | Owner hoàn thành lịch đặt       | PASS    |
| TC06 | Customer tạo đánh giá           | PASS    |
| TC07 | Ngăn đánh giá trùng             | PASS    |
| TC08 | Chỉnh sửa đánh giá cá nhân      | PASS    |
| TC09 | Hiển thị đánh giá công khai     | PASS    |
| TC10 | Admin ẩn đánh giá               | PASS    |
| TC11 | Admin khôi phục đánh giá        | PASS    |
| TC12 | Thống kê chi tiết cơ sở         | PASS    |
| TC13 | Lọc thống kê theo thời gian     | PASS    |
| TC14 | Đối chiếu thống kê với SQLite   | PASS    |
| TC15 | Đồng bộ thống kê khi kiểm duyệt | PASS    |
| TC16 | Kiểm soát quyền truy cập API    | PASS    |

## 4. Kiểm thử tự động

Lệnh thực thi: `python3 scripts/run_checks.py`

- Python unittest: 56/56 PASS.
- Thời gian thực thi unittest: 13,025 giây.
- Kiểm tra cú pháp app.js: PASS.
- Kiểm tra cú pháp advisor.js: PASS.
- Kiểm thử Advisor: PASS.

## 5. Các lỗi đã khắc phục

- Cập nhật bài kiểm thử Review API lỗi thời.
- Khắc phục xung đột cấu hình Local Demo với database kiểm thử.
- Phân biệt HTTP 401 và HTTP 403 trong kiểm thử phân quyền.
- Đóng phản hồi HTTP sau khi đọc dữ liệu lỗi để giải phóng tài nguyên.

## 6. Kiểm thử thực tế

Trưởng nhóm xác nhận đã kiểm thử trực tiếp trên website ServiceHub và chạy kiểm tra API thông qua trình duyệt thành công.

Ảnh hoặc video minh chứng cần được bổ sung vào hồ sơ nghiệm thu.

## 7. Kết luận

Toàn bộ 56 bài kiểm thử tự động đã vượt qua. Các chức năng Sprint 4 đã được triển khai và kiểm thử theo phạm vi hiện tại.

Chờ xác nhận GitHub Actions của PR #46 và hoàn tất hồ sơ nghiệm thu.

Issue liên quan: #39, #36, #37, #38.
