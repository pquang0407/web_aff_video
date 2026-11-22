"""
ADMIN_SERVER.PY - Web Admin Quản Trị & Bộ Lập Lịch Tự Động 24/7 (Module 4)
Chạy độc lập tại: http://127.0.0.1:5050
Tự động chạy ngầm tiến trình Auto-Scheduler kiểm tra lịch đăng mỗi 20 giây!
"""

import base64
import hmac
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import config
import fb_service
import poster
import scheduler_daemon
import tiktok_service

STATIC_DIR = Path(__file__).resolve().parent / "static"
PORT = 5050


def _load_admin_credentials() -> tuple[str, str]:
    """Đọc ADMIN_USER và ADMIN_PASSWORD từ biến môi trường hoặc file .env"""
    env_user = os.getenv("ADMIN_USER", "").strip()
    env_pass = os.getenv("ADMIN_PASSWORD", "").strip()
    env_file = config.BASE_DIR / ".env"
    if (not env_user or not env_pass) and env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "ADMIN_USER" and not env_user:
                    env_user = v
                elif k == "ADMIN_PASSWORD" and not env_pass:
                    env_pass = v
        except Exception:
            pass
    return (env_user or "admin", env_pass or "ThoNews@2026!")


def _get_safe_threads_config() -> dict:
    raw = config.get_threads_config()
    return {
        "enabled": bool(raw.get("enabled", False)),
        "username": raw.get("username", ""),
        "threads_user_id": raw.get("threads_user_id", ""),
        "has_token": bool(raw.get("access_token")),
        "auto_reply_link": bool(raw.get("auto_reply_link", True)),
    }


class AdminRequestHandler(BaseHTTPRequestHandler):
    timeout = 15

    def setup(self) -> None:
        super().setup()
        try:
            self.connection.settimeout(15)
        except Exception:
            pass

    def _require_auth(self) -> bool:
        """Khóa HTTP Basic Auth bảo vệ 100% Web Admin và API trước bot quét IP"""
        expected_user, expected_pass = _load_admin_credentials()
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:].strip()).decode("utf-8", errors="ignore")
                if ":" in decoded:
                    u, p = decoded.split(":", 1)
                    if hmac.compare_digest(u, expected_user) and hmac.compare_digest(p, expected_pass):
                        return True
            except Exception:
                pass
        body = b"401 Unauthorized - Vui long dang nhap Tai khoan Quan Tri"
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Tho-News Social Admin"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def _send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if not self._require_auth():
            return
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/admin", "/admin.html"):
            html_file = STATIC_DIR / "admin.html"
            raw = html_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/state":
            self._send_json({
                "ok": True,
                "fb_cookie": fb_service.get_cookie_status(),
                "fb_pages": fb_service.get_page_config_public(),
                "fb_app": fb_service.get_app_config_public(),
                "tiktok": tiktok_service.get_tiktok_config_public(),
                "threads": _get_safe_threads_config(),
                "scheduler": config.get_scheduler_config(),
                "queue": poster.get_social_queue(),
                "history": poster.get_post_history(),
            })
            return

        if path == "/api/rabbit-bear/logs":
            log_file = Path(__file__).resolve().parent.parent.parent / "storage" / "rabbit_bear_3d_build.log"
            lines = []
            if log_file.exists():
                try:
                    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-30:]
                except Exception:
                    pass
            self._send_json({"ok": True, "logs": lines})
            return

        if path == "/api/rabbit-bear/pending":
            import sys
            factory_dir = Path(__file__).resolve().parent.parent / "2_ai_video_factory"
            if str(factory_dir) not in sys.path:
                sys.path.insert(0, str(factory_dir))
            import rabbit_bear_runner
            jobs = [j for j in rabbit_bear_runner.load_pending_jobs() if j.get("status") == "pending"]
            self._send_json({"ok": True, "jobs": jobs})
            return

        self._send_json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"

        try:
            payload = json.loads(body_raw) if body_raw else {}

            if path == "/api/fb/save-cookies":
                status = fb_service.save_facebook_cookies(payload.get("cookies_text", ""))
                self._send_json({"ok": True, "fb_cookie": status})
                return

            if path == "/api/fb/save-app-config":
                fb_service.save_app_config(
                    payload.get("app_id", ""),
                    payload.get("app_secret", ""),
                )
                self._send_json({"ok": True, "fb_app": fb_service.get_app_config_public()})
                return

            if path == "/api/fb/fetch-pages-token":
                res_info = fb_service.fetch_managed_pages_via_token(
                    payload.get("token", ""),
                    app_id=payload.get("app_id", ""),
                    app_secret=payload.get("app_secret", ""),
                )
                pages = res_info.get("pages", [])
                self._send_json({
                    "ok": True,
                    "fb_pages": fb_service.get_page_config_public(),
                    "fb_app": fb_service.get_app_config_public(),
                    "count": len(pages),
                    "is_permanent": res_info.get("is_permanent", False),
                    "exchange_note": res_info.get("exchange_note", ""),
                })
                return

            if path == "/api/fb/select-page":
                cfg = fb_service.get_page_config()
                fb_service.save_page_config(cfg.get("pages", []), payload.get("page_id", ""))
                self._send_json({"ok": True, "fb_pages": fb_service.get_page_config_public()})
                return

            if path == "/api/fb/toggle-page":
                fb_service.toggle_selected_page(payload.get("page_id", ""))
                self._send_json({"ok": True, "fb_pages": fb_service.get_page_config_public()})
                return

            if path == "/api/tiktok/save-config":
                tiktok_service.save_tiktok_app_config(
                    client_key=payload.get("client_key", ""),
                    client_secret=payload.get("client_secret", ""),
                    post_mode=payload.get("post_mode"),
                    privacy_level=payload.get("privacy_level"),
                )
                auth_url = ""
                try:
                    auth_url = tiktok_service.build_oauth_authorize_url()
                except Exception:
                    pass
                self._send_json({
                    "ok": True,
                    "tiktok": tiktok_service.get_tiktok_config_public(),
                    "auth_url": auth_url,
                })
                return

            if path == "/api/tiktok/exchange-code":
                pub = tiktok_service.exchange_code_for_token(payload.get("code", ""))
                self._send_json({"ok": True, "tiktok": pub})
                return

            if path == "/api/tiktok/post":
                video_id = (payload.get("video_id") or "").strip()
                candidates = [
                    config.BASE_DIR / "web" / "videos" / f"{video_id}.mp4",
                    config.FULL_DIR / f"{video_id}.mp4",
                    config.TEASER_DIR / f"{video_id}_teaser.mp4",
                ]
                video_path = next((p for p in candidates if p.exists()), candidates[0])
                caption = payload.get("caption", "")
                if not caption:
                    meta_p = config.FULL_DIR / f"{video_id}_meta.json"
                    if meta_p.exists():
                        try:
                            m = json.loads(meta_p.read_text(encoding="utf-8"))
                            caption = m.get("social_caption") or m.get("title") or video_id
                        except Exception:
                            caption = video_id
                    else:
                        caption = video_id
                tt_res = tiktok_service.publish_video_to_tiktok(video_path, caption)
                self._send_json({"ok": True, "result": tt_res})
                return

            if path == "/api/threads/save":
                saved = config.save_threads_config(payload)
                self._send_json({"ok": True, "threads": saved})
                return

            if path == "/api/video/delete":
                video_id = payload.get("video_id", "").strip()
                res = poster.delete_video_everywhere(video_id, auto_git_push=True)
                self._send_json({
                    "ok": True,
                    "delete_result": res,
                    "queue": poster.get_social_queue(),
                })
                return

            if path == "/api/queue/clear":
                # Xóa sạch các video cũ trong hàng đợi
                deleted_count = 0
                for mp in config.FULL_DIR.glob("*_meta.json"):
                    try:
                        mp.unlink(missing_ok=True)
                        deleted_count += 1
                    except Exception:
                        pass
                for tp in config.TEASER_DIR.glob("*.*"):
                    if tp.name != ".gitkeep":
                        try:
                            tp.unlink(missing_ok=True)
                        except Exception:
                            pass
                self._send_json({
                    "ok": True,
                    "deleted_count": deleted_count,
                    "queue": poster.get_social_queue(),
                })
                return

            if path == "/api/scheduler/save":
                saved = config.save_scheduler_config(payload)
                self._send_json({"ok": True, "scheduler": saved})
                return

            if path == "/api/scheduler/set-video-time":
                video_id = payload.get("video_id", "")
                scheduled_at = payload.get("scheduled_at", "")
                scheduler_daemon.set_video_schedule(video_id, scheduled_at)
                self._send_json({
                    "ok": True,
                    "queue": poster.get_social_queue(),
                })
                return

            if path == "/api/social/post":
                video_id = payload.get("video_id", "")
                simulate = bool(payload.get("simulate", False))
                page_id = payload.get("page_id")
                platforms = payload.get("platforms")
                result = poster.post_video_to_social(
                    video_id=video_id,
                    platforms=platforms,
                    page_id=page_id,
                    simulate=simulate,
                )
                self._send_json({
                    "ok": True,
                    "result": result,
                    "queue": poster.get_social_queue(),
                    "history": poster.get_post_history(),
                })
                return

            if path == "/api/rabbit-bear/generate":
                import sys
                factory_dir = Path(__file__).resolve().parent.parent / "2_ai_video_factory"
                if str(factory_dir) not in sys.path:
                    sys.path.insert(0, str(factory_dir))
                import rabbit_bear_runner
                article_url = payload.get("url", "").strip()
                if not article_url:
                    self._send_json({"ok": False, "error": "Vui lòng nhập link bài báo tin tức!"}, 400)
                    return
                res = rabbit_bear_runner.trigger_3d_pipeline_from_article(article_url, async_mode=True)
                self._send_json({
                    "ok": True,
                    "pipeline": res,
                    "queue": poster.get_social_queue(),
                })
                return

            if path == "/api/rabbit-bear/complete":
                import os
                import subprocess
                import sys
                import urllib.request
                factory_dir = Path(__file__).resolve().parent.parent / "2_ai_video_factory"
                if str(factory_dir) not in sys.path:
                    sys.path.insert(0, str(factory_dir))
                import rabbit_bear_runner

                job_id = payload.get("job_id", "")
                video_id = payload.get("video_id", "")
                title = payload.get("title", "Bản Tin 3D Thỏ & Gấu")
                chat_id = payload.get("chat_id", "")

                # Cập nhật trạng thái job
                jobs = rabbit_bear_runner.load_pending_jobs()
                for j in jobs:
                    if j.get("job_id") == job_id:
                        j["status"] = "completed"
                        j["video_id"] = video_id
                        if not chat_id:
                            chat_id = j.get("chat_id", "")
                rabbit_bear_runner.save_pending_jobs(jobs)

                # Tự động git pull trên Cloud VM để nhận video 3D mới nhất từ GitHub
                base_dir = str(config.BASE_DIR)
                subprocess.run(["git", "fetch", "origin", "main"], cwd=base_dir, capture_output=True)
                subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=base_dir, capture_output=True)

                # Gửi thông báo hoàn tất trực tiếp về Telegram cho người dùng
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
                web_base = os.getenv("WEB_BASE_URL", "https://tho-news.com").rstrip("/")
                if bot_token and chat_id and video_id:
                    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    msg_text = (
                        f"🎉 <b>HOÀN TẤT DỰNG VIDEO 3D THỎ & GẤU!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎬 <b>Tiêu đề:</b> {title}\n"
                        f"🆔 <b>Mã Video:</b> <code>{video_id}</code>\n"
                        f"🌐 <b>Xem trực tiếp trên Web Player:</b>\n"
                        f"{web_base}/?v={video_id}\n\n"
                        f"✅ <i>Video đã được giữ nguyên bản 100% đưa vào Hàng đợi Social trên Cloud VM!</i>"
                    )
                    tg_payload = json.dumps({
                        "chat_id": chat_id,
                        "text": msg_text,
                        "parse_mode": "HTML",
                    }).encode("utf-8")
                    try:
                        req = urllib.request.Request(tg_url, data=tg_payload, headers={"Content-Type": "application/json"})
                        urllib.request.urlopen(req, timeout=10)
                    except Exception:
                        pass

                self._send_json({"ok": True, "video_id": video_id, "queue": poster.get_social_queue()})
                return

            if path == "/api/rabbit-bear/sync":
                import sys
                factory_dir = Path(__file__).resolve().parent.parent / "2_ai_video_factory"
                if str(factory_dir) not in sys.path:
                    sys.path.insert(0, str(factory_dir))
                import rabbit_bear_runner
                synced = rabbit_bear_runner.sync_existing_3d_masterpieces(clean_legacy=True)
                self._send_json({
                    "ok": True,
                    "count": len(synced),
                    "queue": poster.get_social_queue(),
                })
                return

            if path == "/api/collector/download-url":
                import sys
                collector_dir = Path(__file__).resolve().parent.parent / "1_telegram_collector"
                if str(collector_dir) not in sys.path:
                    sys.path.insert(0, str(collector_dir))
                from url_downloader import download_from_url
                url = payload.get("url", "").strip()
                max_count = int(payload.get("max_count", 3))
                downloaded = download_from_url(url=url, max_downloads=max_count, auto_trigger_pipeline=True)
                self._send_json({
                    "ok": True,
                    "downloaded": downloaded,
                    "count": len(downloaded),
                    "queue": poster.get_social_queue()
                })
                return

            self._send_json({"ok": False, "error": "Unknown endpoint"}, 404)

        except Exception as e:
            traceback.print_exc()
            self._send_json({"ok": False, "error": str(e)}, 400)


class ResilientAdminHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 64


def run_admin_server(port: int = PORT) -> None:
    # Khởi chạy luồng lập lịch tự động 24/7 ngầm
    scheduler_daemon.start_background_scheduler_thread()

    # Lắng nghe đa luồng trên 0.0.0.0 với timeout chống treo cổng khi có bot quét IP
    server = ResilientAdminHTTPServer(("0.0.0.0", port), AdminRequestHandler)
    print("==================================================================")
    print(f" WEB ADMIN & BỘ LẬP LỊCH TỰ ĐỘNG 24/7 ĐANG CHẠY TẠI:")
    print(f" 👉 http://0.0.0.0:{port}")
    print("==================================================================")
    server.serve_forever()


if __name__ == "__main__":
    run_admin_server()
