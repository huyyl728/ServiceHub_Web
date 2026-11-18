# Sprint 2 — Tài khoản, phân quyền và quản lý cơ sở

**Dự án:** ServiceHub_Web · **Nhóm:** 4 thành viên · **Đối chiếu:** 19/11/2026  
**Trạng thái GitHub:** 5/5 Issue đã đóng.  
**Mục tiêu:** Hoàn thiện tài khoản Customer/Owner/Admin, hồ sơ người dùng, quy trình đăng ký cơ sở và API quản lý.

## Product Backlog và kết quả

| Mã | Issue | Nội dung | GitHub |
|---|---|---|---|
| S2-01 | [#6](https://github.com/huyyl728/ServiceHub_Web/issues/6) | Đăng ký, đăng nhập, đăng xuất | Closed |
| S2-02 | [#7](https://github.com/huyyl728/ServiceHub_Web/issues/7) | Hồ sơ người dùng và cập nhật thông tin | Closed |
| S2-03 | [#8](https://github.com/huyyl728/ServiceHub_Web/issues/8) | Phân quyền Customer, Owner, Admin | Closed |
| S2-04 | [#9](https://github.com/huyyl728/ServiceHub_Web/issues/9) | Đăng ký chủ cơ sở và xét duyệt | Closed |
| S2-05 | [#10](https://github.com/huyyl728/ServiceHub_Web/issues/10) | Quản lý cơ sở và dữ liệu nền tảng | Closed |

## Sản phẩm bàn giao

- Xác thực bằng email/mật khẩu; mật khẩu hash PBKDF2-HMAC-SHA256; phiên đăng nhập bearer token.
- Người dùng chỉnh sửa thông tin cá nhân; gửi hồ sơ đăng ký chủ cơ sở.
- Admin duyệt, yêu cầu bổ sung hoặc từ chối hồ sơ; chủ cơ sở được duyệt quản lý cơ sở của mình.
- Schema và API nghiệp vụ tại `server.py`, `schema.sql`; giao diện tương ứng ở `static/js/app.js`.
- Đăng ký tài khoản không được cấp quyền Admin từ tham số do khách gửi.

## API chính và minh chứng

| Chức năng | Endpoint/nguồn |
|---|---|
| Xác thực | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout` |
| Hồ sơ | `GET /api/me`, `PUT /api/me` |
| Đăng ký cơ sở | `POST /api/business-applications` |
| Duyệt hồ sơ | `GET /api/admin/applications` và các endpoint duyệt/từ chối |
| Quản lý cơ sở | `GET /api/businesses/managed`, `PUT /api/owner/businesses/{id}` |

- `tests/test_admin_security.py` kiểm tra quyền Admin, tài khoản cũ và một số ranh giới truy cập.
- Cơ chế tạo Admin local trên bản clone sạch được nâng cấp ở [PR #54](https://github.com/huyyl728/ServiceHub_Web/pull/54); đây là thay đổi vận hành **sau Sprint 2**, không phải minh chứng của riêng Sprint 2.
- Mật khẩu demo chỉ hoạt động trong chế độ local; tài khoản thực/Render phải cấu hình riêng qua [ADMIN_SETUP.md](ADMIN_SETUP.md).

## Đánh giá Sprint

**Đã hoàn thành:** Các chức năng quản lý tài khoản và phê duyệt cơ sở phục vụ Sprint 3.  
**Cần rà soát bổ sung:** Khả năng chống brute force, cấu hình HTTPS và đánh giá bảo mật triển khai thật thuộc [Sprint 5](SPRINT_5.md) và [Sprint 6](SPRINT_6.md).

[← Sprint 1](SPRINT_1.md) · [Sprint 3 →](SPRINT_3.md)
