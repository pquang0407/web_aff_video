import os
import sys
import unittest
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from url_downloader import ensure_facebook_netscape_cookies, FB_NETSCAPE_COOKIE_PATH

class TestUrlDownloader(unittest.TestCase):
    def test_01_cookie_export(self):
        """Kiểm tra xuất Netscape cookie từ facebook_cookies.json"""
        cookie_path = ensure_facebook_netscape_cookies()
        if cookie_path:
            self.assertTrue(os.path.exists(cookie_path))
            with open(cookie_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("# Netscape HTTP Cookie File", content)
                self.assertIn(".facebook.com", content)
                self.assertIn("c_user", content)
            print("✅ Test 1 Passed: Đã chuyển đổi Cookie Facebook sang chuẩn Netscape cho yt-dlp thành công!")
        else:
            print("⚠️ Bỏ qua Test 1 vì chưa có file cookie gốc")

    def test_02_ytdlp_availability(self):
        """Kiểm tra thư viện yt-dlp sẵn sàng"""
        import yt_dlp
        self.assertIsNotNone(yt_dlp.version.__version__)
        print(f"✅ Test 2 Passed: yt-dlp phiên bản {yt_dlp.version.__version__} sẵn sàng tải video đa nền tảng!")

if __name__ == "__main__":
    unittest.main()
