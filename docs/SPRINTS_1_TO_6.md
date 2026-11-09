# SERVICEHUB — KẾ HOẠCH QUẢN LÝ 6 SPRINT

**Nguồn mã:** bản ServiceHub Sprint 4 + VietQR, có các tính năng được xây dựng đến Sprint 4.  
**Repository đề xuất:** `huyyl728/ServiceHub-6-Sprints` (Private).  
**Nhóm:** 4 thành viên; phân công issue thực tế sau khi được mời vào repository.

**Trạng thái:** `code-present` nghĩa là mã nguồn có triển khai nhưng *chưa đồng nghĩa đã được kiểm thử thủ công hoặc nghiệm thu*. `planned` nghĩa là backlog của Sprint 5–6. Toàn bộ Issue ban đầu để Open để kiểm chứng theo tiêu chí nghiệm thu.

| Sprint | Mục tiêu | Issue | Trạng thái ban đầu |
|---|---|---|---|
| Sprint 1 | Khởi tạo dự án và giao diện | S1-01, S1-02, S1-03, S1-04, S1-05 | code-present |
| Sprint 2 | Tài khoản, phân quyền và nhà cung cấp | S2-01, S2-02, S2-03, S2-04, S2-05 | code-present |
| Sprint 3 | Khám phá, dịch vụ, gợi ý và đặt lịch | S3-01, S3-02, S3-03, S3-04, S3-05 | code-present |
| Sprint 4 | Hội viên, ví demo, VietQR và quản trị | S4-01, S4-02, S4-03, S4-04, S4-05 | code-present |
| Sprint 5 | Kiểm thử, bảo mật và cải thiện UX | S5-01, S5-02, S5-03, S5-04, S5-05 | planned |
| Sprint 6 | Nghiệm thu, tài liệu và bàn giao | S6-01, S6-02, S6-03, S6-04, S6-05 | planned |

## Gợi ý phân công
- **Thành viên 1 (Frontend):** HTML/CSS, responsive, tìm kiếm và gợi ý.
- **Thành viên 2 (Backend):** Python, SQLite, API, phân quyền, nghiệp vụ đặt lịch.
- **Thành viên 3 (Provider/Admin):** quản lý cơ sở, dịch vụ, lịch, hội viên và báo cáo.
- **Thành viên 4 (QA/Integration):** 20 test case, Docker, CI, tài liệu và demo.

## Định nghĩa hoàn thành (Definition of Done)
1. Có mã nguồn liên quan trong repo, đã được review; không chỉ đóng issue trên kế hoạch.
2. Có kết quả kiểm thử và minh chứng; thao tác UI cần thử trên trình duyệt.
3. Không chứa `.env`, số tài khoản thật, SQLite dữ liệu cá nhân, hoặc ảnh upload cá nhân.
4. Các nghiệp vụ thanh toán phải giữ trạng thái pending cho đến khi đối soát thực tế.
5. Chỉ đóng Issue sau khi đạt tiêu chí nghiệm thu của chính Issue đó.

## Liên kết tài liệu
- [`GITHUB_BACKLOG.json`](GITHUB_BACKLOG.json) chứa 6 Milestone và 30 Issue với từng điều kiện nghiệm thu.
- [`GITHUB_SETUP.md`](GITHUB_SETUP.md) hướng dẫn xuất bản repo Private, tạo Milestone và Issue tự động bằng GitHub CLI.
- [`../docs/ServiceHub_20_TestCases_4_ThanhVien.xlsx`](ServiceHub_20_TestCases_4_ThanhVien.xlsx) là bộ test 20 trường hợp cần chạy và điền kết quả thực tế.
