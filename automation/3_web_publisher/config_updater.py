"""
CONFIG_UPDATER.PY - Tự động cập nhật danh sách video vào web/config.js (Không cần Database SQL)
Đảm bảo cú pháp JavaScript chuẩn 100%, đưa video mới lên đầu danh sách và hỗ trợ Auto Git Push
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

import config

logger = logging.getLogger("ConfigUpdater")

# Cấu hình mặc định của Web Player (Affiliate, Deals, Flash Sale, Live Chat)
DEFAULT_BASE_CONFIG: Dict[str, Any] = {
    "affiliate": {
        "primaryUrl": "https://shopee.vn/flash_sale",
        "backupUrl": "https://shopee.vn/m/ma-giam-gia",
        "voucherDealUrl": "https://shopee.vn/m/ma-giam-gia",
        "clickMode": "simultaneous",
        "enableDeepLink": True,
    },
    "ui": {
        "siteName": "Media Stream Hub",
        "badgeText": "HD 1080P • FULL CLIP",
        "hotTags": [
            "#ClipNong24H",
            "#BossMeoMukbang",
            "#ThuCungViral",
            "#TrendingReels",
            "#SanVoucher0D",
            "#FullHD",
        ],
    },
    "videos": {},
    "deals": [
        {
            "title": "Mã Freeship Đơn 0Đ Toàn Sàn",
            "badge": "SẮP CHÁY MÃ",
            "platform": "Shopee",
            "discount": "Miễn phí vận chuyển 100%",
            "claimedPercent": 92,
            "exp": "Đã lưu 92% • Còn 8%",
            "url": "https://shopee.vn/m/ma-giam-gia",
        },
        {
            "title": "Voucher Giảm 50% Tối Đa 100K",
            "badge": "HOT NHẤT",
            "platform": "Shopee",
            "discount": "Giảm thẳng 50K - 100K",
            "claimedPercent": 86,
            "exp": "Đã lưu 86% • Khung giờ vàng",
            "url": "https://shopee.vn/flash_sale",
        },
        {
            "title": "Siêu Hội Hoàn Xu Extra 20%",
            "badge": "ĐỘC QUYỀN",
            "platform": "Shopee VIP",
            "discount": "Hoàn tới 200K Xu đơn bất kỳ",
            "claimedPercent": 74,
            "exp": "Đã lưu 74% • Hôm nay",
            "url": "https://shopee.vn/m/ma-giam-gia",
        },
    ],
    "flashProducts": [
        {
            "title": "Tai Nghe Bluetooth Không Dây Bass Căng",
            "priceNew": "9.000đ",
            "priceOld": "159.000đ",
            "sold": "Đã bán 4.8k",
            "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&auto=format&fit=crop&q=80",
            "url": "https://shopee.vn/flash_sale",
        },
        {
            "title": "Sạc Dự Phòng 20.000mAh Sạc Nhanh 22.5W",
            "priceNew": "19.000đ",
            "priceOld": "249.000đ",
            "sold": "Đã bán 3.1k",
            "img": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=200&auto=format&fit=crop&q=80",
            "url": "https://shopee.vn/flash_sale",
        },
        {
            "title": "Quạt Tích Điện Mini Cầm Tay Siêu Mát",
            "priceNew": "1.000đ",
            "priceOld": "85.000đ",
            "sold": "Đã bán 8.9k",
            "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=200&auto=format&fit=crop&q=80",
            "url": "https://shopee.vn/flash_sale",
        },
    ],
    "liveChatMessages": [
        {"user": "Hoàng Nam", "text": "Clip nét căng, xem không bị che mờ tý nào luôn 🔥"},
        {"user": "Thảo Vy", "text": "Vừa bấm lưu được mã Freeship 0đ ở cột bên trái xong, hên quá!"},
        {"user": "Đức Phúc", "text": "Đoạn giữa hài xỉu up xỉu down 😂"},
        {"user": "Kiều Trinh", "text": "Mấy clip đề xuất bên dưới xem cuốn thật sự anh em ơi"},
        {"user": "Minh Quân", "text": "Server phát mượt ghê, bấm cái chạy luôn không phải đợi xoay"},
        {"user": "Bảo Ngọc", "text": "Ai chưa lấy mã 50% bên trái thì bấm lẹ kẻo hết lượt kìa!"},
    ],
}


def load_current_db() -> Dict[str, Any]:
    """Đọc trạng thái hiện tại từ videos_db.json hoặc khởi tạo mới"""
    if config.WEB_VIDEOS_DB.exists():
        try:
            data = json.loads(config.WEB_VIDEOS_DB.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "videos" in data:
                return data
        except Exception as e:
            logger.warning(f"Không đọc được videos_db.json ({e}), khởi tạo mới.")
    return json.loads(json.dumps(DEFAULT_BASE_CONFIG))


def upsert_video_into_config(
    video_entry: Dict[str, Any],
    set_as_default: bool = False,
) -> bool:
    """
    Chèn hoặc cập nhật 1 video vào web/config.js và web/videos_db.json
    """
    db = load_current_db()
    videos_dict: Dict[str, Any] = db.get("videos", {})

    vid_id = video_entry["id"]

    # Xây dựng danh sách video: Đặt video mới lên đầu danh sách
    new_videos_ordered: Dict[str, Any] = {vid_id: video_entry}

    # Giữ lại các video cũ phía sau (loại bỏ 'default' và vid_id trùng)
    for k, v in videos_dict.items():
        if k not in ("default", vid_id):
            new_videos_ordered[k] = v

    # Luôn giữ 'default' trỏ tới video đầu tiên (để tương thích ngược)
    default_copy = dict(video_entry)
    default_copy["id"] = "default"
    new_videos_ordered["default"] = default_copy

    db["videos"] = new_videos_ordered

    # 1. Lưu file JSON backup
    config.WEB_VIDEOS_DB.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2. Sinh file web/config.js chuẩn xác
    js_content = (
        "/**\n"
        " * CONFIG.JS - Được sinh tự động bởi Module 3 (Web Publisher)\n"
        " * Không cần chỉnh sửa thủ công khi thêm video mới.\n"
        " */\n"
        f"const CONFIG = {json.dumps(db, ensure_ascii=False, indent=2)};\n"
    )
    config.WEB_CONFIG_JS.write_text(js_content, encoding="utf-8")
    logger.info(f"Đã cập nhật '{vid_id}' vào web/config.js (Tổng số video: {len(new_videos_ordered)})")

    if config.AUTO_GIT_PUSH:
        _trigger_git_push(vid_id)

    return True


def _trigger_git_push(video_id: str) -> None:
    """Tự động commit và push config.js để Vercel / Cloudflare Pages tự động cập nhật"""
    try:
        subprocess.run(
            ["git", "add", str(config.WEB_CONFIG_JS), str(config.WEB_VIDEOS_DB)],
            cwd=str(config.BASE_DIR),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"chore(publisher): auto publish video {video_id}"],
            cwd=str(config.BASE_DIR),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=str(config.BASE_DIR),
            check=True,
            capture_output=True,
        )
        logger.info(f"[AUTO DEPLOY] Đã git push cập nhật video {video_id} lên Cloud!")
    except Exception as e:
        logger.warning(f"Bỏ qua git push tự động: {e}")
