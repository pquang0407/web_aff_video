"""
RABBIT_BEAR_RUNNER.PY - Bộ điều phối Pipeline Video Tin Tức 3D (Vũ trụ Thỏ & Gấu)
---------------------------------------------------------------------------------
Kết nối trực tiếp động cơ 3D Pixar (D:\nckh\auto-video-gen) vào hệ thống Web Affiliate & Social Poster (D:\web_aff).
Hỗ trợ:
1. Nhận link bài báo bất kỳ (VnExpress, Soha, Dân Trí, Tuổi Trẻ...) từ Web Admin hoặc Telegram Bot.
2. Kích hoạt Pipeline Node.js (run-auto.mjs) tạo kịch bản 4 cảnh Thỏ & Gấu + 1 cảnh Outro cố định.
3. Đảm bảo giọng đọc đồng nhất 100% (vi-VN-NamMinhNeural) lấp đầy 9.35s/10s (không bị ngắn hay dư 4-5s chết).
4. Tự động xuất bản video thành phẩm 9:16 lên Web Player (web/config.js, web/videos_db.json) và Hàng đợi Social (Module 4).
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("RabbitBear3DRunner")

CURRENT_DIR = Path(__file__).resolve().parent
WEB_AFF_ROOT = CURRENT_DIR.parent.parent
LOCAL_AUTO_VIDEO_GEN = Path("d:/nckh/auto-video-gen")
BUNDLED_ENGINE_DIR = CURRENT_DIR / "rabbit_bear_engine"

if LOCAL_AUTO_VIDEO_GEN.exists():
    AUTO_VIDEO_GEN_ROOT = LOCAL_AUTO_VIDEO_GEN
    RUN_AUTO_SCRIPT = AUTO_VIDEO_GEN_ROOT / "scripts" / "run-auto.mjs"
else:
    AUTO_VIDEO_GEN_ROOT = BUNDLED_ENGINE_DIR
    RUN_AUTO_SCRIPT = BUNDLED_ENGINE_DIR / "run-auto.mjs"

STORAGE_RAW_DIR = WEB_AFF_ROOT / "storage" / "1_raw"
STORAGE_FULL_DIR = WEB_AFF_ROOT / "storage" / "2_web_full"
STORAGE_TEASER_DIR = WEB_AFF_ROOT / "storage" / "3_social_teaser"
WEB_VIDEOS_DIR = WEB_AFF_ROOT / "web" / "videos"
LEGACY_ARCHIVE_DIR = WEB_AFF_ROOT / "storage" / "_legacy_archive"


def _probe_duration_str(video_path: Path) -> str:
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        sec = round(float(res.stdout.strip()))
        mins, secs = divmod(sec, 60)
        return f"{mins:02d}:{secs:02d}"
    except Exception:
        return "00:46"


def archive_legacy_reup_clips() -> int:
    """
    Ẩn & lưu trữ toàn bộ các clip reup TikTok/demo cũ sang storage/_legacy_archive/
    để hệ thống chỉ hiển thị các video 3D Vũ trụ Thỏ & Gấu sạch sẽ (có thể khôi phục sau này).
    """
    LEGACY_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived = 0

    for folder in [STORAGE_RAW_DIR, STORAGE_FULL_DIR, STORAGE_TEASER_DIR, WEB_VIDEOS_DIR]:
        if not folder.exists():
            continue
        for f in list(folder.iterdir()):
            if f.name == ".gitkeep" or f.is_dir():
                continue
            if not f.name.startswith("tho_gau_"):
                dest = LEGACY_ARCHIVE_DIR / f"{folder.name}__{f.name}"
                try:
                    shutil.move(str(f), str(dest))
                    archived += 1
                except Exception as e:
                    logger.warning(f"Không thể lưu trữ file cũ {f.name}: {e}")

    logger.info(f"Đã ẩn và chuyển {archived} tệp clip cũ sang kho lưu trữ {LEGACY_ARCHIVE_DIR}")
    return archived


def publish_3d_master_video(
    video_id: str,
    master_video_path: Path,
    title: str,
    social_caption: str,
    category: str = "🐰🐻 VŨ TRỤ THỎ & GẤU 3D",
    source_article_url: str = "",
    set_as_default: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Đưa một video 3D Thỏ & Gấu thành phẩm vào Web Player (Module 3) và Hàng đợi Social (Module 4).
    """
    if not master_video_path.exists():
        logger.error(f"Không tìm thấy file video 3D: {master_video_path}")
        return None

    for d in [STORAGE_FULL_DIR, STORAGE_TEASER_DIR, WEB_VIDEOS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    full_mp4 = STORAGE_FULL_DIR / f"{video_id}.mp4"
    poster_jpg = STORAGE_FULL_DIR / f"{video_id}_poster.jpg"
    web_mp4 = WEB_VIDEOS_DIR / f"{video_id}.mp4"
    web_poster = WEB_VIDEOS_DIR / f"{video_id}_poster.jpg"
    teaser_mp4 = STORAGE_TEASER_DIR / f"{video_id}_teaser.mp4"
    caption_txt = STORAGE_TEASER_DIR / f"{video_id}_caption.txt"

    shutil.copy2(master_video_path, full_mp4)
    shutil.copy2(master_video_path, web_mp4)
    shutil.copy2(master_video_path, teaser_mp4)

    # Cắt frame poster ở giây 2.5 (có sẵn khung đồ họa 24H + nhân vật 3D Thỏ & Gấu sắc nét)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "00:00:02.500",
            "-i",
            str(master_video_path),
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(poster_jpg),
        ],
        capture_output=True,
        check=False,
    )
    if poster_jpg.exists():
        shutil.copy2(poster_jpg, web_poster)

    duration_str = _probe_duration_str(master_video_path)
    caption_txt.write_text(social_caption, encoding="utf-8")

    meta: Dict[str, Any] = {
        "id": video_id,
        "title": title,
        "duration": duration_str,
        "views": "268.4K",
        "likes": "29.5K",
        "uploadDate": "Vừa xong",
        "category": category,
        "pipeline_type": "rabbit_bear_3d",
        "source_article_url": source_article_url,
        "full_video_path": str(full_mp4),
        "poster_path": str(poster_jpg),
        "teaser_video_path": str(teaser_mp4),
        "web_video_url": f"videos/{video_id}.mp4",
        "web_poster_url": f"videos/{video_id}_poster.jpg",
        "target_web_url": f"https://tho-news.com/?v={video_id}",
        "social_caption": social_caption,
        "status": "published_to_web",
        "published_at": datetime.now().isoformat(),
    }

    meta_path = STORAGE_FULL_DIR / f"{video_id}_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Cập nhật web/config.js và web/videos_db.json thông qua Module 3
    pub_dir = WEB_AFF_ROOT / "automation" / "3_web_publisher"
    if str(pub_dir) not in sys.path:
        sys.path.insert(0, str(pub_dir))
    import publisher

    publisher.publish_single_metadata(meta_path, set_as_default=set_as_default)
    logger.info(f"✅ Đã xuất bản video 3D Thỏ & Gấu '{video_id}' lên Web Player & Social Queue!")
    return meta


def sync_existing_3d_masterpieces(clean_legacy: bool = True) -> List[Dict[str, Any]]:
    """
    Ẩn các clip reup cũ và nạp bộ đôi video 3D Thỏ & Gấu chuẩn (Á Đinh Tứ Xuyên & Bóng Đá Thỏ Gấu)
    vào hệ thống Web Player & Social Queue.
    """
    if clean_legacy:
        archive_legacy_reup_clips()

        # Reset sạch danh sách videos trong web/videos_db.json trước khi nạp video 3D Thỏ & Gấu
        db_path = WEB_AFF_ROOT / "web" / "videos_db.json"
        if db_path.exists():
            try:
                db = json.loads(db_path.read_text(encoding="utf-8"))
                db["videos"] = {}
                db_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Lỗi làm sạch videos_db.json: {e}")

    published_items = []

    items_to_sync = [
        {
            "id": "tho_gau_3d_bong_da_vietnam",
            "path": AUTO_VIDEO_GEN_ROOT / "output" / "tho-gau-bong-da-20261118" / "final_tho_gau_vietnam_kyrgyzstan.mp4",
            "title": "🐰🐻 [Bản Tin 3D] Đại Chiến Sân Cỏ: Tiền Đạo Thỏ Đỏ Nã Đại Bác & Cú Sút Giữa Sân Của Gấu Béo",
            "category": "⚽ 24H BÓNG ĐÁ • THỎ & GẤU 3D",
            "source_url": "https://soha.vn/dinh-bac-ghi-ban-nhung-u22-viet-nam-van-thua-nguoc-kyrgyzstan.htm",
            "caption": (
                "⚽🔥 ĐẠI CHIẾN SÂN CỎ 3D: TIỀN ĐẠO THỎ ĐỎ SỐ 7 ĐỐI ĐẦU BẦY GẤU TRẮNG!\n"
                "Mở màn với siêu phẩm nã đại bác cháy lưới kèm màn ăn mừng SIUUU tai thỏ bay phần phật, "
                "nhưng kịch bản phút 88 với cú sút từ giữa sân của đội trưởng Gấu Béo thực sự khiến cả cầu trường bật ngửa!\n"
                "👉 Xem trọn bộ bản Full HD 9:16 tại link dưới bình luận nhé! #ThoVaGau3D #24hBongDa #Hoathinh3D #PixarNews"
            ),
            "is_default": False,
        },
        {
            "id": "tho_gau_3d_a_dinh_tu_xuyen",
            "path": AUTO_VIDEO_GEN_ROOT / "output" / "yading-tu-xuyen-20261118" / "final_khach_viet_a_dinh_tu_xuyen.mp4",
            "title": "🐰🐻 [Bản Tin 3D] Thỏ Đỏ & Gấu Béo Lạc Vào Tiên Cảnh Á Đinh Tứ Xuyên: Vừa Leo Núi Vừa Ôm Bình Oxy",
            "category": "🏔️ 24H KHÁM PHÁ • THỎ & GẤU 3D",
            "source_url": "https://vnexpress.net/khach-viet-ngo-lac-vao-thien-duong-ha-gioi-o-trung-quoc-5139849.html",
            "caption": (
                "🏔️✨ THỎ ĐỎ & GẤU BÉO CHECK-IN THIÊN ĐƯỜNG HẠ GIỚI Á ĐINH (TỨ XUYÊN)!\n"
                "Cảnh sắc hồ ngọc bích dưới chân núi tuyết đẹp như phim kiếm hiệp, nhưng ở độ cao 4.700m thì Thỏ Đỏ phải ôm khư khư bình oxy, "
                "còn Gấu Béo mải tạo dáng bên Hồ Sữa lại trượt chân ngã lăn lông lốc cực hài hước!\n"
                "👉 Xem trọn bộ bản Full HD 9:16 tại link dưới bình luận nhé! #ThoVaGau3D #24hKhamPha #ADinhTuXuyen #Hoathinh3D"
            ),
            "is_default": True,
        },
    ]

    for item in items_to_sync:
        if item["path"].exists():
            res = publish_3d_master_video(
                video_id=item["id"],
                master_video_path=item["path"],
                title=item["title"],
                social_caption=item["caption"],
                category=item["category"],
                source_article_url=item["source_url"],
                set_as_default=item["is_default"],
            )
            if res:
                published_items.append(res)

    return published_items


def can_run_3d_locally() -> bool:
    """Kiểm tra máy hiện tại (Local hoặc Cloud VM) có Node.js + muse_cookie.txt/muse_session.b64 để render trực tiếp không"""
    if not shutil.which("node"):
        return False
    cookie_file = AUTO_VIDEO_GEN_ROOT / "muse_cookie.txt"
    b64_file = AUTO_VIDEO_GEN_ROOT / "muse_session.b64"
    if not cookie_file.exists() and not b64_file.exists():
        return False
    return RUN_AUTO_SCRIPT.exists()


PENDING_JOBS_FILE = WEB_AFF_ROOT / "storage" / "pending_3d_jobs.json"


def load_pending_jobs() -> List[Dict[str, Any]]:
    if not PENDING_JOBS_FILE.exists():
        return []
    try:
        return json.loads(PENDING_JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_pending_jobs(jobs: List[Dict[str, Any]]) -> None:
    PENDING_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue_cloud_3d_job(article_url: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    jobs = load_pending_jobs()
    job = {
        "job_id": f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "article_url": article_url.strip(),
        "chat_id": str(chat_id) if chat_id else "",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    jobs.append(job)
    save_pending_jobs(jobs)
    return job


FIFO_QUEUE_FILE = WEB_AFF_ROOT / "storage" / "rabbit_bear_fifo_queue.json"
_FIFO_LOCK = threading.Lock()
_FIFO_WORKER_THREAD: Optional[threading.Thread] = None


def _get_telegram_bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        return token
    for env_path in [WEB_AFF_ROOT / ".env", AUTO_VIDEO_GEN_ROOT / ".env"]:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass
    return ""


def _send_telegram_text(chat_id: str, html_text: str) -> None:
    if not chat_id:
        return
    token = _get_telegram_bot_token()
    if not token:
        return
    try:
        payload = json.dumps({
            "chat_id": str(chat_id),
            "text": html_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as _:
            pass
    except Exception as e:
        logger.warning(f"Không thể gửi thông báo Telegram tới {chat_id}: {e}")


def _load_fifo_state() -> Dict[str, Any]:
    if not FIFO_QUEUE_FILE.exists():
        return {"current": None, "queue": []}
    try:
        data = json.loads(FIFO_QUEUE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                "current": data.get("current"),
                "queue": data.get("queue") if isinstance(data.get("queue"), list) else [],
            }
    except Exception:
        pass
    return {"current": None, "queue": []}


def _save_fifo_state(state: Dict[str, Any]) -> None:
    FIFO_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FIFO_QUEUE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_fifo_queue_status() -> Dict[str, Any]:
    with _FIFO_LOCK:
        state = _load_fifo_state()
        return {
            "current": state.get("current"),
            "queue": list(state.get("queue", [])),
            "pending_count": len(state.get("queue", [])),
            "is_busy": state.get("current") is not None,
        }


def _fifo_worker_loop() -> None:
    global _FIFO_WORKER_THREAD
    log_file = WEB_AFF_ROOT / "storage" / "rabbit_bear_3d_build.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    while True:
        with _FIFO_LOCK:
            state = _load_fifo_state()
            queue = state.get("queue", [])
            if not queue:
                state["current"] = None
                _save_fifo_state(state)
                _FIFO_WORKER_THREAD = None
                logger.info("✅ [FIFO QUEUE] Đã xử lý xong toàn bộ hàng đợi 3D Thỏ & Gấu.")
                return
            job = queue.pop(0)
            job["status"] = "processing"
            job["started_at"] = datetime.now().isoformat()
            state["current"] = job
            state["queue"] = queue
            _save_fifo_state(state)
            remaining_after = len(queue)

        article_url = job["article_url"]
        chat_id = job.get("chat_id", "")
        notify_on_start = job.get("notify_on_start", True)

        logger.info(
            f"🎬 [FIFO WORKER] Bắt đầu dựng job {job['job_id']}: {article_url} (còn {remaining_after} link chờ)"
        )
        if notify_on_start and chat_id:
            _send_telegram_text(
                chat_id,
                (
                    "🎬 <b>ĐẾN LƯỢT BÀI BÁO CỦA BẠN TRONG HÀNG ĐỢI FIFO!</b>\n"
                    f"📰 <code>{article_url}</code>\n"
                    f"⏳ <i>Đang bắt đầu dựng 3D Thỏ & Gấu (còn {remaining_after} link xếp sau)...</i>"
                ),
            )

        cmd = ["node", str(RUN_AUTO_SCRIPT), article_url]
        if chat_id:
            cmd.extend(["--chat-id", str(chat_id)])

        # Trên Linux Cloud VM (e2-micro), hạ độ ưu tiên CPU & Disk của tiến trình dựng 3D/FFmpeg xuống thấp nhất
        # để Telegram Bot và Web Admin luôn phản hồi tức thì (< 1 giây), không bao giờ bị treo hay nghẽn lệnh!
        if os.name != "nt":
            prefix = []
            if shutil.which("ionice"):
                prefix.extend(["ionice", "-c", "3"])
            if shutil.which("nice"):
                prefix.extend(["nice", "-n", "19"])
            if prefix:
                cmd = prefix + cmd

        exit_code = -1
        tail_err = ""
        try:
            with open(log_file, "a", encoding="utf-8") as out_f:
                out_f.write(
                    f"\n==================== [FIFO JOB {job['job_id']}] {datetime.now().isoformat()} ====================\n"
                )
                out_f.flush()
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(AUTO_VIDEO_GEN_ROOT),
                    stdout=out_f,
                    stderr=subprocess.STDOUT,
                )
                with _FIFO_LOCK:
                    st = _load_fifo_state()
                    if st.get("current") and st["current"].get("job_id") == job["job_id"]:
                        st["current"]["pid"] = proc.pid
                        _save_fifo_state(st)
                exit_code = proc.wait()
        except Exception as e:
            tail_err = str(e)
            logger.error(f"❌ [FIFO WORKER] Lỗi chạy job {job['job_id']}: {e}")

        if exit_code != 0:
            if not tail_err and log_file.exists():
                try:
                    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                    err_lines = [ln for ln in lines[-20:] if "error" in ln.lower() or "fatal" in ln.lower() or "⚠️" in ln]
                    tail_err = (err_lines[-1] if err_lines else (lines[-1] if lines else f"Exit code {exit_code}"))[:260]
                except Exception:
                    tail_err = f"Exit code {exit_code}"
            logger.warning(f"⚠️ [FIFO WORKER] Job {job['job_id']} thất bại (exit={exit_code}): {tail_err}")
            if chat_id:
                _send_telegram_text(
                    chat_id,
                    (
                        "⚠️ <b>KHÔNG THỂ DỰNG VIDEO CHO BÀI BÁO NÀY</b>\n"
                        f"📰 <code>{article_url}</code>\n"
                        f"📌 <b>Lý do:</b> <code>{tail_err}</code>\n"
                        "➡️ <i>Hệ thống sẽ tự động chuyển sang link tiếp theo trong hàng đợi (nếu có).</i>"
                    ),
                )
        else:
            logger.info(f"✅ [FIFO WORKER] Hoàn tất job {job['job_id']} thành công!")

        with _FIFO_LOCK:
            st = _load_fifo_state()
            st["current"] = None
            _save_fifo_state(st)
        time.sleep(2)


def _ensure_fifo_worker_running() -> None:
    global _FIFO_WORKER_THREAD
    if _FIFO_WORKER_THREAD is not None and _FIFO_WORKER_THREAD.is_alive():
        return
    _FIFO_WORKER_THREAD = threading.Thread(target=_fifo_worker_loop, daemon=True, name="RabbitBearFIFOWorker")
    _FIFO_WORKER_THREAD.start()


def start_fifo_worker_if_needed() -> None:
    """Khôi phục hàng đợi FIFO nếu Cloud VM vừa khởi động lại khi đang dở job"""
    if not can_run_3d_locally():
        return
    with _FIFO_LOCK:
        state = _load_fifo_state()
        current = state.get("current")
        queue = state.get("queue", [])
        if current:
            current["status"] = "queued"
            current["notify_on_start"] = True
            queue.insert(0, current)
            state["current"] = None
            state["queue"] = queue
            _save_fifo_state(state)
            logger.info(f"♻️ [FIFO QUEUE] Khôi phục job đang chạy dở về đầu hàng đợi: {current.get('article_url')}")
        has_work = len(queue) > 0
    if has_work:
        _ensure_fifo_worker_running()


def enqueue_fifo_3d_jobs(
    article_urls: List[str],
    chat_id: Optional[str] = None,
    sender_name: str = "",
) -> Dict[str, Any]:
    """
    Nạp 1 hoặc hàng loạt link bài báo vào Hàng đợi FIFO tuần tự (1 video/lần).
    - Nếu Worker đang rảnh: link đầu tiên chạy ngay lập tức, các link sau xếp hàng chờ.
    - Nếu Worker đang bận: tất cả link mới xếp hàng theo thứ tự FIFO (đến trước làm trước).
    """
    clean_urls: List[str] = []
    seen = set()
    for u in article_urls:
        u_clean = u.strip()
        if len(u_clean) > 10 and u_clean not in seen:
            seen.add(u_clean)
            clean_urls.append(u_clean)

    if not can_run_3d_locally():
        jobs = [enqueue_cloud_3d_job(u, chat_id=chat_id) for u in clean_urls]
        return {
            "ok": True,
            "mode": "cloud_bridge_queue",
            "was_busy": False,
            "started_immediately": False,
            "items": [{"article_url": j["article_url"], "job_id": j["job_id"], "position": i + 1} for i, j in enumerate(jobs)],
            "current_job": None,
            "total_pending": len(jobs),
        }

    with _FIFO_LOCK:
        state = _load_fifo_state()
        was_busy = state.get("current") is not None or len(state.get("queue", [])) > 0
        current_job = state.get("current")
        queue = state.get("queue", [])
        added_items = []

        for idx, url in enumerate(clean_urls):
            starts_now = (not was_busy) and (idx == 0)
            job = {
                "job_id": f"fifo_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}",
                "article_url": url,
                "chat_id": str(chat_id) if chat_id else "",
                "sender_name": sender_name or "",
                "status": "queued",
                "notify_on_start": not starts_now,
                "created_at": datetime.now().isoformat(),
            }
            queue.append(job)
            # Nếu bắt đầu ngay (position=0), ngược lại tính vị trí chờ thực tế trong hàng đợi
            wait_pos = 0 if starts_now else (len(queue) if state.get("current") is not None else len(queue) - 1)
            added_items.append({
                "job_id": job["job_id"],
                "article_url": url,
                "starts_now": starts_now,
                "position": wait_pos,
            })

        state["queue"] = queue
        _save_fifo_state(state)
        total_pending = len(queue)

    _ensure_fifo_worker_running()
    return {
        "ok": True,
        "mode": "fifo_queue",
        "was_busy": was_busy,
        "started_immediately": (not was_busy) and len(added_items) > 0,
        "items": added_items,
        "current_job": current_job,
        "total_pending": total_pending,
    }


def trigger_3d_pipeline_from_article(
    article_url: str,
    async_mode: bool = True,
    chat_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Kích hoạt tiến trình sản xuất Video 3D Thỏ & Gấu từ link bài báo (run-auto.mjs).
    - Ở chế độ async_mode=True: Tự động đi qua Hàng đợi FIFO tuần tự (1 video/lần) để chống tràn RAM.
    """
    if async_mode:
        res = enqueue_fifo_3d_jobs([article_url], chat_id=chat_id)
        first = res["items"][0] if res.get("items") else {}
        return {
            "ok": True,
            "mode": res.get("mode", "fifo_queue"),
            "pid": first.get("job_id", "fifo"),
            "was_busy": res.get("was_busy", False),
            "position": first.get("position", 0),
            "current_job": res.get("current_job"),
            "article_url": article_url,
            "message": (
                "Đang xử lý ngay trên Xưởng 3D Thỏ & Gấu!"
                if first.get("starts_now")
                else f"Đã xếp vào Hàng đợi FIFO (Vị trí #{first.get('position', 1)})!"
            ),
        }

    if not can_run_3d_locally():
        job = enqueue_cloud_3d_job(article_url, chat_id=chat_id)
        return {
            "ok": True,
            "mode": "cloud_bridge_queue",
            "pid": job["job_id"],
            "job": job,
            "article_url": article_url,
            "message": "Đã xếp vào hàng đợi Cloud-Bridge!",
        }

    cmd = ["node", str(RUN_AUTO_SCRIPT), article_url.strip()]
    if chat_id:
        cmd.extend(["--chat-id", str(chat_id)])
    res = subprocess.run(cmd, cwd=str(AUTO_VIDEO_GEN_ROOT), capture_output=True, text=True, check=True)
    return {
        "ok": True,
        "mode": "sync",
        "article_url": article_url,
        "output": res.stdout[-1500:],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Điều phối Pipeline Video Tin Tức 3D Vũ trụ Thỏ & Gấu")
    parser.add_argument("--sync-existing", action="store_true", help="Ẩn clip cũ và đồng bộ các video 3D Thỏ & Gấu lên Web & Queue")
    parser.add_argument("--article", type=str, help="Link bài báo tin tức để dựng video 3D Thỏ & Gấu mới")
    parser.add_argument("--sync", action="store_true", help="Chờ dựng xong mới thoát (mặc định chạy async nếu gọi từ server)")
    args = parser.parse_args()

    if args.sync_existing:
        synced = sync_existing_3d_masterpieces(clean_legacy=True)
        print(f"Đã đồng bộ {len(synced)} video 3D Thỏ & Gấu lên hệ thống!")
    elif args.article:
        out = trigger_3d_pipeline_from_article(args.article, async_mode=not args.sync)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
