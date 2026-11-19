"""
LOCAL_CLOUD_3D_BRIDGE.PY - Cầu nối tự động giữa Cloud VM (Telegram Bot 24/7) & Xưởng 3D Local
---------------------------------------------------------------------------------------------
Khi người dùng gửi link bài báo vào Telegram Bot (đang chạy trên Cloud VM e2-micro),
Cloud VM sẽ xếp bài báo vào /api/rabbit-bear/pending.
Tiến trình này trên máy Local sẽ tự động nhận diện job mới sau mỗi 4 giây:
1. Gọi node run-auto.mjs dựng 4 cảnh 3D Pixar trên Muse.ai + Chrome Local.
2. Đẩy video 3D nguyên bản 100% lên GitHub & Vercel CDN.
3. Gọi /api/rabbit-bear/complete báo cho Cloud VM tự động git pull & nhắn tin link Vercel về Telegram!
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [3D-Bridge] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LocalCloud3DBridge")

ROOT_DIR = Path(__file__).resolve().parent
RUN_AUTO_MJS = Path("d:/nckh/auto-video-gen/scripts/run-auto.mjs")
FULL_DIR = ROOT_DIR / "storage" / "2_web_full"
DEFAULT_CLOUD_URL = os.getenv("CLOUD_ADMIN_URL", "http://34.21.148.229:5050").rstrip("/")


def fetch_pending_jobs(cloud_url: str) -> list:
    try:
        req = urllib.request.Request(f"{cloud_url}/api/rabbit-bear/pending", method="GET")
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data.get("jobs", [])
    except Exception:
        pass
    return []


def notify_job_complete(cloud_url: str, job_id: str, video_id: str, title: str, chat_id: str) -> None:
    try:
        payload = json.dumps({
            "job_id": job_id,
            "video_id": video_id,
            "title": title,
            "chat_id": chat_id,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{cloud_url}/api/rabbit-bear/complete",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=15)
        logger.info(f"✅ Đã báo Cloud VM đồng bộ & gửi thông báo Telegram cho video '{video_id}'!")
    except Exception as e:
        logger.warning(f"Không thể gọi callback /api/rabbit-bear/complete: {e}")


def get_newest_3d_meta() -> dict:
    metas = sorted(FULL_DIR.glob("tho_gau_3d_*_meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if metas:
        try:
            return json.loads(metas[0].read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def run_bridge_loop(cloud_url: str = DEFAULT_CLOUD_URL) -> None:
    logger.info("==================================================================")
    logger.info(f"🐰🐻 CẦU NỐI XƯỞNG 3D LOCAL <-> CLOUD VM ĐANG LẮNG NGHE TẠI:")
    logger.info(f"👉 Cloud Endpoint: {cloud_url}")
    logger.info("==================================================================")

    processed_ids = set()

    while True:
        jobs = fetch_pending_jobs(cloud_url)
        for job in jobs:
            job_id = job.get("job_id", "")
            article_url = job.get("article_url", "")
            chat_id = job.get("chat_id", "")
            if not job_id or not article_url or job_id in processed_ids:
                continue

            processed_ids.add(job_id)
            logger.info(f"🎬 Nhận job 3D mới từ Telegram/Cloud [{job_id}]: {article_url}")
            try:
                subprocess.run(
                    ["node", str(RUN_AUTO_MJS), article_url],
                    cwd="d:/nckh/auto-video-gen",
                    check=True,
                )
                newest = get_newest_3d_meta()
                vid_id = newest.get("id", "")
                title = newest.get("title", "Bản Tin 3D Thỏ & Gấu")
                notify_job_complete(cloud_url, job_id, vid_id, title, chat_id)
            except Exception as e:
                logger.error(f"❌ Lỗi xử lý job {job_id}: {e}")

        time.sleep(4)


if __name__ == "__main__":
    url_arg = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else DEFAULT_CLOUD_URL
    run_bridge_loop(url_arg)
