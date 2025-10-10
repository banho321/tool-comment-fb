# Tool Tự Động Tương Tác Facebook Group

Đây là một công cụ tự động hóa được xây dựng bằng Python và Playwright, được thiết kế để quét các bài viết trong các group Facebook đã tham gia, tìm kiếm các bài đăng khớp với từ khóa sản phẩm và tự động bình luận với link bán hàng (ví dụ: Shopee).

Tool được xây dựng với mục tiêu giảm thiểu rủi ro bị đánh dấu là spam bằng cách chỉ tương tác với các bài viết có liên quan.

## Tính năng chính

- **Quét bài viết thông minh**: Tự động vào các group và quét các bài viết mới nhất.
- **Đối sánh từ khóa**: So khớp nội dung bài viết với danh sách sản phẩm (bao gồm cả tên đầy đủ và tên viết tắt/bí danh).
- **Bình luận tự động**: Đăng bình luận theo các mẫu có sẵn, với link sản phẩm tương ứng.
- **Quản lý phiên đăng nhập an toàn**: Sử dụng `login_helper` để đăng nhập thủ công một lần và lưu lại session, không cần lưu mật khẩu.
- **Chống spam**: Tích hợp nhiều cơ chế an toàn:
  - Giới hạn số lượng bình luận mỗi giờ và mỗi ngày.
  - Thời gian chờ ngẫu nhiên giữa các hành động.
  - Mô phỏng hành vi người dùng (cuộn trang, thích bài viết).
  - Chế độ "chạy thử" (`dry-run`) để kiểm tra mà không đăng thật.
- **Dashboard Web**: Giao diện web để theo dõi hoạt động, xem thống kê, lịch sử bình luận.
- **Dễ dàng triển khai**: Đóng gói bằng Docker để chạy ở bất kỳ đâu.

## Cấu trúc thư mục

```
.
├── app.py              # Web server Flask cho dashboard
├── config.yaml         # File cấu hình chính cho bot
├── data/               # Thư mục chứa dữ liệu đầu vào và database
│   ├── facebook_bot.db # Database SQLite (tự động tạo)
│   ├── groups.txt      # Danh sách group ID
│   ├── products.csv    # Danh sách sản phẩm và từ khóa
│   └── templates.txt   # Các mẫu bình luận
├── Dockerfile          # File để build Docker image
├── main.py             # Script chính để chạy bot
├── README.md           # File hướng dẫn này
├── requirements.txt    # Danh sách các thư viện Python
├── sessions/           # Thư mục chứa các phiên đăng nhập đã lưu
│   └── (trống)
├── src/                # Thư mục chứa mã nguồn các module
│   ├── commenter.py
│   ├── crawler.py
│   ├── db.py
│   ├── login_helper.py
│   └── matcher.py
│   └── utils.py
└── templates/          # Thư mục chứa template HTML cho dashboard
    ├── index.html
    └── error.html
```

## Hướng dẫn cài đặt và sử dụng

### 1. Chuẩn bị môi trường

**Cách 1: Cài đặt thủ công (Trên máy của bạn)**

a. Clone repository này về máy.

b. Cài đặt các thư viện Python cần thiết:
```bash
pip install -r requirements.txt
```

c. Cài đặt các trình duyệt cho Playwright:
```bash
playwright install --with-deps
```

**Cách 2: Sử dụng Docker (Khuyến khích)**

a. Cài đặt [Docker](https://www.docker.com/get-started) trên máy của bạn.

b. Build Docker image từ `Dockerfile`:
```bash
docker build -t facebook-bot .
```

### 2. Cấu hình

Trước khi chạy, bạn cần chuẩn bị các file dữ liệu và cấu hình:

a. **`data/products.csv`**:
   - Thêm các sản phẩm của bạn vào file này.
   - Cột `aliases` phải là một mảng JSON (ví dụ: `["viết tắt 1", "viết tắt 2"]`).

b. **`data/groups.txt`**:
   - Thêm ID của các group bạn muốn quét, mỗi ID một dòng.
   - Bạn có thể lấy ID từ URL của group (ví dụ: `facebook.com/groups/1234567890`).

c. **`data/templates.txt`**:
   - Thêm các mẫu bình luận bạn muốn sử dụng.
   - Sử dụng placeholder `{link}` để tool tự động chèn link Shopee.

d. **`config.yaml`**:
   - Chỉnh sửa các tham số như giới hạn bình luận, từ khóa blacklist, v.v. theo nhu cầu của bạn.

### 3. Đăng nhập và Lưu Session

Đây là bước **bắt buộc** phải làm đầu tiên.

- Chạy `login_helper` với một tên định danh cho tài khoản của bạn (ví dụ: `acc1`).
- Một cửa sổ trình duyệt sẽ mở ra. Hãy đăng nhập vào Facebook.
- Sau khi đăng nhập thành công, quay lại cửa sổ dòng lệnh và nhấn `Enter`.
- Session sẽ được lưu tại `sessions/acc1/storage_state.json`.

**Lệnh (chạy thủ công):**
```bash
python src/login_helper.py --account acc1
```

**Lệnh (chạy với Docker):**
*Lưu ý: Docker không thể mở cửa sổ trình duyệt trên máy bạn một cách trực tiếp. Bạn nên chạy bước này thủ công.*

### 4. Chạy Bot

Sau khi đã có session, bạn có thể chạy bot để bắt đầu làm việc.

**Chạy toàn bộ quy trình (Quét -> Lọc -> Bình luận):**
```bash
# Thủ công
python main.py --account acc1

# Với Docker
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/sessions:/app/sessions facebook-bot --account acc1
```

**Chạy với chế độ `dry-run` (an toàn, không bình luận thật):**
```bash
# Thủ công
python main.py --account acc1 --dry-run

# Với Docker
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/sessions:/app/sessions facebook-bot --account acc1 --dry-run
```

**Chỉ chạy một bước (ví dụ: chỉ quét bài viết):**
```bash
python main.py --account acc1 --skip-matcher --skip-commenter
```

### 5. Xem Dashboard

Chạy web server để xem giao diện theo dõi.

**Lệnh (chạy thủ công):**
```bash
python app.py
```
Sau đó, mở trình duyệt và truy cập `http://127.0.0.1:5000`.

**Lệnh (chạy với Docker):**
```bash
# Chạy container ở chế độ nền (-d) và ánh xạ cổng 5000
docker run -d -p 5000:5000 --rm -v $(pwd)/data:/app/data --name fb-dashboard facebook-bot python app.py
```
Sau đó, mở trình duyệt và truy cập `http://localhost:5000`.

Để dừng dashboard, chạy: `docker stop fb-dashboard`.