import json
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import (
    get_video_stats,
    load_settings,
    WEB_BASE_URL,
    SOCIAL_DIR,
    RAW_STORAGE_DIR,
    WEB_FULL_DIR
)


def build_main_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    Tạo bàn phím điều khiển trung tâm đẹp mắt, rực rỡ với màu sắc
    chuẩn Telegram Bot API 9.4+ (style='success', style='danger', style='primary').
    Độ dài chữ được tối ưu tuyệt đối để không bao giờ bị cắt ngắn '...'.
    """
    stats = get_video_stats()
    settings = load_settings()

    auto_mode = settings.get("auto_pipeline_on_receive", True)
    mode_btn_text = "🟢 AUTO 24/7: BẬT" if auto_mode else "🔴 DUYỆT THỦ CÔNG"
    mode_btn_style = "success" if auto_mode else "danger"

    keyboard = [
        # Hàng 1: Nút hành động nổi bật nhất (Màu Đỏ Cam Danger)
        [
            InlineKeyboardButton(
                "🔥 KÍCH HOẠT AUTO PIPELINE (M2 ➔ M4)",
                callback_data="cmd_run_pipeline",
                style="danger"
            )
        ],
        # Hàng 2: Hai nút ngắn gọn, cân xứng (Màu Xanh Dương Primary)
        [
            InlineKeyboardButton(
                f"📥 Video Thô · {stats['raw_count']}",
                callback_data="cmd_view_raw",
                style="primary"
            ),
            InlineKeyboardButton(
                f"🌐 Web Player · {stats['web_count']}",
                callback_data="cmd_view_web",
                style="primary"
            )
        ],
        # Hàng 3: Hàng đợi Social Teasers (Màu Xanh Lá Success rực rỡ, full-width không bao giờ bị cắt)
        [
            InlineKeyboardButton(
                f"📱 HÀNG ĐỢI SOCIAL ({stats['social_count']} SẴN SÀNG)",
                callback_data="cmd_view_social",
                style="success"
            )
        ],
        # Hàng 4: Đăng Kênh Telegram (Full-width, màu Primary)
        [
            InlineKeyboardButton(
                "📢 ĐĂNG LÊN KÊNH TELEGRAM",
                callback_data="cmd_post_channel",
                style="primary"
            )
        ],
        # Hàng 5: Trạng thái Auto và Thống kê
        [
            InlineKeyboardButton(
                mode_btn_text,
                callback_data="cmd_toggle_auto_mode",
                style=mode_btn_style
            ),
            InlineKeyboardButton(
                "📊 THỐNG KÊ",
                callback_data="cmd_system_stats",
                style="primary"
            )
        ],
        # Hàng 6: Điều hướng hệ thống
        [
            InlineKeyboardButton("🔄 Làm mới", callback_data="cmd_refresh_dashboard"),
            InlineKeyboardButton("🌐 Mở Web Player", url=WEB_BASE_URL)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_dashboard_text() -> str:
    """Tạo nội dung giao diện trang chủ gọn gàng, typography cao cấp"""
    stats = get_video_stats()
    settings = load_settings()
    auto_mode = settings.get("auto_pipeline_on_receive", True)
    mode_desc = "🟢 <b>Đang Bật</b> <i>(Cào video ➔ AI Render ➔ Đăng Social)</i>" if auto_mode else "🟡 <b>Duyệt thủ công</b> <i>(Chờ admin duyệt)</i>"

    text = (
        "🚀 <b>AUTO VIDEO AFFILIATE 24/7</b>\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🤖 <b>AI Core:</b> <code>Gemini 3.5 Flash Lite</code>\n"
        "🎬 <b>Render:</b> <code>Fast Blur 9:16 + TTS Synced</code>\n"
        "💰 <b>Affiliate:</b> <code>Shopee / TikTok / Lazada</code>\n\n"
        "📦 <b>HÀNG ĐỢI KHO LƯU TRỮ:</b>\n"
        f"  ├ 📥 <b>Khoang 1 (Raw chờ AI):</b> <code>{stats['raw_count']} video</code>\n"
        f"  ├ 🌐 <b>Khoang 2 (Web Full HD):</b> <code>{stats['web_count']} video</code>\n"
        f"  └ 📱 <b>Khoang 3 (Social Teasers):</b> <code>{stats['social_count']} video sẵn sàng</code>\n\n"
        f"⚙️ <b>Vận hành:</b> {mode_desc}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Gửi link (FB/TikTok/YouTube) hoặc file video để tự động nạp!</i>"
    )
    return text


def build_social_queue_keyboard() -> InlineKeyboardMarkup:
    """Hiển thị danh sách video trong Hàng đợi Social Teasers có màu sắc trực quan"""
    social_files = sorted(list(SOCIAL_DIR.glob("*_teaser.mp4")))
    keyboard = []

    if not social_files:
        social_files = sorted(list(SOCIAL_DIR.glob("*.mp4")))

    for f in social_files[:6]:
        vid_id = f.stem.replace("_teaser", "")
        # Rút ngắn tên để không bị cắt trên màn hình mobile
        short_name = vid_id if len(vid_id) <= 22 else vid_id[:20] + ".."
        btn_text = f"▶️ {short_name}"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"vid_detail_{vid_id}", style="success")
        ])

    keyboard.append([
        InlineKeyboardButton("🚀 ĐĂNG TẤT CẢ LÊN SOCIAL", callback_data="cmd_post_all_social", style="danger")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")
    ])
    return InlineKeyboardMarkup(keyboard)


def build_raw_queue_keyboard() -> InlineKeyboardMarkup:
    """Hiển thị danh sách video thô đang chờ xử lý AI"""
    raw_files = sorted(list(RAW_STORAGE_DIR.glob("*.mp4")))
    keyboard = []

    for f in raw_files[:6]:
        vid_id = f.stem
        short_name = vid_id if len(vid_id) <= 22 else vid_id[:20] + ".."
        btn_text = f"📥 {short_name}.mp4"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"raw_detail_{vid_id}", style="primary")
        ])

    keyboard.append([
        InlineKeyboardButton("🔥 KÍCH HOẠT AI RENDER TẤT CẢ", callback_data="cmd_run_pipeline", style="danger")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Về Bảng Điều Khiển", callback_data="cmd_back_home", style="primary")
    ])
    return InlineKeyboardMarkup(keyboard)


def build_video_action_keyboard(video_id: str) -> InlineKeyboardMarkup:
    """Bàn phím thao tác từng video với màu sắc phân định rõ ràng"""
    web_player_url = f"{WEB_BASE_URL}/?v={video_id}"
    keyboard = [
        [
            InlineKeyboardButton("🎬 Mở Web Player Xem Thử", url=web_player_url)
        ],
        [
            InlineKeyboardButton("🚀 Đăng FB Fanpage & Threads", callback_data=f"act_post_social_{video_id}", style="success")
        ],
        [
            InlineKeyboardButton("📢 Đăng Lên Kênh Telegram", callback_data=f"act_post_channel_{video_id}", style="primary")
        ],
        [
            InlineKeyboardButton("🔙 Hàng Đợi", callback_data="cmd_view_social"),
            InlineKeyboardButton("🏠 Menu Chính", callback_data="cmd_back_home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
