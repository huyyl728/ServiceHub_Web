# Sprint 3 — Tìm kiếm, dịch vụ và đặt lịch

**Dự án:** ServiceHub_Web · **Nhóm:** 4 thành viên · **Đối chiếu:** 19/11/2026  
**Trạng thái GitHub:** 5/5 Issue đã đóng.  
**Mục tiêu:** Cho phép khách khám phá dịch vụ, nhận gợi ý, đặt/hủy lịch; Owner quản lý danh mục và ảnh dịch vụ.

## Product Backlog và kết quả

| Mã | Issue | Nội dung | GitHub |
|---|---|---|---|
| S3-01 | [#11](https://github.com/huyyl728/ServiceHub_Web/issues/11) | Danh sách dịch vụ và lọc danh mục | Closed |
| S3-02 | [#12](https://github.com/huyyl728/ServiceHub_Web/issues/12) | Tìm kiếm từ khóa và gợi ý khi nhập | Closed |
| S3-03 | [#13](https://github.com/huyyl728/ServiceHub_Web/issues/13) | Bộ câu hỏi sở thích cá nhân hóa | Closed |
| S3-04 | [#14](https://github.com/huyyl728/ServiceHub_Web/issues/14) | Owner CRUD dịch vụ và quản lý ảnh | Closed |
| S3-05 | [#15](https://github.com/huyyl728/ServiceHub_Web/issues/15) | Đặt/hủy lịch và kiểm soát xung đột | Closed |

## Sản phẩm bàn giao

- Danh sách theo danh mục, tìm kiếm; trang chi tiết cơ sở và dịch vụ.
- Bộ gợi ý 3 câu hỏi: nhu cầu, phong cách trải nghiệm, mức ngân sách; lọc dịch vụ thực từ API, không tự bịa kết quả.
- Owner tạo/sửa/ẩn dịch vụ, cập nhật ảnh banner cơ sở và ảnh riêng từng dịch vụ.
- Khách xem lịch khả dụng, tạo lịch đặt, xem lịch sử và hủy; backend kiểm tra xung đột khung giờ.
- Chương trình hội viên theo từng cơ sở và chế độ tự xác nhận lịch cho hội viên là phần mở rộng lịch sử, tiếp tục được giữ trong mã nguồn, nhưng không làm thay đổi mục tiêu chính của Sprint 3.

## Thành phần mã và kiểm thử

- Frontend: `static/index.html`, `static/js/app.js`, `static/js/advisor.js`, `static/css/styles.css`.
- Backend: `server.py` (API dịch vụ, khả dụng, lịch đặt, Owner), `schema.sql`.
- Tests: `tests/test_smoke.py`, `tests/test_advisor.js`; hướng dẫn chi tiết ở [DISCOVERY_GUIDE.md](../DISCOVERY_GUIDE.md).
- Kiểm thử viewport gợi ý và các bài thử lịch sử được ghi tại [TESTED.md](../TESTED.md). CI `main` mới nhất: [Passed](https://github.com/huyyl728/ServiceHub_Web/actions/runs/44364381151).

## Đánh giá Sprint

**Đã hoàn thành:** Luồng chính từ tìm kiếm đến tạo lịch đặt đã có và các Issue #11–#15 đã đóng.  
**Giới hạn:** Test backend/JS và ảnh chụp viewport chưa chứng minh mọi tương tác thực tế; kiểm thử thủ công 20 trường hợp và E2E cuối kỳ vẫn theo dõi ở [Sprint 5](SPRINT_5.md) và [Sprint 6](SPRINT_6.md).

[← Sprint 2](SPRINT_2.md) · [Sprint 4 →](SPRINT_4.md)
