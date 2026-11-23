"""
POSTER.PY - Bộ điều phối xuất bản mạng xã hội (Facebook Fanpage + Threads + Auto Comment)
Đọc dữ liệu từ storage/2_web_full/*_meta.json và đăng video Teaser kèm bình luận link tự động
"""

import argparse
import json
import logging
import os
import subprocess
import time
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


def get_posted_video_registry() -> Dict[str, Any]:
    """Danh sách vĩnh viễn các video ID đã đăng lên Facebook (chống trùng 100% ngay cả sau khi xóa file trong storage/)"""
    reg = config.load_json(config.POSTED_VIDEO_IDS_FILE, {})
    return reg if isinstance(reg, dict) else {}


def mark_video_posted_and_free_storage(video_id: str, page_id: str = "", page_name: str = "", posted_at: str = "") -> List[str]:
    """
    Phương án A: Ghi nhận đã đăng vĩnh viễn (chống trùng 100%) + xóa ngay 2 bản .mp4 nặng trong storage/2_web_full & storage/3_social_teaser
    để giải phóng ~70% ổ cứng Cloud VM, nhưng VẪN GIỮ nguyên bản trên web/videos/ (tho-news.com) cho link comment Facebook!
    """
    reg = get_posted_video_registry()
    reg[video_id] = {
        "page_id": str(page_id or ""),
        "page_name": str(page_name or ""),
        "posted_at": posted_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    config.save_json(config.POSTED_VIDEO_IDS_FILE, reg)

    freed: List[str] = []
    redundant_files = [
        config.FULL_DIR / f"{video_id}.mp4",
        config.FULL_DIR / f"{video_id}_poster.jpg",
        config.FULL_DIR / f"{video_id}_meta.json",
        config.TEASER_DIR / f"{video_id}_teaser.mp4",
        config.TEASER_DIR / f"{video_id}_caption.txt",
    ]
    for fp in redundant_files:
        if fp.exists():
            try:
                fp.unlink(missing_ok=True)
                freed.append(str(fp.relative_to(config.BASE_DIR)))
            except Exception as e:
                logger.warning(f"Không thể xóa file tạm storage {fp}: {e}")
    if freed:
        logger.info(f"🧹 [FREE DISK] Đã giải phóng {len(freed)} file thừa trong storage/ cho video '{video_id}' (vẫn giữ trên tho-news.com)!")
    return freed


def get_social_queue() -> List[Dict[str, Any]]:
    """
    Lấy danh sách tất cả các video 3D Thỏ & Gấu (gộp từ storage/2_web_full và web/videos_db.json)
    để Admin luôn nhìn thấy 100% video đang có trên Web tho-news.com để đăng hoặc xóa.
    Đồng thời đối chiếu posted_video_ids.json để đảm bảo 0% đăng trùng!
    """
    posted_reg = get_posted_video_registry()

    for stale in list(config.FULL_DIR.glob("*_meta.json")):
        if not stale.name.startswith("tho_gau_"):
            try:
                stale.unlink(missing_ok=True)
            except Exception:
                pass

    meta_files = sorted(
        config.FULL_DIR.glob("tho_gau_*_meta.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items: List[Dict[str, Any]] = []
    seen_ids = set()
    for mp in meta_files:
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
            vid_id = str(data.get("id") or mp.stem.replace("_meta", ""))
            data["id"] = vid_id
            data["meta_file"] = str(mp)
            # Nếu video đã từng đăng (từ meta cũ) -> ghi vào registry & dọn luôn file thừa trong storage/
            if data.get("status") == "posted_to_social" and vid_id not in posted_reg:
                mark_video_posted_and_free_storage(
                    vid_id,
                    page_id=data.get("posted_page_id", ""),
                    page_name=data.get("posted_page_name", ""),
                    posted_at=data.get("last_posted_at", ""),
                )
                posted_reg = get_posted_video_registry()
            if vid_id in posted_reg:
                data["status"] = "posted_to_social"
                data["posted_page_id"] = posted_reg[vid_id].get("page_id", "")
                data["posted_page_name"] = posted_reg[vid_id].get("page_name", "")
            items.append(data)
            seen_ids.add(vid_id)
        except Exception:
            continue

    # Bổ sung các video đang hiển thị trên Web Player (web/videos_db.json) nếu chưa có trong storage/2_web_full
    web_db_path = config.BASE_DIR / "web" / "videos_db.json"
    if web_db_path.exists():
        try:
            db = json.loads(web_db_path.read_text(encoding="utf-8"))
            for vid_id, vid in (db.get("videos") or {}).items():
                if vid_id == "default" or vid_id in seen_ids or not isinstance(vid, dict):
                    continue
                is_posted = vid_id in posted_reg
                entry = {
                    "id": vid_id,
                    "title": vid.get("title", vid_id),
                    "duration": vid.get("duration", "00:46"),
                    "views": vid.get("views", "0"),
                    "uploadDate": vid.get("uploadDate", ""),
                    "web_video_url": vid.get("videoUrl", f"videos/{vid_id}.mp4"),
                    "web_poster_url": vid.get("posterUrl", f"videos/{vid_id}_poster.jpg"),
                    "target_web_url": f"https://tho-news.com/?v={vid_id}",
                    "status": "posted_to_social" if is_posted else "published_to_web",
                }
                if is_posted:
                    entry["posted_page_id"] = posted_reg[vid_id].get("page_id", "")
                    entry["posted_page_name"] = posted_reg[vid_id].get("page_name", "")
                items.append(entry)
                seen_ids.add(vid_id)
        except Exception:
            pass
    return items


def delete_video_everywhere(video_id: str, auto_git_push: bool = True) -> Dict[str, Any]:
    """
    Xóa triệt để 1 video khỏi Web Player (videos_db.json, config.js, web/videos/*),
    khỏi Hàng đợi Social (storage/2_web_full, storage/3_social_teaser),
    và tự động git push lên GitHub để Vercel gỡ khỏi tho-news.com ngay lập tức!
    """
    vid = (video_id or "").strip()
    if not vid or "/" in vid or "\\" in vid or ".." in vid:
        raise ValueError("Mã video không hợp lệ.")

    deleted_files: List[str] = []
    web_dir = config.BASE_DIR / "web"
    web_videos_dir = web_dir / "videos"
    web_db_path = web_dir / "videos_db.json"
    web_config_js = web_dir / "config.js"

    # 1. Xóa file vật lý trong web/videos, storage/2_web_full, storage/3_social_teaser
    targets = [
        web_videos_dir / f"{vid}.mp4",
        web_videos_dir / f"{vid}_poster.jpg",
        config.FULL_DIR / f"{vid}.mp4",
        config.FULL_DIR / f"{vid}_poster.jpg",
        config.FULL_DIR / f"{vid}_meta.json",
        config.TEASER_DIR / f"{vid}_teaser.mp4",
        config.TEASER_DIR / f"{vid}_caption.txt",
    ]
    for fp in targets:
        if fp.exists():
            try:
                fp.unlink(missing_ok=True)
                deleted_files.append(str(fp.relative_to(config.BASE_DIR)))
            except Exception as e:
                logger.warning(f"Không thể xóa file {fp}: {e}")

    # 2. Xóa khỏi web/videos_db.json và cập nhật lại web/config.js
    removed_from_web_db = False
    if web_db_path.exists():
        db = json.loads(web_db_path.read_text(encoding="utf-8"))
        videos = db.get("videos") or {}
        if vid in videos:
            del videos[vid]
            removed_from_web_db = True

        # Nếu 'default' đang trỏ tới video vừa xóa -> chuyển 'default' sang video mới nhất còn lại
        default_entry = videos.get("default")
        remaining_keys = [k for k in videos.keys() if k != "default"]
        if default_entry and (vid in str(default_entry.get("videoUrl", "")) or vid in str(default_entry.get("posterUrl", ""))):
            if remaining_keys:
                newest = dict(videos[remaining_keys[0]])
                newest["id"] = "default"
                videos["default"] = newest
            else:
                videos.pop("default", None)

        db["videos"] = videos
        web_db_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

        js_header = (
            "/**\n"
            " * CONFIG.JS - Được cập nhật tự động bởi Admin Social Poster\n"
            f" * Cập nhật lúc: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            " */\n"
        )
        web_config_js.write_text(
            js_header + f"const CONFIG = {json.dumps(db, ensure_ascii=False, indent=2)};\n",
            encoding="utf-8",
        )

    # 3. Tự động git push để Vercel gỡ video trên tho-news.com
    git_pushed = False
    git_note = ""
    if auto_git_push:
        try:
            cwd = str(config.BASE_DIR)
            subprocess.run(["git", "add", "-A", "web/"], cwd=cwd, check=True, capture_output=True)
            cm = subprocess.run(
                ["git", "commit", "-m", f"chore(admin): delete video {vid} from web & queue"],
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            if cm.returncode == 0:
                push = subprocess.run(["git", "push", "origin", "main"], cwd=cwd, capture_output=True, text=True)
                if push.returncode != 0:
                    subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=cwd, capture_output=True)
                    push = subprocess.run(["git", "push", "origin", "main"], cwd=cwd, capture_output=True, text=True)
                git_pushed = push.returncode == 0
                git_note = "Đã đẩy GitHub/Vercel (sẽ mất khỏi tho-news.com sau ~30-60 giây)." if git_pushed else (push.stderr or push.stdout)[:180]
            else:
                git_note = "Không có thay đổi mới trên Git."
        except Exception as e:
            git_note = f"Lưu ý Git push: {e}"

    return {
        "ok": True,
        "video_id": vid,
        "removed_from_web_db": removed_from_web_db,
        "deleted_files": deleted_files,
        "git_pushed": git_pushed,
        "git_note": git_note,
    }


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
    candidates = [
        config.TEASER_DIR / f"{video_id}_teaser.mp4",
        config.FULL_DIR / f"{video_id}.mp4",
        config.BASE_DIR / "web" / "videos" / f"{video_id}.mp4",
        Path(meta.get("teaser_video_path", "")),
        Path(meta.get("full_video_path", "")),
    ]
    teaser_path = candidates[0]
    for cand in candidates:
        if cand and cand.is_file() and cand.exists():
            teaser_path = cand
            break

    caption = (custom_caption or meta.get("social_caption") or meta.get("title") or "").strip()
    base_web_url = os.getenv("WEB_BASE_URL", "https://tho-news.com").rstrip("/")
    target_web_url = meta.get("target_web_url") or f"{base_web_url}/?v={video_id}"
    if "zento-web-five" in target_web_url or "webaffvideo-web.vercel.app" in target_web_url:
        target_web_url = f"{base_web_url}/?v={video_id}"

    sched_cfg = config.get_scheduler_config()
    cmt_template = sched_cfg.get("comment_template", "👉 Xem trọn vẹn bản Full HD không che tại đây: {url}")
    comment_text = cmt_template.replace("{url}", target_web_url)

    target_platforms = platforms or sched_cfg.get("platforms", ["facebook", "threads"])
    results: Dict[str, Any] = {}

    # 1. Đăng lên Facebook Fanpage + Auto Comment Link (Hỗ trợ xoay vòng nhiều Page KHÔNG TRÙNG VIDEO)
    if "facebook" in target_platforms:
        try:
            chosen_page_id = (page_id or "").strip() or (meta.get("assigned_page_id") or "").strip()
            if not chosen_page_id:
                chosen_page_id = fb_service.pick_next_round_robin_page_id()
            fb_res = fb_service.publish_video_and_auto_comment(
                video_path=teaser_path,
                caption=caption,
                comment_text=comment_text,
                page_id=chosen_page_id,
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

    # 3. Lưu trạng thái vào metadata và lịch sử (chỉ đánh dấu đã đăng nếu Facebook ok hoặc simulate)
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fb_ok = bool(results.get("facebook", {}).get("ok"))
    freed_files: List[str] = []
    if fb_ok and not simulate:
        p_id = str(results.get("facebook", {}).get("page_id", "") or "")
        p_name = str(results.get("facebook", {}).get("page_name", "") or "")
        freed_files = mark_video_posted_and_free_storage(
            video_id=video_id,
            page_id=p_id,
            page_name=p_name,
            posted_at=now_iso,
        )
    elif simulate:
        meta["status"] = "posted_to_social"
        meta["last_posted_at"] = now_iso
        meta["social_results"] = results
        if meta_path.exists():
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        meta["last_posted_at"] = now_iso
        meta["social_results"] = results
        if meta_path.exists():
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
