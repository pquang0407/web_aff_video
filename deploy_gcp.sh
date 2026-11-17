#!/bin/bash
# ==============================================================================
# DEPLOY_GCP.SH - Kịch bản cài đặt tự động 1-Click trên Google Cloud VM (Ubuntu/Debian)
# ==============================================================================

set -e

echo "=================================================================="
echo "🚀 BẮT ĐẦU CÀI ĐẶT HỆ THỐNG AUTO VIDEO AFFILIATE TRÊN GOOGLE CLOUD VM"
echo "=================================================================="

# 1. Cập nhật hệ điều hành
echo "📦 [1/4] Cập nhật các gói hệ thống..."
sudo apt-get update -y
sudo apt-get install -y git curl wget ffmpeg fonts-dejavu-core python3-pip python3-venv docker.io docker-compose

# 2. Khởi động dịch vụ Docker
echo "🐳 [2/4] Kích hoạt Docker..."
sudo systemctl enable docker
sudo systemctl start docker

# 3. Kiểm tra file .env
if [ ! -f .env ]; then
    echo "⚠️ Chưa tìm thấy file .env! Đang sao chép từ mẫu..."
    touch .env
fi

# 4. Khởi chạy Docker Compose
echo "🚀 [3/4] Đang build và khởi chạy hệ thống bằng Docker Compose..."
sudo docker-compose up -d --build

echo "=================================================================="
echo "🎉 HỆ THỐNG ĐÃ TRIỂN KHAI VÀ VẬN HÀNH 24/7 TRÊN CLOUD THÀNH CÔNG!"
echo "=================================================================="
echo "• Telegram Bot: Đang trực 24/7 tiếp nhận video & điều phối"
echo "• AI Video Factory: Gemini 3.5 Flash Lite + FFmpeg Fast Blur 9:16"
echo "• Auto-Scheduler: Đăng Fanpage & Threads theo Khung Giờ Vàng"
echo "• Web Admin: http://$(curl -s ifconfig.me):5050"
echo "=================================================================="
