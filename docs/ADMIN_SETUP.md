# Tài khoản admin riêng

Website không còn nút đăng nhập demo và không tự tạo khách hàng/chủ cơ sở/admin dùng mật khẩu công khai. Người dùng đăng ký bình thường; chủ cơ sở gửi hồ sơ để admin xét duyệt.

## Tạo cấu hình trên máy

Chạy một lần từ thư mục dự án, với email dành riêng cho quản trị:

```bash
python3 scripts/setup_admin.py --email admin@servicehub.local
```

Script tạo mật khẩu ngẫu nhiên, sao lưu database hiện tại và cấu hình `.env`, tạo/cập nhật admin, rồi lưu hai biến cấu hình vào `.env.admin`. File chỉ có quyền đọc/ghi cho chủ tài khoản máy; mật khẩu không được in ra Terminal. `.env.admin` và các bản sao lưu bị loại khỏi Git và Docker image. Không gửi file này vào chat hoặc commit lên repository.

Nếu `.env.admin` đã có, script dừng để không vô tình đổi mật khẩu. Mở file đó trên máy để xem email/mật khẩu và đăng nhập bằng form thông thường. Khởi động lại server local để mã và cấu hình mới có hiệu lực.

## Áp dụng lên Render

1. Vào dịch vụ ServiceHub → Environment.
2. Thêm đúng hai biến trong file `.env.admin`: `SERVICEHUB_ADMIN_EMAIL` và `SERVICEHUB_ADMIN_PASSWORD`. Mật khẩu tối thiểu 16 ký tự; nên dùng mật khẩu ngẫu nhiên do script tạo.
3. Chọn **Save only** để lưu biến, rồi **Manual Deploy → Deploy latest commit** để chạy bản code mới trên nhánh `main`. Commit bảo vệ admin có thể dùng `[skip render]` để tránh tự triển khai trước khi cấu hình xong. Không đưa `.env`/`.env.admin` lên GitHub.
4. Khi bản mới khởi động, server tạo admin nếu chưa có; hoặc cập nhật mật khẩu admin cùng email và thu hồi phiên cũ nếu mật khẩu thay đổi. Không tự nâng quyền một tài khoản khách hàng đã tồn tại cùng email.
5. Đăng nhập bằng form Email/Mật khẩu thông thường. Tài khoản admin sẽ có mục Quản trị. Xác minh nút demo đã biến mất và mật khẩu mặc định cũ không còn đăng nhập được.

Giữ các biến `SERVICEHUB_BANK_*` hiện có trên Render nếu đang dùng QR; không thay bằng giá trị trống trong `.env.example`. File mẫu chỉ dùng hướng dẫn cấu hình. Với runtime Python, giữ Start Command `SERVICEHUB_PORT=$PORT python server.py` và `SERVICEHUB_HOST=0.0.0.0`. Với Docker, giữ cấu hình khởi động có sẵn trong Dockerfile.

Hướng dẫn Render chính thức: https://render.com/docs/configure-environment-variables và https://render.com/docs/deploys.

Nếu thiếu cả hai biến, server vẫn phục vụ đăng ký/đăng nhập người dùng nhưng không tự tạo admin. Nếu chỉ có một biến hoặc cấu hình không hợp lệ, server dừng khởi động với thông báo cấu hình, không ghi mật khẩu vào log.

## Database từ phiên bản cũ

Trong lần nâng cấp đầu tiên, ba tài khoản `admin@servicehub.local`, `huy@servicehub.local`, `owner@servicehub.local` bị khóa đăng nhập, bỏ quyền admin cũ và thu hồi phiên. Dữ liệu ví, lịch sử giao dịch, lịch đặt và cơ sở vẫn được giữ lại.

Nếu chọn `admin@servicehub.local` làm admin riêng, server tái sử dụng bản ghi admin cũ bằng mật khẩu bí mật mới. Mật khẩu demo cũ không có hiệu lực. Các tài khoản người dùng khác không bị khóa.

Chế độ kiểm thử sử dụng `tests/fixture_server.py` với database trong thư mục tạm. Server thông thường không gọi seed tài khoản mẫu. Chạy toàn bộ kiểm tra bằng:

```bash
python3 scripts/run_checks.py
```

## Đổi mật khẩu về sau

Đổi `SERVICEHUB_ADMIN_PASSWORD` trong Render Environment và triển khai lại. Các phiên của admin đó bị thu hồi khi mật khẩu thay đổi. Đồng bộ giá trị trong `.env` local nếu cần cùng thông tin đăng nhập trên hai môi trường. Không dùng đường dẫn web công khai để tạo hoặc nâng quyền admin.

Đây là thay đổi bảo vệ đăng nhập; không tự giải quyết các vấn đề ví demo/tiền thật, hoàn tiền, tính điểm hoặc lưu trữ Render đã nêu trong báo cáo QA.
