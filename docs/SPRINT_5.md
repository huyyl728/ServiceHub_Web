# Sprint 5 — Kiểm thử, bảo mật, UX và ổn định

**Dự án:** ServiceHub_Web · **Đối chiếu:** 19/11/2026  
**Trạng thái GitHub:** **1/5 Issue đóng, 4/5 Issue còn mở.** Không đánh đồng CI PASS với hoàn thành nghiệm thu thủ công.  
**Mục tiêu:** Kiểm tra sản phẩm trên thiết bị thật, rà soát bảo mật, dữ liệu, Docker/LAN, hồi quy và hồ sơ lỗi.

## Product Backlog hiện tại

| Mã | Issue | Nội dung | GitHub | Còn thiếu trước khi đóng |
|---|---|---|---|---|
| S5-01 | [#21](https://github.com/huyyl728/ServiceHub_Web/issues/21) | 20 test case / 4 thành viên | **Open** | Đủ Actual Result, Pass/Fail/Blocked, ảnh/log của từng case |
| S5-02 | [#22](https://github.com/huyyl728/ServiceHub_Web/issues/22) | UX/tìm kiếm trên điện thoại | **Closed** | Đã có bình luận nghiệm thu; tiếp tục ghi nhận lỗi nếu phát hiện |
| S5-03 | [#23](https://github.com/huyyl728/ServiceHub_Web/issues/23) | Bảo mật và dữ liệu | **Open** | Đối chiếu API trái quyền, upload, cấu hình và bí mật |
| S5-04 | [#24](https://github.com/huyyl728/ServiceHub_Web/issues/24) | Docker/LAN/restart | **Open** | Bằng chứng 2 máy cùng Wi-Fi, bind/port, SQLite + uploads còn sau restart |
| S5-05 | [#25](https://github.com/huyyl728/ServiceHub_Web/issues/25) | Bug report và regression | **Open** | Nhật ký bug, P0 tồn đọng, tái kiểm thử và CI |

## Công việc đã có bằng chứng

- [Issue #22](https://github.com/huyyl728/ServiceHub_Web/issues/22) được đóng 19/11/2026 sau khi đối chiếu checklist và bình luận kiểm thử từ thành viên; [Issue #53](https://github.com/huyyl728/ServiceHub_Web/issues/53) cũng ghi nhận kết quả UI điện thoại.
- Kiểm tra viewport 390px và tư vấn theo sở thích có ghi nhận lịch sử tại [TESTED.md](../TESTED.md), `tests/test_advisor.js`.
- Kiểm tra backend/role/Admin: `tests/test_admin_security.py`, `tests/test_local_demo.py`. PR [#54](https://github.com/huyyl728/ServiceHub_Web/pull/54) thêm khởi chạy từ clone sạch và Admin mẫu nhất quán local.
- CI trên merge commit `019eccc`: [Passed](https://github.com/huyyl728/ServiceHub_Web/actions/runs/44364381151), gồm Linux và thử khởi chạy demo trên macOS/Windows.
- `compose.yaml` định nghĩa cổng 8000 và named volumes cho SQLite, uploads; **chưa có bằng chứng từ Issue #24** xác nhận LAN hai thiết bị.

## Quy trình hoàn tất 4 Issue mở

1. **#21:** 4 thành viên, mỗi người chạy 5 test case từ [bảng Excel](ServiceHub_20_TestCases_4_ThanhVien.xlsx); ghi Expected/Actual, Pass/Fail/Blocked, môi trường, ảnh/log và liên kết.
2. **#23:** Rà soát `.gitignore`, `.env.example`, quyền Owner/Admin, upload ảnh, hash mật khẩu, secret production; ghi case lỗi và phản chứng.
3. **#24:** Kiểm tra `docker compose up --build`, 8000/8001, bind host, LAN trên cùng Wi-Fi, restart và kiểm tra dữ liệu/ảnh vẫn còn; **không dùng Admin demo để mở Internet**.
4. **#25:** Lập bảng Bug ID, severity, bước tái hiện, môi trường, sửa ở PR nào, kết quả regression; xác nhận không còn P0 cản luồng demo.

## Definition of Done

Mỗi Issue chỉ đóng khi có kết quả thực tế, người kiểm thử, bằng chứng và kết luận. Không reset/xóa database thật để chứng minh chạy lại. Chạy CI/`python3 scripts/run_checks.py` chỉ là một phần nghiệm thu.

[← Sprint 4](SPRINT_4.md) · [Sprint 6 →](SPRINT_6.md)
