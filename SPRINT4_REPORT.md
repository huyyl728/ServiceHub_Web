# Báo cáo hoàn thiện ServiceHub — Sprint 1 đến Sprint 4

**Phiên bản:** ServiceHub Python + SQLite + HTML/CSS/JavaScript, nâng cấp 08/11/2026.
**Mục đích:** Bản demo học tập, phục vụ thuyết trình/kiểm thử theo nhóm 4 thành viên. Chức năng thanh toán và ví là mô phỏng.

## 1. Tiến độ theo Sprint

| Sprint | Phạm vi | Thành phần minh chứng |
|---|---|---|
| Sprint 1 | Cấu trúc dự án và UI: trang chủ, danh sách dịch vụ, responsive | `static/index.html`, `static/css/styles.css` |
| Sprint 2 | Backend, SQLite, người dùng và nhà cung cấp, CRUD, phân quyền | `server.py`, `schema.sql`, các API `/api/auth/*`, `/api/owner/*` |
| Sprint 3 | Tìm kiếm/gợi ý, tư vấn 3 câu hỏi, đặt lịch và chi tiết dịch vụ | `static/js/app.js`, `static/js/advisor.js`, `tests/test_advisor.js` |
| **Sprint 4** | Quản trị nâng cao, thông báo, hội viên theo cơ sở, ví demo, test tích hợp và CI | `/api/admin/reports`, `/api/admin/audit`, `/api/admin/businesses`, `/api/notifications/*`, `/api/owner/members`, `tests/test_sprint4.py`, `.github/workflows/ci.yml` |

## 2. Các hạng mục Sprint 4 đã triển khai trong mã nguồn

- **Quản trị:** hồ sơ nhà cung cấp (kế thừa), thêm danh sách cơ sở với nút tạm dừng/kích hoạt, báo cáo trạng thái lịch đặt, thống kê hội viên, thanh toán ví *demo*, nhật ký 50 sự kiện. Admin được kiểm tra ở backend, không chỉ ẩn nút trên frontend.
- **Thông báo:** biểu tượng chuông hiển thị số chưa đọc; trang Tài khoản hiển thị thông báo, thao tác đánh dấu đã đọc/tất cả. Thông báo được lưu vào bảng SQLite `notifications` sẵn có và lọc theo `user_id`.
- **Hội viên:** chủ cơ sở xem danh sách thành viên của chính cơ sở mình. Chương trình hội viên và đặt lịch tự xác nhận cho hội viên được kế thừa từ Sprint trước.
- **Ví demo:** giữ cơ chế nạp/chuyển/chi bằng SQLite, bổ sung thông báo cho giao dịch. Yêu cầu nạp/chuyển trùng mã không làm cộng/trừ số dư lần hai (theo phạm vi test).
- **Sửa lỗi:** `/api/businesses/managed` trước đó bị endpoint chi tiết cơ sở chặn nhầm. Đã tách đường dẫn để owner có thể tải danh sách cơ sở của mình.
- **Tự động hóa:** chạy toàn bộ test trong môi trường database tạm và cấu hình GitHub Actions cho push/PR.

## 3. Tập trung kiểm thử và bằng chứng

`python3 scripts/run_checks.py` chạy kiểm tra cú pháp Python, toàn bộ unittest tích hợp backend trên **database tạm** và bài test advisor JavaScript (khi có Node.js). Bộ test bao gồm các trường hợp: auth, catalog, chuyển ví demo, phân quyền admin, báo cáo, tạm dừng/kích hoạt cơ sở, thông báo cá nhân/đánh dấu đã đọc, hội viên theo cơ sở, đặt lịch và chống xử lý nạp ví trùng.

**Lưu ý:** Unit/integration tests chưa chứng minh mọi luồng trình duyệt đã đạt hoặc hệ thống chịu tải/production an toàn. Sau khi tải bản mới, nhóm cần tự chạy các Test Case thủ công đã thống nhất và ghi lại Pass/Fail thực tế.

## 4. Phân công cho nhóm 4 thành viên (đề xuất)

| Thành viên | Phần kiểm thử/demo | Test Case tham khảo |
|---|---|---|
| 1 | HTML/CSS, responsive, đăng nhập | TC01–TC05 |
| 2 | Tìm kiếm, gợi ý 3 câu hỏi, ngân sách | TC06–TC10 |
| 3 | Chủ cơ sở, CRUD dịch vụ, ảnh riêng và quyền sở hữu | TC11–TC15 |
| 4 | Đặt lịch, ví demo, hội viên, thông báo/admin | TC16–TC20 + test Sprint 4 tự động |

## 5. Kịch bản demo Sprint 4 (4–6 phút)

1. Đăng nhập khách hàng demo → Tài khoản → Thông báo; chọn **Đánh dấu đã đọc**.
2. Trả lời 3 câu hỏi “Hôm nay bạn muốn ăn gì hoặc làm gì?” và xem dịch vụ gợi ý.
3. Đăng nhập tài khoản chủ cơ sở → Quản lý cơ sở → xem hội viên và lịch đặt.
4. Đăng nhập admin demo → Quản trị → xem số liệu, danh sách cơ sở, tạm dừng một cơ sở demo và kích hoạt lại.
5. Terminal: chạy `python3 scripts/run_checks.py` và trình bày kết quả thực tế.

## 6. Cách chạy trên MacBook

```bash
cd ServiceHub_fullstack
SERVICEHUB_PORT=8001 python3 server.py
```

Truy cập `http://127.0.0.1:8001`. Dùng `8001` nếu cổng `8000` đã có server khác chiếm. Không chạy bản mới với đường dẫn database cũ khi chưa sao lưu.

Nếu Docker Desktop đang chạy, ở đúng thư mục dự án:

```bash
docker compose up -d --build
docker compose ps
```

Bản Compose mặc định dùng cổng 8000. Nếu cổng 8000 đã bận, chạy `SERVICEHUB_HOST_PORT=8001 docker compose up -d --build`. Cấu hình Compose sẽ ánh xạ cổng 8001 của Mac vào cổng 8000 trong container.

## 7. Giới hạn chưa hoàn thành / chưa thể khẳng định

- Không có xác nhận về hệ thống production, bảo mật công khai, HTTPS, quản lý bí mật, backup tự động, tải lớn hoặc giám sát.
- Ví/nạp/chuyển/chi là **dữ liệu mô phỏng**, không được sử dụng như tiền thật.
- Không triển khai đồng bộ real-time qua WebSocket; thông báo cập nhật khi truy cập/tải lại tài khoản, không phải push tức thời trên mọi thiết bị.
- Các tài khoản demo chỉ dùng trong môi trường học tập tin cậy. Không đưa dữ liệu người dùng thật hoặc tài khoản demo lên Internet.
