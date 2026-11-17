"""
GEMINI_ANALYZER.PY - Module sử dụng Gemini API (gemini-3.5-flash-lite) để phân tích video:
1. Đọc hiểu nội dung video viral
2. Viết tiêu đề giật gân (Clickbait Hook) cho Web Player
3. Soạn caption mạng xã hội cho Facebook Reels & Threads (có CTA xem cmt)
4. Tự động xác định timestamp đoạn cao trào (Highlight 5-8s) để cắt Teaser
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field

import config

logger = logging.getLogger("GeminiAnalyzer")


class VideoAnalysisResult(BaseModel):
    title: str = Field(description="Tiêu đề tiếng Việt ngắn gọn dưới 75 ký tự, giật gân, khơi gợi tò mò")
    social_caption: str = Field(description="Nội dung bài đăng Facebook/Threads có câu hook cuốn hút, 2-3 câu mô tả gay cấn, 3-5 hashtag, và kêu gọi xem trọn vẹn tại link dưới bình luận")
    voiceover_text: str = Field(description="Câu lồng tiếng AI ngắn gọn 10-18 từ đọc trên video teaser kích thích tò mò và nhắc bấm vào bình luận")
    teaser_start_sec: float = Field(description="Giây bắt đầu của khoảnh khắc gay cấn nhất trong video (nếu video > 30s)")
    teaser_duration_sec: float = Field(description="Thời lượng đoạn highlight khoảng 10 giây (nếu video > 30s)")
    top_banner_text: str = Field(description="Chữ in hoa ngắn gọn dưới 30 ký tự chèn ở viền trên video")
    bottom_banner_text: str = Field(description="Chữ kêu gọi xem tiếp ở bình luận, ví dụ: XEM FULL BẢN RÕ NÉT DƯỚI BÌNH LUẬN ⬇️")


SYSTEM_INSTRUCTION = """
Bạn là chuyên gia biên tập video viral và tối ưu hóa chuyển đổi Traffic Affiliate hàng đầu.
Nhiệm vụ của bạn là xem kỹ video đầu vào và xuất ra dữ liệu JSON chuẩn xác theo đúng nội dung thực tế trong video:
1. Web Player: Tiêu đề giật gân, đúng nội dung trong clip, khơi gợi tò mò cực độ.
2. Social Teaser: Bài đăng Reels / Threads hấp dẫn kèm thời điểm đoạn cao trào (Highlight 5-8 giây).
3. Banner chữ chèn trên và dưới video Teaser để kêu gọi người xem nhấn vào link dưới bình luận.
"""

ANALYSIS_PROMPT = """
Hãy xem kỹ video này, mô tả đúng sự vật/tình huống diễn ra trong video và trả về JSON theo đúng cấu trúc yêu cầu.
Không dùng dấu ngoặc kép lồng bên trong chuỗi văn bản.
"""


def analyze_video_with_gemini(video_path: Path, video_duration: float = 30.0) -> Dict[str, Any]:
    """
    Gửi video lên Gemini API (gemini-3.5-flash-lite) với Structured Output Schema
    """
    api_key = config.GEMINI_API_KEY
    if not api_key:
        logger.warning("Chưa có GEMINI_API_KEY. Sử dụng bộ phân tích dự phòng mặc định.")
        return _fallback_analysis(video_path, video_duration)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        video_file_path = str(video_path)

        logger.info(f"Đang tải video lên Gemini API ({config.GEMINI_MODEL}): {video_path.name}...")
        uploaded_file = client.files.upload(file=video_file_path)

        max_wait = 60
        waited = 0
        while uploaded_file.state.name == "PROCESSING" and waited < max_wait:
            time.sleep(2)
            waited += 2
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name != "ACTIVE":
            logger.warning(f"File state trên Gemini không phải ACTIVE ({uploaded_file.state.name}). Dùng fallback.")
            return _fallback_analysis(video_path, video_duration)

        logger.info(f"Gemini ({config.GEMINI_MODEL}) đang phân tích nội dung video...")
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=[uploaded_file, ANALYSIS_PROMPT],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=VideoAnalysisResult,
                    ),
                )
                break
            except Exception as retry_err:
                if "503" in str(retry_err) or "UNAVAILABLE" in str(retry_err):
                    logger.warning(f"Gemini 503 quá tải tạm thời, thử lại lần {attempt + 1}/3 sau 3 giây...")
                    time.sleep(3)
                else:
                    raise retry_err

        if response is None:
            return _fallback_analysis(video_path, video_duration)

        raw_text = response.text.strip()
        data = json.loads(raw_text)

        # Quy tắc thời lượng:
        # - Nếu video <= 30s (SHORT_VIDEO_THRESHOLD): Giữ nguyên toàn bộ thời lượng video
        # - Nếu video > 30s: Cắt khoảng 10s (TEASER_CUT_DURATION) tại đoạn highlight do Gemini chọn
        if video_duration <= config.SHORT_VIDEO_THRESHOLD:
            teaser_start = 0.0
            teaser_dur = video_duration
        else:
            teaser_start = float(data.get("teaser_start_sec", 0.0))
            teaser_dur = float(data.get("teaser_duration_sec", config.TEASER_CUT_DURATION))
            if teaser_dur > config.TEASER_MAX_DURATION or teaser_dur < 8.0:
                teaser_dur = config.TEASER_CUT_DURATION
            if teaser_start + teaser_dur > video_duration:
                teaser_start = max(0.0, video_duration - teaser_dur)

        result = {
            "title": data.get("title", f"Clip nóng ghi lại diễn biến gây chú ý {video_path.stem}"),
            "social_caption": data.get("social_caption", "Xem clip full tại link bên dưới cmt!"),
            "voiceover_text": data.get("voiceover_text", "Khoảnh khắc bất ngờ đang gây sốt mạng xã hội, xem trọn vẹn tại link dưới bình luận."),
            "teaser_start_sec": teaser_start,
            "teaser_duration_sec": teaser_dur,
            "top_banner_text": data.get("top_banner_text", "DIỄN BIẾN GÂY XÔN XAO"),
            "bottom_banner_text": data.get("bottom_banner_text", "XEM TIẾP FULL CLIP DƯỚI BÌNH LUẬN ⬇️"),
        }
        logger.info(f"Gemini phân tích thành công! Tiêu đề: {result['title']}")
        return result

    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API ({e}). Kích hoạt dữ liệu mặc định.")
        return _fallback_analysis(video_path, video_duration)


def _fallback_analysis(video_path: Path, video_duration: float) -> Dict[str, Any]:
    stem_name = video_path.stem.replace("_", " ").title()
    if video_duration <= config.SHORT_VIDEO_THRESHOLD:
        start_time = 0.0
        teaser_dur = video_duration
    else:
        start_time = max(0.0, (video_duration / 2) - 5.0)
        teaser_dur = config.TEASER_CUT_DURATION

    return {
        "title": f"Cận cảnh diễn biến vụ việc đang gây xôn xao mạng xã hội ({stem_name})",
        "social_caption": (
            f"🚨 KHOẢNH KHẮC ĐANG GÂY BÃO MẠNG XÃ HỘI!\n\n"
            f"Diễn biến bất ngờ được camera an ninh ghi lại toàn bộ chi tiết. "
            f"Đoạn kết khiến nhiều người xem không khỏi bất ngờ.\n\n"
            f"👉 Xem trọn vẹn bản full không che tại link bên dưới bình luận!\n\n"
            f"#Drama #HotClip #CameraAnNinh #BienCang #Trending"
        ),
        "voiceover_text": "Diễn biến bất ngờ đang gây xôn xao mạng xã hội, xem trọn vẹn tại link dưới bình luận.",
        "teaser_start_sec": start_time,
        "teaser_duration_sec": teaser_dur,
        "top_banner_text": "KHOẢNH KHẮC GÂY SỐT MẠNG XÃ HỘI",
        "bottom_banner_text": "XEM TIẾP FULL CLIP DƯỚI BÌNH LUẬN ⬇️",
    }
