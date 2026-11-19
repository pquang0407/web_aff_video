"""
FACTORY.PY - Bộ điều phối tổng thể của Xưởng AI Video Factory (Module 2)
Quy trình: 1_raw -> Gemini Analysis -> FFmpeg Render -> 2_web_full & 3_social_teaser -> Metadata
"""

import argparse
import json
import logging
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import config
import gemini_analyzer
import tts_engine
import video_engine

# Cờ tắt toàn bộ chức năng chỉnh sửa/lật gương/chèn banner/lồng tiếng đè của hệ thống cũ.
# Mặc định False = Giữ nguyên 100% clip gốc để đưa thẳng vào Queue & Web Player.
LEGACY_EDIT_OVERLAY_MODE = False

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AIVideoFactory")

def format_duration(seconds: float) -> str:
    """Đổi số giây sang định dạng mm:ss"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def generate_fake_views() -> str:
    """Tạo số view giả lập ban đầu để tăng độ uy tín"""
    views_k = round(random.uniform(85.0, 320.0), 1)
    return f"{views_k}K"

def process_single_video(input_path: Path, video_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Quy trình xử lý khép kín cho 1 video
    """
    if not input_path.exists():
        logger.error(f"File video không tồn tại: {input_path}")
        return None

    # Tạo ID duy nhất cho video nếu chưa có
    if not video_id:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_id = f"clip_{timestamp_str}"

    logger.info(f"==================================================")
    logger.info(f"BẮT ĐẦU XỬ LÝ VIDEO: {input_path.name} (ID: {video_id})")
    logger.info(f"==================================================")

    # 1. Trích xuất thông tin kỹ thuật
    probe_info = video_engine.probe_video(input_path)
    duration = probe_info.get("duration", 30.0)
    logger.info(f"Thời lượng gốc: {duration:.1f}s | Kích thước: {probe_info['width']}x{probe_info['height']}")

    # 2. Phân tích nội dung & tìm Highlight bằng Gemini AI
    analysis = gemini_analyzer.analyze_video_with_gemini(input_path, duration)

    # 3. Chuẩn bị đường dẫn xuất file
    full_output = config.FULL_DIR / f"{video_id}.mp4"
    poster_output = config.FULL_DIR / f"{video_id}_poster.jpg"
    teaser_output = config.TEASER_DIR / f"{video_id}_teaser.mp4"
    voice_output = config.TEASER_DIR / f"{video_id}_voice.mp3"
    sub_output = config.TEASER_DIR / f"{video_id}_sub.srt"
    metadata_output = config.FULL_DIR / f"{video_id}_meta.json"

    # 4. Trích xuất Poster Thumbnail
    poster_timestamp = min(2.0, max(0.5, duration / 4))
    video_engine.extract_poster(input_path, poster_output, timestamp=poster_timestamp)

    if not LEGACY_EDIT_OVERLAY_MODE:
        # CHẾ ĐỘ MỚI: GIỮ NGUYÊN 100% CLIP GỐC ĐƯA THẲNG VÀO QUEUE & WEB PLAYER (KHÔNG CẮT, KHÔNG LẬT GƯƠNG, KHÔNG CHÈN ĐÈ)
        shutil.copy2(input_path, full_output)
        shutil.copy2(input_path, teaser_output)
        logger.info(f"✅ [KEEP ORIGINAL] Đã giữ nguyên 100% clip gốc đưa vào Web & Queue: {full_output.name}")
    else:
        # [LEGACY HIDDEN - GIỮ LẠI ĐỂ DÙNG SAU KHI BẬT LEGACY_EDIT_OVERLAY_MODE]
        success_full = video_engine.render_full_video(input_path, full_output, hflip=True)
        if not success_full:
            logger.error("Xuất bản Full thất bại!")
            return None

        voiceover_text = analysis.get("voiceover_text", "")
        has_tts = False
        if voiceover_text:
            has_tts = tts_engine.generate_voice_and_sub(voiceover_text, voice_output, sub_output)

        if duration <= config.SHORT_VIDEO_THRESHOLD:
            start_sec = 0.0
            teaser_dur = duration
        else:
            start_sec = max(0.0, float(analysis.get("teaser_start_sec", 0.0)))
            teaser_dur = min(duration, float(analysis.get("teaser_duration_sec", config.TEASER_CUT_DURATION)))
            if start_sec + teaser_dur > duration:
                start_sec = max(0.0, duration - teaser_dur)

        top_text = analysis["top_banner_text"]
        bottom_text = analysis["bottom_banner_text"]

        video_engine.render_teaser(
            input_path=input_path,
            output_path=teaser_output,
            start_sec=start_sec,
            duration_sec=teaser_dur,
            top_text=top_text,
            bottom_text=bottom_text,
            hflip=True,
            voiceover_path=voice_output if has_tts else None,
            subtitle_path=sub_output if has_tts else None
        )

    # 7. Đóng gói Metadata chuẩn để bàn giao cho Module 3 (Web Publisher) & Module 4 (Facebook Poster)
    metadata = {
        "id": video_id,
        "title": analysis["title"],
        "social_caption": analysis["social_caption"],
        "duration": format_duration(duration),
        "views": f"{generate_fake_views()} lượt xem",
        "likes": f"{round(random.uniform(5.0, 25.0), 1)}K",
        "uploadDate": "Vừa xong",
        "raw_source": str(input_path),
        "full_video_path": str(full_output),
        "poster_path": str(poster_output),
        "teaser_video_path": str(teaser_output),
        "created_at": datetime.now().isoformat(),
        "status": "ready_for_publish"
    }

    with open(metadata_output, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info("--------------------------------------------------")
    logger.info(f"HOÀN THÀNH XUẤT XƯỞNG VIDEO: {video_id}")
    logger.info(f"• Bản Full Web: {full_output.name}")
    logger.info(f"• Bản Teaser Social: {teaser_output.name}")
    logger.info(f"• Tiêu đề Web: {analysis['title']}")
    logger.info("--------------------------------------------------")

    # Tự động xuất bản ngay lên Web Player (Module 3) & Git Push
    trigger_web_publisher()

    return metadata

def scan_raw_folder():
    """
    Quét thư mục 1_raw và tự động xử lý các video mới
    """
    valid_extensions = [".mp4", ".mov", ".mkv", ".webm"]
    raw_files = [f for f in config.RAW_DIR.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]

    if not raw_files:
        logger.info(f"Chưa có video nào trong thư mục {config.RAW_DIR}. Đang chờ video mới...")
        return

    logger.info(f"Tìm thấy {len(raw_files)} video mới trong {config.RAW_DIR}!")
    for f in raw_files:
        # Kiểm tra xem video đã từng xử lý chưa (dựa trên tên file)
        target_meta = config.FULL_DIR / f"{f.stem}_meta.json"
        if target_meta.exists():
            logger.info(f"Bỏ qua file đã xử lý: {f.name}")
            continue

        process_single_video(f, video_id=f.stem)

    # Tự động đồng bộ sang Web Player (Module 3) ngay sau khi render xong
    trigger_web_publisher()

def trigger_web_publisher():
    """Tự động gọi Module 3 để cập nhật video mới vào web/config.js & videos_db.json"""
    try:
        import subprocess
        publisher_script = config.BASE_DIR / "automation" / "3_web_publisher" / "publisher.py"
        if publisher_script.exists():
            logger.info("🌐 Tự động kích hoạt Web Publisher (Module 3) để cập nhật config.js...")
            subprocess.run([sys.executable, str(publisher_script)], check=True)
    except Exception as e:
        logger.warning(f"Lỗi khi tự động chạy Web Publisher: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Video Factory Pipeline")
    parser.add_argument("--input", "-i", type=str, help="Đường dẫn file video đầu vào")
    parser.add_argument("--id", type=str, help="Mã ID tùy chỉnh cho video")
    args = parser.parse_args()

    if args.input:
        process_single_video(Path(args.input), video_id=args.id)
    else:
        scan_raw_folder()
