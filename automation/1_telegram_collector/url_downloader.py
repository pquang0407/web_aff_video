import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urlunparse

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("URLDownloader")

# Thư mục gốc & cấu hình
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import (
    RAW_STORAGE_DIR,
    mark_video_downloaded,
    is_video_downloaded,
    load_settings
)

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False
    logger.error("Chưa cài đặt thư viện yt-dlp!")

FB_COOKIES_JSON = ROOT_DIR / "automation" / "4_social_poster" / "data" / "facebook_cookies.json"
FB_NETSCAPE_COOKIE_PATH = CURRENT_DIR / "fb_cookies.txt"
ARCHIVE_FILE_PATH = CURRENT_DIR / "ytdlp_archive.txt"


def ensure_facebook_netscape_cookies() -> str:
    """Chuyển đổi cookies JSON sang định dạng Netscape cookie file để yt-dlp sử dụng"""
    if not FB_COOKIES_JSON.exists():
        return ""
    try:
        with open(FB_COOKIES_JSON, "r", encoding="utf-8") as f:
            cookie_list = json.load(f)

        lines = ["# Netscape HTTP Cookie File"]
        for c in cookie_list:
            name = c.get("name")
            value = c.get("value")
            if name and value:
                lines.append(f".facebook.com\tTRUE\t/\tTRUE\t2147483647\t{name}\t{value}")

        with open(FB_NETSCAPE_COOKIE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return str(FB_NETSCAPE_COOKIE_PATH)
    except Exception as e:
        logger.warning(f"Không thể tạo file cookie Netscape: {e}")
        return ""


def is_bare_facebook_page(url: str) -> bool:
    """Kiểm tra xem URL có phải là trang chủ Fanpage / Profile thay vì video cụ thể không"""
    parsed = urlparse(url)
    if "facebook.com" not in parsed.netloc and "fb.watch" not in parsed.netloc:
        return False
    
    clean_path = parsed.path.strip("/")
    segments = [s for s in clean_path.split("/") if s]
    
    # Các từ khóa nhận diện video cụ thể
    video_keywords = ["reel", "reels", "watch", "videos", "posts", "photo", "story.php", "permalink.php"]
    if any(k in clean_path.lower() for k in video_keywords) or "fb.watch" in url:
        # Nếu là dạng /page_name/videos/12345 thì là video cụ thể
        if "videos" in segments and len(segments) > segments.index("videos") + 1:
            return False
        if "reel" in segments or "watch" in segments or "posts" in segments:
            return False
        # Nếu chỉ dừng ở /page_name/videos hoặc /page_name/reels mà không có id thì vẫn là feed
        if len(segments) <= 2 and (segments[-1] in ["videos", "reels"]):
            return True

    # Link dạng https://www.facebook.com/share/r/xxx hoặc /share/v/xxx là video
    if "share" in segments and len(segments) >= 2 and segments[1] in ["r", "v"]:
        return False

    # Link dạng https://www.facebook.com/tintucvtv24 hoặc /tintucvtv24/
    if len(segments) == 1 and segments[0] not in ["share", "watch", "reel"]:
        return True

    return False


def prepare_candidate_urls(url: str) -> tuple[list, int]:
    """
    Chuẩn hóa URL thông minh:
    - Nếu là link video cụ thể (Reel, Watch, TikTok, YouTube Shorts): Giữ nguyên, tải 1 video.
    - Nếu là Fanpage: Báo lỗi hướng dẫn cụ thể vì Facebook chặn cào feed cả page không có video id.
    - Tách bỏ tham số query thừa (?mibextid=...) để tránh lỗi URL không hợp lệ.
    """
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip("/")
    is_facebook = "facebook.com" in url or "fb.watch" in url

    if is_facebook and is_bare_facebook_page(url):
        raise ValueError(
            f"Liên kết '{url}' là Trang chủ Fanpage, không chứa ID video cụ thể.\n"
            f"💡 Hướng dẫn: Bạn hãy mở video hoặc Reel muốn tải trên trang này -> Bấm nút 'Chia sẻ' (Share) -> Chọn 'Sao chép liên kết' (Copy link) rồi gửi lại nhé!"
        )

    # Kiểm tra xem có phải link video đơn không
    is_single_video = any(
        k in clean_path.lower()
        for k in ["/reel", "/watch", "/videos/", "/posts/", "/photo", "tiktok.com", "youtu.be", "/shorts/"]
    ) or "fb.watch" in url

    if not is_facebook or is_single_video:
        return [url], 1

    # Nếu là link Facebook Share dạng /share/12345...
    if "/share/" in clean_path.lower():
        return [url], 1

    return [url], 1


def download_from_url(url: str, max_downloads: int = 1, auto_trigger_pipeline: bool = True) -> list:
    """
    Tải video tự động từ bất kỳ liên kết nào:
    - Link video đơn: Facebook Reel, Facebook Watch, TikTok, YouTube Shorts...
    - Link Page hoặc Group Facebook: Tự động quét toàn bộ hoặc N video mới nhất!
    - Tự động bỏ qua các video đã tải trước đó qua file archive.
    """
    if not HAS_YTDLP:
        raise RuntimeError("yt-dlp chưa được cài đặt!")

    url = url.strip()
    is_facebook = "facebook.com" in url or "fb.watch" in url

    # Chuẩn bị cookie nếu là Facebook
    cookie_file = ensure_facebook_netscape_cookies() if is_facebook else ""

    # Chuẩn hóa danh sách URL mục tiêu
    candidate_urls, default_max = prepare_candidate_urls(url)
    if max_downloads == 1 and default_max > 1:
        max_downloads = default_max

    # Định danh file chuẩn theo ID video gốc (không dùng timestamp để chống lặp video)
    out_template = str(RAW_STORAGE_DIR / "vid_%(extractor_key)s_%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": out_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "max_downloads": max_downloads,
        "ignoreerrors": True,
        "no_warnings": True,
        "quiet": False,
    }

    # Chỉ ghi log archive khi cào quét hàng loạt từ kênh/Page để tránh tải lặp
    if max_downloads > 1:
        ydl_opts["download_archive"] = str(ARCHIVE_FILE_PATH)

    if cookie_file and os.path.exists(cookie_file):
        ydl_opts["cookiefile"] = cookie_file

    logger.info(f"Bắt đầu tải từ URL: {url} (Tối đa: {max_downloads} video)")

    downloaded_files = []
    before_files = set(RAW_STORAGE_DIR.glob("*.mp4"))

    for target_url in candidate_urls:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([target_url])

            current_new = set(RAW_STORAGE_DIR.glob("*.mp4")) - before_files
            if len(current_new) >= max_downloads:
                break
        except Exception as e:
            logger.warning(f"Lỗi khi thử tải từ {target_url}: {e}")

    after_files = set(RAW_STORAGE_DIR.glob("*.mp4"))
    new_files = list(after_files - before_files)

    # Nếu new_files rỗng (do file video đã tải trước đó trong khoang),
    # tự động tái sử dụng file đã có để tiếp tục đẩy vào AI Pipeline!
    if not new_files and max_downloads == 1:
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    vid_id = str(info.get("id", ""))
                    matched = [f for f in RAW_STORAGE_DIR.glob("*.mp4") if vid_id and vid_id in f.name]
                    if matched:
                        existing_file = matched[0]
                        logger.info(f"Phát hiện video đã có sẵn trong khoang thô: {existing_file.name} -> Đẩy vào AI Pipeline!")
                        new_files.append(existing_file)
        except Exception as check_err:
            logger.debug(f"Không thể kiểm tra file có sẵn: {check_err}")

    for nf in new_files:
        file_size_mb = round(nf.stat().st_size / (1024 * 1024), 2)
        unique_id = f"url_{nf.stem}"
        mark_video_downloaded(unique_id, nf.name, {
            "source_url": url,
            "size_mb": file_size_mb,
            "downloaded_at": datetime.now().isoformat()
        })
        downloaded_files.append({
            "path": str(nf),
            "filename": nf.name,
            "size_mb": file_size_mb,
            "id": nf.stem
        })
        logger.info(f"✅ Đã tải thành công video: {nf.name} ({file_size_mb} MB)")

    # Tự động kích hoạt Pipeline nếu có video mới
    if downloaded_files and auto_trigger_pipeline:
        settings = load_settings()
        if settings.get("auto_pipeline_on_receive", True):
            logger.info("⚡ Tự động kích hoạt AI Video Factory (Module 2 -> 3 -> 4)...")
            factory_script = ROOT_DIR / "automation" / "2_ai_video_factory" / "factory.py"
            if factory_script.exists():
                subprocess.Popen([sys.executable, str(factory_script)])

    return downloaded_files


def main():
    parser = argparse.ArgumentParser(description="Tự động tải video từ Link (Facebook Page, Group, Reel, TikTok, YouTube) vào Pipeline")
    parser.add_argument("url", help="Liên kết Facebook, TikTok, YouTube...")
    parser.add_argument("--max", type=int, default=5, help="Số video tối đa cần tải (với Page/Group, mặc định 5)")
    parser.add_argument("--no-pipeline", action="store_true", help="Không tự động kích hoạt AI pipeline sau khi tải")

    args = parser.parse_args()
    results = download_from_url(
        url=args.url,
        max_downloads=args.max,
        auto_trigger_pipeline=not args.no_pipeline
    )
    print(f"\n🎉 Kết quả: Đã tải {len(results)} video vào storage/1_raw/")
    for r in results:
        print(f" - {r['filename']} ({r['size_mb']} MB)")


if __name__ == "__main__":
    main()
