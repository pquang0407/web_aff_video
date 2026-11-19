#!/bin/bash
# ==============================================================================
# SETUP_CLOUD_3D.SH - Cài đặt toàn bộ Xưởng Phim 3D Thỏ & Gấu chạy 100% trên Cloud VM
# (Node.js 22 + Google Chrome Stable + Puppeteer-Core + Edge-TTS + FFmpeg)
# Không cần bật máy tính cá nhân Local!
# ==============================================================================

set -e

echo "=================================================================="
echo "🐰🐻 CÀI ĐẶT XƯỞNG PHIM 3D THỎ & GẤU CHẠY ĐỘC LẬP 100% TRÊN CLOUD VM"
echo "=================================================================="

# 1. Cài đặt Node.js & NPM nếu chưa có
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "📦 [1/4] Đang cài đặt Node.js & NPM..."
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs npm
else
    echo "✅ [1/4] Node.js & NPM đã cài sẵn: $(node -v) | npm $(npm -v)"
fi

# 2. Cài đặt Google Chrome Stable cho Puppeteer 3D Muse.ai
if ! command -v google-chrome &> /dev/null && ! command -v google-chrome-stable &> /dev/null; then
    echo "🌐 [2/4] Đang cài đặt Google Chrome Stable trên Ubuntu VM..."
    wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get update -y
    sudo apt-get install -y /tmp/google-chrome.deb fonts-liberation fonts-noto-core libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2t64 || sudo apt-get install -y /tmp/google-chrome.deb
    rm -f /tmp/google-chrome.deb
else
    echo "✅ [2/4] Google Chrome đã cài sẵn: $(google-chrome --version || google-chrome-stable --version)"
fi

# 3. Cài đặt thư viện Node (puppeteer-core) trong rabbit_bear_engine
echo "📦 [3/4] Đang cài đặt Puppeteer-Core cho Xưởng 3D Thỏ & Gấu..."
cd "$HOME/web_aff_video/automation/2_ai_video_factory/rabbit_bear_engine"
npm install --no-audit --no-fund

# 4. Cài đặt edge-tts & aiohttp cho giọng đọc vi-VN-NamMinhNeural
echo "🎙️ [4/4] Đang cài đặt Edge-TTS & aiohttp..."
if [ -x "$HOME/web_aff_video/venv/bin/pip" ]; then
    "$HOME/web_aff_video/venv/bin/pip" install --upgrade edge-tts aiohttp
else
    pip3 install --upgrade edge-tts aiohttp --break-system-packages || pip3 install --upgrade edge-tts aiohttp
fi

# Dọn sạch mọi file vid_TikTok cũ còn sót trên máy ảo
cd "$HOME/web_aff_video"
rm -f storage/2_web_full/vid_TikTok_* storage/3_social_teaser/vid_TikTok_* web/videos/vid_TikTok_* || true

# Khởi động lại dịch vụ auto-affiliate
sudo systemctl restart auto-affiliate
sudo systemctl status auto-affiliate --no-pager

echo "=================================================================="
echo "🎉 HOÀN TẤT 100%! CLOUD VM ĐÃ TỰ CHẠY ĐỘC LẬP TOÀN BỘ XƯỞNG PHIM 3D!"
echo "👉 Bạn có thể TẮT MÁY TÍNH CÁ NHÂN và chỉ cần gửi link báo vào Telegram Bot!"
echo "=================================================================="
