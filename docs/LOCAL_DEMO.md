# Thuyết trình local: 3 Customer + 3 Owner

Script `scripts/seed_local_demo.py` tạo **đúng 6 tài khoản demo**, 3 cơ sở,
6 dịch vụ và 3 hồ sơ cơ sở đã được duyệt trong database riêng
`.local-demo/servicehub-demo.db`. Không dùng `tests/fixture_server.py` để trình bày.
Khởi động `server.py` bình thường vẫn không tạo tài khoản demo.

## Chạy trên máy cá nhân

Cần Python 3.10 trở lên; chỉ dùng thư viện chuẩn. Chạy từ thư mục gốc repository.
Dùng một bản checkout local sạch, không mang cấu hình triển khai hosting vào đây.

```sh
SERVICEHUB_ENV=local-demo \
SERVICEHUB_HOST=127.0.0.1 \
SERVICEHUB_DB_PATH="$PWD/.local-demo/servicehub-demo.db" \
SERVICEHUB_ENABLE_BANK_QR=0 \
SERVICEHUB_ADMIN_EMAIL='' SERVICEHUB_ADMIN_PASSWORD='' \
python3 scripts/seed_local_demo.py --local-demo \
  --credentials-file ../servicehub-demo-credentials.json --serve
```

Mở <http://127.0.0.1:8000>; nhấn Ctrl+C để dừng. Nếu cổng bận, thêm
`SERVICEHUB_PORT=8002` vào các biến môi trường và mở cổng tương ứng.
Bỏ `--serve` nếu chỉ muốn seed, chưa mở website.

Nếu đã được bàn giao file JSON, đặt file đó **ngoài repository** rồi thay đường dẫn
`--credentials-file` bằng đường dẫn tới file. Trên macOS/Linux chạy
`chmod 600 /duong/dan/toi/servicehub-demo-credentials.json` nếu cần.
Không có file thì script tự sinh 6 mật khẩu ngẫu nhiên, riêng biệt, dài 24 ký tự;
file mới có quyền `0600`. Thư mục cha phải tồn tại. Script không in mật khẩu.
File JSON chứa `username`, `email`, `role`, `password`; giữ file này để chạy lại.
Không đưa file vào Git, ảnh chụp bài thuyết trình, PR hoặc thư mục `static`.

## Tài khoản và dữ liệu

Ứng dụng **đăng nhập bằng email**, không hỗ trợ đăng nhập bằng username.
Username dưới đây là mã nhận diện trong file bàn giao, không phải cột mới trong DB.

| Username | Email đăng nhập | Vai trò | Cơ sở |
|---|---|---|---|
| customer01 | customer01@demo.servicehub.test | Customer | Không sở hữu cơ sở |
| customer02 | customer02@demo.servicehub.test | Customer | Không sở hữu cơ sở |
| customer03 | customer03@demo.servicehub.test | Customer | Không sở hữu cơ sở |
| owner01 | owner01@demo.servicehub.test | Owner | Sân Thể Thao (Demo Local) |
| owner02 | owner02@demo.servicehub.test | Owner | Mộc Hair (Demo Local) |
| owner03 | owner03@demo.servicehub.test | Owner | Bếp Việt (Demo Local) |

Mỗi Owner sở hữu đúng một cơ sở có 2 dịch vụ, ảnh SVG sẵn có, một hồ sơ
`approved` liên kết đúng `user_id`/`business_id`, và một chương trình hội viên.
Quyền Owner theo cơ chế hiện hành `businesses.owner_id`; không có cột role riêng.
Cả 6 tài khoản đều `is_admin=0`, `login_enabled=1`.

Mỗi Customer nhận 1.000.000 **số dư ví hư cấu** và một dòng lịch sử `demo_credit`
để thử thanh toán lịch đặt. Owner bắt đầu với số dư 0. Không có ngân hàng,
thẻ, giao dịch thực hoặc thông tin liên hệ thật. Không tạo lịch đặt trước để tránh
ngày trình bày bị hết hạn; hãy đặt lịch vào ngày hiện tại hoặc tương lai.

Gợi ý trình bày: đăng nhập customer01, đặt sân → đăng nhập owner01 để xác nhận
→ quay lại customer01 để thanh toán bằng ví demo. Owner02/03 không thể quản lý
lịch hoặc dịch vụ của owner01. Ba Customer có thể đặt dịch vụ tại mọi cơ sở.

## Chạy lại và bảo vệ môi trường công khai

- Chạy lại đúng lệnh và file JSON sẽ xác minh tài khoản hiện có; không nhân đôi,
  không đổi mật khẩu, không ghi đè dịch vụ đã sửa, không cộng lại số dư đã tiêu.
- Mật khẩu dùng trực tiếp `server.hash_password`: PBKDF2-HMAC-SHA256, 240.000 vòng,
  salt ngẫu nhiên 16 byte. Database chỉ lưu hash; JSON riêng là nơi giữ mật khẩu.
- Seed cần cả `--local-demo` và `SERVICEHUB_ENV=local-demo`. Chỉ cho phép loopback,
  đúng đường dẫn DB riêng, QR tắt và không cấu hình admin. Hosting đã nhận diện
  (Render, Heroku, Fly, Cloud Run, Vercel, AWS, Azure) và chế độ production/staging
  bị từ chối. Không đưa demo qua tunnel, reverse proxy công khai hoặc triển khai hosting.
- Database có marker `local_demo_seed_v1`. Khi `server.py` mở database này,
  nó yêu cầu `SERVICEHUB_LOCAL_DEMO=1`, `SERVICEHUB_ENV=local-demo` và cùng các
  điều kiện local trước khi mở HTTP. Script tự đặt cờ đầu tiên khi đã có `--local-demo`.
  Copy DB demo sang đường dẫn production hoặc đổi host thành `0.0.0.0` sẽ bị chặn.
- Script từ chối database có dữ liệu nhưng thiếu marker; không nhận làm dữ liệu demo
  một tài khoản có sẵn, không cấp quyền hoặc đặt lại mật khẩu cho tài khoản đó.
- Nếu thiếu file mật khẩu gốc, mật khẩu thay đổi, tài khoản bị khóa hoặc quan hệ sở hữu
  bị sửa, script báo lỗi và không âm thầm đặt lại dữ liệu. Khôi phục file JSON/DB
  tương ứng. Để làm lại hoàn toàn, dừng máy chủ và di chuyển thư mục `.local-demo`
  sang nơi sao lưu ngoài repo; chạy lại với file JSON cũ hoặc một tên file mới.
- `.local-demo`, SQLite, file mật khẩu có tên `*demo-credentials*.json` được loại khỏi
  Git/Docker. Không commit `.env`, mật khẩu, hash của bộ bàn giao hoặc database demo.

## Kiểm thử

```sh
python3 scripts/run_checks.py
```

Các kiểm thử mới dùng thư mục tạm và mật khẩu sinh trong lúc chạy: số lượng/quan hệ,
hash, seed lặp lại, rollback, va chạm dữ liệu, guard public/production, file bí mật,
6 lần đăng nhập thật qua API, giới hạn Owner, đặt lịch/xác nhận/thanh toán ví demo.
Không cần file mật khẩu thuyết trình để chạy kiểm thử.
