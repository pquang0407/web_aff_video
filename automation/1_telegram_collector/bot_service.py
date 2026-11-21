import os
import sys
import re
import json
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("TelegramAutoAffBot")

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_ADMIN_ID,
    TELEGRAM_CHANNEL_ID,
    RAW_STORAGE_DIR,
    WEB_FULL_DIR,
    SOCIAL_DIR,
    WEB_BASE_URL,
    load_settings,
    save_settings,
    get_video_stats,
    mark_video_downloaded,
    is_video_downloaded,
)
from bot_ui import (
    ENABLE_LEGACY_RAW_COLLECTOR,
    build_main_dashboard_keyboard,
    build_dashboard_text,
    build_social_queue_keyboard,
    build_raw_queue_keyboard,
    build_video_action_keyboard,
)
from url_downloader import download_from_url

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    HAS_TELEGRAM_LIB = True
except ImportError:
    HAS_TELEGRAM_LIB = False
    logger.warning("Thư viện python-telegram-bot chưa được cài đặt!")


async def safe_edit_message_text(query, text: str, reply_markup=None, parse_mode=ParseMode.HTML):
    """Hàm sửa tin nhắn an toàn, bỏ qua lỗi khi nội dung không đổi"""
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "Message is not modified" in str(e):
            pass
        else:
            logger.warning(f"Lỗi khi edit message: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start hoặc /menu - Mở Bảng điều khiển Auto Video Affiliate"""
    text = build_dashboard_text()
    keyboard = build_main_dashboard_keyboard()
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý toàn bộ các nút bấm tương tác trên Telegram"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        # Bỏ qua lỗi "Query is too old" để nút bấm vẫn luôn chạy bình thường
        pass
    data = query.data

    if data in ["cmd_back_home", "cmd_refresh_dashboard"]:
        text = build_dashboard_text()
        keyboard = build_main_dashboard_keyboard()
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)

    elif data == "cmd_toggle_auto_mode":
        settings = load_settings()
        curr = settings.get("auto_pipeline_on_receive", True)
        settings["auto_pipeline_on_receive"] = not curr
        save_settings(settings)
        text = build_dashboard_text()
        keyboard = build_main_dashboard_keyboard()
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)

    elif data == "cmd_view_social":
        stats = get_video_stats()
        text = (
            f"📱 <b>HÀNG ĐỢI SOCIAL TEASERS ({stats['social_count']} video sẵn sàng)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Danh sách video 9:16 dọc đã cắt highlight, chèn lồng tiếng TTS và phụ đề.\n"
            f"Bấm vào từng video để xem chi tiết hoặc đăng ngay:"
        )
        keyboard = build_social_queue_keyboard()
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)

    elif data == "cmd_view_raw":
        stats = get_video_stats()
        text = (
            f"📥 <b>KHO VIDEO THÔ CHỜ XỬ LÝ ({stats['raw_count']} video)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Toàn bộ video được cào hoặc forward vào Telegram đang lưu tại <code>storage/1_raw/</code>.\n"
            f"Bấm nút bên dưới để bắt đầu phân tích AI và render:"
        )
        keyboard = build_raw_queue_keyboard()
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)

    elif data == "cmd_view_web":
        stats = get_video_stats()
        text = (
            f"🌐 <b>KHO VIDEO XUẤT BẢN WEB ({stats['web_count']} video Full HD)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Các video đã sẵn sàng phát trên Web Landing Page kèm Deep Link Affiliate.\n"
            f"👉 Link trang chủ: <a href='{WEB_BASE_URL}'>{WEB_BASE_URL}</a>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Mở Web Trực Tiếp", url=WEB_BASE_URL)],
            [InlineKeyboardButton("🔙 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")]
        ])
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)

    elif data.startswith("vid_detail_"):
        vid_id = data.replace("vid_detail_", "")
        caption_file = SOCIAL_DIR / f"{vid_id}_caption.txt"
        meta_file = WEB_FULL_DIR / f"{vid_id}_meta.json"
        caption_text = ""
        if caption_file.exists():
            try:
                with open(caption_file, "r", encoding="utf-8") as f:
                    caption_text = f.read().strip()
            except Exception:
                pass
        if not caption_text and meta_file.exists():
            try:
                mdata = json.loads(meta_file.read_text(encoding="utf-8"))
                caption_text = mdata.get("social_caption") or mdata.get("title") or ""
            except Exception:
                pass

        if not caption_text:
            caption_text = f"🔥 Xem ngay siêu phẩm {vid_id} cực kỳ hấp dẫn! Bấm link bên dưới để xem bản Full HD không che."

        web_url = f"{WEB_BASE_URL}/?v={vid_id}"
        text = (
            f"🎬 <b>CHI TIẾT VIDEO 3D THỎ & GẤU:</b> <code>{vid_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Caption AI (Facebook / Threads):</b>\n<i>{caption_text}</i>\n\n"
            f"🔗 <b>Link đích Web Player:</b>\n<code>{web_url}</code>\n\n"
            f"🎯 <b>Điều hướng:</b> Khi đăng, link trên sẽ tự động được thả vào bình luận đầu tiên!"
        )
        keyboard = build_video_action_keyboard(vid_id)
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)

    elif data.startswith("act_post_social_"):
        vid_id = data.replace("act_post_social_", "")
        await safe_edit_message_text(query, f"⏳ <b>Đang đăng video <code>{vid_id}</code> lên Facebook Fanpage & Threads + Tự động thả Comment Link...</b>")
        try:
            poster_dir = ROOT_DIR / "automation" / "4_social_poster"
            if str(poster_dir) not in sys.path:
                sys.path.insert(0, str(poster_dir))
            import poster
            res = poster.post_video_to_social(video_id=vid_id, simulate=False)
            await safe_edit_message_text(
                query,
                text=(
                    f"✅ <b>ĐÃ ĐĂNG VIDEO 3D LÊN SOCIAL & THẢ COMMENT LINK!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎬 <b>Mã Video:</b> <code>{vid_id}</code>\n"
                    f"🔗 <b>Link Auto-Comment:</b> <code>{WEB_BASE_URL}/?v={vid_id}</code>\n"
                    f"📊 <b>Kết quả:</b> <code>{json.dumps(res, ensure_ascii=False)[:250]}</code>"
                ),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại hàng đợi", callback_data="cmd_view_social", style="primary")]])
            )
        except Exception as e:
            await safe_edit_message_text(
                query,
                text=f"❌ <b>Lỗi khi đăng Social:</b> <code>{str(e)}</code>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data=f"vid_detail_{vid_id}")]])
            )

    elif data.startswith("act_post_channel_"):
        vid_id = data.replace("act_post_channel_", "")
        candidates = [
            SOCIAL_DIR / f"{vid_id}_teaser.mp4",
            SOCIAL_DIR / f"{vid_id}.mp4",
            WEB_FULL_DIR / f"{vid_id}.mp4",
            ROOT_DIR / "web" / "videos" / f"{vid_id}.mp4",
        ]
        teaser_path = candidates[0]
        for cand in candidates:
            if cand.exists():
                teaser_path = cand
                break

        if not TELEGRAM_CHANNEL_ID:
            await safe_edit_message_text(
                query,
                text=(
                    f"⚠️ <b>Chưa cấu hình TELEGRAM_CHANNEL_ID!</b>\n"
                    f"Hãy thêm ID kênh Telegram của bạn (ví dụ: <code>@kenh_deal_hot</code>) vào file <code>.env</code>."
                ),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data=f"vid_detail_{vid_id}")]])
            )
            return

        if teaser_path.exists():
            await safe_edit_message_text(query, f"⏳ Đang gửi video <code>{vid_id}</code> lên Channel {TELEGRAM_CHANNEL_ID}...")
            try:
                channel_btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎬 Xem Bản Full HD & Săn Deal", url=f"{WEB_BASE_URL}/?v={vid_id}")
                ]])
                caption = f"🔥 <b>CỰC HOT: {vid_id.upper()}</b>\n\n👉 Bấm vào nút bên dưới để xem trọn bộ bản Full HD và nhận ưu đãi độc quyền!"
                
                with open(teaser_path, "rb") as vf:
                    await context.bot.send_video(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        video=vf,
                        caption=caption,
                        reply_markup=channel_btn,
                        parse_mode=ParseMode.HTML
                    )
                await safe_edit_message_text(
                    query,
                    text=f"✅ <b>Đã đăng thành công video {vid_id} lên Channel {TELEGRAM_CHANNEL_ID}!</b>",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại hàng đợi", callback_data="cmd_view_social", style="primary")]])
                )
            except Exception as e:
                await safe_edit_message_text(
                    query,
                    text=f"❌ Lỗi đăng kênh: <code>{str(e)}</code>",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data=f"vid_detail_{vid_id}")]])
                )

    elif data == "cmd_sync_rabbit_bear":
        factory_dir = ROOT_DIR / "automation" / "2_ai_video_factory"
        if str(factory_dir) not in sys.path:
            sys.path.insert(0, str(factory_dir))
        import rabbit_bear_runner
        synced = rabbit_bear_runner.sync_existing_3d_masterpieces(clean_legacy=True)
        await safe_edit_message_text(
            query,
            text=(
                f"🐰🐻 <b>ĐÃ ĐỒNG BỘ {len(synced)} VIDEO 3D THỎ & GẤU LÊN HỆ THỐNG!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "• Đã ẩn toàn bộ các clip cũ sang kho lưu trữ.\n"
                "• Đã cập nhật video 3D Thỏ & Gấu (9:16 Full HD + Giọng đọc NamMinh đồng nhất 9.35s/10s) lên Web Player & Hàng đợi Social!\n\n"
                f"👉 Xem ngay tại: <a href='{WEB_BASE_URL}'>{WEB_BASE_URL}</a>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Xem Hàng Đợi Social", callback_data="cmd_view_social", style="success")],
                [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")]
            ])
        )

    elif data == "cmd_run_pipeline":
        await safe_edit_message_text(
            query,
            text=(
                "⚡ <b>ĐANG KÍCH HOẠT AUTO PIPELINE TOÀN HỆ THỐNG...</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "1. 📥 Quét kho video thô (storage/1_raw)\n"
                "2. 🤖 Gemini AI phân tích, cắt highlight & tạo phụ đề\n"
                "3. 🎞️ FFmpeg dựng Fast Blur 9:16 + TTS giọng đọc\n"
                "4. 🌐 Cập nhật config.js Web Player\n"
                "5. 📱 Đẩy vào hàng đợi Social Poster\n\n"
                "<i>Tiến trình đang chạy ngầm, bạn có thể bấm 'Làm mới' sau 1-2 phút để xem kết quả!</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Làm mới kiểm tra", callback_data="cmd_refresh_dashboard", style="primary")]])
        )
        factory_script = ROOT_DIR / "automation" / "2_ai_video_factory" / "factory.py"
        if factory_script.exists():
            subprocess.Popen([sys.executable, str(factory_script)])

    elif data == "cmd_view_fifo_queue":
        factory_dir = ROOT_DIR / "automation" / "2_ai_video_factory"
        if str(factory_dir) not in sys.path:
            sys.path.insert(0, str(factory_dir))
        import rabbit_bear_runner
        st = await asyncio.to_thread(rabbit_bear_runner.get_fifo_queue_status)
        cur = st.get("current")
        q = st.get("queue", [])
        now_str = datetime.now().strftime("%H:%M:%S")
        lines = [
            f"📋 <b>HÀNG ĐỢI DỰNG 3D THỎ & GẤU (FIFO)</b> • <i>{now_str}</i>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        if cur:
            lines.append(f"🎬 <b>Đang xử lý:</b>\n<code>{cur.get('article_url', '')}</code>")
        else:
            lines.append("🟢 <b>Trạng thái:</b> Xưởng 3D đang rảnh (gửi link là dựng ngay!)")
        if q:
            lines.append(f"\n⏳ <b>Đang xếp hàng chờ ({len(q)} link):</b>")
            for idx, item in enumerate(q[:12], start=1):
                lines.append(f"  {idx}. <code>{item.get('article_url', '')}</code>")
            if len(q) > 12:
                lines.append(f"  <i>... và {len(q) - 12} link khác</i>")
        else:
            lines.append("\n📭 <i>Không có link nào đang chờ.</i>")
        await safe_edit_message_text(
            query,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Làm mới hàng đợi", callback_data="cmd_view_fifo_queue", style="primary")],
                [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")],
            ]),
        )

    elif data == "cmd_system_stats":
        stats = get_video_stats()
        text = (
            "📊 <b>THỐNG KÊ CHI TIẾT HỆ THỐNG AUTO VIDEO AFFILIATE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Module 1 (Telegram & Link Collector):</b> ✅ Hỗ trợ tải FB Page, Group, Video\n"
            f"• <b>Module 2 (AI Video Factory):</b> ✅ Gemini 3.5 Flash Lite + FFmpeg\n"
            f"• <b>Module 3 (Web Publisher):</b> ✅ Đồng bộ config.js & videos_db.json\n"
            f"• <b>Module 4 (Social Poster):</b> ✅ Facebook Fanpage & Threads Queue\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Video Raw: <code>{stats['raw_count']}</code> | Web Full: <code>{stats['web_count']}</code> | Social: <code>{stats['social_count']}</code>\n"
            f"• Web Base: <a href='{WEB_BASE_URL}'>{WEB_BASE_URL}</a>"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="cmd_back_home", style="primary")]])
        await safe_edit_message_text(query, text=text, reply_markup=keyboard)


async def handle_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tự động xử lý khi người dùng gửi 1 hoặc nhiều link Facebook Reel, Watch, TikTok, Shorts...
    Hỗ trợ dán hàng loạt link trong cùng 1 tin nhắn!
    """
    text = update.message.text or ""
    # Trích xuất tất cả các URL có trong tin nhắn
    urls = re.findall(r'(https?://[^\s<>"]+)', text)
    if not urls:
        return

    # Lọc các URL hợp lệ
    valid_urls = [u.strip() for u in urls if len(u.strip()) > 10]
    if not valid_urls:
        return

    total_links = len(valid_urls)
    logger.info(f"Nhận được {total_links} link từ người dùng")

    # CHẾ ĐỘ MỚI: PIPELINE VIDEO TIN TỨC 3D VŨ TRỤ THỎ & GẤU (HỖ TRỢ FIFO QUEUE & GỬI HÀNG LOẠT LINK)
    if not ENABLE_LEGACY_RAW_COLLECTOR:
        chat_id = str(update.effective_chat.id) if update.effective_chat else ""
        user_obj = update.effective_user
        sender_name = (user_obj.full_name if user_obj else "") or chat_id
        status_msg = await update.message.reply_text(
            text=(
                f"⏳ <b>ĐANG TIẾP NHẬN {len(valid_urls)} LINK BÀI BÁO VÀO HÀNG ĐỢI FIFO 3D...</b>"
            ),
            parse_mode=ParseMode.HTML
        )
        try:
            factory_dir = ROOT_DIR / "automation" / "2_ai_video_factory"
            if str(factory_dir) not in sys.path:
                sys.path.insert(0, str(factory_dir))
            import rabbit_bear_runner

            res = await asyncio.to_thread(
                rabbit_bear_runner.enqueue_fifo_3d_jobs,
                valid_urls,
                chat_id=chat_id,
                sender_name=sender_name,
            )
            items = res.get("items", [])
            cur_job = res.get("current_job")

            if len(items) == 1:
                it = items[0]
                if it.get("starts_now"):
                    reply_text = (
                        "🐰🐻 <b>ĐANG XỬ LÝ NGAY TRÊN XƯỞNG 3D THỎ & GẤU!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📰 <b>Bài báo:</b> <code>{it['article_url']}</code>\n"
                        f"🆔 <b>Mã Job:</b> <code>{it['job_id']}</code>\n\n"
                        "🎬 <b>Quy trình 6 bước đang chạy:</b>\n"
                        "1. Cào bài báo → 2. Gemini 3.5/3.1 Flash Lite (retry 3 lần)\n"
                        "3. Thu âm NamMinhNeural (9.43s/10s) → 4. Render đồ họa 9:16\n"
                        "5. Render 4 cảnh 3D Muse.ai + Outro → 6. Đẩy thẳng lên tho-news.com!\n\n"
                        "💡 <i>Bạn hoặc khách có thể gửi thêm 1 hoặc nhiều link (mỗi link 1 dòng), Bot sẽ tự xếp vào Hàng đợi FIFO chạy lần lượt không sợ tràn RAM!</i>"
                    )
                else:
                    cur_line = f"\n🎬 <b>Clip đang dựng hiện tại:</b>\n<code>{cur_job.get('article_url', '')}</code>\n" if cur_job else ""
                    reply_text = (
                        f"⏳ <b>ĐÃ XẾP VÀO HÀNG ĐỢI FIFO (VỊ TRÍ #{it.get('position', 1)})!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📰 <b>Bài báo của bạn:</b> <code>{it['article_url']}</code>\n"
                        f"🆔 <b>Mã Job:</b> <code>{it['job_id']}</code>\n"
                        f"{cur_line}\n"
                        "✅ <i>Hệ thống đang chạy tuần tự từng clip một để đảm bảo an toàn RAM. Tới lượt bài của bạn, Bot sẽ tự báo và trả link <b>tho-news.com</b> ngay khi xong!</i>"
                    )
            else:
                item_lines = []
                for idx, it in enumerate(items[:15], start=1):
                    tag = "🚀 Đang xử lý ngay" if it.get("starts_now") else f"⏳ Chờ lượt #{it.get('position', idx)}"
                    item_lines.append(f"{idx}. <b>{tag}</b>\n   <code>{it['article_url']}</code>")
                if len(items) > 15:
                    item_lines.append(f"<i>... và {len(items) - 15} link khác</i>")
                reply_text = (
                    f"📥 <b>ĐÃ TIẾP NHẬN HÀNG LOẠT {len(items)} LINK VÀO HÀNG ĐỢI FIFO!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    + "\n".join(item_lines)
                    + "\n\n✅ <i>Bot sẽ tự động dựng tuần tự từng video 1 (100% an toàn RAM) và nhắn tin trả link <b>tho-news.com</b> cho từng clip ngay khi hoàn tất!</i>"
                )

            await status_msg.edit_text(
                text=reply_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Xem Hàng Đợi FIFO", callback_data="cmd_view_fifo_queue", style="primary")],
                    [InlineKeyboardButton("📱 Xem Hàng Đợi Social", callback_data="cmd_view_social", style="success")],
                    [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")]
                ]),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Lỗi kích hoạt 3D pipeline FIFO: {e}")
            await status_msg.edit_text(
                text=f"❌ <b>Lỗi xếp hàng pipeline 3D:</b> <code>{str(e)}</code>",
                parse_mode=ParseMode.HTML
            )
        return

    # [LEGACY HIDDEN - GIỮ LẠI ĐỂ DÙNG LẠI SAU NÀY KHI BẬT ENABLE_LEGACY_RAW_COLLECTOR]
    if total_links == 1:
        url = valid_urls[0]
        is_fb_page = (
            ("facebook.com" in url or "fb.watch" in url) and
            not any(k in url for k in ["/reel/", "/videos/", "/watch", "fb.watch", "/share/"])
        )
        if is_fb_page:
            wait_text = (
                f"⏳ <b>Đang quét video từ Facebook Page / Group...</b>\n"
                f"🔗 <code>{url}</code>\n\n"
                f"<i>Hệ thống đang truy cập tab Videos để tải các clip mới nhất vào Pipeline!</i>"
            )
            max_count = 5
        else:
            wait_text = (
                f"⏳ <b>Đang phân tích liên kết và tải video tự động...</b>\n"
                f"🔗 <code>{url}</code>\n\n"
                f"<i>Hệ thống sẽ tải về khoang 1_raw và đưa thẳng vào AI Pipeline!</i>"
            )
            max_count = 1

        status_msg = await update.message.reply_text(wait_text, parse_mode=ParseMode.HTML)

        try:
            loop = asyncio.get_running_loop()
            downloaded = await loop.run_in_executor(
                None,
                lambda: download_from_url(url=url, max_downloads=max_count, auto_trigger_pipeline=True)
            )

            if downloaded:
                file_names = "\n".join([f"• <code>{d['filename']}</code> ({d['size_mb']} MB)" for d in downloaded])
                success_text = (
                    f"🎉 <b>ĐÃ TẢI THÀNH CÔNG {len(downloaded)} VIDEO TỪ LIÊN KẾT!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{file_names}\n\n"
                    f"🚀 <b>AI Pipeline đã được kích hoạt:</b>\n"
                    f"Gemini AI đang phân tích và FFmpeg đang render 9:16 (lật gương hflip + AI voiceover) để xuất bản lên Web Player & Social Queue!"
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Xem Hàng Đợi Social", callback_data="cmd_view_social", style="success")],
                    [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")]
                ])
                await status_msg.edit_text(text=success_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            else:
                await status_msg.edit_text(
                    f"⚠️ <b>Không tìm thấy video mới (hoặc video đã được tải trước đó)!</b>\n"
                    f"Vui lòng kiểm tra lại liên kết hoặc quyền riêng tư của bài viết.",
                    parse_mode=ParseMode.HTML
                )
        except ValueError as ve:
            logger.warning(f"Cảnh báo định dạng URL: {ve}")
            await status_msg.edit_text(
                f"⚠️ <b>LƯU Ý ĐỊNH DẠNG LIÊN KẾT:</b>\n\n"
                f"{str(ve)}\n\n"
                f"📌 <b>Các dạng link Facebook chuẩn được hỗ trợ 100%:</b>\n"
                f"• Thước phim (Reel): <code>https://www.facebook.com/reel/123456...</code>\n"
                f"• Video Watch: <code>https://www.facebook.com/watch/?v=123456...</code>\n"
                f"• Link Share Video/Reel từ app: <code>https://www.facebook.com/share/r/...</code>",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Lỗi khi xử lý URL tải video: {e}")
            await status_msg.edit_text(
                f"❌ <b>Không thể tải video từ liên kết này!</b>\n\n"
                f"Chi tiết: <code>{str(e)}</code>\n\n"
                f"💡 <i>Gợi ý: Mở trực tiếp video/Reel trên Facebook -> Bấm Chia sẻ -> Sao chép liên kết rồi gửi lại nhé!</i>",
                parse_mode=ParseMode.HTML
            )

    else:
        # XỬ LÝ TẢI HÀNG LOẠT NHIỀU LINK CÙNG LÚC
        status_msg = await update.message.reply_text(
            f"📥 <b>PHÁT HIỆN {total_links} LIÊN KẾT HÀNG LOẠT!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Đang tiến hành tải tuần tự từng video và nạp vào AI Video Pipeline...",
            parse_mode=ParseMode.HTML
        )

        all_downloaded = []
        errors = []

        loop = asyncio.get_running_loop()
        for idx, single_url in enumerate(valid_urls, start=1):
            try:
                await status_msg.edit_text(
                    f"⏳ <b>Đang tải video {idx}/{total_links}...</b>\n"
                    f"🔗 <code>{single_url[:60]}...</code>",
                    parse_mode=ParseMode.HTML
                )
                dl_items = await loop.run_in_executor(
                    None,
                    lambda u=single_url: download_from_url(url=u, max_downloads=1, auto_trigger_pipeline=True)
                )
                if dl_items:
                    all_downloaded.extend(dl_items)
            except Exception as ex:
                logger.warning(f"Lỗi tải link {single_url}: {ex}")
                errors.append(f"• Link {idx}: {str(ex)[:60]}")

        summary_lines = [f"• <code>{d['filename']}</code> ({d['size_mb']} MB)" for d in all_downloaded]
        summary_text = "\n".join(summary_lines) if summary_lines else "<i>Không có video mới nào được tải.</i>"
        err_text = f"\n\n⚠️ <b>Lỗi {len(errors)} link:</b>\n" + "\n".join(errors) if errors else ""

        result_msg = (
            f"🎉 <b>HOÀN TẤT TẢI HÀNG LOẠT ({len(all_downloaded)}/{total_links} video thành công)!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{summary_text}{err_text}\n\n"
            f"🚀 <b>Toàn bộ video đã được đưa vào AI Pipeline để tự động lật gương, lồng tiếng và đăng tải!</b>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 Xem Hàng Đợi Social", callback_data="cmd_view_social", style="success")],
            [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")]
        ])
        await status_msg.edit_text(text=result_msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tự động thu thập video khi gửi file trực tiếp"""
    message = update.message
    video = message.video or message.document
    if not video:
        return

    file_id = video.file_id
    file_unique_id = video.file_unique_id
    file_size_mb = round((video.file_size or 0) / (1024 * 1024), 2)

    if is_video_downloaded(file_unique_id):
        await message.reply_text(
            "⚠️ <b>Video này đã được nạp vào hệ thống trước đó!</b>\nĐã bỏ qua để tránh trùng lặp.",
            parse_mode=ParseMode.HTML
        )
        return

    status_reply = await message.reply_text(
        f"⏳ <b>Đang tiếp nhận video...</b>\nDung lượng: {file_size_mb} MB",
        parse_mode=ParseMode.HTML
    )

    try:
        tg_file = await context.bot.get_file(file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = f"auto_{timestamp}_{file_unique_id[:6]}.mp4"
        save_path = RAW_STORAGE_DIR / clean_name

        await tg_file.download_to_drive(custom_path=str(save_path))
        mark_video_downloaded(file_unique_id, clean_name, {"size_mb": file_size_mb})

        settings = load_settings()
        is_auto = settings.get("auto_pipeline_on_receive", True)

        if is_auto:
            success_text = (
                f"✅ <b>ĐÃ TIẾP NHẬN VIDEO THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 <b>Tệp lưu:</b> <code>storage/1_raw/{clean_name}</code>\n"
                f"⚖️ <b>Dung lượng:</b> {file_size_mb} MB\n\n"
                f"🚀 <b>Chế độ Auto 24/7 đang BẬT:</b>\n"
                f"Hệ thống đang tự động đẩy video vào AI Video Factory (Gemini + FFmpeg) để sản xuất Web Full & Social Teaser!"
            )
            factory_script = ROOT_DIR / "automation" / "2_ai_video_factory" / "factory.py"
            if factory_script.exists():
                subprocess.Popen([sys.executable, str(factory_script)])
        else:
            success_text = (
                f"✅ <b>ĐÃ LƯU VIDEO VÀO KHOANG THÔ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 <b>Tệp lưu:</b> <code>storage/1_raw/{clean_name}</code>\n"
                f"⚖️ <b>Dung lượng:</b> {file_size_mb} MB\n"
                f"🟡 Chế độ duyệt thủ công: Bấm nút bên dưới để render AI khi bạn muốn."
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Kích hoạt Render Ngay", callback_data="cmd_run_pipeline", style="danger")],
            [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")]
        ])

        await status_reply.edit_text(text=success_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        logger.info(f"Đã nạp video vào khoang 1_raw: {save_path}")

    except Exception as e:
        logger.error(f"Lỗi tải video Telegram: {e}")
        await status_reply.edit_text(f"❌ Lỗi tiếp nhận video: <code>{str(e)}</code>", parse_mode=ParseMode.HTML)


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /queue - Xem trạng thái Hàng đợi FIFO 3D Thỏ & Gấu"""
    factory_dir = ROOT_DIR / "automation" / "2_ai_video_factory"
    if str(factory_dir) not in sys.path:
        sys.path.insert(0, str(factory_dir))
    import rabbit_bear_runner
    st = await asyncio.to_thread(rabbit_bear_runner.get_fifo_queue_status)
    cur = st.get("current")
    q = st.get("queue", [])
    now_str = datetime.now().strftime("%H:%M:%S")
    lines = [
        f"📋 <b>HÀNG ĐỢI DỰNG 3D THỎ & GẤU (FIFO)</b> • <i>{now_str}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    if cur:
        lines.append(f"🎬 <b>Đang xử lý:</b>\n<code>{cur.get('article_url', '')}</code>")
    else:
        lines.append("🟢 <b>Trạng thái:</b> Xưởng 3D đang rảnh (gửi link là dựng ngay!)")
    if q:
        lines.append(f"\n⏳ <b>Đang xếp hàng chờ ({len(q)} link):</b>")
        for idx, item in enumerate(q[:12], start=1):
            lines.append(f"  {idx}. <code>{item.get('article_url', '')}</code>")
        if len(q) > 12:
            lines.append(f"  <i>... và {len(q) - 12} link khác</i>")
    else:
        lines.append("\n📭 <i>Không có link nào đang chờ.</i>")
    await update.message.reply_text(
        text="\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Làm mới hàng đợi", callback_data="cmd_view_fifo_queue", style="primary")],
            [InlineKeyboardButton("🏠 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")],
        ]),
        parse_mode=ParseMode.HTML,
    )


async def _bot_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f"Telegram Bot handler warning: {context.error}")


def run_telegram_bot():
    """Chạy Telegram Bot lâu dài (hỗ trợ xử lý đồng thời, phản hồi tức thì không bị nghẽn)"""
    if not TELEGRAM_BOT_TOKEN:
        print("\n=======================================================")
        print("⚠️ CHƯA CÓ TELEGRAM_BOT_TOKEN TRONG FILE .env!")
        print("1. Mở Telegram, chat với: @BotFather")
        print("2. Gửi lệnh /newbot và đặt tên cho Bot")
        print("3. Nhận API Token dạng: 7891234567:AAH...")
        print("4. Dán vào file d:\\web_aff\\.env:")
        print("   TELEGRAM_BOT_TOKEN=7891234567:AAH...")
        print("=======================================================\n")
        return False

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)
        .connect_timeout(20)
        .read_timeout(20)
        .write_timeout(20)
        .pool_timeout(20)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", start_command))
    app.add_handler(CommandHandler("queue", queue_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_message))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video_message))
    app.add_error_handler(_bot_error_handler)

    print("🚀 Telegram Auto Video Affiliate Bot đang chạy (Concurrent Mode)...")
    print(f"📂 Thư mục tiếp nhận video: {RAW_STORAGE_DIR}")

    # Khôi phục Hàng đợi FIFO 3D nếu VM vừa restart giữa chừng
    try:
        factory_dir = ROOT_DIR / "automation" / "2_ai_video_factory"
        if str(factory_dir) not in sys.path:
            sys.path.insert(0, str(factory_dir))
        import rabbit_bear_runner
        rabbit_bear_runner.start_fifo_worker_if_needed()
    except Exception as e:
        logger.warning(f"Không thể khôi phục hàng đợi FIFO 3D: {e}")

    app.run_polling(drop_pending_updates=False)
    return True


if __name__ == "__main__":
    run_telegram_bot()
