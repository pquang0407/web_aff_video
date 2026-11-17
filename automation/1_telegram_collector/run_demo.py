import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import TELEGRAM_BOT_TOKEN, get_video_stats, load_settings, RAW_STORAGE_DIR
from bot_service import run_telegram_bot

def show_preview():
    stats = get_video_stats()
    settings = load_settings()
    auto_mode = settings.get("auto_pipeline_on_receive", True)
    mode_str = "🟢 TỰ ĐỘNG 24/7 (BẬT)" if auto_mode else "🟡 THỦ CÔNG (TẮT)"

    print("=" * 68)
    print("🤖 TELEGRAM AUTO VIDEO AFFILIATE 24/7 (MODULE 1 CONTROL CENTER)")
    print("=" * 68)
    print("📱 Giao diện Bảng Điều Khiển Bot trên điện thoại:\n")
    print("┌──────────────────────────────────────────────────────────────────┐")
    print("│ ⚡ HỆ THỐNG AUTO VIDEO AFFILIATE 24/7 - PIPELINE CONTROL CENTER   │")
    print("│ 🤖 AI Core: Gemini 3.5 Flash Lite | 🎞️ Fast Blur 9:16 + TTS      │")
    print("│                                                                  │")
    print(f"│ 📊 TRẠNG THÁI HÀNG ĐỢI KHO LƯU TRỮ:                              │")
    print(f"│ • 📥 Khoang 1 (Raw chờ AI):      {stats['raw_count']} video                     │")
    print(f"│ • 🌐 Khoang 2 (Web Full HD):     {stats['web_count']} video                     │")
    print(f"│ • 📱 Khoang 3 (Social Teasers):  {stats['social_count']} video sẵn sàng          │")
    print(f"│ ⚙️ Chế độ vận hành: {mode_str}                       │")
    print("├──────────────────────────────────────────────────────────────────┤")
    print("│ [🔥 KÍCH HOẠT AUTO PIPELINE (M2 ➔ M4)]                           │")
    print("├─────────────────────────────────┬────────────────────────────────┤")
    print(f"│ [📥 Kho Video Thô ({stats['raw_count']})]        │ [🌐 Kho Web Full ({stats['web_count']})]        │")
    print(f"│ [📱 Hàng Đợi Social ({stats['social_count']})]       │ [📢 Đăng Telegram Channel]     │")
    print("├─────────────────────────────────┴────────────────────────────────┤")
    print(f"│ [{mode_str}]           │ [📊 Thống kê Hệ thống]         │")
    print("│ [🔄 Làm mới]                    │ [🌐 Mở Web Player]             │")
    print("└──────────────────────────────────────────────────────────────────┘")
    print(f"\n📂 Thư mục tiếp nhận video thô: {RAW_STORAGE_DIR}")
    print(f"💡 Chỉ cần GỬI hoặc FORWARD video vào Bot, hệ thống sẽ tự động xử lý trọn gói!\n")

    if not TELEGRAM_BOT_TOKEN:
        print("💡 HƯỚNG DẪN CẤP TOKEN ĐỂ BOT CHẠY THẬT NGAY LẬP TỨC:")
        print("1. Mở Telegram, tìm kiếm: @BotFather")
        print("2. Gửi lệnh /newbot")
        print("3. Đặt tên Bot (VD: Auto Video Aff) và username (VD: auto_video_aff_bot)")
        print("4. Nhận API Token dạng: 7891234567:AAHxyz...")
        print("5. Dán vào file d:\\web_aff\\.env:")
        print("   TELEGRAM_BOT_TOKEN=7891234567:AAHxyz...")
        print("6. Chạy lại lệnh này để Bot online 24/7!")
    else:
        print(f"🔑 Đã tìm thấy TELEGRAM_BOT_TOKEN! Khởi động Bot ngay...")
        run_telegram_bot()

if __name__ == "__main__":
    show_preview()
