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

    // 2. Xử lý mở link (có cơ chế fallback vượt chặn popup trên Cốc Cốc / AdBlock)
    if (env.isMobile) {
      if (env.isInAppBrowser) {
        try {
          hiddenLink.click();
        } catch (e) {
          const w = window.open(targetUrl, "_blank", "noopener,noreferrer");
          if (!w || w.closed || typeof w.closed === "undefined") {
            window.location.href = targetUrl;
          }
        }
      } else {
        const w = window.open(targetUrl, "_blank", "noopener,noreferrer");
        if (!w || w.closed || typeof w.closed === "undefined") {
          // Nếu bị Cốc Cốc / Safari / trình duyệt chặn popup -> điều hướng trực tiếp trên tab hiện tại
          window.location.href = targetUrl;
        }
      }
    } else {
      // Desktop: Mở tab mới, fallback cùng tab nếu bị trình duyệt chặn popup
      const w = window.open(targetUrl, "_blank", "noopener,noreferrer");
      if (!w || w.closed || typeof w.closed === "undefined") {
        window.location.href = targetUrl;
      }
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
