import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("ChannelScraper")

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SOURCE_CHANNELS,
    RAW_STORAGE_DIR,
    mark_video_downloaded,
    is_video_downloaded,
)

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import DocumentAttributeVideo
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False
    logger.warning("Thư viện telethon chưa được cài đặt!")


async def start_channel_scraper():
    """
    Tự động lắng nghe các Channel nguồn công khai bằng Telethon.
    Khi channel đăng video mới, tự động tải về storage/1_raw/
    """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("\n=======================================================")
        print("ℹ️ TELEGRAM_API_ID hoặc TELEGRAM_API_HASH chưa cấu hình trong .env.")
        print("(Tính năng cào tự động từ Channel người khác cần API ID từ my.telegram.org)")
        print("Bạn vẫn có thể dùng Bot chính (bot_service.py) bằng cách gửi/forward video vào Bot.")
        print("=======================================================\n")
        return

    session_name = str(RAW_STORAGE_DIR.parent / "telethon_session")
    client = TelegramClient(session_name, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)

    @client.on(events.NewMessage(chats=TELEGRAM_SOURCE_CHANNELS))
    async def handler(event):
        message = event.message
        if message.video:
            file_unique_id = f"tele_{message.chat_id}_{message.id}"
            if is_video_downloaded(file_unique_id):
                logger.info(f"Bỏ qua video trùng lặp: {file_unique_id}")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"channel_{timestamp}_{message.id}.mp4"
            save_path = RAW_STORAGE_DIR / filename

            logger.info(f"Đang tải video mới từ Channel [{message.chat_id}]...")
            await client.download_media(message, file=str(save_path))

            mark_video_downloaded(
                file_unique_id=file_unique_id,
                filename=filename,
                info={"chat_id": message.chat_id, "message_id": message.id}
            )
            logger.info(f"✅ Đã tải thành công video về: {save_path}")

    print(f"📡 Đang kết nối Telethon cào Channel: {TELEGRAM_SOURCE_CHANNELS}")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    if HAS_TELETHON:
        asyncio.run(start_channel_scraper())
