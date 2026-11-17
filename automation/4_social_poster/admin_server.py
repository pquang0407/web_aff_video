"""
ADMIN_SERVER.PY - Web Admin Quản Trị & Bộ Lập Lịch Tự Động 24/7 (Module 4)
Chạy độc lập tại: http://127.0.0.1:5050
Tự động chạy ngầm tiến trình Auto-Scheduler kiểm tra lịch đăng mỗi 20 giây!
"""

import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import config
import fb_service
import poster
import scheduler_daemon

STATIC_DIR = Path(__file__).resolve().parent / "static"
PORT = 5050


class AdminRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
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
                "fb_pages": fb_service.get_page_config(),
                "threads": config.get_threads_config(),
                "scheduler": config.get_scheduler_config(),
                "queue": poster.get_social_queue(),
                "history": poster.get_post_history(),
            })
            return

        self._send_json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self) -> None:
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

            if path == "/api/fb/fetch-pages-token":
                pages = fb_service.fetch_managed_pages_via_token(payload.get("token", ""))
                self._send_json({"ok": True, "fb_pages": fb_service.get_page_config(), "count": len(pages)})
                return

            if path == "/api/fb/select-page":
                cfg = fb_service.get_page_config()
                saved = fb_service.save_page_config(cfg.get("pages", []), payload.get("page_id", ""))
                self._send_json({"ok": True, "fb_pages": saved})
                return

            if path == "/api/threads/save":
                saved = config.save_threads_config(payload)
                self._send_json({"ok": True, "threads": saved})
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


def run_admin_server(port: int = PORT) -> None:
    # Khởi chạy luồng lập lịch tự động 24/7 ngầm
    scheduler_daemon.start_background_scheduler_thread()

    # Lắng nghe trên 0.0.0.0 để cho phép truy cập từ xa qua IP công khai máy ảo
    server = HTTPServer(("0.0.0.0", port), AdminRequestHandler)
    print("==================================================================")
    print(f" WEB ADMIN & BỘ LẬP LỊCH TỰ ĐỘNG 24/7 ĐANG CHẠY TẠI:")
    print(f" 👉 http://0.0.0.0:{port}")
    print("==================================================================")
    server.serve_forever()


if __name__ == "__main__":
    run_admin_server()
