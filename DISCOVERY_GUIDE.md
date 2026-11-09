# Nâng cấp trải nghiệm người dùng — Gợi ý dịch vụ theo câu hỏi

## 1. Mới có gì?

Ở **Trang chủ**, bấm **“✦ Gợi ý cho tôi”** hoặc cuộn xuống phần **“Hôm nay bạn muốn ăn gì hoặc làm gì?”**. Không cần đăng nhập để nhận gợi ý.

Người dùng lần lượt trả lời:

1. **Hôm nay bạn muốn ăn gì hoặc làm gì?** — Ăn uống, cà phê, thể thao, làm đẹp, spa hoặc khám phá bất ngờ.
2. **Bạn muốn trải nghiệm theo cách nào?** — Nhanh gọn, thư giãn, năng động hoặc không có ưu tiên.
3. **Bạn dự kiến chi bao nhiêu cho mỗi lượt?** — Dưới 100.000đ, 100.000–300.000đ, trên 300.000đ hoặc linh hoạt.

Sau đó nhấn **“Xem gợi ý phù hợp”**. Trang sẽ hiển thị tối đa ba dịch vụ từ dữ liệu đang có của `/api/services`, kèm lý do chọn; người dùng có thể mở chi tiết, đặt lịch, xem toàn bộ dịch vụ hoặc chọn lại.

Nếu không có dịch vụ phù hợp **cả loại hoạt động và ngân sách**, giao diện đề nghị thay đổi câu trả lời, **không tự dựng dữ liệu giả**. Giá `0` của dịch vụ trong dự án có nghĩa **“Liên hệ”**, nên chỉ hiện khi khách chọn ngân sách linh hoạt — không coi là miễn phí.

Các gợi ý là **lọc theo quy tắc**, không phải AI, không truy cập vị trí, không khẳng định lịch trống hoặc mức giá đã được xác nhận tại thời điểm đặt.

## 2. Những file đã cập nhật

| File | Thay đổi |
| --- | --- |
| `static/index.html` | Khu vực hỏi đáp ba bước ngay trên trang chủ; nút CTA; số lượng kết quả tìm kiếm |
| `static/css/styles.css` | Giao diện sáng, thẻ đáp án, progress, kết quả, responsive, focus keyboard và hỗ trợ giảm chuyển động |
| `static/js/advisor.js` **(mới)** | Quy tắc phân loại dịch vụ, lọc ngân sách, ưu tiên trải nghiệm và tạo lý do gợi ý |
| `static/js/app.js` | Tích hợp hỏi đáp với dữ liệu `/api/services`, tương tác, thông báo không có kết quả, điều hướng đặt lịch |
| `server.py` | Bổ sung một mục dịch vụ cà phê **demo, có nhãn rõ** cho quán cà phê demo (giữ nguyên API) |
| `tests/test_advisor.js` **(mới)** | Kiểm thử JavaScript không cần cài thêm thư viện |

Tất cả nghiệp vụ tài khoản, đặt lịch, ví demo và chủ cơ sở vẫn dùng API và thành phần hiện tại; phần tư vấn **không gửi dữ liệu câu trả lời lên server** và không tự thực hiện giao dịch.

## 3. Chạy trên MacBook

Cách không cần Docker:

```bash
cd ServiceHub_fullstack
python3 server.py
```

Truy cập `http://127.0.0.1:8000`. Khi chạy lần đầu ứng dụng tự tạo file database và dữ liệu demo. Nếu cổng 8000 đã được dùng, dừng server cũ trước khi khởi động phiên bản mới.

Cách sử dụng Docker (chỉ khi Docker Desktop **đang chạy**):

```bash
docker compose up -d --build
docker compose ps
```

Truy cập `http://127.0.0.1:8000`. Để dừng: `docker compose down`. **Không** dùng `docker compose down -v` nếu muốn giữ dữ liệu trong volume.

## 4. Kiểm thử

Chạy kiểm tra logic gợi ý (máy cần Node.js, **không phải** điều kiện để chạy web):

```bash
node --check static/js/app.js
node --check static/js/advisor.js
node tests/test_advisor.js
```

Với server đang chạy tại cổng 8000, kiểm thử backend:

```bash
python3 -m unittest discover -s tests -v
```

Demo nên thử: "Ăn một bữa ngon" → "Không quan trọng" → "100.000–300.000đ", sau đó thử "Spa" → "Nhanh gọn" → "Dưới 100.000đ" để quan sát trạng thái không có kết quả (tùy dữ liệu hiện tại).

## 5. Lưu ý khi phát triển tiếp

- Kết quả chỉ căn cứ dịch vụ hiện có từ API, không có đánh giá sao, khoảng cách địa lý hoặc kiểm tra chỗ trống tự động.
- Một dịch vụ được thay đổi giá/danh mục sẽ được phản ánh ở lần tải dữ liệu tiếp theo.
- Các quy tắc nằm trong `static/js/advisor.js`; hãy mở rộng nhãn nhóm khi có loại dịch vụ mới, kèm test mới để tránh gợi ý sai.
- Dữ liệu/demo account dùng để thử nghiệm; chưa đưa app lên Internet khi chưa rà soát bảo mật.
