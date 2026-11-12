# SERVICEHUB — KẾ HOẠCH 6 SPRINT (ĐIỀU CHỈNH PHẠM VI)

**Dự án:** ServiceHub – tìm kiếm, đặt lịch và quản lý lịch dịch vụ trực tuyến.  
**Repository:** `huyyl728/ServiceHub_Web` (Private).  
**Nhóm:** 4 thành viên; **trưởng nhóm tự phân công** qua Assignees, hiện không tự gán cho các Issue Sprint 4 mới.

## Quyết định thay đổi phạm vi sau Sprint Review



## Kế hoạch Sprint (bản mới)

| Sprint | Mục tiêu | Issue | Trạng thái |
|---|---|---|---|
| 1 | Khởi tạo và giao diện | #1–#5 | Closed |
| 2 | Tài khoản, phân quyền, cơ sở | #6–#10 | Closed |
| 3 | Tìm kiếm, gợi ý và đặt lịch | #11–#15 | Closed |
| **4 (điều chỉnh)** | **Đánh giá, bình luận và quản trị cơ sở nâng cao** | **#32–#39 (S4R-01...S4R-08)** | **Open; chưa phân công** |
| 5 | Kiểm thử, bảo mật, UX và ổn định | #21–#25 | Open; giữ kế hoạch QA |
| 6 | Nghiệm thu, tài liệu và bàn giao | #26–#30 | Open |

## Sprint 4 điều chỉnh — Backlog và Acceptance Criteria


| Mã | Issue | Mục tiêu |
|---|---|---|
| S4R-02 | [#33](https://github.com/huyyl728/ServiceHub_Web/issues/33) | Thiết kế SQLite và API đánh giá cửa hàng/dịch vụ |
| S4R-03 | [#34](https://github.com/huyyl728/ServiceHub_Web/issues/34) | Form sao và bình luận cho khách có lịch hoàn thành |
| S4R-04 | [#35](https://github.com/huyyl728/ServiceHub_Web/issues/35) | Hiển thị rating và nhận xét theo đúng cửa hàng/dịch vụ |
| S4R-05 | [#36](https://github.com/huyyl728/ServiceHub_Web/issues/36) | API thống kê Admin cho từng cơ sở |
| S4R-06 | [#37](https://github.com/huyyl728/ServiceHub_Web/issues/37) | Admin Dashboard và chi tiết từng cơ sở |
| S4R-07 | [#38](https://github.com/huyyl728/ServiceHub_Web/issues/38) | Phân quyền đánh giá, ngăn sửa trái phép và kiểm duyệt bình luận |
| S4R-08 | [#39](https://github.com/huyyl728/ServiceHub_Web/issues/39) | Kiểm thử tích hợp, hồi quy và nghiệm thu |

**Nghiệp vụ đánh giá:** Chỉ chủ tài khoản có booking `completed` được đánh giá, không đánh giá trùng một booking; backend kiểm tra quyền, dữ liệu, an toàn nội dung. Review ẩn không tính vào điểm công khai.

**Chỉ số quản trị:** Tổng số lịch đặt, hoàn thành, đã hủy; số lượng dịch vụ; điểm sao và số lượt nhận xét theo từng cửa hàng. Có kiểm tra quyền Admin và đối chiếu số liệu với SQLite.

**Phân công:** Để trống `Assignees` cho #32–#39. Trưởng nhóm tự chọn thành viên dựa trên năng lực và khối lượng công việc. Mỗi Issue cần có nhánh Git riêng và Pull Request.

## Sprint 5 và 6

- **Sprint 6:** Kiểm thử end-to-end Customer → Owner → Admin, tài liệu sử dụng, báo cáo Sprint và buổi demo/đánh giá cuối kỳ.

## Definition of Done

1. Tính năng có code trên nhánh riêng, Pull Request được review và merge.
2. Hoàn thành các tiêu chí nghiệm thu trong Issue; có kết quả test và minh chứng.
3. Không commit `.env`, mật khẩu, thông tin ngân hàng thật hoặc SQLite cá nhân.
4. Không tự đóng Issue chỉ vì đã tạo UI/API; phải xác minh luồng hoạt động.
5. Admin thống kê chính xác, đánh giá đúng điều kiện booking và quyền truy cập.

## Ghi chú GitHub Milestone

Issue #32–#39 hiện được gắn **Milestone số 4**. Tên Milestone #4 cũ cần đổi thành **`Sprint 4 – Đánh giá và quản trị nâng cao`** bằng GitHub UI/CLI. Milestone #5 cần đổi lại thành **`Sprint 5 – Kiểm thử, bảo mật và cải thiện UX`** nếu trước đó bị đổi tên. Việc chỉnh tên không thay đổi lịch sử Issue/commit.
