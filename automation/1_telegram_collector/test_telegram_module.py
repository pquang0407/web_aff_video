import os
import sys
import unittest
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import (
    get_video_stats,
    load_settings,
    save_settings,
    mark_video_downloaded,
    is_video_downloaded,
    RAW_STORAGE_DIR,
    SOCIAL_DIR,
    WEB_FULL_DIR
)
from bot_ui import (
    build_main_dashboard_keyboard,
    build_dashboard_text,
    build_social_queue_keyboard,
    build_raw_queue_keyboard,
    build_video_action_keyboard
)

class TestTelegramAffiliateSystem(unittest.TestCase):
    def test_01_stats_and_settings(self):
        """Kiểm tra đọc số lượng khoang lưu trữ và cấu hình hệ thống"""
        stats = get_video_stats()
        self.assertIn("raw_count", stats)
        self.assertIn("web_count", stats)
        self.assertIn("social_count", stats)
        
        settings = load_settings()
        self.assertIn("auto_pipeline_on_receive", settings)
        self.assertIn("max_video_duration_keep", settings)
        print(f"✅ Test 1 Passed: Quét khoang thành công ({stats['raw_count']} raw, {stats['web_count']} web, {stats['social_count']} social)")

    def test_02_dashboard_ui_layout(self):
        """Kiểm tra giao diện Bảng điều khiển trung tâm & phím bấm"""
        markup = build_main_dashboard_keyboard()
        buttons = markup.inline_keyboard
        
        # Hàng 1: Nút kích hoạt Auto Pipeline
        self.assertIn("KÍCH HOẠT AUTO PIPELINE", buttons[0][0].text)
        
        # Hàng 2: Nút xem kho video thô & web full
        self.assertIn("Video Thô", buttons[1][0].text)
        self.assertIn("Web Player", buttons[1][1].text)
        
        # Hàng 3: Hàng đợi Social & Đăng Channel
        self.assertIn("HÀNG ĐỢI SOCIAL", buttons[2][0].text)
        self.assertIn("ĐĂNG LÊN KÊNH TELEGRAM", buttons[3][0].text)
        
        text = build_dashboard_text()
        self.assertIn("AUTO VIDEO AFFILIATE", text)
        self.assertIn("Gemini 3.5 Flash Lite", text)
        print("✅ Test 2 Passed: Giao diện Bảng Điều Khiển Auto Video Affiliate chuẩn xác!")

    def test_03_queue_keyboards(self):
        """Kiểm tra bàn phím duyệt Hàng đợi Social & Video Thô"""
        social_markup = build_social_queue_keyboard()
        self.assertTrue(len(social_markup.inline_keyboard) >= 1)
        
        raw_markup = build_raw_queue_keyboard()
        self.assertTrue(len(raw_markup.inline_keyboard) >= 1)

        action_markup = build_video_action_keyboard("dance")
        self.assertEqual(len(action_markup.inline_keyboard), 4)
        self.assertIn("Mở Web Player", action_markup.inline_keyboard[0][0].text)
        self.assertIn("Đăng FB Fanpage & Threads", action_markup.inline_keyboard[1][0].text)
        print("✅ Test 3 Passed: Bàn phím duyệt Hàng đợi & Hành động từng Video hoạt động tốt!")

    def test_04_anti_duplicate_ingestion(self):
        """Kiểm tra chống tải trùng lặp video"""
        import time
        test_uid = f"aff_test_video_{int(time.time() * 1000)}"
        self.assertFalse(is_video_downloaded(test_uid))
        mark_video_downloaded(test_uid, "aff_test.mp4", {"size_mb": 8.5})
        self.assertTrue(is_video_downloaded(test_uid))
        print("✅ Test 4 Passed: Cơ chế chống nạp trùng video hoạt động chuẩn xác!")

if __name__ == "__main__":
    unittest.main()
