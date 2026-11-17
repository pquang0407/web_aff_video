"""
TEST_SOCIAL_POSTER.PY - Kiểm thử toàn diện Module 4 (Social Poster + Auto Comment + Web Admin)
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

import config
import fb_service
import poster


def run_test_suite():
    print("==================================================================")
    print(" BẮT ĐẦU KIỂM THỬ MODULE 4 (SOCIAL POSTER & AUTO COMMENT LINK)")
    print("==================================================================\n")

    # 1. Kiểm tra đồng bộ Cookie & Fanpage từ facebook_bot
    print(">>> [TEST 1] Kiểm tra đồng bộ Cookie Facebook & 5 Fanpage có sẵn...")
    cookie_st = fb_service.get_cookie_status()
    page_cfg = fb_service.get_page_config()
    pages = page_cfg.get("pages", [])
    assert cookie_st["connected"] is True, "Cookie Facebook chưa kết nối!"
    assert len(pages) >= 5, "Chưa đồng bộ đủ 5 Fanpage từ facebook_bot!"
    print(f"  [PASS] Cookie Facebook Connected! UID: {cookie_st['uid']} ({cookie_st['cookie_count']} cookies)")
    print(f"  [PASS] Đã nạp sẵn {len(pages)} Fanpage: {[p['name'] for p in pages]}\n")

    # 2. Kiểm tra Hàng Đợi Social Queue
    print(">>> [TEST 2] Kiểm tra Hàng Đợi Video (Social Queue)...")
    queue = poster.get_social_queue()
    assert len(queue) >= 4, "Hàng đợi Social Queue rỗng!"
    print(f"  [PASS] Tìm thấy {len(queue)} video sẵn sàng trong Queue: {[x['id'] for x in queue[:5]]}\n")

    # 3. Kiểm tra Đăng Video Teaser + Auto Comment trên cả Facebook & Threads
    print(">>> [TEST 3] Kiểm thử Đăng Teaser + Tự động Bình luận Link (?v=ID) lên Facebook & Threads...")
    res = poster.post_video_to_social(
        video_id="animal_live_show",
        platforms=["facebook", "threads"],
        simulate=True,
    )
    assert res["video_id"] == "animal_live_show"
    assert "?v=animal_live_show" in res["comment_text"]
    assert res["results"]["facebook"]["ok"] is True
    assert res["results"]["threads"]["ok"] is True

    print(f"  [PASS] Fanpage đã đăng: {res['results']['facebook']['page_name']}")
    print(f"  [PASS] Link bài FB: {res['results']['facebook']['post_url']}")
    print(f"  [PASS] Nội dung Auto-Comment dưới bài FB: {res['comment_text']}")
    print(f"  [PASS] Link bài Threads: {res['results']['threads']['thread_url']}")
    print(f"  [PASS] Nội dung Auto-Reply dưới bài Threads: {res['results']['threads']['reply_text']}\n")

    print("==================================================================")
    print(" TẤT CẢ TEST CASE MODULE 4 ĐỀU ĐẠT 100% (ALL PASSED!)")
    print("==================================================================")


if __name__ == "__main__":
    run_test_suite()
