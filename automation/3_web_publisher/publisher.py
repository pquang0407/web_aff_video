"""
PUBLISHER.PY - Bộ điều phối chính của Module 3 (Web Publisher)
Luồng xử lý:
1. Đọc file <id>_meta.json từ storage/2_web_full/
2. Chạy ở chế độ LOCAL hoặc CLOUD R2 (upload video & poster)
3. Tự động chèn video vào web/config.js (Không cần Database SQL)
4. Xuất ra link đích ?v=ID_MOI để bàn giao cho Module 4 (Social Poster)
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import config
import config_updater
import r2_uploader

AUTOMATION_DIR = Path(__file__).resolve().parent.parent
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))
try:
    import deal_voucher_service
except Exception:
    deal_voucher_service = None

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("WebPublisher")


def _clean_views_str(raw_views: str) -> str:
    """Chuẩn hóa chuỗi lượt xem (bỏ chữ 'lượt xem' thừa nếu có)"""
    return raw_views.replace("lượt xem", "").strip()


def _pick_contextual_image(keyword: str) -> str:
    t = (keyword or "").lower()
    if any(k in t for k in ["bóng đá", "giày đá bóng", "áo đấu", "cầu thủ", "thể thao", "chạy bộ"]):
        return "https://images.unsplash.com/photo-1511886929837-354d827aae26?w=240&auto=format&fit=crop&q=80"
    if any(k in t for k in ["sách", "truyện", "hoàng tử bé", "tiểu thuyết", "lịch sử"]):
        return "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=240&auto=format&fit=crop&q=80"
    if any(k in t for k in ["balo", "vali", "du lịch", "cắm trại", "lều"]):
        return "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=240&auto=format&fit=crop&q=80"
    if any(k in t for k in ["phong thủy", "vòng tay", "tài lộc", "tỳ hưu", "ví da"]):
        return "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=240&auto=format&fit=crop&q=80"
    if any(k in t for k in ["áo khoác", "giữ nhiệt", "thời trang", "váy", "quần", "giày"]):
        return "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=240&auto=format&fit=crop&q=80"
    if any(k in t for k in ["đèn", "bình giữ nhiệt", "máy lọc", "gia dụng", "bếp"]):
        return "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=240&auto=format&fit=crop&q=80"
    if any(k in t for k in ["sạc", "pin", "tai nghe", "điện thoại", "chuột", "bàn phím", "laptop"]):
        return "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=240&auto=format&fit=crop&q=80"
    return "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=240&auto=format&fit=crop&q=80"


def _build_related_products(meta: Dict[str, Any]) -> List[Dict[str, str]]:
    """Tạo danh sách sản phẩm Shopee liên quan theo từ khóa video, bọc qua shp.tho-hoantien.com (0% link chết)"""
    raw_keywords = meta.get("related_keywords") or []
    keywords = [str(k).strip() for k in raw_keywords if str(k).strip()][:3]
    if not keywords:
        return []

    products: List[Dict[str, str]] = []
    for idx, kw in enumerate(keywords):
        search_url = f"https://shopee.vn/search?keyword={quote(kw)}&sortBy=sales"
        aff_url = search_url
        if deal_voucher_service:
            try:
                converted = deal_voucher_service.convert_via_tho_hoantien(search_url)
                aff_url = converted.get("short") or converted.get("affiliate") or search_url
            except Exception as e:
                logger.warning(f"Không convert được link sản phẩm '{kw}': {e}")
        products.append({
            "title": kw[:46],
            "tag": "Bán chạy Shopee" if idx == 0 else "Hoàn tiền Thỏ",
            "subtitle": "Xem top shop uy tín & mã giảm giá",
            "img": _pick_contextual_image(kw),
            "url": aff_url,
        })
    return products


def publish_single_metadata(
    meta_path: Path,
    force_mode: Optional[str] = None,
    simulate_cloud: bool = False,
    set_as_default: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Xuất bản 1 video dựa trên file *_meta.json của Module 2
    """
    if not meta_path.exists():
        logger.error(f"Không tìm thấy file metadata: {meta_path}")
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Lỗi đọc JSON {meta_path.name}: {e}")
        return None

    video_id = meta.get("id") or meta_path.stem.replace("_meta", "")
    full_video_path = Path(meta.get("full_video_path", config.FULL_DIR / f"{video_id}.mp4"))
    poster_path = Path(meta.get("poster_path", config.FULL_DIR / f"{video_id}_poster.jpg"))

    if not full_video_path.exists():
        logger.error(f"File video Full không tồn tại: {full_video_path}")
        return None

    mode = config.get_publish_mode(force_mode)
    logger.info(f"==================================================")
    logger.info(f"XUẤT BẢN VIDEO LÊN WEB: {video_id} | CHẾ ĐỘ: {mode.upper()}")
    logger.info(f"==================================================")

    # 1. Lấy URL video & poster theo chế độ Local hoặc Cloud R2
    video_url, poster_url = r2_uploader.upload_media_pair(
        video_id=video_id,
        video_path=full_video_path,
        poster_path=poster_path,
        mode=mode,
        simulate_cloud=simulate_cloud,
    )

    # 2. Tạo cấu trúc dữ liệu cho web/config.js (kèm sản phẩm Shopee liên quan theo chủ đề video)
    related_products = _build_related_products(meta)
    video_entry = {
        "id": video_id,
        "title": meta.get("title", f"Clip nóng đang gây chú ý ({video_id})"),
        "duration": meta.get("duration", "00:10"),
        "views": _clean_views_str(meta.get("views", "185.4K")),
        "likes": meta.get("likes", "14.2K"),
        "uploadDate": meta.get("uploadDate", "Vừa xong"),
        "category": meta.get("category", "🔥 ĐANG THỊNH HÀNH"),
        "videoUrl": video_url,
        "posterUrl": poster_url,
        "description": (meta.get("social_caption") or "").split("\n")[0]
        or "Xem trọn vẹn bản ghi chất lượng cao Full HD không che.",
    }
    if related_products:
        video_entry["relatedProducts"] = related_products

    # 3. Cập nhật vào web/config.js
    config_updater.upsert_video_into_config(video_entry, set_as_default=set_as_default)

    # 4. Tạo link đích cho bài đăng mạng xã hội
    target_web_url = f"{config.WEB_PUBLIC_URL}/?v={video_id}"

    # 5. Cập nhật lại file *_meta.json để Module 4 (Facebook/Threads Bot) sử dụng
    meta["status"] = "published_to_web"
    meta["publish_mode"] = mode
    meta["published_at"] = datetime.now().isoformat()
    meta["web_video_url"] = video_url
    meta["web_poster_url"] = poster_url
    meta["target_web_url"] = target_web_url
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"• Đã chèn vào config.js: ID='{video_id}'")
    logger.info(f"• Link đích cho Social Cmt: {target_web_url}")
    logger.info(f"--------------------------------------------------")

    return meta


def publish_all(
    force_mode: Optional[str] = None,
    simulate_cloud: bool = False,
    republish_all: bool = False,
) -> List[Dict[str, Any]]:
    """
    Quét toàn bộ *_meta.json trong storage/2_web_full/ và xuất bản lên Web
    """
    meta_files = sorted(
        config.FULL_DIR.glob("*_meta.json"),
        key=lambda p: p.stat().st_mtime,
    )

    if not meta_files:
        logger.info(f"Không có file *_meta.json nào trong {config.FULL_DIR}")
        return []

    published_results: List[Dict[str, Any]] = []
    for idx, mp in enumerate(meta_files):
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not republish_all and data.get("status") == "published_to_web" and not force_mode:
            logger.info(f"Bỏ qua video đã xuất bản: {mp.name} (dùng --all để xuất bản lại)")
            continue

        # Đặt video mới nhất làm default
        is_last = idx == len(meta_files) - 1
        res = publish_single_metadata(
            mp,
            force_mode=force_mode,
            simulate_cloud=simulate_cloud,
            set_as_default=is_last,
        )
        if res:
            published_results.append(res)

    return published_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Publisher Pipeline (Module 3)")
    parser.add_argument("--meta", "-m", type=str, help="Đường dẫn tới 1 file *_meta.json cụ thể")
    parser.add_argument("--mode", choices=["local", "cloud_r2"], help="Ép chạy chế độ local hoặc cloud_r2")
    parser.add_argument("--simulate-cloud", action="store_true", help="Giả lập upload Cloud R2 để test URL CDN")
    parser.add_argument("--all", action="store_true", help="Xuất bản lại toàn bộ video trong 2_web_full")
    args = parser.parse_args()

    if args.meta:
        publish_single_metadata(
            Path(args.meta),
            force_mode=args.mode,
            simulate_cloud=args.simulate_cloud,
            set_as_default=True,
        )
    else:
        publish_all(
            force_mode=args.mode,
            simulate_cloud=args.simulate_cloud,
            republish_all=args.all,
        )
