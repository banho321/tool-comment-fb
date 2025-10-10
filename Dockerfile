# Sử dụng base image chính thức của Playwright cho Python
# Image này đã bao gồm tất cả các dependencies cần thiết cho trình duyệt
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Sao chép file requirements.txt trước để tận dụng Docker cache
# Chỉ khi file này thay đổi, các lệnh sau mới chạy lại
COPY requirements.txt .

# Cài đặt các thư viện Python
# --no-cache-dir để giảm kích thước image
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt các trình duyệt cho Playwright (đã có trong image base nhưng chạy lại để chắc chắn)
# RUN playwright install --with-deps

# Sao chép toàn bộ mã nguồn của ứng dụng vào thư mục làm việc
COPY . .

# Mở cổng 5000 để có thể truy cập dashboard từ bên ngoài container
EXPOSE 5000

# Lệnh mặc định khi container khởi chạy
# Chạy bot với các tham số mặc định. Bạn có thể ghi đè khi chạy container.
# Ví dụ: docker run <image_name> --account my_acc --dry-run
CMD ["python", "main.py", "--account", "default_account"]