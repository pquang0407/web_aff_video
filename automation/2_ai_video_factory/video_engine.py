"""
VIDEO_ENGINE.PY - Động cơ biên tập video chuyên nghiệp bằng FFmpeg
Tự động lách bản quyền:
1. Lật ảnh gương (hflip)
2. Đóng khung 9:16 dọc có nền mờ (Fast Blur)
3. Chèn banner chữ trên (Hook) & dưới (Kêu gọi xem full)
4. Lồng tiếng AI (Voiceover) & chèn phụ đề chạy theo lời nói
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import config

logger = logging.getLogger("VideoEngine")

def _detect_font_file() -> str:
    """Tự động tìm font chữ trên Windows hoặc Linux"""
    win_font = Path(r"C:\Windows\Fonts\arial.ttf")
    if win_font.exists():
        return "C\\:/Windows/Fonts/arial.ttf"
    
    win_segoe = Path(r"C:\Windows\Fonts\segoeui.ttf")
    if win_segoe.exists():
        return "C\\:/Windows/Fonts/segoeui.ttf"

    linux_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    for lf in linux_fonts:
        if Path(lf).exists():
            return lf

    return ""

def probe_video(video_path: Path) -> Dict[str, Any]:
    """Trích xuất thông số kỹ thuật của video bằng ffprobe"""
    cmd = [
        config.FFPROBE_BIN,
        "-v", "error",
        "-show_entries", "format=duration:stream=width,height",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        
        duration = float(data.get("format", {}).get("duration", 0))
        streams = data.get("streams", [])
        width = 1080
        height = 1920
        if streams:
            width = int(streams[0].get("width", 1080))
            height = int(streams[0].get("height", 1920))

        return {
            "duration": duration,
            "width": width,
            "height": height,
            "is_vertical": height > width
        }
    except Exception as e:
        logger.error(f"Lỗi khi probe video: {e}")
        return {"duration": 30.0, "width": 1080, "height": 1920, "is_vertical": True}

def render_teaser(
    input_path: Path,
    output_path: Path,
    start_sec: float,
    duration_sec: float,
    top_text: str = "DIỄN BIẾN BẤT NGỜ",
    bottom_text: str = "XEM FULL CLIP DƯỚI BÌNH LUẬN ⬇️",
    hflip: bool = True,
    voiceover_path: Optional[Path] = None,
    subtitle_path: Optional[Path] = None
) -> bool:
    """
    Cắt và biên tập đoạn Teaser ngắn 5-8s:
    - hflip=True: Lật gương video để lách Content ID
    - Fast Blur: Nền mờ chuẩn 9:16 (1080x1920)
    - Banner trên (Hook) & Banner dưới (Kêu gọi xem full)
    - Hỗ trợ lồng tiếng AI và chèn phụ đề
    """
    logger.info(f"Đang render Teaser ({start_sec}s -> {start_sec + duration_sec}s) [hflip={hflip}]...")
    
    clean_top = top_text.replace(":", "\\:").replace("'", "").replace('"', '').replace("%", "")
    clean_bottom = bottom_text.replace(":", "\\:").replace("'", "").replace('"', '').replace("%", "")

    font_path = _detect_font_file()
    font_filter = f"fontfile='{font_path}':" if font_path else ""

    # Bộ lọc lật ảnh (hflip)
    flip_filter = "hflip," if hflip else ""

    # FilterGraph Teaser
    video_filters = (
        f"[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10:5,scale=1080:1920[bg];"
        f"[0:v]{flip_filter}scale=1080:1080:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        # Banner đen phía trên
        f"drawbox=y=60:color=black@0.75:width=iw:height=180:t=fill,"
        f"drawtext={font_filter}text='{clean_top}':fontcolor=white:fontsize=46:x=(w-text_w)/2:y=125,"
        # Banner đỏ kêu gọi hành động phía dưới
        f"drawbox=y=ih-320:color=red@0.9:width=iw:height=220:t=fill,"
        f"drawtext={font_filter}text='{clean_bottom}':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-220"
    )

    # Chèn phụ đề nếu có file .srt
    if subtitle_path and subtitle_path.exists():
        escaped_sub = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
        video_filters += f",subtitles='{escaped_sub}':force_style='FontSize=22,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,BorderStyle=3'"

    video_filters += "[v]"

    # Cấu hình lệnh FFmpeg
    cmd = [
        config.FFMPEG_BIN,
        "-y",
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-i", str(input_path),
    ]

    # Nếu có lồng tiếng AI (Voiceover)
    if voiceover_path and voiceover_path.exists():
        cmd.extend(["-i", str(voiceover_path)])
        # Trộn âm thanh: Nhỏ tiếng gốc (20%), to tiếng AI (100%)
        cmd.extend([
            "-filter_complex", f"{video_filters};[0:a]volume=0.2[aorig];[1:a]volume=1.0[avoice];[aorig][avoice]amix=inputs=2:duration=first[a]",
            "-map", "[v]",
            "-map", "[a]"
        ])
    else:
        cmd.extend([
            "-filter_complex", video_filters,
            "-map", "[v]",
            "-map", "0:a?"
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path)
    ] )

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Render Teaser thành công: {output_path.name}")
        return True
    except subprocess.CalledProcessError as err:
        logger.error(f"Lỗi khi render Teaser: {err.stderr[:300]}")
        return False

def render_full_video(input_path: Path, output_path: Path, hflip: bool = True) -> bool:
    """
    Biên tập bản Full tối ưu cho Web Player & Cloudflare R2:
    - hflip: Lật gương để lách bản quyền video gốc
    - faststart: Xem trực tiếp mượt mà
    """
    logger.info(f"Đang tối ưu bản Full cho Web Player: {output_path.name} [hflip={hflip}]...")

    flip_opt = ["-vf", "hflip"] if hflip else []

    cmd = [
        config.FFMPEG_BIN,
        "-y",
        "-i", str(input_path),
        *flip_opt,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path)
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Xuất bản Full thành công: {output_path.name}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xuất bản Full: {e}")
        return False

def extract_poster(input_path: Path, output_poster_path: Path, timestamp: float = 1.0) -> bool:
    """Trích xuất 1 ảnh đẹp nhất từ video làm thumbnail cho Web Player"""
    cmd = [
        config.FFMPEG_BIN,
        "-y",
        "-ss", str(timestamp),
        "-i", str(input_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_poster_path)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Trích xuất poster thành công: {output_poster_path.name}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất poster: {e}")
        return False
