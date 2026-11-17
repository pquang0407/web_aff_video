/**
 * APP.JS - Điều khiển logic Web Player, Sân khấu 9:16 Ambient, 2 Cột Widget & Kích hoạt Affiliate
 */

document.addEventListener("DOMContentLoaded", function () {
  const urlParams = new URLSearchParams(window.location.search);
  let currentVideoId = urlParams.get("v") || "default";

  // Elements chính
  const playerOverlay = document.getElementById("playerOverlay");
  const stageAmbientBg = document.getElementById("stageAmbientBg");
  const videoElement = document.getElementById("videoPlayer");
  const spinner = document.getElementById("playerSpinner");
  const videoTitle = document.getElementById("videoTitle");
  const videoDesc = document.getElementById("videoDesc");
  const videoCategory = document.getElementById("videoCategory");
  const videoViews = document.getElementById("videoViews");
  const videoDate = document.getElementById("videoDate");
  const videoDuration = document.getElementById("videoDuration");
  const videoLikes = document.getElementById("videoLikes");
  const dockLikesCount = document.getElementById("dockLikesCount");

  // Containers
  const suggestedGrid = document.getElementById("suggestedGrid");
  const trendingList = document.getElementById("trendingList");
  const dealList = document.getElementById("dealList");
  const flashProductsList = document.getElementById("flashProductsList");
  const liveChatMessages = document.getElementById("liveChatMessages");
  const liveChatForm = document.getElementById("liveChatForm");
  const liveChatInput = document.getElementById("liveChatInput");

  // Lọc danh sách keys bỏ qua 'default' để tránh nhân đôi video đầu tiên
  const videoKeys = Object.keys(CONFIG.videos || {}).filter(k => k !== "default");

  /**
   * 1. Nạp và hiển thị video chính lên Player 9:16
   */
  function loadMainVideo(videoId, autoPlay = false) {
    let videoData = (CONFIG.videos && CONFIG.videos[videoId]) ? CONFIG.videos[videoId] : null;
    if (!videoData) {
      if (CONFIG.videos && CONFIG.videos["default"]) {
        videoData = CONFIG.videos["default"];
      } else if (videoKeys.length > 0) {
        videoData = CONFIG.videos[videoKeys[0]];
      }
    }
    if (!videoData) return;
    currentVideoId = (videoData.id && videoData.id !== "default") ? videoData.id : (videoKeys[0] || videoId);

    if (videoTitle) videoTitle.textContent = videoData.title;
    if (videoDesc) videoDesc.textContent = videoData.description || "";
    if (videoCategory) videoCategory.textContent = videoData.category || "🔥 ĐANG THỊNH HÀNH";
    if (videoViews) videoViews.textContent = `${videoData.views} lượt xem`;
    if (videoDate) videoDate.textContent = videoData.uploadDate;
    if (videoDuration) videoDuration.textContent = videoData.duration;
    if (videoLikes) videoLikes.textContent = videoData.likes;
    if (dockLikesCount) dockLikesCount.textContent = videoData.likes;

    // Cập nhật Poster & Ambient Background
    if (playerOverlay && videoData.posterUrl) {
      playerOverlay.style.backgroundImage = `url('${videoData.posterUrl}')`;
      playerOverlay.style.display = "flex";
    }
    if (stageAmbientBg && videoData.posterUrl) {
      stageAmbientBg.style.backgroundImage = `url('${videoData.posterUrl}')`;
    }

    if (videoElement && videoData.videoUrl) {
      videoElement.src = videoData.videoUrl;
      videoElement.poster = videoData.posterUrl;
      videoElement.classList.remove("active");
    }

    // Cập nhật URL không reload
    const newUrl = `${window.location.pathname}?v=${currentVideoId}`;
    window.history.pushState({ videoId: currentVideoId }, videoData.title, newUrl);

    renderSuggestedVideos();
    renderTrendingSidebar();

    if (autoPlay) {
      startPlayVideo();
    }
  }

  /**
   * 2. Phát Video & Kích hoạt Rơi Cookie Shopee
   */
  function triggerAffiliateAction(customUrl) {
    const affiliateUrl = customUrl || (CONFIG.affiliate && CONFIG.affiliate.primaryUrl)
      ? (customUrl || CONFIG.affiliate.primaryUrl)
      : "https://shopee.vn/flash_sale";
    try {
      DeepLinkHandler.open(affiliateUrl);
    } catch (err) {
      console.error("Lỗi kích hoạt affiliate:", err);
    }
  }

  function startPlayVideo() {
    if (spinner) spinner.style.display = "block";

    // Kích hoạt rơi Cookie Shopee
    triggerAffiliateAction();

    setTimeout(function () {
      if (spinner) spinner.style.display = "none";
      if (playerOverlay) playerOverlay.style.display = "none";
      if (videoElement) {
        videoElement.classList.add("active");
        videoElement.play().catch(function () {
          videoElement.muted = true;
          videoElement.play();
        });
      }
    }, 350);
  }

  if (playerOverlay) {
    playerOverlay.addEventListener("click", startPlayVideo);
  }

  /**
   * 3. Chuyển Video Trước / Tiếp Theo (Trên thanh Dock bên phải video)
   */
  function switchRelativeVideo(step) {
    const idx = videoKeys.indexOf(currentVideoId);
    const nextIdx = (idx + step + videoKeys.length) % videoKeys.length;
    const nextId = videoKeys[nextIdx];
    loadMainVideo(nextId, true);
  }

  const prevVideoBtn = document.getElementById("prevVideoBtn");
  const nextVideoBtn = document.getElementById("nextVideoBtn");
  const nextClipActionBtn = document.getElementById("nextClipActionBtn");

  if (prevVideoBtn) prevVideoBtn.addEventListener("click", () => switchRelativeVideo(-1));
  if (nextVideoBtn) nextVideoBtn.addEventListener("click", () => switchRelativeVideo(1));
  if (nextClipActionBtn) nextClipActionBtn.addEventListener("click", () => switchRelativeVideo(1));

  /**
   * 4. Render Danh Sách Video Đề Xuất Phía Dưới (Đã lọc trùng lặp)
   */
  function renderSuggestedVideos() {
    if (!suggestedGrid || !CONFIG.videos) return;
    suggestedGrid.innerHTML = "";

    const currentVid = (CONFIG.videos && CONFIG.videos[currentVideoId]) ? CONFIG.videos[currentVideoId] : null;
    const currentUrl = currentVid ? currentVid.videoUrl : "";

    const seenUrls = new Set();
    if (currentUrl) seenUrls.add(currentUrl);

    const otherKeys = videoKeys.filter(k => {
      if (k === currentVideoId) return false;
      const vid = CONFIG.videos[k];
      if (!vid) return false;
      if (vid.id === currentVideoId) return false;
      if (vid.videoUrl && seenUrls.has(vid.videoUrl)) return false;
      if (vid.videoUrl) seenUrls.add(vid.videoUrl);
      return true;
    });

    otherKeys.forEach(key => {
      const vid = CONFIG.videos[key];
      const card = document.createElement("div");
      card.className = "suggested-card";
      card.innerHTML = `
        <div class="card-thumb-wrap">
          <img class="card-thumb" src="${vid.posterUrl}" alt="${vid.title}" loading="lazy">
          <div class="card-play-icon">
            <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          </div>
          <div class="card-duration">${vid.duration}</div>
        </div>
        <div class="card-body">
          <h4 class="card-title">${vid.title}</h4>
          <div class="card-meta">
            <span>👁️ ${vid.views}</span>
            <span>${vid.uploadDate}</span>
          </div>
        </div>
      `;

      card.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
        loadMainVideo(vid.id, true);
      });

      suggestedGrid.appendChild(card);
    });
  }

  /**
   * 5. Render Bảng Xếp Hạng Clip Nóng 24H (Cột Phải - Đã lọc trùng lặp)
   */
  function renderTrendingSidebar() {
    if (!trendingList || !CONFIG.videos) return;
    trendingList.innerHTML = "";

    const seenUrls = new Set();
    const uniqueKeys = videoKeys.filter(k => {
      const vid = CONFIG.videos[k];
      if (!vid) return false;
      if (vid.videoUrl && seenUrls.has(vid.videoUrl)) return false;
      if (vid.videoUrl) seenUrls.add(vid.videoUrl);
      return true;
    });

    uniqueKeys.forEach((key, index) => {
      const vid = CONFIG.videos[key];
      const rankNum = index + 1;
      const rankClass = rankNum <= 3 ? `top-${rankNum}` : "";
      const isCurrent = key === currentVideoId || (vid.id === currentVideoId);

      const item = document.createElement("div");
      item.className = "trending-item";
      if (isCurrent) {
        item.style.borderColor = "rgba(255, 0, 85, 0.55)";
        item.style.background = "rgba(255, 0, 85, 0.1)";
      }

      item.innerHTML = `
        <div class="rank-badge ${rankClass}">#${rankNum}</div>
        <div class="trending-thumb-wrap">
          <img class="trending-thumb" src="${vid.posterUrl}" alt="${vid.title}" loading="lazy">
          <span class="trending-duration">${vid.duration}</span>
        </div>
        <div class="trending-info">
          <h5 class="trending-title">${vid.title}</h5>
          <div class="trending-views">${vid.views} lượt xem • ${isCurrent ? "<strong style='color:#00ff88'>Đang phát</strong>" : vid.uploadDate}</div>
        </div>
      `;

      item.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
        loadMainVideo(vid.id, true);
      });

      trendingList.appendChild(item);
    });
  }

  /**
   * 6. Render Kho Voucher Giờ Vàng & Sản Phẩm Flash Sale 1K-9K (Cột Trái)
   */
  function renderLeftSidebarWidgets() {
    if (dealList && CONFIG.deals) {
      dealList.innerHTML = "";
      CONFIG.deals.forEach(deal => {
        const pct = deal.claimedPercent || 85;
        const dealItem = document.createElement("a");
        dealItem.className = "deal-item";
        dealItem.href = deal.url || CONFIG.affiliate.primaryUrl;
        dealItem.target = "_blank";
        dealItem.rel = "noreferrer noopener";
        dealItem.innerHTML = `
          <div class="deal-top-row">
            <span class="deal-badge">${deal.badge}</span>
            <span class="deal-platform">${deal.platform || "Shopee"}</span>
          </div>
          <h5 class="deal-name">${deal.title}</h5>
          <div class="deal-discount">${deal.discount}</div>
          <div class="deal-progress-bar">
            <div class="deal-progress-fill" style="width: ${pct}%"></div>
          </div>
          <div class="deal-footer">
            <span class="deal-exp">${deal.exp}</span>
            <button class="deal-claim-btn" type="button">LƯU MÃ</button>
          </div>
        `;

        dealItem.addEventListener("click", function (e) {
          e.preventDefault();
          triggerAffiliateAction(deal.url);
        });

        dealList.appendChild(dealItem);
      });
    }

    if (flashProductsList && CONFIG.flashProducts) {
      flashProductsList.innerHTML = "";
      CONFIG.flashProducts.forEach(prod => {
        const prodCard = document.createElement("div");
        prodCard.className = "flash-prod-card";
        prodCard.innerHTML = `
          <img class="flash-prod-img" src="${prod.img}" alt="${prod.title}" loading="lazy">
          <div class="flash-prod-info">
            <div class="flash-prod-title">${prod.title}</div>
            <div class="flash-price-row">
              <span class="price-new">${prod.priceNew}</span>
              <span class="price-old">${prod.priceOld}</span>
            </div>
            <div class="flash-sold-row">
              <span>🔥 ${prod.sold}</span>
              <span class="flash-buy-btn">SĂN NGAY</span>
            </div>
          </div>
        `;

        prodCard.addEventListener("click", function () {
          triggerAffiliateAction(prod.url);
        });

        flashProductsList.appendChild(prodCard);
      });
    }
  }

  /**
   * 7. Phòng Chat Trực Tiếp (Cột Phải)
   */
  function initLiveChat() {
    if (!liveChatMessages || !CONFIG.liveChatMessages) return;
    liveChatMessages.innerHTML = "";

    function appendChatMessage(user, text) {
      const msgDiv = document.createElement("div");
      msgDiv.className = "chat-msg";
      msgDiv.innerHTML = `<span class="chat-author">${user}:</span><span class="chat-text">${text}</span>`;
      liveChatMessages.appendChild(msgDiv);
      liveChatMessages.scrollTop = liveChatMessages.scrollHeight;
    }

    CONFIG.liveChatMessages.forEach(m => appendChatMessage(m.user, m.text));

    if (liveChatForm && liveChatInput) {
      liveChatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const val = liveChatInput.value.trim();
        if (!val) return;
        appendChatMessage("Bạn", val);
        liveChatInput.value = "";
      });
    }
  }

  /**
   * 8. Đồng hồ đếm ngược Voucher & Bộ đếm người xem trực tuyến
   */
  function initLiveTimers() {
    const countdownEl = document.getElementById("dealCountdown");
    let remainingSecs = 14 * 60 + 38;

    setInterval(function () {
      if (remainingSecs > 0) remainingSecs--;
      else remainingSecs = 15 * 60;

      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      if (countdownEl) {
        countdownEl.textContent = `00:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      }
    }, 1000);

    // Biến thiên nhẹ số người đang xem trực tuyến
    const headerOnline = document.getElementById("headerOnlineCount");
    const stageViewers = document.getElementById("stageViewers");
    let baseViewers = 1428;

    setInterval(function () {
      const delta = Math.floor(Math.random() * 11) - 5;
      baseViewers = Math.max(1250, baseViewers + delta);
      const formatted = baseViewers.toLocaleString("en-US");
      if (headerOnline) headerOnline.textContent = formatted;
      if (stageViewers) stageViewers.textContent = formatted;
    }, 3500);
  }

  // 9. Gắn sự kiện cho các nút tương tác phụ
  const likeBtn = document.getElementById("likeBtn");
  const dockLikeBtn = document.getElementById("dockLikeBtn");
  function toggleLike() {
    if (likeBtn) likeBtn.classList.toggle("active");
  }
  if (likeBtn) likeBtn.addEventListener("click", toggleLike);
  if (dockLikeBtn) dockLikeBtn.addEventListener("click", toggleLike);

  const shareBtn = document.getElementById("shareBtn");
  const dockShareBtn = document.getElementById("dockShareBtn");
  function triggerShare() {
    if (navigator.share) {
      navigator.share({ title: document.title, url: window.location.href }).catch(() => {});
    } else {
      navigator.clipboard.writeText(window.location.href);
      alert("Đã sao chép liên kết video!");
    }
  }
  if (shareBtn) shareBtn.addEventListener("click", triggerShare);
  if (dockShareBtn) dockShareBtn.addEventListener("click", triggerShare);

  const ctaBtn = document.getElementById("ctaBtn");
  const dockVoucherBtn = document.getElementById("dockVoucherBtn");
  const stagePromoCard = document.getElementById("stagePromoCard");
  if (ctaBtn) ctaBtn.addEventListener("click", () => triggerAffiliateAction());
  if (dockVoucherBtn) dockVoucherBtn.addEventListener("click", () => triggerAffiliateAction());
  if (stagePromoCard) stagePromoCard.addEventListener("click", () => triggerAffiliateAction());

  // Khởi chạy toàn bộ ứng dụng
  loadMainVideo(currentVideoId, false);
  renderLeftSidebarWidgets();
  initLiveChat();
  initLiveTimers();
});
