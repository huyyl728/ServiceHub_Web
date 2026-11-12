# Kiểm tra bản đóng gói

Đã kiểm tra trong môi trường đóng gói:

- `python3 -m py_compile server.py`
- `node --check static/js/app.js`
- `python3 -m unittest discover -s tests -v` khi server chạy tại `127.0.0.1:8000`: 7/7 test hiện có đạt.

Phạm vi kiểm thử hiện tại bao gồm health check, đăng nhập, danh sách dịch vụ và các tình huống chuyển ví mô phỏng. Đây không phải bằng chứng rằng toàn bộ mọi luồng UI đã được kiểm thử hoặc ứng dụng đã sẵn sàng cho production. Xem mục giới hạn/bảo mật trong README trước khi triển khai công khai.

## Kiểm tra bổ sung cho phần gợi ý theo sở thích (03/11/2026)

- `node --check static/js/advisor.js` — đạt.
- `node --check static/js/app.js` — đạt.
- `node tests/test_advisor.js` — các trường hợp phân loại, loại trừ mức giá “Liên hệ”, ngân sách và không bịa kết quả đều đạt.
- `python3 -m unittest discover -s tests -v` với server Python chạy bằng cơ sở dữ liệu SQLite tạm — 7/7 bài đạt.
- Kiểm tra giao diện ở viewport máy tính (1440px) và điện thoại (390px) với Playwright và **dữ liệu API mô phỏng** — luồng 3 câu hỏi, quay lại/chọn lại, kết quả và không có kết quả đều hoạt động; không ghi nhận JavaScript page error hay tràn ngang.
- Đã kiểm tra API thật trả về mục dịch vụ cà phê demo sau khởi động bằng database mới.

Các kết quả trên không phải phép thử triển khai production hoặc kiểm thử end-to-end toàn diện trên máy của người dùng.


## Kiểm thử bản Sprint 4 (08/11/2026)

- Đã chạy `python3 scripts/run_checks.py` bằng SQLite tạm: **13/13** bài kiểm thử Python đạt (7 bài cũ + 6 bài tích hợp Sprint 4).
- Đã kiểm tra cú pháp `server.py`, `static/js/app.js` và `static/js/advisor.js`: đạt.
- `node tests/test_advisor.js`: đạt.
- Thử kiểm tra giao diện tự động bằng trình duyệt headless trong môi trường đóng gói nhưng trình duyệt bị chặn truy cập localhost (`ERR_BLOCKED_BY_ADMINISTRATOR`). Vì vậy **chưa xác minh đầy đủ UI end-to-end trực tiếp trên trình duyệt**; cần nhóm thử thủ công trên MacBook.
- Các test tích hợp Sprint 4 có dữ liệu tạm riêng, không đụng cơ sở dữ liệu ServiceHub thật.

Kết quả này **không chứng minh production-ready, chịu tải hay bảo mật hoàn toàn**.
