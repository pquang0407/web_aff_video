"""
CREATE_SAMPLE_AND_TEST.PY - Tạo video mẫu 10 giây và test toàn diện Module 2
"""

import subprocess
import sys
from pathlib import Path

# Thêm thư mục hiện tại vào sys.path
sys.path.append(str(Path(__file__).resolve().parent))

import config
import factory

def generate_test_video(output_path: Path) -> bool:
    """Tạo 1 video 10 giây có âm thanh để test pipeline"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        config.FFMPEG_BIN,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=10:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=800:duration=10",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except Exception as e:
        print(f"Lỗi tạo video mẫu: {e}")
        return False

if __name__ == "__main__":
    sample_raw = config.RAW_DIR / "sample_test_clip.mp4"
    print(f"1. Đang tạo video mẫu tại: {sample_raw}...")
    if generate_test_video(sample_raw):
        print("Tạo video mẫu thành công!")
    else:
        print("Không tạo được video mẫu!")
        sys.exit(1)

    print("\n2. Đang chạy kiểm thử Factory Pipeline...")
    res = factory.process_single_video(sample_raw, video_id="sample_test_01")
    if res:
        print("\n=== KẾT QUẢ TEST THÀNH CÔNG RỰC RỠ ===")
        print(f"ID Video: {res['id']}")
        print(f"Tiêu đề: {res['title']}")
        print(f"Bản Full Web: {res['full_video_path']}")
        print(f"Bản Teaser: {res['teaser_video_path']}")
        print(f"Poster: {res['poster_path']}")
    else:
        print("\nTest thất bại!")
