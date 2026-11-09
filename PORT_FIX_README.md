# Sửa lỗi Errno 48 khi chạy ServiceHub VietQR

**Nguyên nhân:** Bản trước có `.env.example` chỉ đặt `SERVICEHUB_HOST_PORT=8001`, trong khi `server.py` đọc `SERVICEHUB_PORT`. Vì vậy chạy Python trực tiếp lại dùng cổng mặc định 8000.

**Đã sửa:**
- `server.py` đọc `SERVICEHUB_PORT` trước, sau đó dùng `SERVICEHUB_HOST_PORT` nếu thiếu.
- `.env.example` có cả hai biến để chạy Python và Docker Compose.
- Bổ sung giải thích trong `BANK_QR_GUIDE.md`.

**Chạy bằng Python trên Mac:**
```bash
set -a
source .env
set +a
python3 server.py
```

Dòng đầu log phải hiển thị `127.0.0.1:8001` nếu `.env` có một trong hai biến cổng bằng 8001. Không nên dừng Docker hay tiến trình khác nếu chỉ cần chạy bản mới trên cổng khác.

**Chạy bằng Docker Compose:**
```bash
docker compose --env-file .env up -d --build
```

Không đưa file `.env` chứa thông tin ngân hàng lên Git. Hãy kiểm tra QR với dữ liệu demo và không cần chuyển tiền thật.
