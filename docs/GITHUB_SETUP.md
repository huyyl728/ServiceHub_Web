# ĐƯA SERVICEHUB LÊN GITHUB — 6 SPRINT, 6 MILESTONE, 30 ISSUE

Bộ này được tạo cho tài khoản GitHub **`huyyl728`** với repository mới **`ServiceHub-6-Sprints`** ở chế độ **Private**.

## 1. Điều gì đã chuẩn bị sẵn?

- Mã nguồn ServiceHub Python, SQLite, HTML/CSS/JS, bản QR/VietQR demo, Docker/CI và các tệp test.
- `docs/GITHUB_BACKLOG.json`: kế hoạch 6 Milestone và 30 Issue, mỗi Sprint 5 Issue.
- `docs/SPRINT_1.md` đến `docs/SPRINT_6.md`: hồ sơ từng Sprint với Issue, trạng thái, bằng chứng và phần việc chưa nghiệm thu. Đây là các tài liệu cập nhật; phần còn lại của hướng dẫn này lưu lại quy trình xuất bản GitHub lịch sử.
- `scripts/publish_github.py`: công cụ xuất bản, tự tạo repo Private, commit/push code, tạo nhãn, Milestone, Issue; có thể chạy lại để tránh trùng.
- Không có file `.env`, cơ sở dữ liệu cá nhân hay ảnh người dùng tải lên trong gói ZIP này.

## 2. Các bước trên MacBook

**Bước 1.** Giải nén ZIP, mở Terminal trong thư mục `ServiceHub-6-Sprints`.

```bash
cd ~/Downloads/ServiceHub-6-Sprints
```

Nếu bạn giải nén ở nơi khác, hãy thay đường dẫn bằng thư mục thực tế.

**Bước 2.** Cài GitHub CLI nếu chưa có:

```bash
brew install gh
```

Yêu cầu có Homebrew. Hoặc tải GitHub CLI từ https://cli.github.com/.

**Bước 3.** Đăng nhập tài khoản GitHub:

```bash
gh auth login
```

Chọn GitHub.com, HTTPS, rồi làm theo hướng dẫn đăng nhập trên trình duyệt. **Không gửi token, mật khẩu hay mã xác thực cho người khác.**

**Bước 4.** Xem trước (chưa tạo gì trên GitHub):

```bash
python3 scripts/publish_github.py --dry-run
```

Bạn sẽ thấy `Milestones: 6`, `Issues: 30` và `PRIVATE`.

**Bước 5.** Xuất bản:

```bash
python3 scripts/publish_github.py --publish
```

Script sẽ lần lượt: xác nhận tài khoản GitHub đúng `huyyl728`, tạo commit local, tạo repo Private và push `main`, thêm nhãn, 6 Milestone và 30 Issue.

**Bước 6.** Kiểm tra GitHub:

- Repo: https://github.com/huyyl728/ServiceHub-6-Sprints
- Issues: https://github.com/huyyl728/ServiceHub-6-Sprints/issues
- Milestones: https://github.com/huyyl728/ServiceHub-6-Sprints/milestones
- Source: https://github.com/huyyl728/ServiceHub-6-Sprints/blob/main/server.py

## 3. Sau khi xuất bản

- Vào **Settings → Collaborators** trên GitHub để mời 3 thành viên còn lại; chỉ mời đúng người bạn tin tưởng.
- Mỗi người nhận 5 Test Case trong tệp `docs/ServiceHub_20_TestCases_4_ThanhVien.xlsx`, báo cáo Pass/Fail và bằng chứng cho các Issue liên quan.
- **Không đóng Issue tự động:** mã nguồn có chức năng không đủ để chứng minh đã qua kiểm thử thủ công hay đã nghiệm thu.
- Có thể chạy lại `--publish`: script kiểm tra repo/Milestone/Issue đã tồn tại để tránh tạo trùng. Nếu repo đã có lịch sử không tương thích, Git sẽ từ chối push; script không force-push.

## 4. Quan trọng về thanh toán

Tính năng VietQR sinh mã có thể dùng để chuyển khoản **thật** khi cấu hình ngân hàng thật trong `.env` trên máy. QR **không phải xác nhận giao dịch đã thành công**. Phiên bản này lưu yêu cầu `pending` và chỉ admin đối soát thủ công trước khi xác nhận. Không được commit `.env`, tài khoản ngân hàng thật, database hoặc dữ liệu khách hàng lên GitHub.

## 5. Nếu gặp lỗi

- `gh: command not found`: cài GitHub CLI.
- `You are not logged into any GitHub hosts`: chạy `gh auth login`.
- `Not Found`/`Forbidden` khi tạo repo: kiểm tra tài khoản GitHub và quyền tạo repo.
- `git push` bị từ chối: gửi phần **lỗi không chứa token** để kiểm tra; không dùng `--force` khi chưa đối chiếu lịch sử.
- Không có Node.js: kiểm thử JavaScript có thể thiếu một bước, nhưng mã nguồn vẫn xuất bản được; cài Node.js khi cần kiểm thử đầy đủ.
