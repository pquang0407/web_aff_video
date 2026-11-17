# NHẬT KÝ DỰ ÁN & TÀI LIỆU HỆ THỐNG AUTO VIDEO AFFILIATE

---

## 1. TỔNG QUAN NỘI DUNG DỰ ÁN

* **Mục tiêu:** Xây dựng hệ thống tự động hóa khép kín 100% từ cào clip Telegram, xử lý qua Gemini AI (`gemini-3.5-flash-lite`) + FFmpeg + TTS Voiceover, đẩy lên Cloudflare R2, tự động đăng teaser lên Facebook Fanpage & Threads kèm auto comment link Web Player, điều hướng người xem để tối đa hóa hoa hồng gián tiếp Shopee / Lazada / TikTok Shop.
* **Chiến lược tận dụng Hệ sinh thái sẵn có:**
  1. **Google Cloud VM (Free 1.6tr Credit):** Đảm nhiệm backend 24/7 (Telethon Collector -> Gemini AI -> FFmpeg -> Upload Cloudflare R2).
  2. **Bộ chuyển đổi Aff 3 Sàn (`D:\web\tho-hoan-tien`):** Đã deploy sẵn, hỗ trợ convert link & redirect ẩn nguồn (`no-referrer`) cho cả **Shopee, Lazada, TikTok Shop**.
  3. **Bot đăng bài & Auto Comment (`D:\app\facebook_bot`):** Đã trích xuất lõi Graph API và đồng bộ tự động toàn bộ **Cookie + 5 Fanpage** sang Module 4 (`automation/4_social_poster`).
  4. **Web Landing Page Player (`D:\web_aff\web`):** Trang công khai dành cho người xem clip (3 cột Sticky, sân khấu 9:16 Ambient, Kho Voucher, Săn Deal 1K-9K, Bảng xếp hạng & Live Chat).
  5. **Web Admin Quản Trị Riêng (`automation/4_social_poster/static/admin.html` & `admin_server.py`):** Trang quản trị nội bộ tách biệt hoàn toàn với trang khách xem, dùng để gắn Cookie FB, chọn Fanpage, gắn tài khoản Threads, quản lý Hàng đợi Video (Social Queue) và theo dõi lịch sử Auto-Comment.

---

## 2. CÂY THƯ MỤC DỰ ÁN (PROJECT DIRECTORY TREE)

```text
D:\web_aff\
│   app.md                                  # Nhật ký dự án, tài liệu kiến trúc, log cập nhật
│   docker-compose.yml                      # Quản lý container trên GCP VM
│   .env                                    # Cấu hình GEMINI_API_KEY, gemini-3.5-flash-lite, R2, Meta
│
├── web/                                    # [TRANG CÔNG KHAI CHO KHÁCH XEM CLIP]
│   ├── index.html                          # Bố cục 3 cột Sticky, Sân khấu 9:16 Ambient, Live Chat, Deal 1K
│   ├── config.js                           # Được sinh tự động bởi Module 3 (10 video thực tế)
│   ├── videos_db.json                      # JSON Database tĩnh lưu trữ danh mục video (Không cần SQL)
│   └── assets/
│       ├── css/style.css                   # Giao diện lấp đầy 2 bên, thanh tiến độ mã, dock nút dọc
│       └── js/
│           ├── app.js                      # Logic chuyển bài Trước/Sau, đếm ngược, chat trực tiếp, rơi cookie
│           └── deeplink.js                 # Bộ xử lý Deep Link mở App Shopee & no-referrer
│
├── storage/                                # Thư mục lưu trữ video theo từng giai đoạn
│   ├── 1_raw/                              # Video gốc (cat_mukkbang, dance, dog_mukkbang, chao_co, duck_mukkbang, animal_live_show)
│   ├── 2_web_full/                         # Video Full tối ưu web + Poster JPG + Metadata JSON
│   └── 3_social_teaser/                    # Video Teaser 9:16 dọc + File lồng tiếng .mp3 + Phụ đề .srt
│
└── automation/                             # Các module tự động hóa khép kín 100%
    ├── 1_telegram_collector/               # [ĐÃ HOÀN THIỆN] Thu thập video thô & Bảng điều khiển Auto Video Affiliate
    │   ├── config.py                       # Quản lý khoang 1_raw, 2_web_full, 3_social_teaser & chống trùng lặp
    │   ├── system_settings.json            # Cài đặt chế độ Auto 24/7 vs Duyệt thủ công
    │   ├── bot_ui.py                       # Bảng điều khiển Inline Keyboard điều phối Pipeline & Hàng đợi
    │   ├── bot_service.py                  # Bot tự động nạp video vào 1_raw + Kích hoạt trọn gói M2 -> M4
    │   ├── channel_scraper.py              # Telethon Userbot tự động lắng nghe & cào video từ Channel công khai
    │   ├── url_downloader.py               # Tự động tải video từ Link (Facebook Page, Group, Reel, TikTok, YouTube)
    │   ├── run_demo.py                     # Trình mô phỏng giao diện Telegram Bot trên console
    │   ├── test_telegram_module.py         # Bộ Test Case kiểm thử 100% chức năng Module 1
    │   └── test_url_downloader.py          # Kiểm thử tải link và bộ trích xuất Cookie Netscape
    ├── 2_ai_video_factory/                 # [ĐÃ HOÀN THIỆN] Xưởng AI Video (Gemini 3.5 Flash Lite + FFmpeg + TTS)
    │   ├── config.py                       # Tự động nạp .env & FFmpeg
    │   ├── gemini_analyzer.py              # Pydantic Structured Output + Quy tắc <=30s giữ nguyên, >30s cắt 10s
    │   ├── tts_engine.py                   # Lồng tiếng AI tiếng Việt + Đồng bộ phụ đề .srt
    │   ├── video_engine.py                 # Lật gương (hflip) + Fast Blur 9:16 + Phụ đề + Banner
    │   └── factory.py                      # Bộ điều phối xử lý video tự động hàng loạt
    ├── 3_web_publisher/                    # [ĐÃ HOÀN THIỆN] Xuất bản Web Dual-Mode (Local & Cloud R2)
    │   ├── config.py                       # Tự động nhận diện chế độ LOCAL hoặc CLOUD_R2
    │   ├── r2_uploader.py                  # Upload Cloudflare R2 (S3 API) hoặc gán đường dẫn Local
    │   ├── config_updater.py               # Tự động ghi video mới lên đầu web/config.js + Auto Git Push
    │   ├── publisher.py                    # Bộ điều phối xuất bản video & tạo link đích ?v=ID
    │   └── test_publisher.py               # Bộ 3 Test Case (Cloud R2, Local, End-to-End Module 2 -> 3)
    └── 4_social_poster/                    # [ĐÃ HOÀN THIỆN & PASS 100% TEST CASES] Đăng FB/Threads & Web Admin
        ├── config.py                       # Tự động đồng bộ Cookie & 5 Fanpage từ D:\app\facebook_bot\data
        ├── fb_service.py                   # Đăng Video Teaser lên Fanpage + Tự động bình luận link Web Player
        ├── threads_service.py              # Đăng bài lên Meta Threads + Tự động Reply link Web Player
        ├── poster.py                       # Bộ điều phối đăng đa kênh & quản lý Hàng đợi Social Queue
        ├── admin_server.py                 # Server Web Admin riêng chạy tại http://127.0.0.1:5050
        ├── static/admin.html               # Giao diện Web Admin Quản Trị (Gắn Cookie, Chọn Page, Threads, Queue)
        ├── data/                           # Lưu trữ cấu hình Cookie, Fanpage, Threads, Lịch sử đăng
        └── test_social_poster.py           # Bộ Test Case kiểm thử toàn diện Module 4
```

---

## 3. CHI TIẾT MODULE 4: SOCIAL POSTER & WEB ADMIN RIÊNG BIỆT

### 3.1. Tại sao tách thành Web Admin Riêng (`admin.html` / cổng `5050`)?
* **Bảo mật tuyệt đối:** Trang `web/index.html` là trang công khai trên Vercel / Cloudflare Pages cho khách xem video và nổ cookie Shopee. Toàn bộ phần gắn Cookie Facebook, Page Token, tài khoản Threads và điều khiển Hàng đợi đăng bài được tách riêng sang **Web Admin Quản Trị (`automation/4_social_poster/static/admin.html` hoặc `http://127.0.0.1:5050`)**.
* **Đồng bộ tức thì từ `D:\app\facebook_bot`:**
  * Hệ thống đã tự động copy và nhận diện **Facebook Cookie (`UID: 100007435262523`)** cùng **5 Fanpage sẵn có** của bạn:
    1. `MicroFeast` (`389557840912771`)
    2. `EduTech Solutions` (`953288971202769`)
    3. `Mầm Non Ánh Bình Minh` (`381362311730683`)
    4. `Vựa tôm tươi Văn Quý` (`206330329233037`)
    5. `Trường Mẫu giáo Gia Hào` (`157204847466320`)

### 3.2. Cơ chế Đăng Bài + Tự Động Bình Luận Link (`?v=ID`)
1. **Trên Facebook Fanpage (`fb_service.py`):**
   * Tải video Teaser (`_teaser.mp4`) kèm `social_caption` lên Fanpage qua Graph API `/videos`.
   * Ngay khi nhận được `post_id`, tự động gọi `/comments` để bình luận:
     `👉 Xem trọn vẹn bản Full HD không che tại đây: https://zento-web-five.vercel.app/?v=<id>`
2. **Trên Meta Threads (`threads_service.py`):**
   * Tạo bài đăng Threads kèm video/caption.
   * Tự động tạo bình luận trả lời (`reply_to_id`) ngay dưới bài Threads vừa đăng chứa link Web Player.

---

## 4. CHI TIẾT MODULE 1: TELEGRAM COLLECTOR & AUTO AFFILIATE CONTROL CENTER

### 4.1. Vai Trò Cốt Lõi Trong Hệ Thống Auto Video Affiliate 24/7
Module 1 không phải là shop bán tài khoản, mà là **Trạm Thu Thập Video & Bảng Điều Khiển Tự Động Hóa Từ Xa** qua Telegram:
1. **Thu Thập Video Tự Động (Video Collector):**
   * **Gửi/Forward video vào Bot:** Admin chỉ cần gửi hoặc forward video từ bất kỳ channel TikTok/Reels/Telegram nào vào Bot $\rightarrow$ Bot tự động nhận diện file `.mp4`, kiểm tra trùng lặp qua `file_unique_id`, lưu vào `storage/1_raw/`.
   * **Chế độ Auto 24/7:** Khi bật chế độ `auto_pipeline_on_receive: True`, ngay khi nhận video thô, hệ thống tự động kích hoạt ngầm **Module 2 (AI Video Factory) $\rightarrow$ Module 3 (Web Publisher) $\rightarrow$ Module 4 (Social Poster)** mà admin không cần thao tác thêm!
   * **Lắng nghe Channel công khai (`channel_scraper.py`):** Dùng Telethon Client để tự động cào video mới từ các channel nguồn công khai.
2. **Bảng Điều Khiển Trực Quan Trên Telegram (Control Center):**
   * Thiết kế giao diện nút bấm Inline Keyboard tương tác xịn sò chuẩn phong cách Telegram Bot hiện đại:
     * `[🔥 KÍCH HOẠT AUTO PIPELINE (M2 ➔ M4)]`: Chạy render toàn bộ kho video thô sang Web & Social Teasers.
     * `[📥 Kho Video Thô]` / `[🌐 Kho Web Full]` / `[📱 Hàng Đợi Social]`: Xem danh sách và số lượng video ở từng khoang lưu trữ.
     * `[🟢 Auto 24/7: BẬT / 🟡 Duyệt thủ công]`: Nút bấm chuyển đổi nhanh chế độ tự động hoặc thủ công.
     * `[📢 Đăng Kênh Telegram]`: Đăng video teaser 9:16 trực tiếp lên Telegram Channel của admin kèm nút bấm mở Web Player (`?v=ID`) để ăn hoa hồng!
     * `[🎬 Mở Web Player Xem Thử]`: Nút liên kết trực tiếp xem trang phát video thực tế.

### 4.2. Tính Năng Tải Tự Động Từ Link Đa Nền Tảng Vào Pipeline (`url_downloader.py`)
Hệ thống hỗ trợ nạp video tự động từ bất kỳ liên kết nào qua 3 cổng giao tiếp:
1. **Qua Telegram Bot (`bot_service.py`):**
   * Người dùng chỉ cần dán/gửi link Facebook Page, Group, Reel, Watch, TikTok, YouTube Shorts vào chat với Bot.
   * Bot tự động nhận diện URL $\rightarrow$ Tải video về `storage/1_raw/` $\rightarrow$ Đẩy thẳng vào AI Video Factory (M2) $\rightarrow$ Xuất bản Web (M3) $\rightarrow$ Đẩy vào Social Queue (M4)!
2. **Qua Web Admin Quản Trị (`admin.html` / cổng `5050`):**
   * Tích hợp thanh công cụ: *`📥 Nạp Nhanh Video Từ Link (Facebook Page, Group, Reel, TikTok, YouTube)`*.
   * Dán link và bấm **"⚡ Tải & Chạy Pipeline"** $\rightarrow$ Hệ thống tự cào và làm mới hàng đợi trong 3 giây.
3. **Qua Dòng Lệnh CLI (`url_downloader.py`):**
   * Chạy lệnh: `python automation/1_telegram_collector/url_downloader.py <URL> [--max N]`
   * Tự động chuyển đổi Cookie Facebook sang chuẩn Netscape (`fb_cookies.txt`) để vượt qua các rào cản đăng nhập của Facebook khi tải video từ Group kín hoặc Page.

---

## 5. NHẬT KÝ CẬP NHẬT & SỬA ĐỔI (CHANGELOG)

### [2026-11-17 17:36] - Chuyển Đổi 100% Liên Kết Sang Tên Miền Thương Hiệu `shp.tho-hoantien.com`
* **Chuẩn hóa định dạng liên kết theo đúng hệ thống Thỏ Hoàn Tiền:**
  * Toàn bộ link trên Web Player (`primaryUrl`, `backupUrl`, `voucherDealUrl`, toàn bộ Deals và Flash Products) đã được chuyển đổi trực tiếp qua API chính thức:
    * Ví dụ: `https://shp.tho-hoantien.com/vtOWH1`, `https://shp.tho-hoantien.com/y8N7JE`, `https://shp.tho-hoantien.com/mRXrmG`...
  * **Cơ chế Silent Redirect (Ẩn Referrer):**
    * Khi người dùng click, domain `shp.tho-hoantien.com` tự động render trang chuyển hướng ẩn danh (`<meta name="referrer" content="no-referrer">`) trước khi đưa người dùng vào ứng dụng Shopee.
    * Đảm bảo tính bảo mật, chuyên nghiệp tuyệt đối cho thương hiệu và 100% hoa hồng hoàn tiền gắn chặt với tài khoản `phuquang04072001@gmail.com` (`vid_30a2abe6e6`).

### [2026-11-17 17:32] - Thanh Lọc 100% Mã Giới Thiệu: Xóa Sổ Hoàn Toàn nghien.co & Mã Bên Thứ Ba
* **Cam kết bảo toàn hoa hồng cho User:**
  * Bổ sung hàm `sanitize_shopee_origin_url()`: Tẩy sạch toàn bộ các tham số rác bám theo link gốc như: `an_...`, `mmp_pid`, `uls_trackid`, `utm_campaign`, `utm_content`, `utm_medium`, `utm_source`, `utm_term`, `sub_id`, `sub_id1`..`sub_id5`, `share_user_id`, `viewer`, `stm_source`, `stm_medium`.
  * **Xóa sổ 100% dấu vết của `nghien.co`, `noti.sale`:**
    * Link gốc (`origin_link`) chỉ còn duy nhất đường dẫn sản phẩm/sự kiện nguyên bản của Shopee (`https://shopee.vn/m/ma-giam-gia`, `https://shopee.vn/flash_sale`, `https://live.shopee.vn/universal-link/share?session=...`).
    * Tham số Affiliate DUY NHẤT tồn tại trên toàn bộ đường dẫn là:
      * `affiliate_id=17395210573` (Cổng Shopee Affiliate của Thỏ Hoàn Tiền).
      * `sub_id={campaign}-vid_30a2abe6e6` (Mã định danh riêng gắn chặt với email `phuquang04072001@gmail.com`).
    * **Đảm bảo 100% doanh số và hoa hồng hoàn tiền chỉ chảy về tài khoản Thỏ Hoàn Tiền của bạn**, không chia sẻ hay thất thoát bất kỳ % nào cho kênh nguồn.

### [2026-11-17 17:28] - Bắt Trúng Căn Nguyên Gốc Gây Link Die (error_page) & Kiểm Thử Live 10/10 Sống 100%
* **Căn nguyên kỹ thuật gây lỗi `error_page` (mkt single page application):**
  * Kênh Telegram `@nghiensandeal` thường chia sẻ cả link Lazada và TikTok Shop thông qua các link rút gọn trung gian như `https://nghien.co/iHtXci` hay `https://noti.sale/post/59055`.
  * Khi bộ convert bọc link rút gọn này vào cổng điều hướng Shopee (`https://s.shopee.vn/an_redir?origin_link=...`), máy chủ Shopee kiểm tra thấy tên miền gốc **không thuộc `*.shopee.vn`**, do đó Shopee lập tức từ chối và hiển thị màn hình lỗi `https://shope.ee/error_page`.
* **Biện pháp xử lý triệt để:**
  * Hàm `validate_and_expand_url()` bắt buộc phải giải mã link rút gọn tới **URL đích thực tế cuối cùng**.
  * Chỉ các URL đích thực sự thuộc hệ sinh thái Shopee (`shopee.vn`, `live.shopee.vn`, `shp.ee`) mới được phép đưa vào cổng `an_redir`.
  * Mọi bài viết dẫn sang Lazada, TikTok hoặc link không xác định đều được tự động chuyển hướng sang các trang sự kiện Shopee chính thức vĩnh cửu (`/m/ma-giam-gia`, `/flash_sale`).
  * Tích hợp hàm `verify_affiliate_link_health()`: Tự động chạy HTTP request kiểm tra thực tế link sau khi sinh, nếu có bất kỳ dấu hiệu `error_page` nào sẽ tự động thay thế ngay.
* **Kết quả kiểm thử thực tế (Live Test):**
  * Đã quét trực tiếp toàn bộ 10 liên kết trên Web Player.
  * **10/10 liên kết ĐẠT CHUẨN 200 OK**, chuyển hướng trực tiếp về app/web Shopee có gắn đầy đủ mã hoa hồng `an_17395210573` và `vid_30a2abe6e6` của user. **0 link die!**

### [2026-11-17 17:22] - Chuẩn Hóa Content Voucher/Deal & Khớp Ảnh Sản Phẩm Thông Minh
* **Chuẩn hóa nội dung Voucher:**
  * Xử lý cắt bỏ các ký tự dấu ngoặc kép, dấu mũi tên `→`, từ điều hướng thừa (`kéo xuống...`).
  * Chuẩn hóa thành các tiêu đề marketing bắt mắt: *Voucher Shopee VIP Giảm 25% Đơn 0Đ*, *Voucher Giảm 50% Tối Đa 100K Toàn Sàn*...
  * Thêm cơ chế `seen_voucher_titles` loại bỏ hoàn toàn tình trạng 2 thẻ voucher trùng lặp hiển thị cạnh nhau.
* **Khớp ảnh sản phẩm thông minh theo danh mục (`get_smart_product_image`):**
  * Tự động nhận diện ngành hàng từ tên sản phẩm để gán ảnh đại diện Unsplash chất lượng cao:
    * Mỹ phẩm / Skincare (Cocoon, serum, nước hoa hồng) $\rightarrow$ Gán ảnh chai tinh chất mỹ phẩm sang trọng.
    * Đồ gia dụng / Nước giặt $\rightarrow$ Gán ảnh gia dụng.
    * Công nghệ (Tai nghe, Sạc, Pin) $\rightarrow$ Gán ảnh thiết bị công nghệ.
  * Chuẩn hóa giá tiền hiển thị sang định dạng tiền Việt Nam (`269.000đ` thay vì `269K`).
* **Đồng bộ tự động:** Toàn bộ liên kết đều tiếp tục gắn mã hoa hồng hoàn tiền `vid_30a2abe6e6` (`phuquang04072001@gmail.com`).

### [2026-11-17 17:20] - Xử Lý Link Trang Chủ Fanpage Facebook (`/tintucvtv24/`) & Hướng Dẫn Định Dạng Chuẩn
* **Hiện tượng:** Người dùng gửi link trang chủ Fanpage VTV24 (`https://www.facebook.com/tintucvtv24/`) khiến yt-dlp báo lỗi `Unsupported URL`.
* **Nguyên nhân kỹ thuật:**
  * Facebook áp dụng cơ chế cuộn feed vô tận (infinite dynamic feed) bằng GraphQL React có xác thực bảo mật khắt khe. Các công cụ tải video (yt-dlp) không thể tự động bóc tách video từ đường dẫn Trang chủ Fanpage chung nếu không có ID bài viết hoặc ID video cụ thể.
* **Cải tiến trong `url_downloader.py` & `bot_service.py`:**
  * Thêm hàm `is_bare_facebook_page()` phát hiện ngay lập tức khi người dùng vô tình dán link Trang chủ Fanpage hoặc Profile cá nhân.
  * Bot tự động phản hồi thông báo hướng dẫn trực quan:
    * Mở video/Reel cần tải trên Fanpage.
    * Bấm nút **Chia sẻ** (Share) $\rightarrow$ **Sao chép liên kết** (Copy link).
    * Hỗ trợ 100% các định dạng video chuẩn: `/reel/...`, `/watch/?v=...`, `/videos/...`, `/share/r/...`, `/share/v/...`.

### [2026-11-17 17:14] - Tự Động Hóa Quét Deal Mỗi 15 Phút & Bộ Lọc Chống Link Die (error_page) 100%
* **Khắc phục lỗi dính link die (`shope.ee/error_page` / MKT Single Page Application):**
  * **Nguyên nhân:** Regex cào từ text Telegram từng bắt nhầm ký tự dấu câu bám đuôi (ví dụ `https://shp.ee/eziuej7m=`), khiến Shopee từ chối và trả về trang `error_page` 404.
  * **Giải pháp `validate_and_expand_url()`:**
    1. Làm sạch triệt để các ký tự rác bám đuôi URL (`=`, `>`, `)`, `]`, `.`, `?`, `;`, `#`...).
    2. Gửi request HTTP kiểm tra thực tế (HTTP 200 OK). Nếu phản hồi có mã $\ge 400$, chuyển hướng về `error_page` hoặc chứa chuỗi `mkt single page application`, hệ thống lập tức loại bỏ ngay!
    3. Tự động fallback sang các trang sự kiện chính thức vĩnh viễn không chết của Shopee (`/m/ma-giam-gia`, `/flash_sale`, `/m/mien-phi-van-chuyen`, `/m/hoan-xu-extra`).
* **Vòng lặp tự động cập nhật mỗi 15 phút (900 giây):**
  * Tích hợp daemon `run_15m_daemon()` và `start_daemon_background_thread()`.
  * Tự động chạy nền ngay khi `bot_service.py` khởi động, hoặc có thể chạy độc lập qua lệnh `python automation/deal_voucher_service.py --daemon`.
  * Cập nhật thời gian thực `lastUpdated` trong [config.js](file:///d:/web_aff/web/config.js).

### [2026-11-17 17:08] - Tích Hợp Thành Công Bộ Cào Deal/Voucher Telegram & Gắn 100% Tracking Aff tho-hoan-tien
* **Xây dựng module `automation/deal_voucher_service.py`:**
  * **Nguồn cào:** Tự động quét kênh Telegram công khai `https://t.me/s/nghiensandeal`.
  * **Phân loại thông minh:** Bóc tách riêng **Kho Voucher** (mã toàn sàn, freeship, hoàn xu) và **Sản phẩm Flash Deal 1K-9K**.
  * **Chuyển đổi Affiliate qua `tho-hoan-tien`:**
    * Gọi trực tiếp API backend live `https://tho-hoan-tien-backend.onrender.com/api/convert` (hoặc thuật toán sinh sub_id nội bộ).
    * Email gắn kết: `phuquang04072001@gmail.com` $\rightarrow$ sinh mã định danh tracking duy nhất: `vid_30a2abe6e6`.
    * Cấu trúc link aff Shopee: `https://s.shopee.vn/an_redir?origin_link=...&affiliate_id=17395210573&sub_id={prefix}-vid_30a2abe6e6`.
  * **Đồng bộ vào Web Player:**
    * Đã ghi nhận thành công vào [config.js](file:///d:/web_aff/web/config.js) và [videos_db.json](file:///d:/web_aff/web/videos_db.json).
    * Toàn bộ 4 voucher cột trái, 3 sản phẩm flash sale, cùng 3 link chính `primaryUrl`, `backupUrl`, `voucherDealUrl` (dùng để thả cookie khi bấm xem video) đều đã được gắn mã hoa hồng hoàn tiền `vid_30a2abe6e6` của user.

### [2026-11-17 17:01] - Sửa Triệt Để Lỗi Trùng Lặp Video Trên Web Player & Chuẩn Hóa Bộ Nhớ Cache
* **Nguyên nhân gây lặp video trên Web Player (`index.html`):**
  1. **Lặp do key `'default'`:** `config_updater.py` sao chép video mới vào cả key `id` lẫn key `'default'`. Khi `app.js` duyệt toàn bộ danh sách `videoKeys`, cả 2 thẻ này đều được render ra giao diện khiến clip mới nhất (như *Nạp 6.6 triệu chơi app đỏ đen...*) bị hiển thị 2 lần liên tiếp.
  2. **Lặp do video mẫu test cũ:** Các file thử nghiệm ban đầu (`chao_co`, `duck_mukkbang`, `dog_mukkbang`, `sample_test_01`, `cat_ai_voice_demo`) đều có chung tiêu đề mặc định *"Cận cảnh diễn biến vụ việc đang gây xôn xao mạng xã hội..."* khiến cột bên phải xuất hiện 5-6 dòng giống hệt nhau.
  3. **Lặp do tên file tải về:** `url_downloader.py` từng đặt tên file đính kèm `timestamp` khiến cùng một video tải 2 lần ở thời điểm khác nhau sẽ mang tên khác nhau.
* **Các bước khắc phục triệt để:**
  1. **Nâng cấp `web/assets/js/app.js`:**
     * Thêm bộ lọc `const videoKeys = Object.keys(CONFIG.videos || {}).filter(k => k !== "default");` loại bỏ hoàn toàn mục trùng `'default'`.
     * Bổ sung cơ chế `Set(seenUrls)` trong cả `renderSuggestedVideos()` và `renderTrendingSidebar()` để chống hiển thị lặp ngay từ tầng UI (bảo vệ 2 lớp).
  2. **Sửa `automation/3_web_publisher/config_updater.py`:**
     * Đưa video mới lên đầu danh sách `new_videos_ordered`, chỉ giữ `'default'` ở cuối cùng làm con trỏ dự phòng chứ không chiếm slot trong danh sách bài phát.
  3. **Sửa `automation/1_telegram_collector/url_downloader.py`:**
     * Đổi mẫu lưu file sang chuẩn `vid_%(extractor_key)s_%(id)s.%(ext)s` (không chứa timestamp ngẫu nhiên), kết hợp `download_archive` của yt-dlp để chặn tải trùng.
  4. **Dọn sạch `web/config.js` & `web/videos_db.json`:**
     * Loại bỏ toàn bộ các clip rác mock test cũ, chỉ giữ 6 video chất lượng cao thực tế đã phân tích đầy đủ bởi Gemini AI.

* Bổ sung hàm `trigger_web_publisher()` trong `automation/2_ai_video_factory/factory.py`:
  * Ngay khi Gemini AI và FFmpeg render xong video, tự động kích hoạt Module 3 (`publisher.py`) để đồng bộ ngay video mới vào `web/config.js` và `web/videos_db.json`.
  * Đã đồng bộ thành công cả 12 video (bao gồm cả clip cào từ TikTok `dl_20261117_162009_7708668189600730388` và `duck_mukkbang`) lên đầu danh sách Web Player.

### [2026-11-17 16:04] - Bổ sung Tính Năng Cào Video từ Link Facebook Group, Page, Reel, TikTok vào Pipeline
* Xây dựng `automation/1_telegram_collector/url_downloader.py`:
  * Tận dụng `yt-dlp` (2026.08.19) kết hợp bộ chuyển đổi Cookie Facebook Netscape.
  * Hỗ trợ tải video đơn (Reel, Watch, Shorts) hoặc tải hàng loạt từ Page, Group.
  * Tự động kích hoạt ngầm `factory.py` (Module 2 -> 3 -> 4) ngay sau khi tải xong.
* Tích hợp vào **Telegram Bot (`bot_service.py`)**: Tự động bắt link text trong tin nhắn chat và xử lý nền async.
* Tích hợp vào **Web Admin (`admin.html` & `admin_server.py`)**: Thêm thanh nạp nhanh link và endpoint `/api/collector/download-url`.
* Chạy kiểm thử tự động `test_url_downloader.py` và `test_telegram_module.py` đạt **100% PASS**.

### [2026-11-17 15:43] - Điều chỉnh Chuẩn Hóa Module 1: Tập trung 100% vào Hệ Thống Auto Video Affiliate
* Loại bỏ phần shop bán tài khoản/phần mềm không liên quan, định hình đúng bản chất Module 1:
  * `automation/1_telegram_collector/config.py`: Quản lý khoang lưu trữ `1_raw`, `2_web_full`, `3_social_teaser`, chống trùng lặp và lưu cài đặt vận hành `system_settings.json`.
  * `automation/1_telegram_collector/bot_ui.py`: Bảng điều khiển Inline Keyboard trung tâm (Chạy pipeline, duyệt khoang video, hàng đợi Social, bật/tắt Auto 24/7, đăng Channel).
  * `automation/1_telegram_collector/bot_service.py`: Tự động tải video vào `1_raw` và tự động kích hoạt AI Video Factory.
  * `automation/1_telegram_collector/channel_scraper.py`: Telethon worker tự động cào video từ Channel công khai.
  * `automation/1_telegram_collector/run_demo.py`: Trình mô phỏng giao diện Bảng điều khiển Telegram trên máy tính.
  * `automation/1_telegram_collector/test_telegram_module.py`: Bộ kiểm thử 4 Test Cases đạt **100% PASS** trong `0.014s`.

### [2026-11-17 15:24] - Bổ sung Bộ Lập Lịch Tự Động 24/7 (`scheduler_daemon.py`) & Xử lý Token Hết Hạn
* **Thêm `scheduler_daemon.py` chạy ngầm 24/7:**
  * Hỗ trợ **3 cơ chế tự động đăng bài** mà không cần người dùng bấm tay:
    1. **Theo Khung Giờ Vàng mỗi ngày (`time_slots`):** Mặc định `08:00, 11:30, 17:30, 20:30` $\rightarrow$ Cứ đến giờ là tự bốc 1 video trong `Social Queue` đi đăng lên Fanpage & Threads + tự động bình luận link.
    2. **Theo Chu Kỳ Giãn Cách (`interval`):** Cứ mỗi `X phút` (ví dụ 60 phút) tự động đăng 1 bài.
    3. **Hẹn giờ riêng cho từng Video (`scheduled_at`):** Chọn ngày giờ cụ thể ngay trên từng dòng video trong Queue.
* **Xử lý thông báo Token Facebook hết hạn (Mã lỗi 190 / Subcode 463):**
  * Token cũ từ ngày 13/11 trong `facebook_bot` đã hết hạn phiên $\rightarrow$ Bổ sung thông báo hướng dẫn trực quan trên trang Admin để dán Token mới từ Graph API Explorer chỉ với 1 nút bấm **"Cập nhật Token"**.

### [2026-11-17 15:14] - Hoàn thành Module 4 (`4_social_poster`) & Web Admin Riêng
* Xây dựng trọn bộ `config.py`, `fb_service.py`, `threads_service.py`, `poster.py`, `admin_server.py` và giao diện `static/admin.html`.
* Tự động đồng bộ Cookie Facebook và 5 Fanpage từ `D:\app\facebook_bot\data\`.
* Chạy kiểm thử `test_social_poster.py` đạt **100% PASS cả 3 Test Cases**:
  * **Test 1:** Kết nối thành công Cookie (`UID: 100007435262523`) & nạp đủ 5 Fanpage.
  * **Test 2:** Nạp thành công 9 video đã xuất bản vào Hàng đợi `Social Queue`.
  * **Test 3:** Đăng thử nghiệm thành công video `animal_live_show` lên Fanpage `MicroFeast` và `Threads`, tự động thả comment link `https://zento-web-five.vercel.app/?v=animal_live_show` ngay dưới bài đăng!
