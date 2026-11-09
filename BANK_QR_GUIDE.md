# ServiceHub – Hướng dẫn thử tính năng chuyển khoản VietQR

## 1. Giới hạn quan trọng

- **Mã VietQR chứa thông tin nhận chuyển khoản thật** khi người quản trị nhập tài khoản ngân hàng hợp lệ. Quét QR có thể dẫn tới **giao dịch tiền thật**. Chỉ thử tạo/hiển thị QR bằng dữ liệu minh họa trong bài tập, không cần chuyển tiền thật.
- QR chỉ chứa ngân hàng nhận, số tài khoản, số tiền và nội dung chuyển khoản. **Không có chức năng tự nhận biết khoản tiền đã đến.** Không đánh dấu đã thanh toán chỉ vì người dùng bấm nút, gửi ảnh chụp màn hình hoặc tạo QR.
- Admin chỉ đánh dấu **Đã xác nhận** sau khi tự đối chiếu **sao kê ngân hàng thực tế**, kiểm tra tài khoản nhận, số tiền, nội dung chuyển khoản và mã giao dịch; một mã giao dịch không được dùng để xác nhận hai yêu cầu.
- Sau khi admin đối soát và xác nhận, hệ thống **cộng số tiền vào ví ServiceHub đúng một lần** và ghi lịch sử giao dịch. Việc này không tạo thanh toán trong bảng `payments` và không hoàn tất lịch đặt.
- Ảnh QR sử dụng Quick Link của `img.vietqr.io` (bên thứ ba). Khi trình duyệt tải ảnh, thông tin ngân hàng nhận, số tiền và nội dung chuyển khoản được gửi đến dịch vụ này qua URL. Nếu bạn không đồng ý điều đó, **không bật VietQR**.
- Không yêu cầu số thẻ, mật khẩu, mã OTP hoặc thông tin đăng nhập ngân hàng. Không công khai tệp `.env`.
- Đây là bản demo chức năng và đối soát thủ công, **không phải cổng thanh toán production**. Đối với triển khai thật, cần xác minh chủ tài khoản, quy trình xử lý hoàn tiền, bảo mật tài khoản, phân quyền và tích hợp đối soát ngân hàng đáng tin cậy.

## 2. Thiết lập tài khoản nhận trên Mac (Python)

1. Giải nén dự án vào một thư mục riêng, mở Terminal trong thư mục `ServiceHub_fullstack`.
2. Tạo tệp cấu hình riêng:

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

3. Mở `.env` bằng trình soạn thảo, đặt:

   ```dotenv
   SERVICEHUB_ENABLE_BANK_QR=1
   SERVICEHUB_BANK_BIN=MA_BIN_6_SO
   SERVICEHUB_BANK_ACCOUNT=SO_TAI_KHOAN
   SERVICEHUB_BANK_NAME="TEN CHU TAI KHOAN"
   SERVICEHUB_PORT=8001       # Khi chạy Python trực tiếp
   SERVICEHUB_HOST_PORT=8001  # Khi chạy Docker Compose
   ```

   Các giá trị `MA_BIN_6_SO`, `SO_TAI_KHOAN` và `TEN CHU TAI KHOAN` chỉ là chỗ giữ chỗ, **bạn phải thay bằng thông tin chính xác** nếu bật QR. Giữ dấu nháy kép quanh tên chủ tài khoản có khoảng trắng. Dùng tài khoản nhận mà bạn có quyền sử dụng; không gửi các thông tin này vào cuộc trò chuyện. Nếu chưa muốn dùng tài khoản thật, giữ `SERVICEHUB_ENABLE_BANK_QR=0` để phần tạo QR được khóa.

4. Phiên bản đã sửa **tự đọc `.env` trong cùng thư mục với `server.py`** khi chạy bằng Python; không cần `source .env`:

   ```bash
   python3 server.py
   ```

   Nếu cần ghi đè cổng: `SERVICEHUB_PORT=8001 python3 server.py`. Biến môi trường đang có luôn ưu tiên hơn `.env`. Nếu bạn từng `source` một file cấu hình cũ, mở Terminal mới hoặc kiểm tra biến đang dùng trước khi khởi chạy.

**Lưu ý:** `server.py` ưu tiên `SERVICEHUB_PORT`, nếu thiếu thì dùng `SERVICEHUB_HOST_PORT`. Nếu cả hai đều thiếu, server dùng cổng 8000. Khi chạy Docker Compose, cổng trong container vẫn là 8000 và `SERVICEHUB_HOST_PORT` chỉ đổi cổng bên ngoài.

5. Mở `http://127.0.0.1:8001` → đăng nhập → **Tài khoản** → **Thanh toán bằng QR chuyển khoản** → nhập số tiền → **Tạo mã QR**. Hệ thống hiển thị ảnh QR, nội dung chuyển khoản dạng `SH...`, và trạng thái **Chờ xác nhận**. Bạn có thể thử tạo QR mà **không phải chuyển khoản**.

## 3. Docker Compose

`compose.yaml` đã đọc các biến `SERVICEHUB_ENABLE_BANK_QR`, `SERVICEHUB_BANK_BIN`, `SERVICEHUB_BANK_ACCOUNT` và `SERVICEHUB_BANK_NAME` từ `.env`. Có thể chạy:

```bash
docker compose --env-file .env up -d --build
```

Truy cập `http://127.0.0.1:8001` nếu `.env` có `SERVICEHUB_HOST_PORT=8001`.

## 4. Luồng người dùng và quản trị viên

**Khách hàng:** tạo yêu cầu QR (`10.000` đến `5.000.000` VNĐ) → nhận QR có số tiền + nội dung riêng → xem trạng thái `pending` → theo dõi khi admin xác nhận hoặc từ chối.

**Admin:** đăng nhập → **Quản trị** → **Đối soát VietQR** → chỉ sau khi kiểm tra giao dịch thật trên sao kê, chọn **Đã đối soát** và nhập mã giao dịch từ ngân hàng; nếu không khớp, chọn **Từ chối** và nhập lý do. Hệ thống lưu nhật ký và gửi thông báo cho khách.

**Chú ý:** Trạng thái `confirmed`, số dư và lịch sử giao dịch được cập nhật trong cùng một transaction. Gửi lại yêu cầu xác nhận không cộng tiền lần hai; yêu cầu bị từ chối không cộng tiền. Khi khởi động, server tự bổ sung tiền cho các yêu cầu `confirmed` từ phiên bản cũ còn thiếu giao dịch `bank_qr_topup`. Trong Tài khoản, bấm **Làm mới số dư** để cập nhật ví và lịch sử.

## 5. API và bảng dữ liệu

| API | Vai trò |
|---|---|
| `GET /api/bank-qr/config` | Trạng thái cấu hình và thông tin người nhận (đăng nhập) |
| `POST /api/bank-qr/requests` | Tạo yêu cầu gồm `amount`, `request_id` duy nhất |
| `GET /api/bank-qr/requests/me` | Xem yêu cầu thuộc chính người đăng nhập |
| `GET /api/admin/bank-qr/requests` | Admin xem các yêu cầu cần đối soát |
| `POST /api/admin/bank-qr/requests/{id}/confirm` | Admin xác nhận kèm `verified:true` và mã giao dịch ngân hàng |
| `POST /api/admin/bank-qr/requests/{id}/reject` | Admin từ chối và ghi lý do |

Bảng `bank_qr_requests` có `amount`, `reference` (duy nhất), `request_id` (chống tạo trùng), `status`, người đối soát, thời điểm và `bank_transaction_ref` (duy nhất).

## 6. Kiểm thử an toàn và không dùng tiền thật

Chạy:

```bash
python3 scripts/run_checks.py
```

Script dùng cơ sở dữ liệu SQLite tạm và tài khoản ngân hàng **giả định** để kiểm tra logic tạo QR, phân quyền, xác thực thủ công, chống trùng mã giao dịch, chỉ cộng ví sau đối soát và bổ sung giao dịch cũ không bị trùng. **Không gửi lệnh chuyển khoản đến ngân hàng.**

## 7. Các giới hạn trước khi triển khai công khai

- Chưa có webhook ngân hàng có chữ ký, kiểm chứng giao dịch tự động hay đồng bộ sao kê.
- Chưa tự động liên kết QR với lịch đặt và chưa có cơ chế hoàn tiền/đối soát theo từng cơ sở.
- Demo còn có tài khoản mẫu; bắt buộc loại bỏ hoặc thay đổi trước khi triển khai thật.
- Trước khi dùng cho tiền thật hoặc khách hàng thật, cần triển khai dịch vụ thanh toán phù hợp, xác minh quyền nhận tiền và tham khảo yêu cầu pháp lý liên quan.

Nguồn định dạng Quick Link: https://www.vietqr.io/qr-dong

## 8. Xử lý lỗi tạo QR (bản sửa cấu hình)

- Đặt `.env` **cạnh `server.py`** trong thư mục dự án đang chạy. Đừng nhầm với `.env.example`, và đừng copy nó vào gói ZIP hoặc GitHub.
- Khởi động bằng `python3 server.py`; dòng đầu Terminal sẽ ghi `VietQR configured` hoặc liệt kê **tên biến** cần sửa (không in số tài khoản).
- Mở website đúng cổng (ví dụ `http://127.0.0.1:8001`), **đăng nhập** và mở Tài khoản. Nếu QR chưa sẵn sàng, giao diện sẽ báo chi tiết biến cấu hình sai.
- Với VietinBank, điền `SERVICEHUB_BANK_BIN=970415`; kiểm tra số tài khoản và tên thụ hưởng ở file `.env` riêng.
- Nếu đã tạo yêu cầu nhưng ảnh mã QR không hiện, trình duyệt có thể không tải được ảnh từ `img.vietqr.io`. Khi đó kiểm tra mạng, chọn “Mở ảnh QR”, và **không chuyển tiền** nếu chưa thấy rõ thông tin.
- Không tự cộng ví hoặc xác nhận thanh toán chỉ vì đã tạo QR. Đây là demo để kiểm thử, không phải hệ thống thu tiền thật.
