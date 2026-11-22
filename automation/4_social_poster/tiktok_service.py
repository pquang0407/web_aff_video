"""
TIKTOK_SERVICE.PY - Dịch vụ Auto-Đăng Video lên TikTok qua TikTok Content Posting API v2
Hỗ trợ:
1. Login Kit OAuth 2.0 (Authorization Code -> Access Token + Refresh Token 365 ngày)
2. Tự động làm mới Access Token ngầm khi hết hạn 24h
3. Upload Video qua FILE_UPLOAD:
   - Chế độ Inbox / Nháp (video.upload): Hoạt động ngay lập tức trên Sandbox & Production
   - Chế độ Direct Post (video.publish): Đăng thẳng lên kênh (SELF_ONLY trên Sandbox, PUBLIC sau khi duyệt Audit)
"""

import logging
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
import config

logger = logging.getLogger("TikTokService")

TIKTOK_REDIRECT_URI = "https://tho-news.com/tiktok-callback.html"
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
TIKTOK_INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_DIRECT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"


def get_tiktok_config() -> Dict[str, Any]:
    return config.load_json(
        config.TIKTOK_CONFIG_FILE,
        {
            "enabled": False,
            "client_key": "",
            "client_secret": "",
            "post_mode": "inbox",       # 'inbox' (video.upload) hoặc 'direct' (video.publish)
            "privacy_level": "SELF_ONLY",  # 'SELF_ONLY' (Sandbox) hoặc 'PUBLIC_TO_EVERYONE' (Production đã duyệt)
            "access_token": "",
            "refresh_token": "",
            "open_id": "",
            "display_name": "",
            "expires_at": 0,
            "updated_at": "",
        },
    )


def get_tiktok_config_public() -> Dict[str, Any]:
    """Trả thông tin cấu hình TikTok cho Web Admin nhưng ẨN TUYỆT ĐỐI secret & token"""
    cfg = get_tiktok_config()
    sec = cfg.get("client_secret", "")
    masked = (sec[:4] + "••••••••" + sec[-4:]) if len(sec) >= 10 else ("••••" if sec else "")
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "client_key": cfg.get("client_key", ""),
        "has_secret": bool(sec),
        "client_secret_masked": masked,
        "post_mode": cfg.get("post_mode", "inbox"),
        "privacy_level": cfg.get("privacy_level", "SELF_ONLY"),
        "connected": bool(cfg.get("access_token") or cfg.get("refresh_token")),
        "open_id": cfg.get("open_id", ""),
        "display_name": cfg.get("display_name", ""),
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "updated_at": cfg.get("updated_at", ""),
    }


def save_tiktok_app_config(
    client_key: str = "",
    client_secret: str = "",
    post_mode: Optional[str] = None,
    privacy_level: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    cfg = get_tiktok_config()
    if client_key.strip():
        cfg["client_key"] = client_key.strip()
    if client_secret.strip():
        cfg["client_secret"] = client_secret.strip()
    if post_mode in ("inbox", "direct"):
        cfg["post_mode"] = post_mode
    if privacy_level in ("SELF_ONLY", "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR"):
        cfg["privacy_level"] = privacy_level
    if enabled is not None:
        cfg["enabled"] = bool(enabled)
    cfg["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    config.save_json(config.TIKTOK_CONFIG_FILE, cfg)
    return cfg


def build_oauth_authorize_url() -> str:
    cfg = get_tiktok_config()
    client_key = cfg.get("client_key", "").strip()
    if not client_key:
        raise ValueError("Vui lòng nhập Client Key của TikTok trước!")
    scopes = "user.info.basic,video.upload"
    if cfg.get("post_mode") == "direct":
        scopes = "user.info.basic,video.upload,video.publish"
    params = {
        "client_key": client_key,
        "scope": scopes,
        "response_type": "code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": secrets.token_hex(8),
    }
    return f"{TIKTOK_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(auth_code: str) -> Dict[str, Any]:
    """Đổi Authorization Code lấy Access Token (24h) + Refresh Token (365 ngày)"""
    code = auth_code.strip()
    if not code:
        raise ValueError("Vui lòng dán mã Authorization Code từ trang callback TikTok!")
    cfg = get_tiktok_config()
    client_key = cfg.get("client_key", "").strip()
    client_secret = cfg.get("client_secret", "").strip()
    if not client_key or not client_secret:
        raise ValueError("Thiếu Client Key hoặc Client Secret của TikTok!")

    payload = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
    }
    res = requests.post(
        TIKTOK_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    data = res.json() if res.content else {}
    if not res.ok or "access_token" not in data:
        raise RuntimeError(f"Lỗi đổi TikTok Token ({res.status_code}): {res.text[:260]}")

    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", cfg.get("refresh_token", ""))
    open_id = data.get("open_id", "")
    expires_in = int(data.get("expires_in", 86400) or 86400)

    display_name = cfg.get("display_name", "")
    try:
        u_res = requests.get(
            TIKTOK_USER_INFO_URL,
            params={"fields": "open_id,display_name"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if u_res.ok:
            u_data = u_res.json().get("data", {}).get("user", {})
            if u_data.get("display_name"):
                display_name = u_data["display_name"]
    except Exception:
        pass

    cfg.update({
        "enabled": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "open_id": open_id,
        "display_name": display_name or open_id or "TikTok Creator",
        "expires_at": int(time.time()) + expires_in,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    config.save_json(config.TIKTOK_CONFIG_FILE, cfg)
    return get_tiktok_config_public()


def ensure_valid_access_token() -> str:
    """Tự động gia hạn Access Token bằng Refresh Token (365 ngày) khi sắp hết hạn"""
    cfg = get_tiktok_config()
    access_token = cfg.get("access_token", "").strip()
    refresh_token = cfg.get("refresh_token", "").strip()
    expires_at = int(cfg.get("expires_at", 0) or 0)

    if access_token and time.time() < (expires_at - 300):
        return access_token

    if not refresh_token:
        if access_token:
            return access_token
        raise RuntimeError("Chưa kết nối tài khoản TikTok (thiếu Access/Refresh Token).")

    payload = {
        "client_key": cfg.get("client_key", "").strip(),
        "client_secret": cfg.get("client_secret", "").strip(),
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    res = requests.post(
        TIKTOK_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    data = res.json() if res.content else {}
    if not res.ok or "access_token" not in data:
        raise RuntimeError(f"Không thể gia hạn TikTok Token ({res.status_code}): {res.text[:220]}")

    cfg["access_token"] = data["access_token"]
    if data.get("refresh_token"):
        cfg["refresh_token"] = data["refresh_token"]
    cfg["expires_at"] = int(time.time()) + int(data.get("expires_in", 86400) or 86400)
    cfg["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    config.save_json(config.TIKTOK_CONFIG_FILE, cfg)
    logger.info("✅ Đã tự động gia hạn TikTok Access Token thành công!")
    return cfg["access_token"]


def publish_video_to_tiktok(video_path: Path, caption: str) -> Dict[str, Any]:
    """Upload video MP4 lên TikTok qua Content Posting API v2 (FILE_UPLOAD)"""
    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    cfg = get_tiktok_config()
    access_token = ensure_valid_access_token()
    video_bytes = video_path.read_bytes()
    video_size = len(video_bytes)
    post_mode = cfg.get("post_mode", "inbox")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    if post_mode == "direct":
        init_url = TIKTOK_DIRECT_INIT_URL
        init_body = {
            "post_info": {
                "title": (caption or "Bản tin 3D Thỏ & Gấu #ThoVaGau3D")[:2200],
                "privacy_level": cfg.get("privacy_level", "SELF_ONLY"),
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        }
    else:
        init_url = TIKTOK_INBOX_INIT_URL
        init_body = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            }
        }

    init_res = requests.post(init_url, json=init_body, headers=headers, timeout=30)
    init_json = init_res.json() if init_res.content else {}
    err_obj = init_json.get("error") or {}
    if not init_res.ok or (err_obj.get("code") and err_obj.get("code") != "ok"):
        raise RuntimeError(f"TikTok Init Upload lỗi ({init_res.status_code}): {init_res.text[:280]}")

    data_obj = init_json.get("data") or {}
    upload_url = data_obj.get("upload_url")
    publish_id = data_obj.get("publish_id", "")
    if not upload_url:
        raise RuntimeError(f"TikTok không trả về upload_url: {init_res.text[:260]}")

    put_headers = {
        "Content-Type": "video/mp4",
        "Content-Length": str(video_size),
        "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
    }
    put_res = requests.put(upload_url, data=video_bytes, headers=put_headers, timeout=180)
    if not put_res.ok:
        raise RuntimeError(f"TikTok PUT Video thất bại ({put_res.status_code}): {put_res.text[:220]}")

    return {
        "ok": True,
        "platform": "tiktok",
        "post_mode": post_mode,
        "publish_id": publish_id,
        "display_name": cfg.get("display_name", ""),
        "note": (
            "Video đã được đẩy vào Hộp thư / Nháp trên App TikTok của bạn!"
            if post_mode == "inbox"
            else f"Video đã được đăng thẳng lên TikTok ({cfg.get('privacy_level', 'SELF_ONLY')})!"
        ),
    }
