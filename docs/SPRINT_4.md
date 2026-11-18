# Sprint 4 — Đánh giá, bình luận và quản trị nâng cao (điều chỉnh)

**Dự án:** ServiceHub_Web · **Đối chiếu:** 19/11/2026  
**Trạng thái GitHub:** 8/8 Issue của Sprint 4 điều chỉnh (**#32–#39**) đã đóng, các PR liên quan đã merge.  
**Mục tiêu chính thức:** Website tìm kiếm và **đặt lịch không thanh toán**, có đánh giá dịch vụ/cơ sở, kiểm duyệt và thống kê Admin.

## Quyết định thay đổi phạm vi

Sau Sprint Review và góp ý của giảng viên, nhóm **loại bỏ thanh toán/VietQR khỏi luồng chính**. Bộ Issue Sprint 4 cũ [#16–#20](https://github.com/huyyl728/ServiceHub_Web/issues?q=is%3Aissue+is%3Aclosed+label%3Asprint%3A4) đã đóng và được giữ làm lịch sử phát triển; **không** dùng bộ đó để nghiệm thu Sprint 4 điều chỉnh. Các chức năng cũ (hội viên, ví mô phỏng, thông báo) nếu còn tồn tại ở backend không được trình bày là luồng thanh toán chính thức.

## Product Backlog điều chỉnh và kết quả

| Mã | Issue | Nội dung | GitHub |
|---|---|---|---|
| S4R-01 | [#32](https://github.com/huyyl728/ServiceHub_Web/issues/32) | Bỏ thanh toán khỏi website đặt lịch | Closed |
| S4R-02 | [#33](https://github.com/huyyl728/ServiceHub_Web/issues/33) | SQLite/API đánh giá cơ sở và dịch vụ | Closed |
| S4R-03 | [#34](https://github.com/huyyl728/ServiceHub_Web/issues/34) | Giao diện khách tạo/chỉnh sửa đánh giá | Closed |
| S4R-04 | [#35](https://github.com/huyyl728/ServiceHub_Web/issues/35) | Điểm sao và bình luận công khai theo cơ sở/dịch vụ | Closed |
| S4R-05 | [#36](https://github.com/huyyl728/ServiceHub_Web/issues/36) | API thống kê chi tiết từng cơ sở | Closed |
| S4R-06 | [#37](https://github.com/huyyl728/ServiceHub_Web/issues/37) | Admin Dashboard và trang chi tiết cơ sở | Closed |
| S4R-07 | [#38](https://github.com/huyyl728/ServiceHub_Web/issues/38) | Phân quyền, ngăn sửa trái phép, kiểm duyệt đánh giá | Closed |
| S4R-08 | [#39](https://github.com/huyyl728/ServiceHub_Web/issues/39) | Kiểm thử tích hợp, hồi quy và nghiệm thu | Closed |

## Chức năng và tiêu chí nghiệp vụ

- Khách chỉ đánh giá booking thuộc sở hữu của mình và ở trạng thái `completed`; không được đánh giá trùng một booking.
- Khách được chỉnh sửa đánh giá của mình khi hợp lệ; bình luận được ràng buộc kiểu dữ liệu/độ dài và escape ở frontend.
- Admin ẩn/khôi phục đánh giá; đánh giá bị ẩn không tính trong điểm sao công khai.
- API thống kê của Admin theo từng cơ sở: số lịch đặt, số hoàn thành/hủy, số dịch vụ, điểm sao và số lượt đánh giá; có lọc thời gian/đối chiếu SQLite.
- Booking, thao tác của Owner và Review tích hợp giữa backend, frontend và database.

Mã nguồn liên quan: `server.py`, `schema.sql`, `static/js/app.js`, `static/css/public-reviews.css`, `static/css/review-form.css`. Đặc tả API đánh giá ở [REVIEW_API.md](REVIEW_API.md).

## Bằng chứng triển khai

- [PR #40](https://github.com/huyyl728/ServiceHub_Web/pull/40): loại bỏ luồng thanh toán.
- [PR #49](https://github.com/huyyl728/ServiceHub_Web/pull/49), [#50](https://github.com/huyyl728/ServiceHub_Web/pull/50), [#51](https://github.com/huyyl728/ServiceHub_Web/pull/51): backend, form và hiển thị đánh giá.
- [PR #52](https://github.com/huyyl728/ServiceHub_Web/pull/52): thống kê và UI Admin; [PR #42](https://github.com/huyyl728/ServiceHub_Web/pull/42): quyền/kiểm duyệt.
- [PR #46](https://github.com/huyyl728/ServiceHub_Web/pull/46): báo cáo kiểm thử tích hợp; `tests/test_reviews.py` và `tests/test_s4r08_additive.py`.

### Kết quả nghiệm thu đã được ghi nhận (báo cáo ngày 16/11/2026)

| Nhóm bài kiểm thử | Các trường hợp được ghi nhận | Kết quả theo báo cáo |
|---|---|---|
| Tài khoản, tìm kiếm | TC01–TC02 | PASS |
| Đặt lịch, Owner xác nhận/hoàn thành | TC03–TC05 | PASS |
| Tạo, ngăn trùng, sửa, hiển thị đánh giá | TC06–TC09 | PASS |
| Admin ẩn/khôi phục đánh giá | TC10–TC11 | PASS |
| Thống kê, lọc thời gian, đối chiếu SQLite, đồng bộ kiểm duyệt | TC12–TC15 | PASS |
| Quyền API | TC16 | PASS |

- Báo cáo Sprint 4 cũ ghi nhận **56/56 unittest PASS**, kiểm tra cú pháp JS và Advisor PASS tại thời điểm thực hiện. Đây là **kết quả lịch sử**, không tự coi là số lượng test mới nhất.
- Trưởng nhóm từng xác nhận kiểm thử website/API; **ảnh/video minh chứng chưa được đính kèm đầy đủ** theo nội dung đóng Issue #39.
- CI trên `main` sau PR #54: [ServiceHub checks — Passed](https://github.com/huyyl728/ServiceHub_Web/actions/runs/44364381151); không suy ra toàn bộ UI E2E đã được kiểm chứng.

## Kết luận và phần chuyển sang Sprint 5–6

**Sprint 4 điều chỉnh: đã đóng 8/8 Issue và có mã/kiểm thử tích hợp.** Nghiệm thu thiết bị thật, 20 test case thủ công, hồi quy liên Sprint và hồ sơ bàn giao vẫn thuộc [Sprint 5](SPRINT_5.md) và [Sprint 6](SPRINT_6.md). Không tuyên bố production-ready.

[← Sprint 3](SPRINT_3.md) · [Sprint 5 →](SPRINT_5.md)
