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
  const leftVideoList = document.getElementById("leftVideoList");
  const trendingList = document.getElementById("trendingList");
  const relatedProductsList = document.getElementById("relatedProductsList");
  const relatedTopicBadge = document.getElementById("relatedTopicBadge");
  const dealList = document.getElementById("dealList");
  const flashProductsList = document.getElementById("flashProductsList");
  const liveChatMessages = document.getElementById("liveChatMessages");
  const liveChatForm = document.getElementById("liveChatForm");
  const liveChatInput = document.getElementById("liveChatInput");

  // Lọc danh sách keys bỏ qua 'default' và loại trùng videoUrl để chuyển clip không bị lặp
  const seenInitUrls = new Set();
  const videoKeys = Object.keys(CONFIG.videos || {}).filter(k => {
    if (k === "default") return false;
    const vid = CONFIG.videos[k];
    if (!vid) return false;
    const urlKey = (vid.videoUrl || "").trim();
    if (urlKey && seenInitUrls.has(urlKey)) return false;
    if (urlKey) seenInitUrls.add(urlKey);
    return true;
  });

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
    if (vid.posterUrl) {
      let p = vid.posterUrl.trim();
      if (p.startsWith("http://") || p.startsWith("https://")) return p;
      if (p.startsWith("../storage/2_web_full/")) {
        p = "videos/" + p.replace("../storage/2_web_full/", "");
      }
      return p;
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
    if (!vid) return "explore";
    const text = `${vid.id || ""} ${vid.title || ""} ${vid.description || ""}`.toLowerCase();
    if (/bóng đá|man utd|pochettino|liverpool|champions league|messi|neymar|yamal|ronaldo|u17|u23|đội tuyển|marathon|yoga|pilates|vận động viên|thể thao|phạt đền|sân cỏ|trận đấu|hlv|cầu thủ|cup|lượt năm/.test(text)) {
      return "sports";
    }
    if (/ra tòa|lừa đảo|chủ tịch|đảng dân chủ|jensen huang|nvidia|chip|ai|điện thoại|công nghệ|tiktoker|vụ án|pháp luật|tử vong|tai nạn|không khí lạnh|cảnh báo|chính trị|quốc hội|bầu cử/.test(text)) {
      return "news";
    }
    return "explore";
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
    if (videoCategory) {
      const cleanCat = String(videoData.category || "BẢN TIN 3D")
        .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\uFE0F]/gu, "")
        .trim();
      videoCategory.textContent = cleanCat || "BẢN TIN 3D";
    }
    if (videoDate) videoDate.textContent = videoData.uploadDate || "Mới cập nhật";
    if (videoDuration) videoDuration.textContent = videoData.duration || "--:--";

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
      videoElement.load();
      videoElement.classList.remove("active");
    }

    // Cập nhật URL không reload
    const newUrl = `${window.location.pathname}?v=${currentVideoId}`;
    window.history.pushState({ videoId: currentVideoId }, videoData.title, newUrl);

    renderSuggestedVideos();
    renderTrendingSidebar();
    renderRelatedProductsForVideo(videoData);
    if (typeof syncLikeUI === "function") syncLikeUI();

    if (autoPlay && (hasAlreadyRedirectedOnce() || hasStartedPlayingInSession)) {
      startPlayVideo(false);
    }
  }

  /**
   * 2. Phát Video & Kích hoạt Rơi Cookie Shopee (1 LẦN / PHIÊN MỞ TAB — ĐÓNG TAB MỞ LẠI SẼ KÍCH HOẠT LẠI)
   */
  const AFF_ONCE_STORAGE_KEY = "tho_news_aff_redirected_session_v2";
  let hasRedirectedInSession = false;
  let hasStartedPlayingInSession = false;

  function hasAlreadyRedirectedOnce() {
    if (hasRedirectedInSession) return true;
    try {
      return window.sessionStorage.getItem(AFF_ONCE_STORAGE_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function markRedirectedOnce() {
    hasRedirectedInSession = true;
    try {
      window.sessionStorage.setItem(AFF_ONCE_STORAGE_KEY, "1");
    } catch (e) {}
  }

  function triggerAffiliateAction(customUrl) {
    // Khóa chặt: 1 người dùng chỉ bị chuyển duy nhất 1 lần khi bấm Play lần đầu, tuyệt đối không chuyển lần 2
    if (hasAlreadyRedirectedOnce()) return;
    markRedirectedOnce();

    const affiliateUrl = customUrl || (CONFIG.affiliate && CONFIG.affiliate.primaryUrl)
      ? (customUrl || CONFIG.affiliate.primaryUrl)
      : "https://shopee.vn/flash_sale";
    try {
      DeepLinkHandler.open(affiliateUrl);
    } catch (err) {
      console.error("Lỗi kích hoạt affiliate:", err);
    }
  }

  function playVideoNow() {
    if (spinner) spinner.style.display = "none";
    if (playerOverlay) playerOverlay.style.display = "none";
    if (videoElement) {
      hasStartedPlayingInSession = true;
      videoElement.classList.add("active");
      const playPromise = videoElement.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(function () {
          videoElement.muted = true;
          videoElement.play().catch(function () {});
        });
      }
    }
  }

  function startPlayVideo(isUserPlayClick = false) {
    // Chỉ chuyển hướng duy nhất 1 lần khi người dùng bấm Play lần đầu tiên vào web
    if (isUserPlayClick && !hasAlreadyRedirectedOnce()) {
      triggerAffiliateAction();
    }

    // Khi tự chuyển video tiếp theo (auto-next) hoặc đã phát trước đó, gọi play() ngay lập tức
    // để giữ quyền phát có tiếng trên iOS Safari / Chrome Mobile
    if (!isUserPlayClick) {
      playVideoNow();
      return;
    }

    if (spinner) spinner.style.display = "block";
    setTimeout(playVideoNow, 350);
  }

  if (playerOverlay) {
    playerOverlay.addEventListener("click", function () {
      startPlayVideo(true);
    });
  }

  /**
   * 3. Chuyển Video Trước / Tiếp Theo (Dock + Tự động qua video mới khi hết video cũ)
   */
  function switchRelativeVideo(step) {
    if (!videoKeys || videoKeys.length === 0) return;
    const idx = videoKeys.indexOf(currentVideoId);
    const baseIdx = idx >= 0 ? idx : 0;
    const nextIdx = (baseIdx + step + videoKeys.length) % videoKeys.length;
    const nextId = videoKeys[nextIdx];
    loadMainVideo(nextId, true);
  }

  if (videoElement) {
    videoElement.addEventListener("play", function () {
      hasStartedPlayingInSession = true;
    });

    // Tự động chuyển sang video kế tiếp khi video hiện tại phát hết
    videoElement.addEventListener("ended", function () {
      if (videoKeys.length > 1) {
        switchRelativeVideo(1);
      } else {
        videoElement.currentTime = 0;
        playVideoNow();
      }
    });
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
            <span>${vid.duration || "00:46"}</span>
            <span>${vid.uploadDate || "Mới cập nhật"}</span>
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
   * 5. Render Danh Sách Clip Chia Đều 2 Bên (Cột Trái: Bản Tin 3D Mới Nhất | Cột Phải: Bảng Xếp Hạng 24H)
   */
  function createSidebarVideoItem(vid, key, rankNum) {
    const poster = getSmartPoster(vid);
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
        <div class="trending-views">${isCurrent ? "<strong style='color:#00ff88'>Đang phát</strong>" : (vid.uploadDate || "Mới cập nhật")}</div>
      </div>
    `;

    item.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
      loadMainVideo(vid.id, true);
    });
    return item;
  }

  function renderTrendingSidebar() {
    if (!CONFIG.videos) return;
    if (leftVideoList) leftVideoList.innerHTML = "";
    if (trendingList) trendingList.innerHTML = "";

    const seenUrls = new Set();
    const uniqueKeys = videoKeys.filter(k => {
      const vid = CONFIG.videos[k];
      if (!vid) return false;
      if (vid.videoUrl && seenUrls.has(vid.videoUrl)) return false;
      if (vid.videoUrl) seenUrls.add(vid.videoUrl);
      return true;
    });

    if (uniqueKeys.length === 0) {
      const emptyHtml = `
        <div style="padding: 30px 16px; text-align: center; color: var(--text-muted); font-size: 13px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1);">
          <div style="font-size: 26px; margin-bottom: 8px;">🔥</div>
          <div>Kho bản tin 3D đang chờ clip mới được nạp vào.</div>
        </div>
      `;
      if (leftVideoList) leftVideoList.innerHTML = emptyHtml;
      if (trendingList) trendingList.innerHTML = emptyHtml;
      return;
    }

    const UP_NEXT_COUNT = 4;

    // Cột Phải: Phát tiếp theo (chỉ hiện gọn 4 clip kế tiếp để không bị ngợp màn hình)
    if (trendingList) {
      const curIdx = uniqueKeys.indexOf(currentVideoId);
      const ordered = curIdx >= 0
        ? [...uniqueKeys.slice(curIdx + 1), ...uniqueKeys.slice(0, curIdx)]
        : uniqueKeys;
      ordered.slice(0, UP_NEXT_COUNT).forEach((key, index) => {
        const vid = CONFIG.videos[key];
        trendingList.appendChild(createSidebarVideoItem(vid, key, index + 1));
      });
    }
  }

  /**
   * 5B. Render Sản Phẩm Shopee Liên Quan Theo Chủ Đề Video (0ms, không reload, 0% link chết)
   * - Ưu tiên relatedProducts gắn sẵn từ Gemini + shp.tho-hoantien.com trong config.js
   * - Fallback tự động khớp chủ đề video cho các clip cũ (link tìm kiếm Shopee bán chạy gắn affiliate_id=17395210573)
   */
  function buildShopeeAffSearchUrl(keyword) {
    const searchUrl = `https://shopee.vn/search?keyword=${encodeURIComponent(keyword)}&sortBy=sales`;
    return `https://s.shopee.vn/an_redir?origin_link=${encodeURIComponent(searchUrl)}&affiliate_id=17395210573&sub_id=tho_news_ctx-vid_30a2abe6e6`;
  }

  function pickVariedItems(pool, videoId, count = 3) {
    if (!pool || pool.length <= count) return pool || [];
    let hash = 0;
    const s = String(videoId || "");
    for (let i = 0; i < s.length; i++) hash = ((hash << 5) - hash + s.charCodeAt(i)) | 0;
    const start = Math.abs(hash) % pool.length;
    const out = [];
    for (let i = 0; i < count; i++) out.push(pool[(start + i) % pool.length]);
    return out;
  }

  function getContextualFallbackProducts(videoData) {
    const text = `${videoData?.title || ""} ${videoData?.description || ""}`.toLowerCase();
    const vidId = videoData?.id || "";

    // 1. Bóng đá (nhận diện đầy đủ CLB, giải đấu, cầu thủ, HLV)
    if (/bóng đá|man utd|pochettino|liverpool|champions league|messi|neymar|yamal|ronaldo|u17|u23|đội tuyển|phạt đền|sân cỏ|cầu thủ|bàn thắng|v-league|world cup|hlv|lượt năm/.test(text)) {
      return {
        badge: "BÓNG ĐÁ",
        items: pickVariedItems([
          { title: "Giày Đá Bóng Sân Cỏ Nhân Tạo Đinh TF", tag: "Bán chạy Shopee", subtitle: "Ôm chân bám sân, nhiều size", img: "https://images.unsplash.com/photo-1511886929837-354d827aae26?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("giày đá bóng nam đinh tf") },
          { title: "Áo Đấu Câu Lạc Bộ & Đội Tuyển Bản Đẹp", tag: "Hot Trend", subtitle: "Vải mè Thái thoáng khí, thấm hút", img: "https://images.unsplash.com/photo-1580087256394-dc596e1c8f4f?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("áo bóng đá câu lạc bộ") },
          { title: "Quả Bóng Đá Thi Đấu Chuẩn Size 5", tag: "Ưu đãi Shopee", subtitle: "Tặng kim bơm và lưới đựng", img: "https://images.unsplash.com/photo-1575361204480-aadea25e6e68?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("quả bóng đá chuẩn size 5") },
          { title: "Tất Đá Bóng Chống Trơn Cao Cấp", tag: "Bán chạy Shopee", subtitle: "Đệm silicon bám giày cực chắc", img: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("tất đá bóng chống trơn") },
          { title: "Túi Đựng Giày Đá Bóng 2 Ngăn Chống Nước", tag: "Shopee Mall", subtitle: "Gọn nhẹ mang đi sân mỗi tuần", img: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("túi đựng giày đá bóng") }
        ], vidId)
      };
    }

    // 2. Chạy bộ / Marathon / Yoga / Pilates / Tập luyện
    if (/marathon|yoga|pilates|chạy bộ|vận động viên|thể thao|tập gym|sức mạnh|thể lực/.test(text)) {
      return {
        badge: "THỂ THAO",
        items: pickVariedItems([
          { title: "Giày Chạy Bộ Đệm Êm Nhẹ Siêu Bền", tag: "Bán chạy Shopee", subtitle: "Phù hợp chạy marathon & tập hàng ngày", img: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("giày chạy bộ nam nữ êm chân") },
          { title: "Thảm Tập Yoga TPE 2 Lớp Chống Trượt", tag: "Shopee Mall", subtitle: "Dày 8mm kèm dây đai và túi đựng", img: "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("thảm tập yoga tpe chống trượt") },
          { title: "Đồng Hồ Thể Thao Đo Nhịp Tim & Bước Chân", tag: "Ưu đãi Shopee", subtitle: "Pin trâu 14 ngày, kháng nước 5ATM", img: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("đồng hồ thông minh thể thao") },
          { title: "Bình Nước Thể Thao Dung Tích Lớn 1L", tag: "Deal Hời", subtitle: "Nhựa Tritan an toàn, có vạch chia giờ", img: "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("bình nước thể thao 1 lít") }
        ], vidId)
      };
    }

    // 3. Ẩm thực / Quán ăn / Mì / Nấu nướng
    if (/quán mì|bát|ăn|nướng|món ăn|ẩm thực|cà phê|trà|nhà bếp|nấu/.test(text)) {
      return {
        badge: "ẨM THỰC",
        items: pickVariedItems([
          { title: "Nồi Lẩu Điện Đa Năng Chống Dính 2 Tầng", tag: "Bán chạy Shopee", subtitle: "Nấu mì, hấp, chiên xào tiện lợi", img: "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("nồi lẩu điện mini đa năng") },
          { title: "Bộ Bát Đũa Gốm Sứ Phong Cách Nhật", tag: "Shopee Mall", subtitle: "Men sứ cao cấp an toàn lò vi sóng", img: "https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("bộ bát đũa gốm sứ nhật bản") },
          { title: "Hộp Cơm Cắm Điện Giữ Nhiệt Văn Phòng", tag: "Ưu đãi Shopee", subtitle: "Hâm nóng đồ ăn nhanh trong 5 phút", img: "https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("hộp cơm cắm điện giữ nhiệt") },
          { title: "Combo Gia Vị Nấu Mì Cay & Lẩu Tứ Xuyên", tag: "Hot Trend", subtitle: "Chuẩn vị quán, dễ nấu tại nhà", img: "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("gói gia vị lẩu mì cay") }
        ], vidId)
      };
    }

    // 4. Sách / Văn học / Lịch sử
    if (/hoàng tử bé|sách|truyện|bông hồng|chiến tranh|lịch sử|nhà ngô|bùi thị xuân|thời tống|kinh đô|dinh độc lập|đọc sách|tác phẩm/.test(text)) {
      return {
        badge: "SÁCH HAY",
        items: pickVariedItems([
          { title: "Sách Hoàng Tử Bé (Bản In Màu Bìa Cứng)", tag: "Bestseller", subtitle: "Giảm tới 30% trên Shopee", img: "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("sách Hoàng Tử Bé") },
          { title: "Sách Lịch Sử & Văn Hóa Việt Nam Hay Nhất", tag: "Shopee Mall", subtitle: "Sách chính hãng NXB Trẻ / Nhã Nam", img: "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("sách lịch sử việt nam hay") },
          { title: "Đèn Đọc Sách Chống Cận & Đèn Ngủ Tiểu Hành Tinh", tag: "Đánh giá cao", subtitle: "Ánh sáng dịu mắt ban đêm", img: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("đèn đọc sách chống cận") },
          { title: "Kệ Sách Gỗ Để Bàn Lắp Ráp Tiện Lợi", tag: "Ưu đãi Shopee", subtitle: "Gọn gàng góc học tập và làm việc", img: "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("kệ sách gỗ để bàn") }
        ], vidId)
      };
    }

    // 5. Công nghệ / AI / Điện thoại / Khoa học
    if (/điện thoại|jensen huang|nvidia|chip|ai|khoa học|laptop|game|tiktoker|công nghệ|máy tính/.test(text)) {
      return {
        badge: "CÔNG NGHỆ",
        items: pickVariedItems([
          { title: "Củ Sạc Nhanh GaN 65W Nhỏ Gọn Đa Cổng", tag: "Shopee Mall", subtitle: "Sạc cùng lúc điện thoại và laptop", img: "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("củ sạc nhanh gan 65w") },
          { title: "Tai Nghe Bluetooth Chống Ồn Chủ Động ANC", tag: "Bán chạy Shopee", subtitle: "Pin 30 giờ, âm bass sâu rõ nét", img: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("tai nghe bluetooth chống ồn anc") },
          { title: "Chuột Không Dây Yên Tĩnh Pin Sạc", tag: "Ưu đãi Shopee", subtitle: "Kết nối Bluetooth & USB siêu nhạy", img: "https://images.unsplash.com/photo-1527814050087-3793815479db?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("chuột không dây silent") },
          { title: "Giá Đỡ Laptop & Điện Thoại Hợp Kim Nhôm", tag: "Deal Hời", subtitle: "Gập gọn tản nhiệt tốt chống mỏi cổ", img: "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("giá đỡ laptop hợp kim nhôm") }
        ], vidId)
      };
    }

    // 6. Phong thủy / Con giáp / Tài lộc
    if (/con giáp|mưa tài lộc|giàu sang|tài lộc|phong thủy|vận may|đổi vận|thắp hương|viên mãn/.test(text)) {
      return {
        badge: "PHONG THỦY",
        items: pickVariedItems([
          { title: "Vòng Tay Đá Phong Thủy Hút Tài Lộc", tag: "Bán chạy Shopee", subtitle: "Đủ mệnh Kim - Mộc - Thủy - Hỏa - Thổ", img: "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("vòng tay đá phong thủy tài lộc") },
          { title: "Ví Da Nam Nữ Dáng Dài Giữ Lộc", tag: "Deal Hot", subtitle: "Da thật cao cấp, nhiều ngăn tiện lợi", img: "https://images.unsplash.com/photo-1627123424574-724758594e93?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("ví da nam nữ cao cấp") },
          { title: "Mèo Thần Tài & Tượng Phong Thủy Để Bàn", tag: "Ưu đãi Shopee", subtitle: "Trang trí bàn làm việc & cửa hàng", img: "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("mèo thần tài để bàn") },
          { title: "Nụ Trầm Hương Tự Nhiên Thư Giãn", tag: "Shopee Mall", subtitle: "Hương dịu nhẹ thanh lọc không gian", img: "https://images.unsplash.com/photo-1602928321679-560bb453f190?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("nụ trầm hương tự nhiên") }
        ], vidId)
      };
    }

    // 7. Du lịch / Khám phá / Kiến trúc
    if (/du lịch|khám phá|á đinh|tứ xuyên|khai phong|công viên|biển|núi|tàu cao tốc|phượt|ngôi nhà|chợ đông xuân|việt nam có một nơi/.test(text)) {
      return {
        badge: "DU LỊCH",
        items: pickVariedItems([
          { title: "Balo Du Lịch Chống Nước Đa Năng", tag: "Bán chạy Shopee", subtitle: "Đựng laptop và quần áo 3-5 ngày", img: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("balo du lịch chống nước") },
          { title: "Vali Kéo Du Lịch Size 20 Chống Vỡ", tag: "Shopee Mall", subtitle: "Khóa số TSA an toàn đi máy bay", img: "https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("vali kéo du lịch size 20") },
          { title: "Sạc Dự Phòng Sạc Nhanh 20.000mAh", tag: "Ưu đãi Shopee", subtitle: "Nhỏ gọn mang lên máy bay", img: "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("sạc dự phòng 20000mah sạc nhanh") },
          { title: "Gối Cổ Du Lịch Cao Su Non Gấp Gọn", tag: "Deal Hời", subtitle: "Êm ái đi tàu xe và máy bay", img: "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("gối cổ du lịch cao su non") }
        ], vidId)
      };
    }

    // 8. Đời sống / Thời tiết / Gia đình / Sức khỏe / Mặc định đa dạng theo video.id
    return {
      badge: "ĐỜI SỐNG",
      items: pickVariedItems([
        { title: "Áo Khoác Gió Giữ Nhiệt Chống Nước", tag: "Bán chạy Shopee", subtitle: "Form đẹp mặc đôi nam nữ", img: "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("áo khoác gió giữ nhiệt") },
        { title: "Bình Giữ Nhiệt Inox 304 LocknLock", tag: "Shopee Mall", subtitle: "Giữ nóng lạnh suốt 12 giờ", img: "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("bình giữ nhiệt inox 304") },
        { title: "Máy Massage Cổ Vai Gáy Hồng Ngoại", tag: "Ưu đãi Shopee", subtitle: "Thư giãn giảm mỏi sau ngày dài", img: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("máy massage cổ vai gáy") },
        { title: "Tai Nghe Bluetooth Chống Ồn Pin Trâu", tag: "Bán chạy Shopee", subtitle: "Âm thanh nổi xem clip cực đã", img: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("tai nghe bluetooth chống ồn") },
        { title: "Đèn Ngủ Cảm Biến Thông Minh Siêu Tiết Kiệm", tag: "Deal Hời", subtitle: "Ánh sáng ấm áp cho phòng ngủ", img: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("đèn ngủ cảm biến thông minh") },
        { title: "Sạc Dự Phòng Mini Sạc Nhanh 22.5W", tag: "Shopee Mall", subtitle: "Nhỏ gọn bỏ túi, bảo hành 12 tháng", img: "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=240&auto=format&fit=crop&q=80", url: buildShopeeAffSearchUrl("sạc dự phòng mini sạc nhanh") }
      ], vidId)
    };
  }

  function renderRelatedProductsForVideo(videoData) {
    if (!relatedProductsList) return;
    relatedProductsList.innerHTML = "";

    const prebuilt = Array.isArray(videoData?.relatedProducts) && videoData.relatedProducts.length > 0
      ? { badge: "SÁT CHỦ ĐỀ", items: videoData.relatedProducts }
      : getContextualFallbackProducts(videoData);

    if (relatedTopicBadge) {
      relatedTopicBadge.textContent = prebuilt.badge;
    }

    prebuilt.items.forEach(prod => {
      const card = document.createElement("a");
      card.className = "flash-prod-card";
      card.href = prod.url || (CONFIG.affiliate && CONFIG.affiliate.primaryUrl) || "https://shopee.vn/flash_sale";
      card.target = "_blank";
      card.rel = "noopener noreferrer";
      card.style.textDecoration = "none";
      card.style.color = "inherit";
      card.innerHTML = `
        <img class="flash-prod-img" src="${prod.img}" alt="${prod.title}" loading="lazy" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=240&auto=format&fit=crop&q=80';">
        <div class="flash-prod-info">
          <div class="flash-prod-title">${prod.title}</div>
          <div style="font-size:11px; color: var(--text-muted); margin-top:2px;">${prod.subtitle || "Top bán chạy trên Shopee"}</div>
          <div class="flash-sold-row" style="margin-top:6px;">
            <span style="color:#ff9f43; font-weight:600;">${prod.tag || "Bán chạy"}</span>
            <span class="flash-buy-btn">XEM GIÁ</span>
          </div>
        </div>
      `;
      relatedProductsList.appendChild(card);
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

    const cleanLiveMessages = CONFIG.liveChatMessages.filter(
      m => !/freeship|mã 50%|voucher/i.test(m.text || "")
    );
    (cleanLiveMessages.length ? cleanLiveMessages : CONFIG.liveChatMessages).forEach(
      m => appendChatMessage(m.user, m.text)
    );

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

  // 9. Gắn sự kiện cho các nút tương tác phụ (Tim, Theo dõi, Chia sẻ, Hashtag lọc video)
  const likeBtn = document.getElementById("likeBtn");
  const dockLikeBtn = document.getElementById("dockLikeBtn");
  const likedVideoIds = new Set();

  function formatLikeDelta(rawStr, delta) {
    const s = String(rawStr || "0").trim();
    const m = s.match(/^([0-9]+(?:\.[0-9]+)?)\s*([KM]?)$/i);
    if (!m) return s;
    const base = parseFloat(m[1]);
    const suffix = (m[2] || "").toUpperCase();
    if (suffix === "K") return `${Math.max(0, base + delta * 0.1).toFixed(1)}K`;
    if (suffix === "M") return `${Math.max(0, base + delta * 0.01).toFixed(2)}M`;
    return String(Math.max(0, Math.round(base + delta)));
  }

  function syncLikeUI() {
    const isLiked = likedVideoIds.has(currentVideoId);
    const label = isLiked ? "Đã thích" : "Thích";
    if (videoLikes) videoLikes.textContent = label;
    if (dockLikesCount) dockLikesCount.textContent = label;
    if (likeBtn) likeBtn.classList.toggle("active", isLiked);
    if (dockLikeBtn) {
      dockLikeBtn.classList.toggle("active", isLiked);
      dockLikeBtn.style.color = isLiked ? "#ff2a5f" : "";
    }
  }

  function toggleLike() {
    if (likedVideoIds.has(currentVideoId)) {
      likedVideoIds.delete(currentVideoId);
    } else {
      likedVideoIds.add(currentVideoId);
    }
    syncLikeUI();
  }
  if (likeBtn) likeBtn.addEventListener("click", toggleLike);
  if (dockLikeBtn) dockLikeBtn.addEventListener("click", toggleLike);

  // Nút Theo dõi kênh
  const followBtn = document.getElementById("followBtn");
  if (followBtn) {
    let isFollowing = true;
    followBtn.addEventListener("click", function () {
      isFollowing = !isFollowing;
      followBtn.textContent = isFollowing ? "Đã theo dõi ✓" : "+ Theo dõi";
      followBtn.style.opacity = isFollowing ? "1" : "0.85";
      followBtn.style.background = isFollowing ? "" : "rgba(255,255,255,0.12)";
    });
  }

  // Click Hashtag xu hướng để lọc video & cuộn xuống danh sách
  const hotTagsWrap = document.getElementById("hotTagsWrap");
  if (hotTagsWrap) {
    const tagToCat = {
      "#24hKhamPha": "explore",
      "#24hTinNong": "news",
      "#VuTruThoVaGau3D": "all",
      "#BanTin3D": "all",
      "#ThoNews247": "all",
      "#FullHD1080P": "all"
    };
    const chips = hotTagsWrap.querySelectorAll(".tag-chip");
    chips.forEach(chip => {
      chip.style.cursor = "pointer";
      chip.addEventListener("click", function () {
        const tagText = (chip.textContent || "").trim();
        const targetCat = tagToCat[tagText] || "all";
        chips.forEach(c => { c.style.borderColor = ""; c.style.color = ""; });
        chip.style.borderColor = "#ff2a5f";
        chip.style.color = "#fff";

        currentCategory = targetCat;
        currentPage = 1;
        const tabContainer = document.getElementById("categoryTabsBar");
        if (tabContainer) {
          tabContainer.querySelectorAll(".cat-tab-btn").forEach(b => {
            b.classList.toggle("active", (b.dataset.cat || "all") === targetCat);
          });
        }
        renderSuggestedVideos();
        document.getElementById("suggestedSection")?.scrollIntoView({ behavior: "smooth" });
      });
    });
  }

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

  // Khởi chạy toàn bộ ứng dụng (không mô phỏng bình luận/người xem giả)
  initCategoryTabs();
  loadMainVideo(currentVideoId, false);
  syncLikeUI();
  renderLeftSidebarWidgets();
});
