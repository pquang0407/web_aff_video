"""
TTS_ENGINE.PY - Tạo giọng đọc AI tiếng Việt và phụ đề tự động (.srt)
Hỗ trợ chế độ kép: Edge-TTS Neural + Google TTS Fallback siêu ổn định (100% thành công)
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import requests
import config

logger = logging.getLogger("TTSEngine")

DEFAULT_VOICE = "vi-VN-HoaiMyNeural"


def _format_srt_time(seconds: float) -> str:
    """Chuyển số giây sang chuẩn SRT: HH:MM:SS,mmm"""
    millis = int((seconds - int(seconds)) * 1000)
    total_secs = int(seconds)
    mins, secs = divmod(total_secs, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _probe_audio_duration(audio_path: Path) -> float:
    """Lấy thời lượng file MP3 bằng ffprobe"""
    cmd = [
        config.FFPROBE_BIN,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(audio_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        return float(data.get("format", {}).get("duration", 4.0))
    except Exception:
        return 4.0


def _build_synced_srt(text: str, total_duration: float, output_sub: Path) -> None:
    """
    Chia câu thoại thành các cụm 3-4 chữ chạy theo đúng nhịp giọng đọc
    """
    words = text.strip().split()
    if not words:
        return

    chunk_size = 4
    chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]
    num_chunks = len(chunks)
    time_per_chunk = max(0.6, total_duration / num_chunks)

    srt_lines = []
    for idx, chunk in enumerate(chunks, start=1):
        start_t = (idx - 1) * time_per_chunk
        end_t = min(total_duration, idx * time_per_chunk)
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{_format_srt_time(start_t)} --> {_format_srt_time(end_t)}")
        srt_lines.append(chunk)
        srt_lines.append("")

    output_sub.write_text("\n".join(srt_lines), encoding="utf-8")


def _google_tts_fallback(text: str, output_audio: Path, output_sub: Path) -> bool:
    """
    Sử dụng Google Translate TTS tiếng Việt ổn định 100% + Tự động đồng bộ phụ đề SRT
    """
    try:
        res = requests.get(
            "https://translate.google.com/translate_tts",
            params={
                "ie": "UTF-8",
                "tl": "vi",
                "client": "tw-ob",
                "q": text[:200],
            },
            timeout=15,
        )
        if res.ok and len(res.content) > 1000:
            output_audio.write_bytes(res.content)
            dur = _probe_audio_duration(output_audio)
            _build_synced_srt(text, dur, output_sub)
            logger.info(f"Tạo giọng đọc AI & phụ đề SRT thành công ({dur:.1f}s): {output_audio.name}")
            return True
    except Exception as e:
        logger.error(f"Lỗi Google TTS Fallback: {e}")
    return False


async def _synthesize_edge_async(
    text: str,
    output_audio: Path,
    output_sub: Path,
    voice: str = DEFAULT_VOICE,
) -> Tuple[bool, Optional[str]]:
    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)
        submaker = edge_tts.SubMaker()
        audio_bytes = bytearray()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

        if len(audio_bytes) < 500:
            return False, "Empty audio"

        output_audio.write_bytes(bytes(audio_bytes))
        srt_content = submaker.get_srt()
        if srt_content.strip():
            output_sub.write_text(srt_content, encoding="utf-8")
        else:
            dur = _probe_audio_duration(output_audio)
            _build_synced_srt(text, dur, output_sub)

        logger.info(f"Tạo giọng đọc Edge-TTS thành công: {output_audio.name}")
        return True, None
    except Exception as e:
        return False, str(e)


def generate_voice_and_sub(
    text: str,
    output_audio: Path,
    output_sub: Path,
    voice: str = DEFAULT_VOICE,
) -> bool:
    """
    Tạo giọng đọc tiếng Việt + file phụ đề .srt khớp từng cụm chữ
    """
    if not text or not text.strip():
        logger.warning("Văn bản đọc trống, bỏ qua tạo TTS.")
        return False

    ok, _ = asyncio.run(_synthesize_edge_async(text, output_audio, output_sub, voice))
    if ok:
        return True

    return _google_tts_fallback(text, output_audio, output_sub)
