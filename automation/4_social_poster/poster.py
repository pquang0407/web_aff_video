"""
POSTER.PY - Bộ điều phối xuất bản mạng xã hội (Facebook Fanpage + Threads + Auto Comment)
Đọc dữ liệu từ storage/2_web_full/*_meta.json và đăng video Teaser kèm bình luận link tự động
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
import fb_service
import threads_service

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SocialPoster")


def get_social_queue() -> List[Dict[str, Any]]:
    """
    Lấy danh sách tất cả các video đã qua Module 2 & 3 để hiển thị lên Hàng Đợi (Queue)
    """
    meta_files = sorted(
        config.FULL_DIR.glob("*_meta.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items: List[Dict[str, Any]] = []
    for mp in meta_files:
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
            data["meta_file"] = str(mp)
            items.append(data)
        except Exception:
            continue
    return items


def get_post_history() -> List[Dict[str, Any]]:
    return config.load_json(config.POST_HISTORY_FILE, [])


def append_post_history(entry: Dict[str, Any]) -> None:
    history = get_post_history()
    history.insert(0, entry)
    config.save_json(config.POST_HISTORY_FILE, history[:200])


def post_video_to_social(
    video_id: str,
    platforms: Optional[List[str]] = None,
    page_id: Optional[str] = None,
    custom_caption: Optional[str] = None,
    simulate: bool = False,
) -> Dict[str, Any]:
    """
    Đăng 1 video Teaser lên Facebook Fanpage & Threads + Tự động bình luận link Web Player
    """
    meta_path = config.FULL_DIR / f"{video_id}_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Không tìm thấy metadata cho video '{video_id}' tại {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    teaser_path = Path(meta.get("teaser_video_path", config.TEASER_DIR / f"{video_id}_teaser.mp4"))
    if not teaser_path.exists():
        teaser_path = Path(meta.get("full_video_path", config.FULL_DIR / f"{video_id}.mp4"))

    caption = (custom_caption or meta.get("social_caption") or meta.get("title") or "").strip()
    target_web_url = meta.get("target_web_url") or f"https://zento-web-five.vercel.app/?v={video_id}"

    sched_cfg = config.get_scheduler_config()
    cmt_template = sched_cfg.get("comment_template", "👉 Xem trọn vẹn bản Full HD không che tại đây: {url}")
    comment_text = cmt_template.replace("{url}", target_web_url)

    target_platforms = platforms or sched_cfg.get("platforms", ["facebook", "threads"])
    results: Dict[str, Any] = {}

    # 1. Đăng lên Facebook Fanpage + Auto Comment Link
    if "facebook" in target_platforms:
        try:
            fb_res = fb_service.publish_video_and_auto_comment(
                video_path=teaser_path,
                caption=caption,
                comment_text=comment_text,
                page_id=page_id,
                simulate=simulate,
            )
            results["facebook"] = fb_res
        except Exception as fb_err:
            logger.error(f"Lỗi khi đăng bài Facebook: {fb_err}")
            results["facebook"] = {"ok": False, "error": str(fb_err)}

    # 2. Đăng lên Meta Threads + Auto Reply Link
    if "threads" in target_platforms:
        try:
            th_res = threads_service.publish_thread_with_auto_reply(
                caption=caption,
                reply_text=comment_text,
                video_public_url=meta.get("web_video_url"),
                simulate=simulate,
            )
            results["threads"] = th_res
        except Exception as th_err:
            logger.warning(f"Lỗi khi đăng bài Threads: {th_err}")
            results["threads"] = {"ok": False, "error": str(th_err)}

    # 3. Lưu trạng thái vào metadata và lịch sử
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta["status"] = "posted_to_social"
    meta["last_posted_at"] = now_iso
    meta["social_results"] = results
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    history_entry = {
        "video_id": video_id,
        "title": meta.get("title"),
        "target_web_url": target_web_url,
        "comment_text": comment_text,
        "platforms": target_platforms,
        "results": results,
        "posted_at": now_iso,
        "mode": "simulation" if simulate else "live",
    }
    append_post_history(history_entry)

    return history_entry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Social Poster Pipeline (Module 4)")
    parser.add_argument("--id", type=str, help="ID video cần đăng (ví dụ: dance, cat_mukkbang)")
    parser.add_argument("--simulate", action="store_true", help="Chạy ở chế độ giả lập an toàn")
    args = parser.parse_args()

    if args.id:
        res = post_video_to_social(args.id, simulate=args.simulate)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        queue = get_social_queue()
        print(f"Đang có {len(queue)} video trong hàng đợi Social Queue.")
