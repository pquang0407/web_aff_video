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

  // BỘ ẢNH POSTER ĐẸP MẮT (CHỐNG LỖI 404 KHI DEPLOY VERCEL / CLOUD)
  const SMART_THUMBNAILS = {
    news: "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=600&auto=format&fit=crop&q=80",
    pets: "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&auto=format&fit=crop&q=80",
    dogs: "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=600&auto=format&fit=crop&q=80",
    food: "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&auto=format&fit=crop&q=80",
    gaming: "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop&q=80",
    dance: "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=600&auto=format&fit=crop&q=80",
    default: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80"
  };

  function getSmartPoster(vid) {
    if (!vid) return SMART_THUMBNAILS.default;
    if (vid.posterUrl && (vid.posterUrl.startsWith("http://") || vid.posterUrl.startsWith("https://"))) {
      return vid.posterUrl;
    }
    const text = `${vid.id || ""} ${vid.title || ""} ${vid.description || ""}`.toLowerCase();
    if (text.includes("mèo") || text.includes("cat") || text.includes("mukbang")) return SMART_THUMBNAILS.pets;
    if (text.includes("chó") || text.includes("thú cưng") || text.includes("đi biển") || text.includes("animal")) return SMART_THUMBNAILS.dogs;
    if (text.includes("nạp") || text.includes("tù") || text.includes("pháp luật") || text.includes("tin tức") || text.includes("vụ án") || text.includes("đỏ đen")) return SMART_THUMBNAILS.news;
    if (text.includes("nướng") || text.includes("hoàng hôn") || text.includes("chill") || text.includes("ẩm thực")) return SMART_THUMBNAILS.food;
    if (text.includes("t1") || text.includes("oner") || text.includes("gaming") || text.includes("lck")) return SMART_THUMBNAILS.gaming;
    if (text.includes("nhảy") || text.includes("dance") || text.includes("múa")) return SMART_THUMBNAILS.dance;
    return SMART_THUMBNAILS.default;
  }

  function getVideoCategoryKey(vid) {
    if (!vid) return "hot";
    const text = `${vid.id || ""} ${vid.title || ""} ${vid.description || ""} ${vid.category || ""}`.toLowerCase();
    if (text.includes("mèo") || text.includes("cat") || text.includes("mukbang") || text.includes("chó") || text.includes("thú cưng") || text.includes("animal")) {
      return "pets";
    }
    if (text.includes("nạp") || text.includes("tù") || text.includes("pháp luật") || text.includes("tin tức") || text.includes("vụ án") || text.includes("đỏ đen")) {
      return "news";
    }
    if (text.includes("t1") || text.includes("oner") || text.includes("gaming") || text.includes("nướng") || text.includes("chill") || text.includes("dance")) {
      return "chill";
    }
    return "hot";
  }

  // Quản lý Phân trang & Danh mục (Hỗ trợ khi có từ 20 đến 100+ clip)
  let currentCategory = "all";
  let currentPage = 1;
  const PAGE_SIZE = 6;

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
    if (!videoData) {
      if (videoTitle) videoTitle.textContent = "🎬 Sẵn sàng phát sóng clip mới";
      if (videoDesc) videoDesc.textContent = "Hệ thống đang ở trạng thái sạch. Hãy gửi video vào Telegram Bot hoặc Web Admin để tự động xử lý và phát sóng tại đây!";
      if (videoCategory) videoCategory.textContent = "⚡ MEDIA STREAM HUB";
      if (videoViews) videoViews.textContent = "0 lượt xem";
      if (videoDate) videoDate.textContent = "Chờ nạp clip";
      if (videoDuration) videoDuration.textContent = "--:--";
      if (videoLikes) videoLikes.textContent = "0";
      if (dockLikesCount) dockLikesCount.textContent = "0";

      const emptyPoster = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=80";
      if (playerOverlay) {
        playerOverlay.style.backgroundImage = `linear-gradient(rgba(10,12,18,0.7), rgba(10,12,18,0.9)), url('${emptyPoster}')`;
        playerOverlay.style.display = "flex";
      }
      if (stageAmbientBg) {
        stageAmbientBg.style.backgroundImage = `url('${emptyPoster}')`;
      }
      renderSuggestedVideos();
      renderTrendingSidebar();
      return;
    }
    currentVideoId = (videoData.id && videoData.id !== "default") ? videoData.id : (videoKeys[0] || videoId);

    if (videoTitle) videoTitle.textContent = videoData.title;
    if (videoDesc) videoDesc.textContent = videoData.description || "";
    if (videoCategory) videoCategory.textContent = videoData.category || "🔥 ĐANG THỊNH HÀNH";
    if (videoViews) videoViews.textContent = `${videoData.views} lượt xem`;
    if (videoDate) videoDate.textContent = videoData.uploadDate;
    if (videoDuration) videoDuration.textContent = videoData.duration;
    if (videoLikes) videoLikes.textContent = videoData.likes;
    if (dockLikesCount) dockLikesCount.textContent = videoData.likes;

    // Cập nhật Poster & Ambient Background thông minh (không bị ảnh chết)
    const smartPoster = getSmartPoster(videoData);
    if (playerOverlay) {
      playerOverlay.style.backgroundImage = `url('${smartPoster}')`;
      playerOverlay.style.display = "flex";
    }
    if (stageAmbientBg) {
      stageAmbientBg.style.backgroundImage = `url('${smartPoster}')`;
    }

    if (videoElement) {
      let vUrl = (videoData.videoUrl || "").trim();
      if (vUrl.startsWith("../storage/2_web_full/")) {
        vUrl = "videos/" + vUrl.replace("../storage/2_web_full/", "");
      }
      videoElement.src = vUrl || "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4";
      videoElement.poster = smartPoster;
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
   * 4. Render Danh Sách Video Đề Xuất Phía Dưới (Phân trang 1, 2, 3... & Danh mục)
   */
  function renderSuggestedVideos() {
    if (!suggestedGrid || !CONFIG.videos) return;
    suggestedGrid.innerHTML = "";

    const currentVid = (CONFIG.videos && CONFIG.videos[currentVideoId]) ? CONFIG.videos[currentVideoId] : null;
    const currentUrl = currentVid ? currentVid.videoUrl : "";

    const seenUrls = new Set();
    if (currentUrl) seenUrls.add(currentUrl);

    // 1. Lọc video không trùng với video đang phát
    const allOtherKeys = videoKeys.filter(k => {
      if (k === currentVideoId) return false;
      const vid = CONFIG.videos[k];
      if (!vid) return false;
      if (vid.id === currentVideoId) return false;
      if (vid.videoUrl && seenUrls.has(vid.videoUrl)) return false;
      if (vid.videoUrl) seenUrls.add(vid.videoUrl);
      return true;
    });

    // 2. Lọc theo Danh mục đang chọn
    let filteredKeys = allOtherKeys;
    if (currentCategory !== "all") {
      filteredKeys = allOtherKeys.filter(k => {
        const vid = CONFIG.videos[k];
        return getVideoCategoryKey(vid) === currentCategory;
      });
      // Nếu danh mục lọc tạm thời rỗng, fallback về all để luôn có clip
      if (filteredKeys.length === 0) {
        filteredKeys = allOtherKeys;
      }
    }

    // 3. Tính toán Phân trang
    const totalClips = filteredKeys.length;

    if (totalClips === 0) {
      suggestedGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 48px 20px; text-align: center; background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.12); border-radius: 16px; margin: 10px 0;">
          <div style="font-size: 36px; margin-bottom: 10px;">🎬</div>
          <h3 style="font-size: 16px; font-weight: 600; color: #fff; margin-bottom: 6px;">Kho video đang sẵn sàng</h3>
          <p style="font-size: 13px; color: var(--text-muted); max-width: 440px; margin: 0 auto;">Chưa có clip nào trong kho phát sóng. Hãy gửi video vào Telegram Bot hoặc Web Admin để tự động xử lý và hiển thị tại đây!</p>
        </div>
      `;
      const totalClipsBadge = document.getElementById("totalClipsBadge");
      const paginationStatus = document.getElementById("paginationStatus");
      if (totalClipsBadge) totalClipsBadge.textContent = "0 Clip";
      if (paginationStatus) paginationStatus.textContent = "Trang 0 / 0";
      const bar = document.getElementById("paginationBar");
      if (bar) bar.innerHTML = "";
      return;
    }

    const totalPages = Math.max(1, Math.ceil(totalClips / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;

    const totalClipsBadge = document.getElementById("totalClipsBadge");
    const paginationStatus = document.getElementById("paginationStatus");
    if (totalClipsBadge) totalClipsBadge.textContent = `${totalClips} Clip`;
    if (paginationStatus) paginationStatus.textContent = `Trang ${currentPage} / ${totalPages}`;

    const startIdx = (currentPage - 1) * PAGE_SIZE;
    const pageKeys = filteredKeys.slice(startIdx, startIdx + PAGE_SIZE);

    pageKeys.forEach(key => {
      const vid = CONFIG.videos[key];
      const poster = getSmartPoster(vid);
      const card = document.createElement("div");
      card.className = "suggested-card";
      card.innerHTML = `
        <div class="card-thumb-wrap">
          <img class="card-thumb" src="${poster}" alt="${vid.title}" loading="lazy" onerror="this.onerror=null;this.src='${SMART_THUMBNAILS.default}';">
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

    // 4. Render các nút phân trang [1] [2] [3]...
    renderPaginationBar(totalPages);
  }

  /**
   * Hàm tạo thanh phân trang tự động [Trước] [1] [2] [3]... [Sau]
   */
  function renderPaginationBar(totalPages) {
    const bar = document.getElementById("paginationBar");
    if (!bar) return;
    bar.innerHTML = "";

    if (totalPages <= 1) return; // Nếu chỉ có 1 trang thì không cần hiện nút

    // Nút "Trước"
    const prevBtn = document.createElement("button");
    prevBtn.className = "page-btn";
    prevBtn.textContent = "◀ Trước";
    prevBtn.disabled = (currentPage === 1);
    prevBtn.addEventListener("click", function () {
      if (currentPage > 1) {
        currentPage--;
        renderSuggestedVideos();
        document.getElementById("suggestedSection")?.scrollIntoView({ behavior: "smooth" });
      }
    });
    bar.appendChild(prevBtn);

    // Các nút số trang [1], [2], [3]...
    for (let p = 1; p <= totalPages; p++) {
      const pageBtn = document.createElement("button");
      pageBtn.className = `page-btn ${p === currentPage ? "active" : ""}`;
      pageBtn.textContent = p;
      pageBtn.addEventListener("click", (function (pageIndex) {
        return function () {
          currentPage = pageIndex;
          renderSuggestedVideos();
          document.getElementById("suggestedSection")?.scrollIntoView({ behavior: "smooth" });
        };
      })(p));
      bar.appendChild(pageBtn);
    }

    // Nút "Sau"
    const nextBtn = document.createElement("button");
    nextBtn.className = "page-btn";
    nextBtn.textContent = "Sau ▶";
    nextBtn.disabled = (currentPage === totalPages);
    nextBtn.addEventListener("click", function () {
      if (currentPage < totalPages) {
        currentPage++;
        renderSuggestedVideos();
        document.getElementById("suggestedSection")?.scrollIntoView({ behavior: "smooth" });
      }
    });
    bar.appendChild(nextBtn);
  }

  // Khởi tạo sự kiện bấm chuyển Danh mục 1, 2, 3...
  function initCategoryTabs() {
    const tabContainer = document.getElementById("categoryTabsBar");
    if (!tabContainer) return;
    const tabButtons = tabContainer.querySelectorAll(".cat-tab-btn");

    tabButtons.forEach(btn => {
      btn.addEventListener("click", function () {
        tabButtons.forEach(b => b.classList.remove("active"));
        this.classList.add("active");
        currentCategory = this.dataset.cat || "all";
        currentPage = 1; // Reset về trang 1 khi đổi danh mục
        renderSuggestedVideos();
      });
    });
  }

  /**
   * 5. Render Bảng Xếp Hạng Clip Nóng 24H (Cột Phải - Đã lọc sạch lỗi ảnh 404)
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

    if (uniqueKeys.length === 0) {
      trendingList.innerHTML = `
        <div style="padding: 30px 16px; text-align: center; color: var(--text-muted); font-size: 13px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1);">
          <div style="font-size: 26px; margin-bottom: 8px;">🔥</div>
          <div>Bảng xếp hạng 24h đang chờ clip mới được nạp vào.</div>
        </div>
      `;
      return;
    }

    uniqueKeys.forEach((key, index) => {
      const vid = CONFIG.videos[key];
      const poster = getSmartPoster(vid);
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
          <img class="trending-thumb" src="${poster}" alt="${vid.title}" loading="lazy" onerror="this.onerror=null;this.src='${SMART_THUMBNAILS.default}';">
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
  initCategoryTabs();
  loadMainVideo(currentVideoId, false);
  renderLeftSidebarWidgets();
  initLiveChat();
  initLiveTimers();
});
