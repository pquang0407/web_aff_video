"""
R2_UPLOADER.PY - Bộ tải file lên Cloudflare R2 CDN hoặc xuất đường dẫn Local
Hỗ trợ 2 chế độ:
- 'local': Dùng đường dẫn tương đối ../storage/2_web_full/ (không tốn băng thông, test tức thì)
- 'cloud_r2': Upload lên Cloudflare R2 (S3 API) và trả về link CDN công khai
"""

import logging
from pathlib import Path
from typing import Tuple

import config

logger = logging.getLogger("R2Uploader")


def upload_media_pair(
    video_id: str,
    video_path: Path,
    poster_path: Path,
    mode: str = "local",
    simulate_cloud: bool = False,
) -> Tuple[str, str]:
    """
    Trả về bộ (video_url, poster_url) tương ứng với chế độ 'local' hoặc 'cloud_r2'
    """
    if mode == "local":
        video_url = f"../storage/2_web_full/{video_path.name}"
        poster_url = f"../storage/2_web_full/{poster_path.name}"
        logger.info(f"[LOCAL MODE] Gán đường dẫn trực tiếp: {video_url}")
        return video_url, poster_url

    # Chế độ CLOUD R2
    video_key = f"videos/{video_path.name}"
    poster_key = f"posters/{poster_path.name}"
    public_video_url = f"{config.R2_PUBLIC_DOMAIN}/{video_key}"
    public_poster_url = f"{config.R2_PUBLIC_DOMAIN}/{poster_key}"

    if simulate_cloud:
        logger.info(f"[CLOUD R2 SIMULATION] Giả lập upload thành công lên CDN: {public_video_url}")
        return public_video_url, public_poster_url

    if not config.is_cloud_r2_configured():
        logger.warning("Chưa cấu hình đủ R2_ACCOUNT_ID / ACCESS_KEY trong .env! Tự động chuyển về LOCAL MODE.")
        return upload_media_pair(video_id, video_path, poster_path, mode="local")

    try:
        import boto3
        from botocore.config import Config as BotoConfig

        endpoint_url = f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
            config=BotoConfig(signature_version="s3v4"),
            region_name="auto",
        )

        logger.info(f"[CLOUD R2] Đang upload video {video_path.name} lên bucket '{config.R2_BUCKET_NAME}'...")
        s3.upload_file(
            str(video_path),
            config.R2_BUCKET_NAME,
            video_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )

        if poster_path.exists():
            logger.info(f"[CLOUD R2] Đang upload poster {poster_path.name}...")
            s3.upload_file(
                str(poster_path),
                config.R2_BUCKET_NAME,
                poster_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

        logger.info(f"[CLOUD R2] Upload hoàn tất! Link CDN: {public_video_url}")
        return public_video_url, public_poster_url

    except Exception as e:
        logger.error(f"Lỗi khi upload lên Cloudflare R2 ({e}). Fallback về đường dẫn Local.")
        return upload_media_pair(video_id, video_path, poster_path, mode="local")
