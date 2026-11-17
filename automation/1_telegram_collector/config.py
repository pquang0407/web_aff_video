import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc dự án
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent

# Load .env
load_dotenv(ROOT_DIR / ".env")

# Các kho lưu trữ video của hệ thống
RAW_STORAGE_DIR = ROOT_DIR / "storage" / "1_raw"
WEB_FULL_DIR = ROOT_DIR / "storage" / "2_web_full"
SOCIAL_DIR = ROOT_DIR / "storage" / "3_social_teaser"

RAW_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
WEB_FULL_DIR.mkdir(parents=True, exist_ok=True)
SOCIAL_DIR.mkdir(parents=True, exist_ok=True)

# File lưu lịch sử video đã tải (chống trùng lặp)
DOWNLOADED_LOG_PATH = CURRENT_DIR / "downloaded_videos.json"

# File cấu hình & chế độ vận hành hệ thống
SETTINGS_FILE = CURRENT_DIR / "system_settings.json"

# Cấu hình Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()

# Cấu hình Telethon Userbot (cào channel nguồn công khai)
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
TELEGRAM_SOURCE_CHANNELS = [
    ch.strip() for ch in os.getenv("TELEGRAM_SOURCE_CHANNELS", "@trend_videos_channel").split(",") if ch.strip()
]

# Base URL Web Player
WEB_BASE_URL = os.getenv("WEB_BASE_URL", "https://zento-web-five.vercel.app")


def load_settings() -> dict:
    """Tải cài đặt chế độ vận hành của hệ thống"""
    default_settings = {
        "auto_pipeline_on_receive": True,  # Nhận video là tự động chạy trọn gói M2 -> M4
        "auto_comment_link": True,         # Tự động thả bình luận link Web Player
        "default_platform": "all",         # Đăng cả Fanpage + Threads + Telegram Channel
        "max_video_duration_keep": 30      # Video <= 30s giữ nguyên, > 30s cắt highlight 10s
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings


def save_settings(settings: dict):
    """Lưu cài đặt vận hành"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_video_stats() -> dict:
    """Lấy số lượng video thực tế trong các khoang"""
    raw_files = list(RAW_STORAGE_DIR.glob("*.mp4"))
    web_files = list(WEB_FULL_DIR.glob("*.mp4"))
    social_files = list(SOCIAL_DIR.glob("*.mp4"))
    return {
        "raw_count": len(raw_files),
        "web_count": len(web_files),
        "social_count": len(social_files),
        "raw_files": [f.name for f in raw_files],
        "social_files": [f.name for f in social_files]
    }


def is_video_downloaded(file_unique_id: str) -> bool:
    """Kiểm tra video đã thu thập trước đó chưa để tránh trùng lặp"""
    if not DOWNLOADED_LOG_PATH.exists():
        return False
    try:
        with open(DOWNLOADED_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return file_unique_id in data
    except Exception:
        return False


def mark_video_downloaded(file_unique_id: str, filename: str, info: dict = None):
    """Đánh dấu video đã được tải về khoang 1_raw"""
    data = {}
    if DOWNLOADED_LOG_PATH.exists():
        try:
            with open(DOWNLOADED_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data[file_unique_id] = {
        "filename": filename,
        "timestamp": os.path.getmtime(str(RAW_STORAGE_DIR / filename)) if (RAW_STORAGE_DIR / filename).exists() else 0,
        "info": info or {}
    }
    with open(DOWNLOADED_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
