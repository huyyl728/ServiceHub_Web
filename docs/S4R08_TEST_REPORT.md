# S4R-08 — Báo cáo kiểm thử bổ sung (chỉ thêm file)

## 1. Phạm vi và nguyên tắc

Bộ test được thêm mới tại `tests/test_s4r08_additive.py`. Không sửa, xóa hoặc thay thế file backend, frontend, schema, CI hay test hiện hữu. Máy chủ kiểm thử sử dụng SQLite tạm thông qua `tests/fixture_server.py`.

## 2. Test case và kết quả thực tế

| ID | Vai trò / chức năng | Kết quả kỳ vọng | Kết quả thực tế |
|---|---|---|---|
| S4R08-API-01 | Customer tạo booking không thanh toán | HTTP 201, trạng thái pending, không cần payment | **PASS** |
| S4R08-E2E-02 | Owner xác nhận và hoàn thành booking | Customer nhìn thấy trạng thái completed | **PASS** |
| S4R08-ADM-03 | Admin xem thống kê booking | Tổng booking tăng đúng 1 | **PASS** |
| S4R08-AUTH-04 | Customer/Owner truy cập sai quyền Admin/Owner | HTTP 403 | **PASS** |
| S4R08-VAL-05 | Gửi booking không đăng nhập / ngày sai | HTTP 401 / 400 | **PASS** |
| S4R08-REV-06 | Customer gửi review và gửi trùng | Có review và chặn review trùng | **FAIL / BLOCKED** |
| S4R08-UI-07 | Kiểm thử trực tiếp trên trình duyệt | Chụp ảnh luồng Customer/Owner/Admin | **NOT RUN** |

## 3. Kết quả chạy lệnh

Đã chạy từ thư mục gốc dự án:

```bash
python3 -m unittest discover -s tests -p "test_s4r08_additive.py" -v
```

Kết quả: **4/4 test PASS**.

Đã chạy toàn bộ kiểm tra:

```bash
python3 scripts/run_checks.py
```

Kết quả:
- `py_compile server.py`: PASS
- Python unittest discovery: **25/25 PASS**
- `node --check static/js/app.js`: PASS
- `node --check static/js/advisor.js`: PASS
- `node tests/test_advisor.js`: PASS
- Lệnh tổng thể kết thúc với mã thoát `0`.

Lưu ý: Python runtime in cảnh báo warmup của spreadsheet tool ra stderr trong môi trường chạy; cảnh báo này không làm test thất bại và không thuộc mã nguồn ServiceHub.

## 4. Bug / blocker phát hiện

- API hiện hỗ trợ Customer tạo booking, Owner xác nhận và hoàn thành, Admin đọc `/api/admin/stats`.
- Trong `schema.sql` không có bảng review dành cho booking; `server.py` không có API tạo review booking.
- Test gửi `POST /api/reviews` nhận `404 ENDPOINT_NOT_FOUND`. Vì endpoint chưa tồn tại, không thể kiểm thử logic review trùng. Đây là **FAIL theo tiêu chí nghiệm thu**, không phải PASS.
- Theo yêu cầu không sửa code sẵn có, bộ test chỉ ghi nhận blocker và không tự bổ sung chức năng review.
- Booking hiện không yêu cầu thanh toán; payload tạo booking không có trường `payment` hoặc `payment_url`.

## 5. Kiểm thử trình duyệt — checklist cần nhóm thực hiện

Chưa có bằng chứng trình duyệt thật trong lượt xử lý này. Khi chạy website trên máy nhóm, thực hiện và lưu ảnh màn hình cho từng bước:

1. Customer: đăng nhập, tìm dịch vụ, chọn ngày/giờ, đặt lịch; xác nhận không bị chuyển sang thanh toán.
2. Owner: đăng nhập đúng tài khoản chủ cơ sở, mở lịch đặt, xác nhận rồi hoàn thành lịch.
3. Customer: tải lại danh sách lịch đặt và kiểm tra trạng thái hoàn thành.
4. Admin: đăng nhập tài khoản quản trị, mở trang thống kê và đối chiếu tổng số lịch đặt.
5. Customer/Owner: thử mở khu vực không thuộc quyền; ghi nhận thông báo từ chối.
6. Tìm kiếm và đăng nhập: xác nhận vẫn hoạt động sau thay đổi chỉ-thêm.

Không đánh dấu các bước trên là Pass trước khi nhóm tự thực hiện và lưu ảnh bằng chứng.

## 6. Trạng thái nghiệm thu

**Chưa đủ điều kiện đóng Issue S4R-08.** Cần:
1. Trưởng nhóm quyết định cách xử lý chức năng review booking còn thiếu. Muốn hoàn tất review và chặn review trùng sẽ cần thay đổi chức năng/schema, hiện bị giới hạn bởi yêu cầu không sửa code.
2. Nhóm thực hiện kiểm thử trình duyệt và lưu ảnh minh chứng.
3. Push nhánh riêng, tạo commit/PR liên kết Issue.
4. Trưởng nhóm review PR và bằng chứng trước khi đóng Issue.
