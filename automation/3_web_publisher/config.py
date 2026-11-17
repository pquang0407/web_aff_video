"""
CONFIG.PY - Cấu hình cho Web Publisher (Module 3)
Hỗ trợ 2 chế độ tự động (Dual-Mode):
1. LOCAL MODE: Khi chưa điền key R2 -> Lưu đường dẫn tương đối để chạy trực tiếp trên máy
2. CLOUD R2 MODE: Khi đã điền key R2 -> Tự động đẩy file lên Cloudflare R2 CDN và cập nhật web
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
FULL_DIR = STORAGE_DIR / "2_web_full"
WEB_DIR = BASE_DIR / "web"
WEB_CONFIG_JS = WEB_DIR / "config.js"
WEB_VIDEOS_DB = WEB_DIR / "videos_db.json"


def _load_dotenv_dict() -> dict[str, str]:
    env_vars: dict[str, str] = {}
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return env_vars


_DOTENV = _load_dotenv_dict()


def _get_env(key: str, default: str = "") -> str:
    val = os.environ.get(key) or _DOTENV.get(key) or default
    return val.strip()


# Cấu hình Cloudflare R2
R2_ACCOUNT_ID = _get_env("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = _get_env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = _get_env("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = _get_env("R2_BUCKET_NAME", "web-aff-videos")
R2_PUBLIC_DOMAIN = _get_env("R2_PUBLIC_DOMAIN", "https://media.ten-mien-cua-ban.com").rstrip("/")

# Tên miền trang Web Player đích (dùng để tạo link ?v=ID gửi sang Module 4)
WEB_PUBLIC_URL = _get_env("WEB_PUBLIC_URL", _get_env("WEB_BASE_URL", "https://webaffvideo-web.vercel.app")).rstrip("/")

# Tự động Git Push để Vercel / Cloudflare Pages tự deploy khi cập nhật config.js
AUTO_GIT_PUSH = _get_env("AUTO_GIT_PUSH", "true").lower() in ("true", "1", "yes")


def is_cloud_r2_configured() -> bool:
    """Kiểm tra xem đã cấu hình đầy đủ thông tin Cloudflare R2 chưa"""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME)


def get_publish_mode(force_mode: str | None = None) -> str:
    """
    Trả về chế độ hoạt động: 'cloud_r2' hoặc 'local'
    """
    if force_mode in ("local", "cloud_r2"):
        return force_mode
    return "cloud_r2" if is_cloud_r2_configured() else "local"
