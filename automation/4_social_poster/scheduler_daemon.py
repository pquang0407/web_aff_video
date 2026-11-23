"""
SCHEDULER_DAEMON.PY - Bộ Lập Lịch Tự Động Đăng Bài 24/7 (Chạy ngầm trên Cloud / Server)
Hỗ trợ 3 cơ chế lập lịch:
1. Theo Khung Giờ Vàng cố định mỗi ngày (Ví dụ: 08:00, 11:30, 17:30, 20:30)
2. Theo Chu Kỳ Giãn Cách (Ví dụ: Cách mỗi 60 phút tự bốc 1 clip trong Queue ra đăng)
3. Đặt lịch riêng cho từng Video cụ thể trong Hàng Đợi
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import config
import fb_service
import poster

logger = logging.getLogger("SchedulerDaemon")


def set_video_schedule(video_id: str, scheduled_iso: str) -> Dict[str, Any]:
    """Gán lịch hẹn giờ đăng riêng cho 1 video cụ thể"""
    meta_path = config.FULL_DIR / f"{video_id}_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Không tìm thấy metadata cho video '{video_id}'")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["scheduled_at"] = scheduled_iso
    if scheduled_iso:
        meta["status"] = "scheduled"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def check_and_run_due_posts() -> Optional[Dict[str, Any]]:
    """
    Kiểm tra xem đã đến giờ đăng tự động chưa. Nếu đến giờ -> Tự bốc 1 video trong Queue ra đăng!
    """
    sched = config.get_scheduler_config()
    queue = poster.get_social_queue()
    now = datetime.now()
    now_hm = now.strftime("%H:%M")
    now_iso = now.strftime("%Y-%m-%d %H:%M")

    # 1. Kiểm tra xem có video nào được hẹn giờ cụ thể (Per-Video Schedule) đã đến hạn không
    for item in queue:
        sched_at = item.get("scheduled_at")
        if sched_at and item.get("status") != "posted_to_social":
            if now_iso >= sched_at.replace("T", " ")[:16]:
                vid_id = item["id"]
                logger.info(f"[AUTO SCHEDULER] Đến lịch hẹn của video '{vid_id}' ({sched_at}) -> Tự động đăng!")
                res = poster.post_video_to_social(
                    video_id=vid_id,
                    simulate=bool(sched.get("simulate_mode", False)),
                    allow_duplicate=False,
                )
                config.save_scheduler_config({"last_auto_run": now.isoformat()})
                return res

    # 2. Nếu bật Auto-Post 24/7 toàn cục
    if not sched.get("auto_post_enabled", False):
        return None

    # Tìm danh sách các video chưa đăng
    pending_videos = [x for x in queue if x.get("status") != "posted_to_social"]
    if not pending_videos:
        return None

    mode = sched.get("schedule_mode", "time_slots")
    last_run_str = sched.get("last_auto_run", "")
    should_fire = False

    if mode == "time_slots":
        slots = sched.get("daily_time_slots", ["08:00", "11:30", "17:30", "20:30"])
        # Kiểm tra nếu giờ hiện tại nằm trong khung giờ vàng và chưa chạy trong phút này
        if now_hm in slots and not last_run_str.startswith(now.strftime("%Y-%m-%dT%H:%M")):
            should_fire = True

    elif mode == "interval":
        interval_mins = max(5, int(sched.get("interval_minutes", 60)))
        if not last_run_str:
            should_fire = True
        else:
            try:
                last_dt = datetime.fromisoformat(last_run_str)
                elapsed_mins = (now - last_dt).total_seconds() / 60.0
                if elapsed_mins >= interval_mins:
                    should_fire = True
            except Exception:
                should_fire = True

    if should_fire:
        # Lưu mốc last_auto_run trước để đảm bảo không bắn lặp trong cùng 1 phút
        config.save_scheduler_config({"last_auto_run": now.isoformat()})

        page_cfg = fb_service.get_page_config()
        selected_page_ids = page_cfg.get("selected_page_ids") or []
        if not selected_page_ids:
            fallback_pid = page_cfg.get("selected_page_id") or ""
            selected_page_ids = [fallback_pid] if fallback_pid else [""]

        # Lấy danh sách clip chưa đăng theo thứ tự FIFO (cũ nhất lên trước)
        fifo_pending = list(reversed(pending_videos))
        num_to_post = min(len(selected_page_ids), len(fifo_pending))
        batch_results = []

        logger.info(
            f"[AUTO SCHEDULER 24/7] Đúng khung giờ ({mode}): Bắn {num_to_post} clip khác nhau cho {num_to_post}/{len(selected_page_ids)} Page (KHÔNG TRÙNG BÀI)!"
        )
        for i in range(num_to_post):
            vid_id = fifo_pending[i]["id"]
            # Dùng pick_next_round_robin_page_id để nếu kho ít clip hơn số Page thì vẫn chia đều công bằng qua các khung giờ
            target_pid = fb_service.pick_next_round_robin_page_id() if selected_page_ids[0] else None
            logger.info(f"  -> [{i + 1}/{num_to_post}] Đăng clip '{vid_id}' lên Page ID={target_pid}")
            try:
                res = poster.post_video_to_social(
                    video_id=vid_id,
                    page_id=target_pid,
                    simulate=bool(sched.get("simulate_mode", False)),
                    allow_duplicate=False,
                )
                batch_results.append(res)
            except Exception as post_err:
                logger.error(f"  ❌ Lỗi đăng clip '{vid_id}' lên Page {target_pid}: {post_err}")
            if i < num_to_post - 1:
                time.sleep(3)

        return {"batch_count": len(batch_results), "results": batch_results}

    return None


def start_background_scheduler_thread() -> threading.Thread:
    """Khởi chạy luồng kiểm tra lịch đăng ngầm mỗi 20 giây"""
    def _loop():
        logger.info("Đã khởi động Background Auto-Scheduler 24/7!")
        while True:
            try:
                check_and_run_due_posts()
            except Exception as e:
                logger.error(f"Lỗi trong tiến trình Auto-Scheduler: {e}")
            time.sleep(20)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t
