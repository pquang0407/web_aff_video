r"""
CONFIG.PY - Cấu hình cho Social Poster & Web Admin (Module 4)
Tự động kế thừa dữ liệu Cookie & 5 Fanpage có sẵn từ D:\app\facebook_bot\data
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
FULL_DIR = STORAGE_DIR / "2_web_full"
TEASER_DIR = STORAGE_DIR / "3_social_teaser"

MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FB_COOKIES_FILE = DATA_DIR / "facebook_cookies.json"
FB_PAGE_CONFIG_FILE = DATA_DIR / "page_config.json"
FB_APP_CONFIG_FILE = DATA_DIR / "fb_app_config.json"
THREADS_CONFIG_FILE = DATA_DIR / "threads_config.json"
POST_HISTORY_FILE = DATA_DIR / "post_history.json"
SCHEDULER_CONFIG_FILE = DATA_DIR / "scheduler_config.json"

# Thư mục facebook_bot sẵn có của bạn
LEGACY_FB_BOT_DATA = Path(r"D:\app\facebook_bot\data")


def sync_from_legacy_facebook_bot() -> None:
    r"""
    Tự động đồng bộ Cookie và danh sách Fanpage từ D:\app\facebook_bot\data sang Module 4
    """
    if LEGACY_FB_BOT_DATA.exists():
        legacy_cookies = LEGACY_FB_BOT_DATA / "facebook_cookies.json"
        if legacy_cookies.exists() and not FB_COOKIES_FILE.exists():
            shutil.copy2(legacy_cookies, FB_COOKIES_FILE)

        legacy_pages = LEGACY_FB_BOT_DATA / "page_config.json"
        if legacy_pages.exists() and not FB_PAGE_CONFIG_FILE.exists():
            shutil.copy2(legacy_pages, FB_PAGE_CONFIG_FILE)


sync_from_legacy_facebook_bot()


def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_threads_config() -> Dict[str, Any]:
    return load_json(
        THREADS_CONFIG_FILE,
        {
            "enabled": False,
            "threads_user_id": "",
            "access_token": "",
            "session_cookie": "",
            "username": "",
            "auto_reply_link": True,
        },
    )


def save_threads_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    current = get_threads_config()
    current.update(cfg)
    save_json(THREADS_CONFIG_FILE, current)
    return current


def get_scheduler_config() -> Dict[str, Any]:
    return load_json(
        SCHEDULER_CONFIG_FILE,
        {
            "auto_post_enabled": True,
            "schedule_mode": "time_slots",  # 'time_slots' (Khung giờ vàng) hoặc 'interval' (Cách mỗi X phút)
            "daily_time_slots": ["08:00", "11:30", "17:30", "20:30"],
            "interval_minutes": 60,
            "simulate_mode": False,
            "comment_template": "👉 Xem trọn vẹn bản Full HD không che tại đây: {url}",
            "platforms": ["facebook", "threads"],
            "last_auto_run": "",
        },
    )


def save_scheduler_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    current = get_scheduler_config()
    current.update(cfg)
    save_json(SCHEDULER_CONFIG_FILE, current)
    return current
