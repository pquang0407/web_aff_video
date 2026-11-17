/**
 * DEEPLINK.JS - Xử lý chuyển hướng mở App Shopee & rơi Cookie
 * Tối ưu hóa cho In-App Browser của Facebook, TikTok, Zalo, Instagram
 */

const DeepLinkHandler = (function () {
  /**
   * Nhận diện thiết bị và môi trường trình duyệt
   */
  function detectEnvironment() {
    const ua = navigator.userAgent || navigator.vendor || window.opera;
    const isAndroid = /android/i.test(ua);
    const isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
    const isMobile = isAndroid || isIOS;

    // Nhận diện In-App Browser (FB, TikTok, Zalo, Messenger, etc.)
    const isFB = /FBAN|FBAV|FB_IAB/i.test(ua);
    const isTikTok = /musical_ly|bytedance|tiktok/i.test(ua);
    const isZalo = /zalo/i.test(ua);
    const isInAppBrowser = isFB || isTikTok || isZalo;

    return {
      isAndroid,
      isIOS,
      isMobile,
      isInAppBrowser,
      isFB,
      isTikTok,
      isZalo
    };
  }

  /**
   * Mở link affiliate với cơ chế rơi Cookie và DeepLink
   */
  function triggerAffiliate(targetUrl) {
    if (!targetUrl) return;

    const env = detectEnvironment();

    // 1. Tạo liên kết ẩn với chính sách che nguồn (no-referrer)
    const hiddenLink = document.createElement("a");
    hiddenLink.href = targetUrl;
    hiddenLink.rel = "noreferrer noopener";
    hiddenLink.referrerPolicy = "no-referrer";
    hiddenLink.target = "_blank";
    hiddenLink.style.display = "none";
    document.body.appendChild(hiddenLink);

    // 2. Xử lý mở link
    if (env.isMobile) {
      if (env.isInAppBrowser) {
        // Trong WebView (FB, TikTok), window.open thường bị chặn
        // Dùng click trực tiếp trên thẻ link hoặc location.href qua tab mới
        try {
          hiddenLink.click();
        } catch (e) {
          window.open(targetUrl, "_blank", "noopener,noreferrer");
        }
      } else {
        // Trình duyệt ngoài (Chrome, Safari di động): click thẻ ẩn hoặc window.open
        hiddenLink.click();
      }
    } else {
      // Desktop: Mở tab mới
      window.open(targetUrl, "_blank", "noopener,noreferrer");
    }

    // Dọn dẹp DOM
    setTimeout(() => {
      if (hiddenLink.parentNode) {
        hiddenLink.parentNode.removeChild(hiddenLink);
      }
    }, 1000);
  }

  return {
    detect: detectEnvironment,
    open: triggerAffiliate
  };
})();
