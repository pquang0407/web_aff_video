"""
MAIN_CLOUD_DAEMON.PY - Trình Điều Phối 24/7 Toàn Diện Hệ Thống Auto Video Affiliate
Chạy độc lập trên Cloud VM (GCP, VPS, Docker) đảm nhiệm:
1. Module 1: Telegram Bot Ingestion (Nhận video/link 24/7 & điều khiển từ xa)
2. Module 2 & 3: Xưởng AI Video Factory + Web Publisher (Tự động xử lý khi có video)
3. Module 4: Auto-Scheduler Daemon (Tự động đăng Fanpage & Threads theo khung giờ vàng)
4. Web Admin Quản Trị Cổng 5050
"""

import os
import sys
import time
import signal
import logging
import threading
import subprocess
from pathlib import Path

logging.basicConfig(
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CloudMasterDaemon")

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "automation" / "1_telegram_collector"))
sys.path.insert(0, str(ROOT_DIR / "automation" / "4_social_poster"))

IS_RUNNING = True


def signal_handler(sig, frame):
    global IS_RUNNING
    logger.info("Nhận tín hiệu dừng (SIGINT/SIGTERM), đang dọn dẹp các tiến trình...")
    IS_RUNNING = False
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_telegram_bot_worker():
    """Luồng chạy Telegram Bot (Module 1)"""
    logger.info("🚀 [Worker 1] Khởi chạy Telegram Bot...")
    bot_script = ROOT_DIR / "automation" / "1_telegram_collector" / "bot_service.py"
    while IS_RUNNING:
        try:
            proc = subprocess.Popen([sys.executable, str(bot_script)])
            proc.wait()
            if not IS_RUNNING:
                break
            logger.warning("[Worker 1] Telegram Bot bị ngắt, tự động khởi động lại sau 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[Worker 1] Lỗi chạy Telegram Bot: {e}")
            time.sleep(5)


def run_admin_and_scheduler_worker():
    """Luồng chạy Web Admin & Auto-Scheduler (Module 4)"""
    logger.info("🚀 [Worker 2] Khởi chạy Web Admin Cổng 5050 & Bộ Lập Lịch 24/7...")
    admin_script = ROOT_DIR / "automation" / "4_social_poster" / "admin_server.py"
    while IS_RUNNING:
        try:
            proc = subprocess.Popen([sys.executable, str(admin_script)])
            proc.wait()
            if not IS_RUNNING:
                break
            logger.warning("[Worker 2] Web Admin bị ngắt, tự động khởi động lại sau 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[Worker 2] Lỗi chạy Web Admin: {e}")
            time.sleep(5)


def run_cron_scanner_worker():
    """Luồng quét khoang 1_raw định kỳ phòng khi có video sót"""
    logger.info("🚀 [Worker 3] Khởi chạy Quét Kho Video Thô định kỳ...")
    factory_script = ROOT_DIR / "automation" / "2_ai_video_factory" / "factory.py"
    while IS_RUNNING:
        try:
            # Quét mỗi 10 phút kiểm tra xem có video nào trong 1_raw chưa render không
            time.sleep(600)
            if not IS_RUNNING:
                break
            logger.info("⏰ [Worker 3] Quét định kỳ khoang storage/1_raw...")
            subprocess.run([sys.executable, str(factory_script)])
        except Exception as e:
            logger.error(f"[Worker 3] Lỗi quét định kỳ: {e}")


def main():
    print("=" * 70)
    print("🌟 KHỞI ĐỘNG HỆ THỐNG AUTO VIDEO AFFILIATE 24/7 TRÊN CLOUD 🌟")
    print("=" * 70)
    print(f"📁 Thư mục gốc dự án: {ROOT_DIR}")
    print(f"🤖 AI Model: Gemini 3.5 Flash Lite")
    print(f"📱 Web Admin: http://0.0.0.0:5050")
    print("=" * 70)

    # 1. Khởi động Worker Telegram Bot
    t1 = threading.Thread(target=run_telegram_bot_worker, daemon=True)
    t1.start()

    # 2. Khởi động Worker Web Admin & Auto-Scheduler
    t2 = threading.Thread(target=run_admin_and_scheduler_worker, daemon=True)
    t2.start()

    # 3. Khởi động Worker Quét Định Kỳ
    t3 = threading.Thread(target=run_cron_scanner_worker, daemon=True)
    t3.start()

    logger.info("✅ Tất cả dịch vụ ngầm đã kích hoạt thành công!")
    logger.info("💡 Hệ thống đang vận hành 24/7. Bấm Ctrl+C để thoát.")

    while IS_RUNNING:
        time.sleep(1)


if __name__ == "__main__":
    main()
