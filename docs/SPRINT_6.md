# Sprint 6 — Nghiệm thu, tài liệu và bàn giao

**Dự án:** ServiceHub_Web · **Đối chiếu:** 19/11/2026  
**Trạng thái GitHub:** **0/5 Issue đóng, 5/5 còn mở.**  
**Mục tiêu:** Nghiệm thu nghiệp vụ Customer–Owner–Admin, hoàn chỉnh tài liệu, báo cáo 6 Sprint và demo cuối kỳ.

## Product Backlog hiện tại

| Mã | Issue | Nội dung | GitHub | Còn thiếu |
|---|---|---|---|---|
| S6-01 | [#26](https://github.com/huyyl728/ServiceHub_Web/issues/26) | Kiểm thử E2E toàn luồng | Open | E2E browser thật, Pass/Fail và ảnh/video |
| S6-02 | [#27](https://github.com/huyyl728/ServiceHub_Web/issues/27) | README, kiến trúc, hướng dẫn vận hành | Open | Chuẩn hóa tài liệu cũ, xác nhận clone sạch và kiểm thử theo hướng dẫn |
| S6-03 | [#28](https://github.com/huyyl728/ServiceHub_Web/issues/28) | Báo cáo 6 Sprint và GitHub | Open | Liên kết đúng Issue/PR/Milestone và hồ sơ nghiệm thu tổng hợp |
| S6-04 | [#29](https://github.com/huyyl728/ServiceHub_Web/issues/29) | Chuẩn bị thuyết trình 4 thành viên | Open | Slide, phân công, lời thoại, demo offline và phương án dự phòng |
| S6-05 | [#30](https://github.com/huyyl728/ServiceHub_Web/issues/30) | Nghiệm thu MVP và rủi ro thực tế | Open | Kiểm tra HTTPS, backup/restore, secret, vận hành thật và rủi ro |

## Kịch bản E2E cần nghiệm thu (#26)

1. **Customer:** đăng ký/đăng nhập → tìm cơ sở/dịch vụ → đặt lịch; kiểm tra lịch xuất hiện trong tài khoản.
2. **Owner:** đăng nhập → xem lịch của cơ sở mình → xác nhận và hoàn thành lịch.
3. **Customer:** đánh giá lịch `completed` → điểm sao/bình luận hiển thị đúng; kiểm tra ngăn đánh giá trùng.
4. **Admin:** đăng nhập → kiểm duyệt bình luận → xem thống kê theo cơ sở, kiểm tra thay đổi số liệu/điểm sao.
5. **Bảo vệ quyền:** khách không sửa dữ liệu của Owner khác; Owner không thực hiện hành động Admin.
6. **Restart:** dừng/chạy lại ứng dụng → tài khoản, lịch, nhận xét không bị mất.

**Thay đổi phạm vi cần đồng bộ với Issue #26/#30:** Nội dung cũ vẫn nhắc VietQR. Sau Sprint 4 điều chỉnh, **không yêu cầu trình diễn chuyển tiền, thanh toán ngân hàng hoặc đối soát**. Luồng chính chỉ là đặt lịch, đánh giá và quản trị.

## Tài liệu và bàn giao (#27–#28)

- [README.md](../README.md): hướng dẫn clone/chạy `server.py`, môi trường Mac/Windows, API và giới hạn.
- [SPRINT_1.md](SPRINT_1.md) đến [SPRINT_6.md](SPRINT_6.md): mỗi Sprint một file, đối chiếu trạng thái Issue ngày 19/11/2026.
- [LOCAL_DEMO.md](LOCAL_DEMO.md), [ADMIN_SETUP.md](ADMIN_SETUP.md): cấu hình local và Admin riêng trên production.
- [REVIEW_API.md](REVIEW_API.md): hợp đồng API review; [TESTED.md](../TESTED.md): bằng chứng kiểm thử lịch sử.
- [PR #54](https://github.com/huyyl728/ServiceHub_Web/pull/54): chạy trực tiếp server.py từ bản clone sạch, Admin local cố định và CI đa nền tảng.
- [GitHub Actions — main](https://github.com/huyyl728/ServiceHub_Web/actions/runs/44364381151): kiểm thử tự động PASS. **Chưa tương đương** nghiệm thu E2E và triển khai thực tế.

## Chuẩn bị demo nhóm (#29)

| Phần trình bày đề xuất | Nội dung minh họa |
|---|---|
| Thành viên 1 | Giới thiệu dự án, kiến trúc, Sprint 1–2 |
| Thành viên 2 | Tìm kiếm, gợi ý và đặt lịch (Sprint 3) |
| Thành viên 3 | Owner, bình luận/đánh giá và Admin Analytics (Sprint 4) |
| Thành viên 4 | Kịch bản kiểm thử, bảo mật, giới hạn, kết luận (Sprint 5–6) |

Phân công trên chỉ là **đề xuất**, chưa có xác nhận trên Issue #29. Chuẩn bị tài khoản/test data riêng, demo offline dự phòng và không tiết lộ secret production.

## Rủi ro trước triển khai thật (#30)

- Website Python/SQLite hiện là **MVP phục vụ học tập và demo**, chưa production-ready.
- Không dùng mật khẩu Admin mẫu công khai trên Internet; triển khai thật phải có Admin secret riêng.
- Chưa nghiệm thu đầy đủ HTTPS/reverse proxy, kiểm soát phiên, sao lưu–khôi phục, giám sát, độ tải và vận hành nhiều người dùng.
- Tách kết luận: `code-present` ≠ `automated-tests-passed` ≠ `manual-accepted` ≠ `production-ready`.

## Definition of Done

Có đủ kết quả E2E, biên bản nghiệm thu, hướng dẫn thành viên mới chạy, kịch bản demo nhóm, báo cáo rủi ro và liên kết Issue/PR minh chứng. Cho đến lúc đó, **Sprint 6 vẫn Open**.

[← Sprint 5](SPRINT_5.md) · [Quay về README](../README.md)
