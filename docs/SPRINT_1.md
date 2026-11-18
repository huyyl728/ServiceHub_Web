# Sprint 1 — Khởi tạo dự án và giao diện

**Dự án:** ServiceHub_Web · **Nhóm:** 4 thành viên · **Đối chiếu:** 19/11/2026  
**Trạng thái GitHub:** 5/5 Issue đã đóng; phạm vi Sprint 1 hoàn thành theo backlog.  
**Mục tiêu:** Tạo nền tảng Python/SQLite, bộ giao diện HTML/CSS/JS, điều hướng và tài liệu khởi động.

## Product Backlog và kết quả

| Mã | Issue | Nội dung | GitHub |
|---|---|---|---|
| S1-01 | [#1](https://github.com/huyyl728/ServiceHub_Web/issues/1) | Khởi tạo Python, SQLite và cấu trúc frontend | Closed |
| S1-02 | [#2](https://github.com/huyyl728/ServiceHub_Web/issues/2) | Trang chủ, điều hướng và khu vực dịch vụ | Closed |
| S1-03 | [#3](https://github.com/huyyl728/ServiceHub_Web/issues/3) | CSS, design system và responsive | Closed |
| S1-04 | [#4](https://github.com/huyyl728/ServiceHub_Web/issues/4) | Các trang hỗ trợ UX, nội dung và SEO cơ bản | Closed |
| S1-05 | [#5](https://github.com/huyyl728/ServiceHub_Web/issues/5) | Tài liệu chạy local và chuẩn bị Git | Closed |

## Sản phẩm bàn giao

- `server.py`: HTTP server và API bằng Python standard library; `schema.sql`: schema SQLite.
- `static/index.html` và `static/js/app.js`: giao diện một trang, các vùng chức năng và điều hướng.
- `static/css/styles.css`: design tokens, bố cục, biểu mẫu và CSS responsive.
- `static/404.html`, `static/privacy.html`, `static/thank-you.html`, `static/robots.txt`: các trang hỗ trợ và thông tin cơ bản.
- `README.md`: yêu cầu môi trường, cách clone, cách chạy, cấu trúc thư mục; Docker và GitHub được bổ sung ở các Sprint tiếp theo.

## Kiểm chứng

- Có mã nguồn tương ứng trong `main`; trạng thái các Issue #1–#5 đã đóng.
- Có kiểm tra cú pháp Python/JavaScript và kiểm thử smoke trong `tests/test_smoke.py`; CI tại [ServiceHub checks](https://github.com/huyyl728/ServiceHub_Web/actions/runs/44364381151) đã đạt trên commit merge PR #54.
- CI phản ánh trạng thái mã nguồn hiện tại, **không thay thế** đánh giá trực quan trên các loại thiết bị.

## Đánh giá Sprint

**Đã hoàn thành:** Khung ứng dụng và giao diện nền tảng đủ để phát triển đăng nhập, dịch vụ và đặt lịch.  
**Giới hạn:** Không kết luận ứng dụng đã sẵn sàng triển khai Internet; bảo mật và nghiệm thu thiết bị được theo dõi ở [Sprint 5](SPRINT_5.md) và [Sprint 6](SPRINT_6.md).

[Quay về README](../README.md) · [Sprint 2 →](SPRINT_2.md)
