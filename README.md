# ServiceHub — Full-stack MVP (6 Sprint)

Bản MVP chạy độc lập của ServiceHub: frontend HTML/CSS/JavaScript, backend API Python chuẩn và SQLite. Không cần cài thư viện Python bên ngoài.


## Quản lý dự án trên GitHub — 6 Sprint

- [Kế hoạch 6 Sprint](docs/SPRINTS_1_TO_6.md)

**Trạng thái:** mã nguồn hiện tại được phát triển đến Sprint 4; Sprint 5–6 là phần công việc tiếp theo cần nghiệm thu. Không coi test backend đạt đồng nghĩa toàn bộ UI đã qua test.

## Điểm mới — Bộ gợi ý theo sở thích

Trên **Trang chủ**, chọn **✦ Gợi ý cho tôi** để trả lời ba câu hỏi: hôm nay muốn ăn/làm gì, thích kiểu trải nghiệm nào và ngân sách bao nhiêu. Hệ thống lọc **dịch vụ thật từ API**, xếp hạng và hiển thị tối đa ba gợi ý có giải thích. Có thể quay lại/chọn lại, xem chi tiết hoặc đặt lịch. Không cần đăng nhập để nhận gợi ý và không gửi câu trả lời tới backend. Đây là đề xuất theo quy tắc, **không phải AI** và không khẳng định còn chỗ.

Xem hướng dẫn, các file liên quan và lệnh test trong **[DISCOVERY_GUIDE.md](DISCOVERY_GUIDE.md)**.

## 1. Yêu cầu

- Python 3.10 trở lên (đã kiểm tra bằng Python 3.13).
- Trình duyệt hiện đại.
- Không cần Node.js, npm hoặc thư viện Python bên ngoài.

## 2. Clone và chạy bản demo tổng hợp

Sau khi clone repository, mở Terminal trong thư mục dự án. Không cần cài thêm thư viện.

**macOS/Linux:**

```bash
git clone https://github.com/huyyl728/ServiceHub_Web.git
cd ServiceHub_Web
python3 scripts/start_demo.py
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/huyyl728/ServiceHub_Web.git
cd ServiceHub_Web
py -3 scripts/start_demo.py
```

Nếu đã clone trước đó, chỉ cần cập nhật mã nguồn và chạy lệnh Python tương ứng. Có thể dùng `python` thay `py -3` nếu Windows không có Python Launcher.

Mở địa chỉ được in khi server chạy (mặc định http://127.0.0.1:8001). Lần đầu tự tạo cấu hình, database và 7 tài khoản demo (1 Admin, 3 Customer, 3 Owner), 3 cơ sở và 6 dịch vụ. Thông tin đăng nhập Admin trong `.env`, thông tin Customer/Owner trong `.local-demo/main-credentials.json`. Không đưa các file này lên GitHub.

Trên macOS có thể chạy `./start-mac.command` (nếu cần: `chmod +x start-mac.command`); trên Windows mở `start-windows.bat`. Dừng bằng Ctrl+C. Nếu cổng bị chiếm, thêm `--port 8002`.

Bản demo sử dụng database riêng từng thư mục; chạy lại giữ dữ liệu. Nếu đã có database thông thường hay cấu hình khác, script từ chối ghi đè; hãy giữ dữ liệu và clone sang thư mục mới để chạy demo. Xem [hướng dẫn Local Demo](docs/LOCAL_DEMO.md).

### Chạy thông thường (không tạo demo)

Dùng `python3 server.py` (Windows: `py -3 server.py`) với cấu hình riêng. Để triển khai public, đặt `SERVICEHUB_LOCAL_DEMO=0`, sử dụng database không chứa dữ liệu demo; không sử dụng script khởi chạy demo.

### Chạy bằng Docker (tùy chọn)

Nếu đã cài Docker Desktop, từ thư mục dự án chạy:

```bash
docker compose up --build
```

Sau đó mở <http://127.0.0.1:8000>. Compose lưu database và ảnh tải lên trong volume để dữ liệu không biến mất khi container được tạo lại. Cấu hình này giúp chạy nhất quán hơn, nhưng **không tự biến ứng dụng thành production-ready**; vẫn cần reverse proxy HTTPS, bảo mật vận hành và các bước trong mục 8–9.

## 3. Tài khoản và quyền quản trị

Khách hàng đăng ký bằng email của mình; chủ cơ sở gửi hồ sơ xét duyệt. Các nút đăng nhập demo và tài khoản mặc định công khai đã được loại bỏ.

Admin riêng được cấu hình qua `SERVICEHUB_ADMIN_EMAIL` và `SERVICEHUB_ADMIN_PASSWORD`. Chạy `python3 scripts/setup_admin.py --email admin@servicehub.local` để tạo cấu hình bí mật và xem [hướng dẫn admin trên local/Render](docs/ADMIN_SETUP.md). Không commit mật khẩu, `.env` hoặc `.env.admin`.

## 4. Chức năng hiện có

- Đăng ký/đăng nhập/đăng xuất; mật khẩu băm bằng PBKDF2-HMAC-SHA256; phiên đăng nhập bearer token hết hạn sau 12 giờ.
- Một tài khoản vừa là khách hàng vừa có thể nộp hồ sơ chủ cơ sở.
- Admin xem, chấp thuận, yêu cầu bổ sung hoặc từ chối hồ sơ.
- Sau khi duyệt, người dùng có quyền quản lý cơ sở đã được tạo.
- Khám phá và tìm kiếm dịch vụ, lọc theo danh mục.
- Xem lịch trống và tạo lịch đặt; backend kiểm tra xung đột thời gian.
- Khách hàng xem/hủy lịch; chủ cơ sở xác nhận/hoàn thành/hủy lịch.
- Chủ cơ sở tạo, sửa, tạm ngừng và mở lại dịch vụ.
- Chủ cơ sở tải ảnh banner riêng cho cơ sở PNG/JPEG/WebP tối đa 5 MB; ảnh lưu trong `static/uploads`, đường dẫn lưu trong SQLite và hiển thị trên thẻ dịch vụ nếu dịch vụ chưa có ảnh riêng.
- Mỗi dịch vụ có trường `services.image_path` và nút **Thêm ảnh dịch vụ / Đổi ảnh dịch vụ** riêng. Ảnh của dịch vụ A không ghi đè ảnh dịch vụ B; ảnh banner cơ sở và ảnh từng dịch vụ là hai loại dữ liệu độc lập. Sau upload, frontend tải lại danh sách chủ cơ sở và catalog công khai để đồng bộ trang chủ/danh sách.
- Upload banner và ảnh dịch vụ kiểm tra định dạng, chữ ký tệp và dung lượng; chặn gửi lặp ở giao diện và xử lý lỗi API rõ ràng. Có migration tự bổ sung cột ảnh nếu database được tạo từ phiên bản cũ. Giới hạn request body đủ cho ảnh 5 MB mã hóa Base64.
- Dữ liệu demo bổ sung cho nhà hàng, salon, spa, sân thể thao và quán cà phê; các cơ sở được ghi rõ là demo và dùng ảnh minh họa SVG được đóng gói sẵn trong dự án.
- Trang 404 tùy chỉnh, trang cảm ơn, chính sách quyền riêng tư mẫu, breadcrumb, FAQ, case study minh họa, CTA trên màn hình đầu và CTA cố định trên mobile.
- Meta description/title theo view, Open Graph/social share image, alt text, link chỉ đường Google Maps và schema JSON-LD mẫu.
- `robots.txt` và tích hợp GA4 tùy chọn trong `static/js/analytics.js`; GA không chạy cho đến khi cấu hình Measurement ID và có consent.
- Nội dung đánh giá, case study, đội ngũ và cơ sở được đánh dấu demo; không được xem là đánh giá hoặc doanh nghiệp đã xác minh.
- Hồ sơ khách hàng có họ tên, email, số điện thoại và địa chỉ liên hệ; chủ cơ sở lưu/cập nhật tên, loại hình, địa chỉ, số điện thoại, mô tả và banner.
- Chương trình hội viên nền tảng và chương trình riêng của cơ sở; tham gia chương trình.
- Thông báo trong dữ liệu backend và thống kê cơ bản cho admin.
- API health check tại `/api/health`.

## Kiểm thử

Chạy `python3 scripts/run_checks.py`. Bộ test tự chạy server với tài khoản fixture trên SQLite tạm; không dùng server đang có dữ liệu thật. Server chạy bình thường không tự tạo tài khoản demo. Kiểm thử gồm quyền admin, khóa tài khoản/phiên demo cũ và giới hạn đọc tệp static.

## 5. Cấu trúc thư mục

```text
ServiceHub_fullstack/
├── server.py                 # HTTP server, API routes, auth, business logic
├── schema.sql                # Database tables, indexes and relationships
├── servicehub.db             # SQLite DB tự sinh khi chạy lần đầu
├── static/
│   ├── 404.html
│   ├── thank-you.html
│   ├── privacy.html
│   ├── robots.txt
│   ├── images/social-share.svg
│   ├── images/social-share.png
│   ├── images/demo-restaurant.svg, demo-salon.svg, demo-spa.svg, demo-sport.svg, demo-cafe.svg
│   ├── images/team-demo.svg
│   ├── index.html            # Giao diện SPA
│   ├── css/styles.css        # Design tokens, components, responsive layout
│   ├── js/api.js             # Lớp gọi API và quản lý phiên phía client
│   ├── js/app.js             # Điều hướng, rendering và event handlers
│   ├── js/analytics.js       # GA4 tùy chọn, tắt mặc định
│   └── uploads/              # Ảnh chủ cơ sở tải lên
├── tests/test_smoke.py       # Kiểm tra API cơ bản
└── README.md
```

### Để dễ sửa/debug

- Đổi màu/khoảng cách chung: sửa biến CSS trong `static/css/styles.css` phần `:root`.
- Thêm/sửa endpoint backend: tìm phần `def api()` trong `server.py`.
- Tập trung logic gọi API: `static/js/api.js`.
- Sửa giao diện và event handlers: `static/js/app.js`.
- Kiểm tra lỗi trình duyệt: DevTools → Console và Network.
- Kiểm tra dữ liệu: dùng SQLite browser hoặc chạy `sqlite3 servicehub.db` nếu máy đã có SQLite CLI.

## 6. API chính

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`
- `GET /api/me`, `PUT /api/me`
- `GET /api/services`, `GET /api/categories`
- `POST /api/business-applications`, `GET /api/business-applications/me`, `PUT /api/business-applications/{id}`
- `GET /api/admin/applications`, `POST /api/admin/applications/{id}/approve|changes|reject`
- `GET /api/businesses/managed`, `PUT /api/owner/businesses/{id}`
- `GET|POST /api/owner/services`, `PUT|DELETE /api/owner/services/{id}`
- `GET /api/owner/bookings?business_id={id}`
- `GET /api/services/{id}/availability?date=YYYY-MM-DD`
- `POST /api/bookings`, `GET /api/bookings/me`, `POST /api/bookings/{id}/cancel`
- `GET /api/activity/me` (lịch sử hoạt động của tài khoản)
- `GET /api/memberships/me`, `POST /api/memberships/{id}/join`, `GET /api/activity/me`
- `POST /api/media/upload` (banner cơ sở), `POST /api/owner/services/{id}/image` (ảnh riêng từng dịch vụ), `GET /api/admin/stats`, `GET /api/health`

Các API riêng tư dùng header `Authorization: Bearer <token>`.

## 8. Lưu ý kiến trúc và bảo mật

Bản MVP dùng Python standard library + SQLite để dễ chạy local và không yêu cầu cài thêm dependency. Đây là một lựa chọn triển khai thực nghiệm khác với phương án mục tiêu ASP.NET Core + SQL Server trong tài liệu kiến trúc. Nếu môn học bắt buộc ASP.NET Core/SQL Server, cần chuyển backend và schema sang stack đó.

Một số điểm production vẫn cần bổ sung trước khi mở công khai:

- Dùng framework web được duy trì và middleware bảo mật; giới hạn đăng nhập và chống brute force.
- Thiết lập HTTPS, CORS/CSRF phù hợp, secret và session store an toàn.
- Chuyển SQLite sang SQL Server/PostgreSQL khi triển khai nhiều người dùng.
- Lưu ảnh vào object storage, quét và kiểm tra nội dung tệp.
- Thêm kiểm thử tự động đầy đủ, migrations, backup, monitoring và audit policy.
- Review kỹ concurrency của đặt lịch và quyền truy cập trước khi public.


## 9. Những việc cần cấu hình trước khi public

- Thay `localhost:8000` trong schema bằng domain thật; cấu hình sitemap và robots.txt cho domain khi triển khai.
- Cập nhật nội dung chính sách quyền riêng tư với quy trình thu thập/xử lý dữ liệu thật.
- Trong `static/js/analytics.js`, điền GA4 Measurement ID của dự án và chỉ bật sau khi triển khai cơ chế xin consent phù hợp.
- Thay ảnh demo SVG bằng ảnh được cấp quyền sử dụng của các cơ sở thật; xin phép trước khi đăng ảnh đội ngũ/đối tác.
- Chỉ hiển thị review thật khi có nguồn và sự đồng ý; các review hiện tại là mẫu demo có ghi nhãn.
- Các URL Google Maps sử dụng tìm kiếm theo địa chỉ demo; xác minh địa chỉ chính xác trước khi đưa vào production.

## Nâng cấp: chi tiết cơ sở và hội viên theo từng quán

- Nhấn vào ảnh hoặc tên dịch vụ để mở thông tin cơ sở: giới thiệu, địa chỉ, số điện thoại, bản đồ, các dịch vụ/thực đơn và giá.
- Mỗi cơ sở hiển thị chương trình hội viên riêng nếu đã thiết lập chương trình.
- Người dùng đăng nhập để tham gia chương trình hội viên; trạng thái tham gia và điểm tích lũy được lưu trong SQLite, liên kết với đúng chương trình của cơ sở.
- Danh sách hội viên đã tham gia vẫn hiển thị trong mục Tài khoản → Hội viên.

## Sprint 4 — Hoàn thiện bản demo (bản nâng cấp 08/11/2026)

Bản này kế thừa Sprint 1–3 và tính năng tư vấn ba câu hỏi. Các bổ sung:

- **Thông báo trong tài khoản:** chuông hiển thị số chưa đọc; xem, đánh dấu một thông báo hoặc toàn bộ đã đọc. Có thông báo cho lịch đặt, hội viên, nạp/chuyển ví mô phỏng và thay đổi trạng thái cơ sở.
- **Chủ cơ sở:** xem danh sách hội viên đã tham gia chương trình của cơ sở mình; API bảo đảm chỉ chủ sở hữu xem được.
- **Kiểm thử Sprint 4:** thêm `tests/test_sprint4.py` với database SQLite tạm, script `scripts/run_checks.py`, CI GitHub Actions `.github/workflows/ci.yml`.
- **Khắc phục:** đường dẫn `/api/businesses/managed` không còn bị route chi tiết cơ sở công khai chặn nhầm.

**Chạy tất cả kiểm thử mà không thay đổi DB của bạn:** `python3 scripts/run_checks.py`. Xem [`SPRINT4_REPORT.md`](SPRINT4_REPORT.md) để đọc bảng chức năng, kết quả, giới hạn và phân công cho nhóm bốn người.

> Đây vẫn là MVP chạy local/LAN với dữ liệu demo, **không phải production**. Ví chỉ mô phỏng, không tích hợp ngân hàng. Cần rà soát an toàn trước khi đưa ra Internet. Không sử dụng tài khoản demo khi triển khai công khai.

### Nếu MacBook đã dùng cổng 8000

- Chạy Python riêng bản Sprint 4: `SERVICEHUB_PORT=8001 python3 server.py` rồi mở `http://127.0.0.1:8001`.
- Chạy bằng Docker trên cổng 8001: `SERVICEHUB_HOST_PORT=8001 docker compose up -d --build`. Bên trong container vẫn là cổng 8000.
- Nếu chạy nhiều phiên bản, dùng **database riêng** cho bản mới, không trỏ nhầm vào file của bản cũ. Không xóa Docker volume khi muốn giữ dữ liệu.
