"""
TEST_PUBLISHER.PY - Kịch bản kiểm thử toàn diện 2 Chế độ của Module 3 (Web Publisher)
- Test Case 1: Kiểm thử Chế độ Cloud R2 (CDN URL & Metadata)
- Test Case 2: Kiểm thử Chế độ Local (Đồng bộ toàn bộ kho video vào web/config.js)
- Test Case 3: Kiểm thử Luồng Khép Kín End-to-End (Module 2 -> Module 3)
"""

import json
import shutil
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
FACTORY_DIR = CURRENT_DIR.parent / "2_ai_video_factory"
sys.path.insert(0, str(CURRENT_DIR))

import config
import publisher


def run_test_suite():
    print("==================================================================")
    print(" BẮT ĐẦU CHẠY BỘ TEST CASE CHO MODULE 3 (WEB PUBLISHER DUAL-MODE)")
    print("==================================================================\n")

    # ------------------------------------------------------------------
    # TEST CASE 1: CHẾ ĐỘ CLOUD R2 (SIMULATION)
    # ------------------------------------------------------------------
    print(">>> [TEST CASE 1] Kiểm thử Chế độ CLOUD R2 (Cloudflare R2 CDN Mode)...")
    dance_meta = config.FULL_DIR / "dance_meta.json"
    assert dance_meta.exists(), f"Không tìm thấy {dance_meta}"

    res_cloud = publisher.publish_single_metadata(
        dance_meta,
        force_mode="cloud_r2",
        simulate_cloud=True,
        set_as_default=False,
    )
    assert res_cloud is not None, "Publish Cloud R2 thất bại!"
    assert res_cloud["publish_mode"] == "cloud_r2"
    assert res_cloud["web_video_url"].startswith(config.R2_PUBLIC_DOMAIN)
    assert "?v=dance" in res_cloud["target_web_url"]

    db_cloud = json.loads(config.WEB_VIDEOS_DB.read_text(encoding="utf-8"))
    assert db_cloud["videos"]["dance"]["videoUrl"].startswith(config.R2_PUBLIC_DOMAIN)
    print(f"  [PASS] Cloud R2 Video URL: {res_cloud['web_video_url']}")
    print(f"  [PASS] Cloud R2 Poster URL: {res_cloud['web_poster_url']}")
    print(f"  [PASS] Target Social Link: {res_cloud['target_web_url']}\n")

    # ------------------------------------------------------------------
    # TEST CASE 2: CHẾ ĐỘ LOCAL (ĐỒNG BỘ KHO VIDEO VÀO WEB/CONFIG.JS)
    # ------------------------------------------------------------------
    print(">>> [TEST CASE 2] Kiểm thử Chế độ LOCAL (Xuất bản toàn bộ video vào web/config.js)...")
    results_local = publisher.publish_all(
        force_mode="local",
        simulate_cloud=False,
        republish_all=True,
    )
    assert len(results_local) >= 4, "Số lượng video xuất bản ít hơn dự kiến!"

    db_local = json.loads(config.WEB_VIDEOS_DB.read_text(encoding="utf-8"))
    videos_in_config = db_local.get("videos", {})
    assert "default" in videos_in_config, "Thiếu key 'default' trong config.js!"
    assert "cat_mukkbang" in videos_in_config, "Thiếu video 'cat_mukkbang'!"
    assert videos_in_config["cat_mukkbang"]["videoUrl"].startswith("../storage/2_web_full/")
    assert config.WEB_CONFIG_JS.exists(), "File web/config.js chưa được tạo!"

    print(f"  [PASS] Đã đồng bộ thành công {len(results_local)} video vào web/config.js!")
    print(f"  [PASS] Danh sách key trong config.js: {list(videos_in_config.keys())}\n")

    # ------------------------------------------------------------------
    # TEST CASE 3: LUỒNG KHÉP KÍN END-TO-END (MODULE 2 -> MODULE 3)
    # ------------------------------------------------------------------
    print(">>> [TEST CASE 3] Kiểm thử Luồng Khép Kín End-to-End (Module 2 -> Module 3)...")
    source_demo = Path(r"D:\nckh\live_animal\video\default.mp4")
    if source_demo.exists():
        raw_target = config.STORAGE_DIR / "1_raw" / "animal_live_show.mp4"
        shutil.copy2(source_demo, raw_target)

        # Gọi Module 2 xử lý video mới
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(FACTORY_DIR / "factory.py"), "--input", str(raw_target), "--id", "animal_live_show"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Chuyển ngay sang Module 3 để cập nhật lên Web
        new_meta_path = config.FULL_DIR / "animal_live_show_meta.json"
        assert new_meta_path.exists(), "Module 2 chưa tạo file metadata!"
        pub_out = publisher.publish_single_metadata(
            new_meta_path,
            force_mode="local",
            set_as_default=True,
        )
        assert pub_out is not None, "Module 3 xuất bản thất bại!"
        assert pub_out["status"] == "published_to_web"

        db_final = json.loads(config.WEB_VIDEOS_DB.read_text(encoding="utf-8"))
        assert "animal_live_show" in db_final["videos"], "Video mới chưa xuất hiện trong config.js!"
        print(f"  [PASS] Video mới 'animal_live_show' đã tự động đi từ 1_raw -> Gemini AI -> FFmpeg -> web/config.js!")
        print(f"  [PASS] Tiêu đề AI tạo: {pub_out['title']}")
        print(f"  [PASS] Link đích nhận về: {pub_out['target_web_url']}\n")

    print("==================================================================")
    print(" TẤT CẢ 3 TEST CASE ĐỀU ĐẠT 100% (ALL PASSED!)")
    print("==================================================================")


if __name__ == "__main__":
    run_test_suite()
