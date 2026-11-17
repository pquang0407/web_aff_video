"""
THREADS_SERVICE.PY - Dịch vụ Đăng Video lên Meta Threads & Tự Động Trả Lời Link
Hỗ trợ:
1. Meta Threads Graph API chính thức (graph.threads.net)
2. Lưu Cookie phiên đăng nhập Threads.net
3. Tự động tạo bình luận trả lời (Reply Thread) gắn link Web Player ngay dưới bài vừa đăng
"""

import logging
import time
from typing import Any, Dict, Optional

import requests
import config

logger = logging.getLogger("ThreadsService")


def publish_thread_with_auto_reply(
    caption: str,
    reply_text: str,
    video_public_url: Optional[str] = None,
    simulate: bool = False,
) -> Dict[str, Any]:
    """
    Đăng bài lên Threads + Tự động trả lời (Reply) chứa link Web Player bên dưới bài
    """
    t_cfg = config.get_threads_config()
    username = t_cfg.get("username") or "threads_channel"

    if simulate or not t_cfg.get("access_token"):
        fake_thread_id = f"th_{int(time.time())}"
        fake_reply_id = f"th_reply_{int(time.time())}"
        logger.info(f"[THREADS SIMULATION] Đã đăng bài lên Threads @{username} (ID: {fake_thread_id})")
        logger.info(f"[THREADS SIMULATION] Đã tự động Reply link dưới bài: '{reply_text}'")
        return {
            "ok": True,
            "platform": "threads",
            "mode": "simulation",
            "username": username,
            "thread_id": fake_thread_id,
            "thread_url": f"https://www.threads.net/@{username}/post/{fake_thread_id}",
            "reply_id": fake_reply_id,
            "reply_text": reply_text,
        }

    user_id = t_cfg.get("threads_user_id", "").strip()
    token = t_cfg.get("access_token", "").strip()

    if not user_id or not token:
        logger.info("[THREADS] Chưa cấu hình Threads User ID hoặc Access Token, bỏ qua đăng Threads.")
        return {
            "ok": False,
            "platform": "threads",
            "error": "Chưa cấu hình Threads User ID hoặc Access Token."
        }

    if token.startswith("EAA"):
        logger.warning("[THREADS] Token được nhập là mã Facebook (EAA...), không tương thích với Threads API (graph.threads.net).")
        return {
            "ok": False,
            "platform": "threads",
            "error": "Token hiện tại là Facebook Token (EAA...). Threads yêu cầu Token từ Meta Threads Graph API riêng."
        }

    # Bước 1: Tạo Container bài đăng chính trên Threads
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    payload: Dict[str, Any] = {
        "text": caption,
        "access_token": token,
    }
    if video_public_url and video_public_url.startswith("http"):
        payload["media_type"] = "VIDEO"
        payload["video_url"] = video_public_url
    else:
        payload["media_type"] = "TEXT"

    r1 = requests.post(create_url, data=payload, timeout=30)
    if not r1.ok:
        raise RuntimeError(f"Lỗi tạo container Threads ({r1.status_code}): {r1.text[:250]}")

    creation_id = r1.json().get("id")
    time.sleep(5)

    # Bước 2: Xuất bản bài đăng chính
    pub_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    r2 = requests.post(
        pub_url,
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    if not r2.ok:
        raise RuntimeError(f"Lỗi publish Threads ({r2.status_code}): {r2.text[:250]}")

    thread_id = r2.json().get("id")
    logger.info(f"[THREADS LIVE] Đăng bài thành công! Thread ID: {thread_id}")

    # Bước 3: Tự động Reply gắn link Web Player dưới bài vừa đăng
    reply_id = None
    if reply_text and thread_id and t_cfg.get("auto_reply_link", True):
        time.sleep(2)
        r_rep = requests.post(
            create_url,
            data={
                "media_type": "TEXT",
                "text": reply_text,
                "reply_to_id": thread_id,
                "access_token": token,
            },
            timeout=20,
        )
        if r_rep.ok:
            rep_cid = r_rep.json().get("id")
            r_rep_pub = requests.post(
                pub_url,
                data={"creation_id": rep_cid, "access_token": token},
                timeout=20,
            )
            if r_rep_pub.ok:
                reply_id = r_rep_pub.json().get("id")
                logger.info(f"[THREADS LIVE] Đã tự động Reply link thành công! Reply ID: {reply_id}")

    return {
        "ok": True,
        "platform": "threads",
        "mode": "live",
        "username": username,
        "thread_id": thread_id,
        "thread_url": f"https://www.threads.net/@{username}/post/{thread_id}",
        "reply_id": reply_id,
        "reply_text": reply_text,
    }
