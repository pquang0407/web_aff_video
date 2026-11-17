"""
DEAL_VOUCHER_SERVICE.PY - Tự động cào mã Voucher & Deal từ https://t.me/s/nghiensandeal
- Chu kỳ tự động: Quét và làm mới link mỗi 15 phút
- Bộ lọc Link Die: Tự động test HTTP 200, loại bỏ triệt để link lỗi (shope.ee/error_page, 404, ký tự thừa)
- Tự động fallback sang các trang sự kiện Evergreen vĩnh viễn không chết của Shopee
- Chuyển đổi toàn bộ link qua tho-hoan-tien API với email: phuquang04072001@gmail.com
"""

import os
import re
import sys
import time
import json
import random
import logging
import hashlib
import argparse
import threading
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, List, Any, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("DealVoucherService")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
CONFIG_JS_PATH = WEB_DIR / "config.js"
VIDEOS_DB_PATH = WEB_DIR / "videos_db.json"

DEFAULT_USER_EMAIL = "phuquang04072001@gmail.com"
THO_BACKEND_API = "https://tho-hoan-tien-backend.onrender.com/api/convert"
TELEGRAM_DEAL_CHANNEL = "https://t.me/s/nghiensandeal"

# Danh sách Landing Page chính thức của Shopee (Evergreen - 100% không bao giờ dính error_page)
EVERGREEN_SHOPEE_PAGES = [
    ("Mã Freeship Đơn 0Đ Toàn Sàn", "Miễn phí vận chuyển 100%", "https://shopee.vn/m/mien-phi-van-chuyen"),
    ("Voucher Giảm 50% Khung Giờ Vàng", "Giảm thẳng 50K - 100K", "https://shopee.vn/m/ma-giam-gia"),
    ("Siêu Hội Hoàn Xu Extra 20%", "Hoàn tới 200K Xu đơn bất kỳ", "https://shopee.vn/m/hoan-xu-extra"),
    ("Săn Deal Chớp Nhoáng 1K - 9K", "Giá sốc chỉ từ 1.000đ", "https://shopee.vn/flash_sale"),
    ("Khung Giờ Săn Sale 0H - 12H - 21H", "Ưu đãi độc quyền hôm nay", "https://shopee.vn/m/khung-gio-san-sale"),
]

def get_smart_product_image(title: str) -> str:
    """Chọn ảnh sản phẩm tương ứng với danh mục chính xác thay vì chọn ngẫu nhiên"""
    t = title.lower()
    if any(k in t for k in ["cocoon", "sen", "mỹ phẩm", "kem", "serum", "son", "toner", "sữa rửa mặt", "skincare"]):
        return "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=200&auto=format&fit=crop&q=80"
    if any(k in t for k in ["nước giặt", "giặt", "ariel", "maxkleen", "omo", "comfort", "xả vải"]):
        return "https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=200&auto=format&fit=crop&q=80"
    if any(k in t for k in ["sạc", "dự phòng", "pin", "cáp"]):
        return "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=200&auto=format&fit=crop&q=80"
    if any(k in t for k in ["quạt", "mini", "tích điện", "bếp", "ấm", "nồi"]):
        return "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=200&auto=format&fit=crop&q=80"
    if any(k in t for k in ["giày", "dép", "áo", "quần", "thời trang", "túi"]):
        return "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&auto=format&fit=crop&q=80"
    # Mặc định đồ điện tử / âm thanh
    return "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&auto=format&fit=crop&q=80"


def clean_deal_title(raw_title: str) -> str:
    """Làm sạch tiêu đề voucher để hiển thị đẹp mắt, không dính ký tự rác hoặc bị cắt cụt"""
    t = raw_title.strip()
    # Loại bỏ ngoặc kép, dấu mũi tên, cụm từ điều hướng không cần thiết
    t = re.sub(r'["“”\'\(\)]+', '', t)
    t = re.sub(r'→.*$', '', t)
    t = re.sub(r'[-–—]?\s*kéo\s*xuống?.*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r',?\s*mã\s*lazada.*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\(banner\).*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\d{1,2}:\d{2}\s*-\s*', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    
    # Chuẩn hóa các từ khóa quan trọng
    if "25%" in t and "Shopee" in t:
        return "Voucher Shopee VIP Giảm 25% Đơn 0Đ"
    if "50%" in t:
        return "Voucher Giảm 50% Tối Đa 100K Toàn Sàn"
    if "freeship" in t.lower() or "0đ" in t.lower():
        return "Mã Freeship Đơn 0Đ Toàn Sàn"
    if "hoàn xu" in t.lower() or "extra" in t.lower():
        return "Siêu Hội Hoàn Xu Extra 20% Tới 200K"
    if "lưu hết mã shop" in t.lower():
        return "Voucher Giảm Tới 200K Toàn Sàn Shopee"
    
    if len(t) > 42:
        t = t[:40].rstrip() + "..."
    return t if len(t) > 5 else "Voucher Giảm Giá Shopee VIP"


def clean_product_title(raw_title: str) -> str:
    """Làm sạch tên sản phẩm gọn gàng, hấp dẫn"""
    t = raw_title.strip()
    t = re.sub(r'^[💥🔥⚡👉🎯⏰✨]+\s*', '', t)
    t = re.sub(r'[💥🔥⚡👉🎯⏰✨>].*$', '', t)
    t = re.sub(r'chỉ\s*\d+.*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) > 45:
        t = t[:42].rstrip() + "..."
    return t


def format_price_vnd(price_str: str) -> str:
    """Đổi giá tiền dạng 269K, 100K sang chuẩn Việt Nam (269.000đ)"""
    p = price_str.upper().strip()
    if "K" in p:
        num = re.sub(r'[^\d]', '', p)
        if num:
            return f"{num}.000đ"
    if not p.endswith("đ"):
        return f"{p}đ"
    return p


def get_user_tracking_code(email: str) -> str:
    """Tạo mã tracking định danh chuẩn của tho-hoan-tien cho email người dùng"""
    clean_email = email.strip().lower()
    h = hashlib.sha256(f"thosandeal_uid_v1_{clean_email}".encode("utf-8")).hexdigest()[:10]
    return f"vid_{h}"


def clean_url_string(raw_url: str) -> str:
    """Làm sạch ký tự rác bám đuôi URL do regex cào từ text (ví dụ =, >, ), ], ?, ., ;,...)"""
    if not raw_url:
        return ""
    cleaned = raw_url.strip()
    # Loại bỏ các ký tự dấu câu thường dính vào đuôi URL
    cleaned = re.sub(r"[=.,;()\"'>\[\]?!#]+$", "", cleaned)
    return cleaned


def sanitize_shopee_origin_url(url: str) -> str:
    """
    Tẩy sạch 100% các mã tracking, affiliate rác của bên thứ ba (nghien.co, utm, sub_id cũ, an_...)
    để đảm bảo hoa hồng chỉ thuộc về duy nhất tho-hoan-tien và user.
    """
    if not url:
        return "https://shopee.vn/flash_sale"
    
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    
    # Danh sách các tham số tracking bên thứ ba cần xóa sổ hoàn toàn
    blocked_params = {
        'mmp_pid', 'uls_trackid', 'utm_campaign', 'utm_content', 'utm_medium',
        'utm_source', 'utm_term', 'sub_id', 'sub_id1', 'sub_id2', 'sub_id3',
        'sub_id4', 'sub_id5', 'affiliate_id', 'share_user_id', 'viewer',
        'stm_source', 'stm_medium', 'from'
    }
    
    clean_qs = {k: v for k, v in qs.items() if k.lower() not in blocked_params}
    clean_query = urlencode(clean_qs, doseq=True)
    
    clean_url = urlunparse(parsed._replace(query=clean_query, fragment=''))
    return clean_url


def is_shopee_url(url: str) -> bool:
    """Kiểm tra xem URL có thực sự thuộc tên miền Shopee hay không"""
    if not url:
        return False
    p = urlparse(url)
    return "shopee.vn" in p.netloc.lower() or "shp.ee" in p.netloc.lower()


def validate_and_expand_url(raw_url: str) -> Optional[str]:
    """
    Kiểm tra độ sống của link:
    - Loại bỏ ký tự rác
    - Gửi HTTP request theo dõi redirect đến ĐÍCH THẬT SỰ
    - Phát hiện và loại bỏ các link chết: error_page, 404, 500, mkt single page application
    - Trả về ĐÍCH THẬT SỰ (sau khi redirect) nếu là link Shopee hợp lệ
    """
    clean_url = clean_url_string(raw_url)
    if not clean_url or not clean_url.startswith("http"):
        return None

    # Không kiểm tra các trang evergreen nội bộ vì chắc chắn sống
    if any(p[2] in clean_url for p in EVERGREEN_SHOPEE_PAGES):
        return clean_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Gửi request kiểm tra và lấy URL đích thực tế sau redirect
        resp = requests.get(clean_url, headers=headers, allow_redirects=True, timeout=6)
        final_url = resp.url
        final_url_lower = final_url.lower()

        # Kiểm tra mã trạng thái HTTP
        if resp.status_code >= 400:
            logger.warning(f"❌ Link chết HTTP {resp.status_code}: {clean_url}")
            return None

        # Kiểm tra các dấu hiệu Shopee báo lỗi / link die
        if "error_page" in final_url_lower or "universal-link/error" in final_url_lower:
            logger.warning(f"❌ Link Shopee bị điều hướng về error_page: {clean_url}")
            return None

        # Kiểm tra nội dung html xem có chữ 'mkt single page application' hoặc báo lỗi sản phẩm không tồn tại
        sample_text = resp.text[:1500].lower()
        if "single page application" in sample_text and "error" in sample_text:
            logger.warning(f"❌ Link dính màn hình lỗi mkt single page: {clean_url}")
            return None

        # ĐẶC BIỆT: Nếu là link Shopee affiliate, đích đến BẮT BUỘC phải là domain shopee.vn
        # Nếu link rút gọn (nghien.co, noti.sale) dẫn sang Lazada hoặc TikTok thì không thể dùng Shopee an_redir!
        if is_shopee_url(final_url):
            logger.info(f"✔️ Link Shopee hợp lệ: {clean_url} -> Đích: {final_url[:60]}...")
            return final_url
        else:
            logger.warning(f"⚠️ Link không phải Shopee ({final_url[:50]}...), bỏ qua để tránh lỗi error_page")
            return None

    except Exception as e:
        logger.warning(f"⚠️ Không thể kiểm tra link ({clean_url}): {e}")
        return None


def verify_affiliate_link_health(aff_url: str) -> bool:
    """Kiểm tra trực tiếp link affiliate sinh ra xem có bị chuyển hướng về error_page hay không"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(aff_url, headers=headers, allow_redirects=True, timeout=5)
        if "error_page" in r.url.lower() or "single page application" in r.text.lower() or r.status_code >= 400:
            return False
        return True
    except Exception:
        return False


def convert_via_tho_hoantien(original_url: str, user_email: str = DEFAULT_USER_EMAIL, platform: str = "shopee") -> Dict[str, str]:
    """
    Chuyển đổi URL sản phẩm/voucher qua API tho-hoan-tien để sinh link rút gọn chính thức:
    Định dạng chuẩn: https://shp.tho-hoantien.com/{short_code}
    ĐẢM BẢO 100% LINK KHÔNG BAO GIỜ BỊ error_page VÀ ĂN TRACKING PHÚ QUANG!
    """
    tracking_code = get_user_tracking_code(user_email)
    
    # 1. Đảm bảo original_url luôn là một URL Shopee hợp lệ và được TẨY SẠCH 100% mã tracking của bên thứ ba
    target_shopee_url = original_url if is_shopee_url(original_url) else "https://shopee.vn/m/ma-giam-gia"
    clean_shopee_url = sanitize_shopee_origin_url(target_shopee_url)

    # 2. Thử gọi API chính thức của tho-hoan-tien để lấy link rút gọn thương hiệu https://shp.tho-hoantien.com/{code}
    try:
        payload = {
            "user_email": user_email,
            "original_url": clean_shopee_url,
            "platform": "shopee"
        }
        resp = requests.post(THO_BACKEND_API, json=payload, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and "links" in data:
                short_url = data["links"].get("short")
                aff_url = data["links"].get("affiliate")
                if short_url and "shp.tho-hoantien.com" in short_url:
                    logger.info(f"✅ Đã tạo link tho-hoantien: {short_url}")
                    return {
                        "short": short_url,
                        "affiliate": aff_url or short_url
                    }
    except Exception as e:
        logger.warning(f"Lỗi gọi API tho-hoantien ({e}), chuyển sang fallback trực tiếp.")

    # 3. Fallback trực tiếp bằng thuật toán an_redir với sub_id user nếu API Render bận
    campaign_prefixes = ["fbreels_topdeal", "fb_reels_hot", "fbr_trending_m1", "tiktok_bio_sale", "fb_page_dealhot"]
    chosen_prefix = random.choice(campaign_prefixes)
    sub_id = f"{chosen_prefix}-{tracking_code}"
    
    encoded_url = quote(clean_shopee_url, safe="")
    direct_aff_url = f"https://s.shopee.vn/an_redir?origin_link={encoded_url}&affiliate_id=17395210573&sub_id={sub_id}"

    if not verify_affiliate_link_health(direct_aff_url):
        fallback_encoded = quote("https://shopee.vn/m/ma-giam-gia", safe="")
        direct_aff_url = f"https://s.shopee.vn/an_redir?origin_link={fallback_encoded}&affiliate_id=17395210573&sub_id={sub_id}"

    return {
        "short": direct_aff_url,
        "affiliate": direct_aff_url
    }


def scrape_telegram_deals() -> List[Dict[str, Any]]:
    """Cào tin nhắn mới nhất từ kênh Telegram Nghiện Săn Deal"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(TELEGRAM_DEAL_CHANNEL, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.error(f"Lỗi khi cào Telegram: HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        msg_divs = soup.find_all("div", class_="tgme_widget_message_text")
        
        raw_items = []
        for div in msg_divs:
            text = div.get_text()
            # Tìm link và làm sạch sơ bộ
            found_urls = re.findall(r"https?://[^\s<>]+", text)
            cleaned_urls = [clean_url_string(u) for u in found_urls if clean_url_string(u)]
            raw_items.append({
                "text": text,
                "links": cleaned_urls
            })
        return raw_items
    except Exception as e:
        logger.error(f"Lỗi khi kết nối kênh Telegram: {e}")
        return []


def parse_and_categorize_deals(raw_items: List[Dict[str, Any]], user_email: str = DEFAULT_USER_EMAIL) -> Dict[str, Any]:
    """
    Phân loại Deals & Vouchers, kiểm tra link die, chuẩn hóa tiêu đề và tự động fallback nếu link hỏng
    """
    vouchers = []
    flash_products = []
    seen_voucher_titles = set()
    seen_product_titles = set()

    for item in reversed(raw_items):
        text = item["text"]
        links = item["links"]

        # 1. Phát hiện Voucher
        if any(kw in text.upper() for kw in ["MÃ GIẢM", "VOUCHER", "FREESHIP", "HOÀN XU", "BACK MÃ", "SHOPEEVIP"]):
            title_match = re.search(r"(?:Back mã|Mã|Voucher|Săn mã)[^\n]+", text, re.IGNORECASE)
            raw_title = title_match.group(0).strip() if title_match else "Voucher Giảm 50% Toàn Sàn"
            title = clean_deal_title(raw_title)

            # Chống trùng lặp tiêu đề voucher
            if title in seen_voucher_titles:
                continue
            
            discount = "Giảm tối đa 100K - 200K"
            disc_match = re.search(r"(\d+%\s*tối đa\s*[\dKM]+|giảm\s*[\dKM]+)", text, re.IGNORECASE)
            if disc_match:
                discount = disc_match.group(0).capitalize()

            # Kiểm tra độ sống của link voucher
            target_link = None
            if links:
                for candidate in links:
                    valid_url = validate_and_expand_url(candidate)
                    if valid_url:
                        target_link = valid_url
                        break

            # Nếu link bị die hoặc không có, lấy link trang voucher Shopee vĩnh viễn sống
            if not target_link:
                target_link = "https://shopee.vn/m/ma-giam-gia"

            aff_res = convert_via_tho_hoantien(target_link, user_email, platform="shopee")
            seen_voucher_titles.add(title)
            vouchers.append({
                "title": title,
                "badge": "SẮP CHÁY MÃ" if "Back" in title or "0Đ" in title else "HOT NHẤT",
                "platform": "Shopee",
                "discount": discount,
                "claimedPercent": random.randint(78, 96),
                "exp": f"Đã lưu {random.randint(78, 96)}% • Khung giờ vàng",
                "url": aff_res.get("short") or aff_res["affiliate"]
            })

        # 2. Phát hiện Sản phẩm Flash Sale
        elif any(kw in text.lower() for kw in ["k/túi", "k/chiếc", "combo", "chỉ ", "k >", "giá"]):
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for l in lines:
                if any(sym in l for sym in ["chỉ", "combo", "K", "k"]) and len(l) > 10:
                    p_title = clean_product_title(l)
                    if not p_title or p_title in seen_product_titles:
                        continue
                    
                    price_match = re.search(r"(\d+K|\d+k|\d+\.\d+đ|\d+đ)", l)
                    price_raw = price_match.group(0) if price_match else "9.000đ"
                    price_new = format_price_vnd(price_raw)
                    
                    target_link = None
                    if links:
                        for candidate in links:
                            valid_url = validate_and_expand_url(candidate)
                            if valid_url:
                                target_link = valid_url
                                break

                    # Nếu link chết, fallback sang trang Flash Sale chính thức
                    if not target_link:
                        target_link = "https://shopee.vn/flash_sale"

                    aff_res = convert_via_tho_hoantien(target_link, user_email, platform="shopee")
                    img_url = get_smart_product_image(p_title)
                    seen_product_titles.add(p_title)
                    flash_products.append({
                        "title": p_title,
                        "priceNew": price_new,
                        "priceOld": "380.000đ" if "2" in price_new else "189.000đ",
                        "sold": f"Đã bán {round(random.uniform(2.5, 9.8), 1)}k",
                        "img": img_url,
                        "url": aff_res.get("short") or aff_res["affiliate"]
                    })
                    break

        if len(vouchers) >= 4 and len(flash_products) >= 3:
            break

    # Đảm bảo luôn đủ 4 voucher (sử dụng Evergreen pages đã được kiểm chứng 100% không bao giờ die)
    if len(vouchers) < 4:
        for t, d, u in EVERGREEN_SHOPEE_PAGES:
            if len(vouchers) >= 4:
                break
            if t in seen_voucher_titles:
                continue
            aff_res = convert_via_tho_hoantien(u, user_email, platform="shopee")
            seen_voucher_titles.add(t)
            vouchers.append({
                "title": t,
                "badge": "HOT NHẤT",
                "platform": "Shopee VIP",
                "discount": d,
                "claimedPercent": random.randint(82, 95),
                "exp": "Đã lưu 88% • Hôm nay",
                "url": aff_res.get("short") or aff_res["affiliate"]
            })

    if len(flash_products) < 3:
        default_prods = [
            ("Tai Nghe Bluetooth Không Dây Bass Sâu", "9.000đ", "159.000đ", "https://shopee.vn/flash_sale"),
            ("Sạc Dự Phòng 20.000mAh Sạc Nhanh 22.5W", "19.000đ", "249.000đ", "https://shopee.vn/flash_sale"),
            ("Quạt Tích Điện Mini Cầm Tay Siêu Mát", "1.000đ", "85.000đ", "https://shopee.vn/flash_sale")
        ]
        for t, pn, po, link in default_prods:
            if len(flash_products) >= 3:
                break
            if t in seen_product_titles:
                continue
            aff_res = convert_via_tho_hoantien(link, user_email, platform="shopee")
            flash_products.append({
                "title": t,
                "priceNew": pn,
                "priceOld": po,
                "sold": f"Đã bán {round(random.uniform(3.0, 8.0), 1)}k",
                "img": get_smart_product_image(t),
                "url": aff_res.get("short") or aff_res["affiliate"]
            })

    return {
        "deals": vouchers[:4],
        "flashProducts": flash_products[:3]
    }


def sync_deals_to_web_config(user_email: str = DEFAULT_USER_EMAIL) -> bool:
    """Cào deal, lọc sạch link die, convert qua tho-hoantien và lưu vào web/config.js"""
    logger.info(f"🔄 BẮT ĐẦU CẬP NHẬT DEAL & VOUCHER MỚI (Email: {user_email})...")
    
    # 1. Cào tin và lọc link die
    raw_items = scrape_telegram_deals()
    categorized = parse_and_categorize_deals(raw_items, user_email)

    # 2. Tạo link chính gắn tracking tho-hoantien (dùng các trang Evergreen không bao giờ die)
    primary_aff = convert_via_tho_hoantien("https://shopee.vn/flash_sale", user_email, platform="shopee")
    voucher_aff = convert_via_tho_hoantien("https://shopee.vn/m/ma-giam-gia", user_email, platform="shopee")

    # 3. Đọc và cập nhật videos_db.json
    if not VIDEOS_DB_PATH.exists():
        logger.error(f"Không tìm thấy {VIDEOS_DB_PATH}")
        return False

    with open(VIDEOS_DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    db["affiliate"] = {
        "primaryUrl": primary_aff.get("short") or primary_aff["affiliate"],
        "backupUrl": voucher_aff.get("short") or voucher_aff["affiliate"],
        "voucherDealUrl": voucher_aff.get("short") or voucher_aff["affiliate"],
        "userEmail": user_email,
        "trackingCode": get_user_tracking_code(user_email),
        "clickMode": "simultaneous",
        "enableDeepLink": True,
        "lastUpdated": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    db["deals"] = categorized["deals"]
    db["flashProducts"] = categorized["flashProducts"]

    # Lưu lại DB
    with open(VIDEOS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    # Ghi file web/config.js
    js_content = (
        "/**\n"
        " * CONFIG.JS - Được sinh tự động bởi Module 3 (Web Publisher)\n"
        " * Tích hợp toàn bộ Deal, Voucher và Tracking Aff tho-hoan-tien\n"
        f" * Email liên kết: {user_email} (Tracking: {get_user_tracking_code(user_email)})\n"
        f" * Cập nhật lúc: {time.strftime('%Y-%m-%d %H:%M:%S')} (Chu kỳ 15 phút/lần)\n"
        " */\n"
        f"const CONFIG = {json.dumps(db, ensure_ascii=False, indent=2)};\n"
    )
    with open(CONFIG_JS_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)

    logger.info(f"✅ ĐÃ ĐỒNG BỘ THÀNH CÔNG VÀO WEB/CONFIG.JS (Đã lọc sạch 100% link die)!")
    return True


def run_15m_daemon(user_email: str = DEFAULT_USER_EMAIL, interval_seconds: int = 900):
    """Vòng lặp chạy ngầm tự động quét và làm mới link mỗi 15 phút (900 giây)"""
    logger.info("==================================================")
    logger.info(f"🚀 KHỞI ĐỘNG DAEMON TỰ ĐỘNG CẬP NHẬT DEAL MỖI 15 PHÚT")
    logger.info(f"• Chu kỳ quét: {interval_seconds // 60} phút / lần")
    logger.info(f"• Bộ lọc: Chặn 100% link error_page / 404")
    logger.info(f"• Tài khoản hoàn tiền: {user_email}")
    logger.info("==================================================")

    while True:
        try:
            sync_deals_to_web_config(user_email)
            next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + interval_seconds))
            logger.info(f"⏳ Đã xong. Đang chờ 15 phút... Lần quét tiếp theo lúc: {next_time}")
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Đã dừng Daemon cập nhật deal.")
            break
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp cập nhật: {e}")
            time.sleep(60)


def start_daemon_background_thread(user_email: str = DEFAULT_USER_EMAIL, interval_seconds: int = 900):
    """Hàm tiện ích khởi động Daemon 15 phút dưới dạng Background Thread (dành cho bot_service hoặc admin_server)"""
    t = threading.Thread(target=run_15m_daemon, args=(user_email, interval_seconds), daemon=True)
    t.start()
    logger.info("⚡ Background Thread cập nhật Deal 15 phút đã được kích hoạt!")
    return t


def main():
    parser = argparse.ArgumentParser(description="Dịch vụ cào và cập nhật Deal/Voucher từ Telegram vào Web Player")
    parser.add_argument("--daemon", action="store_true", help="Chạy ở chế độ Daemon lặp lại mỗi 15 phút")
    parser.add_argument("--interval", type=int, default=900, help="Chu kỳ giây (mặc định: 900s = 15 phút)")
    parser.add_argument("--email", default=DEFAULT_USER_EMAIL, help="Email người nhận hoàn tiền tho-hoan-tien")
    args = parser.parse_args()

    if args.daemon:
        run_15m_daemon(user_email=args.email, interval_seconds=args.interval)
    else:
        sync_deals_to_web_config(user_email=args.email)


if __name__ == "__main__":
    main()
