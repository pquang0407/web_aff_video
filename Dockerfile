FROM python:3.12-slim

# Thiết lập môi trường không tương tác & không tạo file .pyc
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Cài đặt FFmpeg, font chữ cho phụ đề, curl và các công cụ cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Sao chép file cấu hình thư viện và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn
COPY . .

# Tạo sẵn các thư mục storage
RUN mkdir -p storage/1_raw storage/2_web_full storage/3_social_teaser

# Mở cổng 5050 cho Web Admin
EXPOSE 5050

# Chạy Master Cloud Daemon 24/7
CMD ["python", "main_cloud_daemon.py"]
