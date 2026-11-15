# ServiceHub — Review API

## 1. Overview

- Sprint: 4
- Task: S4R-02
- Issue: #33
- Database: SQLite
- Backend: Python
- Format: JSON

## 2. Business Rules

- Người đánh giá phải sở hữu booking.
- Booking phải có trạng thái completed.
- Mỗi booking chỉ có một review.
- Rating là số nguyên từ 1 đến 5.
- Comment tối đa 1000 ký tự.
- Chỉ chủ sở hữu review được chỉnh sửa.
- Review bị ẩn không được chỉnh sửa.
- Review bị ẩn không tính vào điểm công khai.

## 3. Authentication

Các API yêu cầu đăng nhập sử dụng:

Authorization: Bearer <token>
Content-Type: application/json

## 4. API Endpoints

| Method | Endpoint                   | Auth |
| ------ | -------------------------- | ---- |
| POST   | /api/reviews               | Yes  |
| PUT    | /api/reviews/{id}          | Yes  |
| GET    | /api/reviews/me            | Yes  |
| GET    | /api/reviews?business_id=1 | No   |
| GET    | /api/reviews?service_id=1  | No   |

## 5. Create Review

POST /api/reviews

Request:

```json
{
  "booking_id": 1,
  "rating": 5,
  "comment": "Dịch vụ rất tốt."
}
```

Response: 201 Created

Backend tự xác định user_id, business_id
và service_id từ dữ liệu booking.

## 6. Update Review

PUT /api/reviews/{id}

Request:

```json
{
  "rating": 4,
  "comment": "Nội dung đã cập nhật."
}
```

Response: 200 OK

Không cho phép thay đổi booking_id,
user_id, business_id, service_id
hoặc is_visible thông qua API này.

## 7. Personal Reviews

GET /api/reviews/me

Response: 200 OK

Trả về danh sách đánh giá của người
đang đăng nhập, bao gồm review bị ẩn.

Frontend sử dụng booking_id để liên kết
review với lịch sử đặt lịch.

## 8. Public Reviews

GET /api/reviews?business_id=1&page=1

Hoặc:

GET /api/reviews?service_id=1&page=1

Example response:

```json
{
  "success": true,
  "data": {
    "average_rating": 5.0,
    "review_count": 1,
    "page": 1,
    "page_size": 20,
    "reviews": [
      {
        "id": 1,
        "business_id": 1,
        "service_id": 2,
        "rating": 5,
        "comment": "Dịch vụ tốt.",
        "customer_name": "Customer",
        "created_at": "2026-11-15 14:00:00",
        "updated_at": "2026-11-15 14:00:00"
      }
    ]
  }
}
```

- Tối đa 20 review mỗi trang.
- Chỉ truyền business_id hoặc service_id.
- Chỉ trả về review công khai.
- average_rating là null nếu chưa có review.

## 9. Error Codes

| HTTP | Error Code              |
| ---- | ----------------------- |
| 400  | INVALID_RATING          |
| 400  | INVALID_COMMENT         |
| 400  | COMMENT_TOO_LONG        |
| 400  | INVALID_BOOKING_ID      |
| 400  | INVALID_REVIEW_ID       |
| 400  | INVALID_REVIEW_FILTER   |
| 400  | INVALID_ID              |
| 400  | INVALID_PAGE            |
| 401  | AUTH_REQUIRED           |
| 404  | BOOKING_NOT_FOUND       |
| 404  | REVIEW_NOT_FOUND        |
| 404  | REVIEW_TARGET_NOT_FOUND |
| 409  | BOOKING_NOT_COMPLETED   |
| 409  | REVIEW_ALREADY_EXISTS   |
| 409  | REVIEW_HIDDEN           |

## 10. Frontend Integration

- Chỉ hiện nút đánh giá với booking completed.
- Sử dụng GET /api/reviews/me để kiểm tra
  booking đã được đánh giá hay chưa.
- Hiển thị nút chỉnh sửa nếu review được phép sửa.
- Không tự tính điểm từ một trang review.
- Sử dụng average_rating và review_count từ API.
- Escape comment và customer_name trước khi render.
- Không chèn trực tiếp bình luận vào innerHTML.

## 11. Testing

Run review tests:

    python3 -m unittest discover -s tests -p 'test_reviews.py' -v

Run all checks:

    python3 scripts/run_checks.py

Local verification (2026-11-15):

- Existing Python tests: 27/27 PASS
- Review integration tests: 15/15 PASS
- Total Python tests: 42/42 PASS
- JavaScript syntax: PASS
- Advisor tests: PASS

## 12. Related Tasks

- S4R-03: Customer review interface
- S4R-04: Public reviews and ratings
- S4R-05: Admin statistics API
- S4R-07: Review moderation
- S4R-08: Sprint integration testing

Admin moderation endpoints are outside
the scope of S4R-02.
