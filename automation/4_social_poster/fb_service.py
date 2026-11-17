"""
FB_SERVICE.PY - Dịch vụ Đăng Video Fanpage & Tự Động Bình Luận Link (Trích xuất & Nâng cấp từ facebook_bot)
1. Quản lý Cookie Facebook & trích xuất Page Access Token
2. Đăng Video Teaser 9:16 lên Fanpage qua Graph API
3. Tự động thả bình luận (Auto-Comment) chứa link Web Player ngay dưới bài vừa đăng
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import config

logger = logging.getLogger("FBService")


def get_cookie_status() -> Dict[str, Any]:
    cookies = config.load_json(config.FB_COOKIES_FILE, [])
    if not isinstance(cookies, list) or not cookies:
        return {"connected": False, "uid": None, "cookie_count": 0}

    cookie_dict = {c.get("name"): c.get("value") for c in cookies if isinstance(c, dict)}
    uid = cookie_dict.get("c_user")
    has_xs = bool(cookie_dict.get("xs"))
    return {
        "connected": bool(uid and has_xs),
        "uid": uid,
        "cookie_count": len(cookies),
    }


def save_facebook_cookies(cookies_raw: str) -> Dict[str, Any]:
    """Lưu Cookie Facebook từ định dạng JSON (Cookie-Editor) hoặc chuỗi key=value"""
    raw = cookies_raw.strip()
    if not raw:
        raise ValueError("Nội dung Cookie trống.")

    parsed_list: List[Dict[str, str]] = []
    if raw.startswith("["):
        data = json.loads(raw)
        for item in data:
            if isinstance(item, dict) and "name" in item and "value" in item:
                parsed_list.append({"name": str(item["name"]), "value": str(item["value"])})
    else:
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                parsed_list.append({"name": k.strip(), "value": v.strip()})

    cookie_map = {c["name"]: c["value"] for c in parsed_list}
    if "c_user" not in cookie_map or "xs" not in cookie_map:
        raise ValueError("Cookie không hợp lệ (thiếu c_user hoặc xs). Hãy copy từ trình duyệt đã đăng nhập Facebook.")

    config.save_json(config.FB_COOKIES_FILE, parsed_list)
    return get_cookie_status()


def get_page_config() -> Dict[str, Any]:
    return config.load_json(
        config.FB_PAGE_CONFIG_FILE,
        {"pages": [], "selected_page_id": ""},
    )


def save_page_config(pages: List[Dict[str, Any]], selected_page_id: Optional[str] = None) -> Dict[str, Any]:
    sel_id = selected_page_id or (pages[0]["id"] if pages else "")
    data = {"pages": pages, "selected_page_id": str(sel_id)}
    config.save_json(config.FB_PAGE_CONFIG_FILE, data)
    return data


def fetch_managed_pages_via_token(user_or_page_token: str) -> List[Dict[str, Any]]:
    """Lấy danh sách Fanpage từ User Access Token hoặc Page Access Token"""
    token = user_or_page_token.strip()
    if not token:
        raise ValueError("Vui lòng nhập Access Token.")

    url = f"https://graph.facebook.com/v21.0/me/accounts?fields=id,name,access_token,category,picture{{url}}&access_token={token}"
    res = requests.get(url, timeout=15)
    pages: List[Dict[str, Any]] = []

    if res.ok:
        for item in res.json().get("data", []):
            pic = item.get("picture", {}).get("data", {}).get("url")
            pages.append({
                "id": str(item.get("id")),
                "name": item.get("name", ""),
                "access_token": item.get("access_token") or token,
                "category": item.get("category", "Trang Facebook"),
                "picture_url": pic,
            })
        if pages:
            save_page_config(pages)
            return pages

    # Fallback nếu là Page Token trực tiếp
    me_url = f"https://graph.facebook.com/v21.0/me?fields=id,name,category,picture{{url}}&access_token={token}"
    me_res = requests.get(me_url, timeout=15)
    if me_res.ok:
        me_data = me_res.json()
        if me_data.get("id") and me_data.get("name"):
            pic = me_data.get("picture", {}).get("data", {}).get("url")
            pages.append({
                "id": str(me_data.get("id")),
                "name": me_data.get("name", ""),
                "access_token": token,
                "category": me_data.get("category", "Trang Facebook"),
                "picture_url": pic,
            })
            save_page_config(pages)
            return pages

    raise RuntimeError(f"Không lấy được danh sách Fanpage từ Token: {res.text[:200]}")


def publish_video_and_auto_comment(
    video_path: Path,
    caption: str,
    comment_text: str,
    page_id: Optional[str] = None,
    simulate: bool = False,
) -> Dict[str, Any]:
    """
    1. Đăng video Teaser lên Fanpage
    2. Ngay khi đăng xong -> Tự động bình luận link Web Player bên dưới bài đăng
    """
    page_cfg = get_page_config()
    pages = page_cfg.get("pages", [])
    target_page_id = page_id or page_cfg.get("selected_page_id")

    selected_page = None
    for p in pages:
        if str(p.get("id")) == str(target_page_id):
            selected_page = p
            break
    if not selected_page and pages:
        selected_page = pages[0]

    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file video Teaser: {video_path}")

    # Chế độ Giả lập kiểm thử (Simulation Mode)
    if simulate:
        page_name = selected_page.get("name", "Demo Fanpage") if selected_page else "Demo Fanpage"
        p_id = selected_page.get("id", "1000999888") if selected_page else "1000999888"
        fake_post_id = f"{p_id}_{int(time.time())}"
        fake_comment_id = f"{fake_post_id}_cmt_{int(time.time())}"
        logger.info(f"[FB SIMULATION] Đã đăng Teaser '{video_path.name}' lên Page '{page_name}' (Post ID: {fake_post_id})")
        logger.info(f"[FB SIMULATION] Đã tự động bình luận dưới bài: '{comment_text}' (Cmt ID: {fake_comment_id})")
        return {
            "ok": True,
            "platform": "facebook",
            "mode": "simulation",
            "page_id": p_id,
            "page_name": page_name,
            "post_id": fake_post_id,
            "post_url": f"https://www.facebook.com/{fake_post_id}",
            "comment_id": fake_comment_id,
            "comment_text": comment_text,
        }

    if not selected_page:
        raise ValueError("Chưa có Fanpage nào được cấu hình. Vui lòng kết nối Fanpage trên trang Admin.")

    p_id = str(selected_page["id"]).strip()
    p_name = selected_page.get("name", p_id)
    token = str(selected_page["access_token"]).strip()

    # Bước 1: Upload Video lên Fanpage
    logger.info(f"[FB LIVE] Đang tải video Teaser '{video_path.name}' lên Fanpage '{p_name}' ({p_id})...")
    video_url = f"https://graph.facebook.com/v21.0/{p_id}/videos"

    # Đảm bảo link Web Player luôn xuất hiện cả ở cuối Caption để tăng tối đa chuyển đổi
    full_description = caption
    if comment_text and comment_text not in caption:
        full_description = f"{caption}\n\n{comment_text}"

    with open(video_path, "rb") as f:
        res = requests.post(
            video_url,
            data={"description": full_description, "access_token": token},
            files={"source": f},
            timeout=120,
        )

    if not res.ok:
        err_text = res.text[:350]
        if '"code":190' in err_text or "Session has expired" in err_text:
            raise RuntimeError(
                "Token Fanpage đã hết hạn (từ ngày 13/11). "
                "Vui lòng lấy Access Token mới trên Graph API Explorer và dán vào ô 'Thêm Fanpage bằng Access Token' ở cột trái rồi bấm 'Lấy Page'!"
            )
        raise RuntimeError(f"Lỗi đăng video lên Fanpage ({res.status_code}): {err_text}")

    res_json = res.json()
    post_id = res_json.get("id") or res_json.get("post_id")
    logger.info(f"[FB LIVE] Đăng video thành công! Post ID: {post_id}")

    # Bước 2: Tự động bình luận link Web Player ngay dưới video vừa đăng
    comment_id = None
    if comment_text and post_id:
        time.sleep(3)
        # Thử comment trực tiếp vào video ID hoặc Post ID
        for target_id in [post_id, f"{p_id}_{post_id}"]:
            cmt_url = f"https://graph.facebook.com/v21.0/{target_id}/comments"
            cmt_res = requests.post(
                cmt_url,
                data={"message": comment_text, "access_token": token},
                timeout=30,
            )
            if cmt_res.ok:
                comment_id = cmt_res.json().get("id")
                logger.info(f"[FB LIVE] Đã tự động thả comment link thành công! Comment ID: {comment_id}")
                break
            else:
                if '"code":200' in cmt_res.text:
                    logger.warning(
                        "[FB LIVE] Thiếu quyền 'pages_manage_engagement' trong Access Token để tự động bình luận! "
                        "(Đừng lo, link Web Player đã được tự động gắn vào cuối Caption bài đăng để người xem bấm xem full)."
                    )
                    break
                else:
                    logger.warning(f"[FB LIVE] Không thể comment tự động ({cmt_res.status_code}): {cmt_res.text[:200]}")

    return {
        "ok": True,
        "platform": "facebook",
        "mode": "live",
        "page_id": p_id,
        "page_name": p_name,
        "post_id": post_id,
        "post_url": f"https://www.facebook.com/{post_id}",
        "comment_id": comment_id,
        "comment_text": comment_text,
    }
