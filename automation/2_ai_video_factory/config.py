"""
CONFIG.PY - Cấu hình cho Xưởng AI Video Factory (Module 2)
"""

import os
import json
from pathlib import Path

# Thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
RAW_DIR = STORAGE_DIR / "1_raw"
FULL_DIR = STORAGE_DIR / "2_web_full"
TEASER_DIR = STORAGE_DIR / "3_social_teaser"

# Đảm bảo các thư mục tồn tại
for d in [RAW_DIR, FULL_DIR, TEASER_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Đọc biến môi trường từ file .env dự án
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

# Tự động dò tìm đường dẫn FFmpeg & FFprobe
def _detect_ffmpeg():
    custom_ffmpeg = Path(r"D:\ffmpeg\bin\ffmpeg.exe")
    if custom_ffmpeg.exists():
        return str(custom_ffmpeg)
    env_ffmpeg = os.environ.get("FFMPEG_PATH") or _DOTENV.get("FFMPEG_PATH")
    if env_ffmpeg and Path(env_ffmpeg).exists():
        return env_ffmpeg
    return "ffmpeg"

def _detect_ffprobe():
    custom_ffprobe = Path(r"D:\ffmpeg\bin\ffprobe.exe")
    if custom_ffprobe.exists():
        return str(custom_ffprobe)
    env_ffprobe = os.environ.get("FFPROBE_PATH") or _DOTENV.get("FFPROBE_PATH")
    if env_ffprobe and Path(env_ffprobe).exists():
        return env_ffprobe
    return "ffprobe"

FFMPEG_BIN = _detect_ffmpeg()
FFPROBE_BIN = _detect_ffprobe()

# Cấu hình Gemini API
# Ưu tiên lấy từ: 1. ENV hệ thống, 2. file .env dự án, 3. D:\app\facebook_bot\data\gemini_config.json
def _get_gemini_api_key():
    api_key = os.environ.get("GEMINI_API_KEY") or _DOTENV.get("GEMINI_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()

    fb_bot_config = Path(r"D:\app\facebook_bot\data\gemini_config.json")
    if fb_bot_config.exists():
        try:
            with open(fb_bot_config, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("api_key", "").strip()
                if key:
                    return key
        except Exception:
            pass

    return ""

def _get_gemini_model():
    model = os.environ.get("GEMINI_MODEL") or _DOTENV.get("GEMINI_MODEL")
    if model and model.strip():
        return model.strip()
    return "gemini-3.5-flash-lite"

GEMINI_API_KEY = _get_gemini_api_key()
GEMINI_MODEL = _get_gemini_model()

# Cấu hình quy tắc cắt & render video
SHORT_VIDEO_THRESHOLD = 30.0  # Video <= 30s thì giữ nguyên toàn bộ thời lượng để đăng
TEASER_CUT_DURATION = 10.0    # Video > 30s thì cắt đoạn highlight khoảng 10s
TEASER_MAX_DURATION = 12.0    # Giây tối đa khi cắt highlight cho video dài
DEFAULT_FONT = "Arial"        # Font chữ hiển thị banner
