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


# Cờ ẩn tính năng nạp video thô / dán link clip cũ (giữ lại code để bật lại khi cần)
ENABLE_LEGACY_RAW_COLLECTOR = False


def build_main_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    Tạo bàn phím điều khiển trung tâm cho Hệ thống Video Tin Tức 3D Vũ trụ Thỏ & Gấu.
    Các nút nạp video thô cũ được ẩn đi qua cờ ENABLE_LEGACY_RAW_COLLECTOR để dùng lại sau này.
    """
    stats = get_video_stats()
    settings = load_settings()

    auto_mode = settings.get("auto_pipeline_on_receive", True)
    mode_btn_text = "🟢 AUTO 24/7: BẬT" if auto_mode else "🔴 DUYỆT THỦ CÔNG"
    mode_btn_style = "success" if auto_mode else "danger"

    keyboard = [
        # Hàng 1: Đồng bộ & Xuất bản Kho 3D Thỏ & Gấu
        [
            InlineKeyboardButton(
                "🐰🐻 ĐỒNG BỘ KHO VIDEO 3D THỎ & GẤU",
                callback_data="cmd_sync_rabbit_bear",
                style="danger"
            )
        ],
    ]

    # [LEGACY HIDDEN - GIỮ LẠI ĐỂ DÙNG LẠI SAU NÀY KHI BẬT ENABLE_LEGACY_RAW_COLLECTOR]
    if ENABLE_LEGACY_RAW_COLLECTOR:
        keyboard.append([
            InlineKeyboardButton(
                "🔥 KÍCH HOẠT AUTO PIPELINE (M2 ➔ M4)",
                callback_data="cmd_run_pipeline",
                style="danger"
            )
        ])
        keyboard.append([
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
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                f"🌐 KHO WEB PLAYER 3D ({stats['web_count']} VIDEO)",
                callback_data="cmd_view_web",
                style="primary"
            )
        ])

    keyboard.extend([
        # Hàng 3: Hàng đợi Social Teasers (Màu Xanh Lá Success rực rỡ)
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
    ])
    return InlineKeyboardMarkup(keyboard)


def build_dashboard_text() -> str:
    """Tạo nội dung giao diện trang chủ Vũ trụ Thỏ & Gấu 3D Pixar"""
    stats = get_video_stats()
    settings = load_settings()
    auto_mode = settings.get("auto_pipeline_on_receive", True)
    mode_desc = "🟢 <b>Đang Bật</b> <i>(Gửi link báo ➔ Dựng 3D Thỏ & Gấu ➔ Web & Social)</i>" if auto_mode else "🟡 <b>Duyệt thủ công</b> <i>(Chờ admin duyệt)</i>"

    text = (
        "🐰🐻 <b>XƯỞNG VIDEO TIN TỨC 3D (VŨ TRỤ THỎ & GẤU)</b>\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🤖 <b>Đạo diễn AI:</b> <code>Gemini 2.5 Flash (4-Act Story)</code>\n"
        "🎙️ <b>Giọng đọc:</b> <code>NamMinhNeural (Đồng nhất 100% • 9.35s/10s)</code>\n"
        "🎬 <b>3D Engine:</b> <code>Pixar 3D Muse.ai + Outro Like/Follow</code>\n"
        "💰 <b>Affiliate:</b> <code>Shopee / TikTok / Lazada</code>\n\n"
        "📦 <b>TRẠNG THÁI KHO PHÁT SÓNG:</b>\n"
        f"  ├ 🌐 <b>Web Player 3D (Full HD 9:16):</b> <code>{stats['web_count']} video</code>\n"
        f"  └ 📱 <b>Hàng đợi Social (FB/Threads):</b> <code>{stats['social_count']} video sẵn sàng</code>\n\n"
        f"⚙️ <b>Vận hành:</b> {mode_desc}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Gửi link bài báo (VnExpress, Soha, Dân Trí...) vào đây để tự động sản xuất video 3D Thỏ & Gấu!</i>"
    )
    return text


def build_social_queue_keyboard() -> InlineKeyboardMarkup:
    """Hiển thị danh sách video 3D Thỏ & Gấu trong Hàng đợi Social (đồng bộ cả Local & Cloud VM)"""
    meta_files = sorted(
        list(WEB_FULL_DIR.glob("*_meta.json")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    keyboard = []

    if meta_files:
        for mf in meta_files[:8]:
            vid_id = mf.stem.replace("_meta", "")
            label = vid_id
            try:
                mdata = json.loads(mf.read_text(encoding="utf-8"))
                label = mdata.get("title") or vid_id
            except Exception:
                pass
            short_name = label if len(label) <= 32 else label[:30] + ".."
            keyboard.append([
                InlineKeyboardButton(f"▶️ {short_name}", callback_data=f"vid_detail_{vid_id}", style="success")
            ])
    else:
        social_files = sorted(list(SOCIAL_DIR.glob("*_teaser.mp4")))
        for f in social_files[:6]:
            vid_id = f.stem.replace("_teaser", "")
            short_name = vid_id if len(vid_id) <= 22 else vid_id[:20] + ".."
            keyboard.append([
                InlineKeyboardButton(f"▶️ {short_name}", callback_data=f"vid_detail_{vid_id}", style="success")
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
