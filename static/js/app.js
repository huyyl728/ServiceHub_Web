/* ServiceHub UI controller. API calls are delegated to api.js; view rendering stays here. */
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const state = {
    user: null,
    profile: null,
    services: [],
    businessId: null,
    authMode: "login",
    bookingService: null,
  };
  const discoveryState = {
    step: 0,
    answers: { goal: null, vibe: null, budget: null },
    shown: false,
  };
  const money = (n) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
      maximumFractionDigits: 0,
    }).format(Number(n || 0));
  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const statusName = (s) =>
    ({
      pending: "Chờ xác nhận",
      confirmed: "Đã xác nhận",
      completed: "Hoàn thành",
      cancelled: "Đã hủy",
      rejected: "Từ chối",
      approved: "Đã chấp thuận",
      changes_requested: "Cần bổ sung",
    })[s] ||
    s ||
    "Chưa có";
  const statusClass = (s) =>
    [
      "pending",
      "confirmed",
      "completed",
      "cancelled",
      "rejected",
      "approved",
    ].includes(s)
      ? s
      : s === "changes_requested"
        ? "pending"
        : "";
  const activityLabel = (a) =>
    ({
      login: "Đăng nhập",
      logout: "Đăng xuất",
      profile_updated: "Cập nhật hồ sơ",
      business_application_submitted: "Gửi hồ sơ cơ sở",
      business_profile_updated: "Cập nhật thông tin cơ sở",
      service_image_uploaded: "Tải ảnh dịch vụ",
      media_uploaded: "Cập nhật ảnh cơ sở",
      application_approved: "Duyệt hồ sơ cơ sở",
      application_rejected: "Từ chối hồ sơ cơ sở",
    })[a] || a.replaceAll("_", " ");
  function toast(message, error = false) {
    const el = document.createElement("div");
    el.className = "toast" + (error ? " error" : "");
    el.textContent = message;
    $("#toast-region").append(el);
    setTimeout(() => el.remove(), 4200);
  }
  function setMessage(el, message, error = false) {
    if (!el) return;
    el.textContent = message;
    el.classList.toggle("error", error);
  }
  function showView(name) {
    const target = $(`#view-${name}`);
    if (!target) name = "home";
    $$(".view").forEach((v) =>
      v.classList.toggle("active", v.id === `view-${name}`),
    );
    $$(".nav-link").forEach((b) =>
      b.classList.toggle("active", b.dataset.view === name),
    );
    const meta = {
      home: [
        "ServiceHub | Khám phá và đặt lịch dịch vụ",
        "Khám phá nhà hàng, spa, salon và dịch vụ thể thao trên ServiceHub.",
      ],
      services: [
        "Khám phá dịch vụ | ServiceHub",
        "Tìm dịch vụ theo danh mục, xem giá và thông tin cơ sở.",
      ],
      bookings: [
        "Lịch đặt của tôi | ServiceHub",
        "Theo dõi các yêu cầu đặt lịch của bạn.",
      ],
      profile: [
        "Tài khoản | ServiceHub",
        "Quản lý hồ sơ cá nhân và đăng ký làm chủ cơ sở.",
      ],
      owner: [
        "Quản lý cơ sở | ServiceHub",
        "Quản lý dịch vụ, hình ảnh và lịch đặt của cơ sở.",
      ],
      admin: ["Quản trị | ServiceHub", "Khu vực quản trị và xét duyệt hồ sơ."],
    }[name] || ["ServiceHub", "Khám phá và đặt lịch dịch vụ."];
    document.title = meta[0];
    const desc = document.querySelector('meta[name="description"]');
    if (desc) desc.content = meta[1];
    const labels = {
      home: "Trang chủ",
      services: "Khám phá dịch vụ",
      bookings: "Lịch đặt của tôi",
      profile: "Tài khoản",
      owner: "Quản lý cơ sở",
      admin: "Quản trị",
    };
    const crumbs = $("#breadcrumbs");
    if (crumbs) {
      crumbs.classList.toggle("hidden", name === "home");
      $("#breadcrumb-current").textContent = labels[name] || "Trang chủ";
    }
    $(".main-nav").classList.remove("open");
    history.replaceState(null, "", `#${name}`);
    if (name === "services") loadServices();
    if (name === "profile") loadProfile();
    if (name === "bookings") loadBookings();
    if (name === "owner") loadOwner();
    if (name === "admin") loadAdmin();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function updateAuthUI() {
    const user = state.user;
    $("#session-label").textContent = user ? user.name : "Chưa đăng nhập";
    $("#open-auth").classList.toggle("hidden", Boolean(user));
    $("#logout-btn").classList.toggle("hidden", !user);
    $$(".auth-nav").forEach((el) => el.classList.toggle("hidden", !user));
    $(".owner-nav").classList.toggle(
      "hidden",
      !user || !state.profile?.businesses?.length,
    );
    $(".admin-nav").classList.toggle("hidden", !user || !user.is_admin);
    $("#notification-shortcut").classList.toggle("hidden", !user);
    if (!user) {
      $("#notification-badge").classList.add("hidden");
      $("#notification-badge").textContent = "0";
    }
  }
  async function syncUser() {
    if (!API.hasToken()) {
      state.user = null;
      state.profile = null;
      updateAuthUI();
      return;
    }
    try {
      const r = await API.get("/api/me");
      state.profile = r.data;
      state.user = r.data.user;
      API.saveSession({
        token: localStorage.getItem("servicehub_token"),
        user: state.user,
      });
    } catch {
      API.clearSession();
      state.user = null;
      state.profile = null;
    }
    updateAuthUI();
    if (state.user) refreshNotificationBadge();
  }
  function openModal(id) {
    $(`#${id}`).classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }
  function closeModals() {
    $$(".modal").forEach((m) => m.classList.add("hidden"));
    document.body.style.overflow = "";
  }
  function authMode(mode) {
    state.authMode = mode;
    $("#auth-title").textContent =
      mode === "login" ? "Chào mừng trở lại" : "Tạo tài khoản ServiceHub";
    $("#auth-submit").textContent =
      mode === "login" ? "Đăng nhập" : "Tạo tài khoản";
    $("#auth-name-wrap").classList.toggle("hidden", mode === "login");
    $("#auth-phone-wrap").classList.toggle("hidden", mode === "login");
    $("#auth-name-wrap input").required = mode === "register";
    $("#auth-name-wrap input").disabled = mode === "login";
    $("#auth-phone-wrap input").disabled = mode === "login";
    $$(".auth-tab").forEach((b) =>
      b.classList.toggle("active", b.dataset.authMode === mode),
    );
    setMessage($("#auth-message"), "");
  }
  async function submitAuth(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const path =
        state.authMode === "login" ? "/api/auth/login" : "/api/auth/register";
      const result = await API.post(path, payload);
      API.saveSession(result.data);
      await syncUser();
      closeModals();
      toast(
        state.authMode === "login"
          ? "Đăng nhập thành công."
          : "Tạo tài khoản thành công.",
      );
      showView("home");
    } catch (e) {
      setMessage($("#auth-message"), e.message, true);
    }
  }
  function serviceCard(s) {
    const icons = {
      "Sân bóng": "⚽",
      "Thể thao": "◉",
      "Làm đẹp": "✂",
      Spa: "✦",
      "Nhà hàng": "⌂",
    };
    const photo = s.image_path || s.business_banner;
    const visual = photo
      ? `<img src="${esc(photo)}" alt="${s.image_path ? `Ảnh dịch vụ ${esc(s.name)}` : `Ảnh cơ sở ${esc(s.business_name || s.name)}`}" loading="lazy" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display='none';this.parentElement.classList.add('no-photo')">`
      : `<span>${icons[s.category] || "✦"}</span>`;
    const maps =
      "https://www.google.com/maps/search/?api=1&query=" +
      encodeURIComponent(s.business_address || "");
    return `<article class="service-card"><button type="button" class="service-detail-trigger" data-business-detail="${s.business_id}" aria-label="Xem chi tiết ${esc(s.business_name || s.name)}"><div class="service-visual ${photo ? "has-photo" : ""}">${visual}<span class="service-category">${esc(s.category)}</span></div></button><div class="service-content"><h3><button type="button" class="text-button" data-business-detail="${s.business_id}">${esc(s.name)}</button></h3><p>${esc(s.description || "Thông tin dịch vụ đang được cập nhật.")}</p><div class="service-meta"><span>⌖ ${esc(s.business_name || "ServiceHub Partner")}</span><span>◷ ${Number(s.duration_minutes || 60)} phút</span></div><p class="service-address">${esc(s.business_address || "Địa chỉ đang cập nhật")} · <a href="${maps}" target="_blank" rel="noopener noreferrer">Chỉ đường ↗</a></p><div class="service-footer"><span class="price">${Number(s.price) === 0 ? "Liên hệ" : money(s.price)} <small>/ lượt</small></span><button class="btn btn-dark" data-book-service="${s.id}">Đặt lịch ↗</button></div></div></article>`;
  }
  async function openBusinessDetails(id) {
    const host = $("#business-detail-content");
    host.innerHTML = '<p class="muted">Đang tải thông tin cơ sở...</p>';
    openModal("business-detail-modal");
    try {
      const r = await API.get(`/api/businesses/${Number(id)}`),
        d = r.data,
        b = d.business;
      const photo = b.banner_path
        ? `<img class="business-detail-banner" src="${esc(b.banner_path)}" alt="Ảnh ${esc(b.name)}">`
        : "";
      const services =
        d.services
          .map(
            (s) =>
              `<article class="business-detail-service">${s.image_path ? `<img src="${esc(s.image_path)}" alt="${esc(s.name)}">` : ""}<div class="business-detail-service-main"><b>${esc(s.name)}</b><p>${esc(s.description || "Thông tin dịch vụ đang được cập nhật.")}</p><small>${Number(s.duration_minutes || 60)} phút</small></div><div class="business-detail-service-action"><strong>${Number(s.price) === 0 ? "Liên hệ" : money(s.price)}</strong><button class="btn btn-dark btn-small" data-book-service="${s.id}">Đặt lịch</button></div></article>`,
          )
          .join("") || '<p class="muted">Cơ sở chưa đăng dịch vụ.</p>';
      const memberships =
        d.memberships
          .map((m) => {
            const joined = state.profile?.memberships?.some(
              (x) => Number(x.program_id) === Number(m.id),
            );
            return `<article class="business-membership"><div><b>${esc(m.name)}</b><p>${esc(m.description || "Chương trình hội viên riêng của cơ sở.")}</p><small>Điểm tích lũy: ${Number(m.points_per_currency || 1)} điểm cho mỗi đơn vị tiền theo quy định chương trình.</small></div>${joined ? '<span class="status-pill">Đã tham gia</span>' : `<button class="btn btn-light btn-small" data-join-membership="${m.id}">Đăng ký hội viên</button>`}</article>`;
          })
          .join("") ||
        '<p class="muted">Quán chưa thiết lập chương trình hội viên.</p>';
      host.innerHTML = `${photo}<p class="eyebrow">THÔNG TIN CƠ SỞ</p><h2 id="business-detail-title" data-business-id="${b.id}">${esc(b.name)}</h2><p class="business-detail-category">${esc(b.category)}</p><p>${esc(b.description || "Cơ sở chưa cập nhật phần giới thiệu.")}</p><div class="business-detail-contact"><p><b>Địa chỉ:</b> ${esc(b.address || "Chưa cập nhật")}</p><p><b>Điện thoại:</b> ${esc(b.phone || "Chưa cập nhật")}</p><a class="btn btn-outline btn-small" href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(b.address || "")}" target="_blank" rel="noopener noreferrer">Xem bản đồ ↗</a></div><h3 class="detail-section-title">Dịch vụ và thực đơn</h3><div class="business-detail-services">${services}</div><h3 class="detail-section-title">Chương trình hội viên của quán</h3><p class="muted">Mỗi cơ sở có chương trình và quyền lợi riêng. Đăng nhập để tham gia và xem hội viên trong hồ sơ của bạn.</p><div class="business-memberships">${memberships}</div>`;
    } catch (e) {
      host.innerHTML = `<h2>Không tải được thông tin</h2><p class="muted">${esc(e.message)}</p>`;
    }
  }
  const SEARCH_GROUPS = [
    {
      label: "Quán ăn và nhà hàng",
      terms: [
        "quan an",
        "nha hang",
        "an uong",
        "am thuc",
        "quan xa",
        "di an",
        "food",
      ],
      category: ["nhà hàng", "quan an", "ẩm thực"],
      icon: "🍜",
    },
    {
      label: "Đồ ăn sáng",
      terms: [
        "an sang",
        "pho",
        "bun",
        "banh mi",
        "xoi",
        "chao",
        "hu tieu",
        "mi",
      ],
      category: ["nhà hàng", "ẩm thực"],
      icon: "🥖",
    },
    {
      label: "Cà phê và đồ uống",
      terms: ["ca phe", "cafe", "tra sua", "do uong", "nuoc ep", "sinh to"],
      category: ["đồ uống", "cà phê"],
      icon: "☕",
    },
    {
      label: "Sân bóng và thể thao",
      terms: [
        "da bong",
        "san bong",
        "bong da",
        "the thao",
        "san mini",
        "pickleball",
        "cau long",
        "tennis",
      ],
      category: ["sân bóng", "thể thao"],
      icon: "⚽",
    },
    {
      label: "Cắt tóc và salon",
      terms: [
        "cat toc",
        "salon",
        "barber",
        "tao kieu toc",
        "nhuom toc",
        "uon toc",
      ],
      category: ["làm đẹp", "salon"],
      icon: "✂️",
    },
    {
      label: "Spa và chăm sóc da",
      terms: [
        "spa",
        "lam dep",
        "cham soc da",
        "massage",
        "thu gian",
        "lam mong",
        "nail",
      ],
      category: ["spa", "làm đẹp"],
      icon: "✨",
    },
  ];
  const norm = (v) =>
    String(v || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .trim();
  function relevantServices(items, query, category = "") {
    const q = norm(query);
    const words = q.split(/\s+/).filter(Boolean);
    const expanded = new Set([q]);
    SEARCH_GROUPS.forEach((g) => {
      if (
        g.terms.some((t) => norm(t).includes(q) || q.includes(norm(t))) ||
        (g.label && norm(g.label).includes(q))
      ) {
        g.terms.forEach((t) => expanded.add(norm(t)));
        expanded.add(norm(g.label));
      }
    });
    return items
      .map((s) => {
        const fields = [
          s.name,
          s.description,
          s.category,
          s.business_name,
          s.business_address,
        ].map(norm);
        const hay = fields.join(" ");
        let score = 0;
        if (q && fields[0] === q) score += 15;
        if (q && fields[0].includes(q)) score += 9;
        if (q && fields[2].includes(q)) score += 8;
        if (q && fields[3].includes(q)) score += 6;
        if (q && fields[1].includes(q)) score += 4;
        words.forEach((w) => {
          if (w.length > 1 && hay.includes(w)) score += 2;
        });
        if (q)
          for (const term of expanded) {
            if (term !== q && term.length > 2 && hay.includes(term))
              score += 1.5;
          }
        if (category && norm(s.category) !== norm(category)) score = -1;
        return { s, score };
      })
      .filter((x) => (!q || x.score > 0) && x.score >= 0)
      .sort(
        (a, b) =>
          b.score - a.score ||
          String(a.s.name).localeCompare(String(b.s.name), "vi"),
      )
      .map((x) => x.s);
  }
  function hideSuggestions() {
    const box = $("#search-suggestions"),
      input = $("#service-search");
    if (box) {
      box.classList.add("hidden");
      box.innerHTML = "";
    }
    if (input) input.setAttribute("aria-expanded", "false");
  }
  function showSuggestions() {
    const input = $("#service-search"),
      box = $("#search-suggestions");
    if (!input || !box) return;
    const q = input.value.trim();
    if (!q) {
      hideSuggestions();
      return;
    }
    const nq = norm(q);
    const matches = SEARCH_GROUPS.filter(
      (g) =>
        norm(g.label).includes(nq) ||
        g.terms.some((t) => norm(t).includes(nq) || nq.includes(norm(t))),
    ).slice(0, 4);
    const live = relevantServices(state.allServices || [], q).slice(0, 3);
    const options = [
      ...matches.map((g) => ({
        label: g.label,
        sub: "Tìm theo danh mục",
        icon: g.icon,
        query: g.label,
      })),
      ...live.map((s) => ({
        label: s.name,
        sub: `${s.business_name || s.category} · ${money(s.price)}`,
        icon: "⌕",
        query: s.name,
      })),
    ]
      .filter(
        (x, i, a) => a.findIndex((y) => norm(y.label) === norm(x.label)) === i,
      )
      .slice(0, 6);
    if (!options.length) {
      box.innerHTML =
        '<div class="suggestion-empty">Chưa có gợi ý chính xác. Nhấn Tìm kiếm để thử từ khóa này.</div>';
    } else
      box.innerHTML = options
        .map(
          (o, i) =>
            `<button type="button" class="suggestion-option" role="option" data-suggestion="${esc(o.query)}"><span class="suggestion-icon">${o.icon}</span><span><b>${esc(o.label)}</b><small>${esc(o.sub)}</small></span><span class="suggestion-arrow">↗</span></button>`,
        )
        .join("");
    box.classList.remove("hidden");
    input.setAttribute("aria-expanded", "true");
  }
  function renderDiscoveryStep() {
    const advisor = window.ServiceHubAdvisor;
    if (!advisor) return;
    const { questions } = advisor,
      step = discoveryState.step,
      question = questions[step];
    $("#discovery-step-label").textContent =
      `Câu ${step + 1} / ${questions.length}`;
    const progress = $("#discovery-progress");
    progress.setAttribute("aria-valuenow", String(step + 1));
    $("#discovery-progress-fill").style.width =
      `${((step + 1) / questions.length) * 100}%`;
    $("#discovery-question").textContent = question.title;
    $("#discovery-note").textContent = question.note;
    $("#discovery-options").innerHTML = question.options
      .map((option) => {
        const active = discoveryState.answers[question.key] === option.id;
        return `<button type="button" class="discovery-option${active ? " selected" : ""}" data-discovery-option="${esc(option.id)}" aria-pressed="${active}"><span class="discovery-option-icon" aria-hidden="true">${option.icon}</span><span><strong>${esc(option.label)}</strong><small>${esc(option.hint)}</small></span><span class="discovery-option-check" aria-hidden="true">${active ? "✓" : "→"}</span></button>`;
      })
      .join("");
    $("#discovery-back").disabled = step === 0;
    const next = $("#discovery-next");
    next.disabled = !discoveryState.answers[question.key];
    next.textContent =
      step === questions.length - 1 ? "Xem gợi ý phù hợp ↗" : "Tiếp tục →";
    const labels = ["goal", "vibe", "budget"].map((key, i) => {
      const value = discoveryState.answers[key];
      const selected = questions[i].options.find(
        (option) => option.id === value,
      );
      return `<span class="${selected ? "answered" : ""}">${i + 1}. ${selected ? esc(selected.label) : ["Bạn muốn làm gì?", "Kiểu trải nghiệm?", "Ngân sách dự kiến?"][i]}</span>`;
    });
    $("#discovery-answers").innerHTML = labels.join("");
    if (!discoveryState.shown) $("#discovery-results").classList.add("hidden");
  }
  function renderDiscoveryResults() {
    const host = $("#discovery-results"),
      advisor = window.ServiceHubAdvisor;
    if (!advisor) return;
    discoveryState.shown = true;
    host.classList.remove("hidden");
    if (!Array.isArray(state.allServices)) {
      host.innerHTML =
        '<div class="discovery-empty"><h3>Chưa tải được danh sách dịch vụ</h3><p>Vui lòng kiểm tra máy chủ rồi thử tải lại để nhận gợi ý từ dữ liệu thực tế.</p><button class="btn btn-dark" type="button" id="discovery-retry">Tải lại gợi ý ↻</button></div>';
      return;
    }
    const picks = advisor.recommend(
      state.allServices,
      discoveryState.answers,
      3,
    );
    if (!picks.length) {
      host.innerHTML =
        '<div class="discovery-empty"><h3>Chưa có lựa chọn khớp cả ba câu trả lời</h3><p>ServiceHub không tạo dịch vụ giả hoặc tự nhận là còn chỗ. Hãy thử đổi mức ngân sách, loại hoạt động, hoặc khám phá toàn bộ danh sách.</p><div class="discovery-result-actions"><button type="button" class="btn btn-outline" id="discovery-change">Đổi câu trả lời</button><button type="button" class="btn btn-dark" data-view="services">Xem tất cả dịch vụ ↗</button></div></div>';
      return;
    }
    host.innerHTML = `<div class="discovery-result-heading"><div><p class="eyebrow">DỰA TRÊN CÂU TRẢ LỜI CỦA BẠN</p><h3>${picks.length} gợi ý để bạn tham khảo</h3><p>Đề xuất dựa trên loại dịch vụ, thời lượng và giá niêm yết. Vui lòng xem chi tiết và kiểm tra lịch trước khi đặt.</p></div><button type="button" class="btn btn-outline btn-small" id="discovery-restart">↻ Chọn lại</button></div><div class="discovery-result-grid">${picks.map(({ service, reasons }, i) => `<div class="discovery-pick"><div class="discovery-match"><strong>GỢI Ý ${String(i + 1).padStart(2, "0")}</strong><span>${reasons.map(esc).join(" · ")}</span></div>${serviceCard(service)}</div>`).join("")}</div><div class="discovery-bottom-link"><button class="text-link" type="button" data-view="services">Khám phá tất cả dịch vụ ↗</button></div>`;
  }
  function chooseDiscoveryOption(value) {
    const question = window.ServiceHubAdvisor?.questions[discoveryState.step];
    if (!question || !question.options.some((option) => option.id === value))
      return;
    discoveryState.answers[question.key] = value;
    // Choices later in the flow remain valid, but previous results are no longer current.
    discoveryState.shown = false;
    renderDiscoveryStep();
  }
  function resetDiscovery() {
    discoveryState.step = 0;
    discoveryState.answers = { goal: null, vibe: null, budget: null };
    discoveryState.shown = false;
    renderDiscoveryStep();
    $("#discovery-results").classList.add("hidden");
    $("#discovery-assistant").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
  function bindDiscoveryEvents() {
    $("#discovery-options").addEventListener("click", (e) => {
      const option = e.target.closest("[data-discovery-option]");
      if (option) chooseDiscoveryOption(option.dataset.discoveryOption);
    });
    $("#discovery-back").addEventListener("click", () => {
      if (discoveryState.step > 0) {
        discoveryState.step--;
        discoveryState.shown = false;
        renderDiscoveryStep();
      }
    });
    $("#discovery-next").addEventListener("click", () => {
      const question = window.ServiceHubAdvisor?.questions[discoveryState.step];
      if (!question || !discoveryState.answers[question.key]) return;
      if (discoveryState.step < 2) {
        discoveryState.step++;
        discoveryState.shown = false;
        renderDiscoveryStep();
      } else {
        renderDiscoveryResults();
        $("#discovery-results").scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
    $("#discovery-results").addEventListener("click", async (e) => {
      if (e.target.closest("#discovery-restart")) {
        resetDiscovery();
        return;
      }
      if (e.target.closest("#discovery-change")) {
        discoveryState.step = 2;
        discoveryState.shown = false;
        renderDiscoveryStep();
        $("#discovery-assistant").scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
        return;
      }
      if (e.target.closest("#discovery-retry")) {
        await loadServices();
        renderDiscoveryResults();
      }
    });
  }
  async function loadServices() {
    const q = $("#service-search")?.value?.trim() || "";
    const cat = $("#category-filter")?.value || "";
    try {
      const [sr, cr] = await Promise.all([
        API.get("/api/services"),
        API.get("/api/categories"),
      ]);
      state.allServices = sr.data;
      const sel = $("#category-filter");
      const current = sel.value;
      sel.innerHTML =
        '<option value="">Tất cả danh mục</option>' +
        cr.data.map((c) => `<option>${esc(c)}</option>`).join("");
      sel.value = current;
      state.services = relevantServices(state.allServices, q, cat);
      const html = state.services.length
        ? state.services.map(serviceCard).join("")
        : '<div class="empty-state full-width"><h2>Chưa tìm thấy dịch vụ phù hợp</h2><p>Thử cách gọi khác, ví dụ “ăn sáng”, “đá bóng”, “cắt tóc” hoặc chọn một danh mục bên trên.</p><button class="btn btn-outline" type="button" id="clear-service-search">Xóa bộ lọc</button></div>';
      $("#service-results").innerHTML = html;
      if (discoveryState.shown) renderDiscoveryResults();
      const count = $("#service-result-count");
      if (count)
        count.textContent = `${state.services.length} dịch vụ phù hợp${q ? ` với “${q}”` : ""}`;
      $("#home-services").innerHTML =
        (state.allServices || []).slice(0, 3).map(serviceCard).join("") ||
        '<p class="muted">Chưa có dịch vụ.</p>';
      hideSuggestions();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function beginBooking(id) {
    const s =
      state.services.find((x) => Number(x.id) === Number(id)) ||
      (await API.get("/api/services")).data.find(
        (x) => Number(x.id) === Number(id),
      );
    if (!s) return;
    if (!API.hasToken()) {
      toast("Đăng nhập trước khi đặt lịch.");
      openModal("auth-modal");
      return;
    }
    state.bookingService = s;
    const form = $("#booking-form");
    form.reset();
    form.elements.service_id.value = s.id;
    form.elements.date.min = new Date().toISOString().slice(0, 10);
    $("#booking-title").textContent = s.name;
    $("#booking-service-description").textContent =
      `${s.business_name || ""} · ${s.description || ""}`;
    $("#booking-price").textContent =
      Number(s.price) === 0 ? "Liên hệ" : money(s.price);
    form.elements.start_time.innerHTML =
      '<option value="">Chọn ngày trước</option>';
    setMessage($("#booking-message"), "");
    openModal("booking-modal");
  }
  async function loadAvailability() {
    const form = $("#booking-form"),
      date = form.elements.date.value,
      sid = form.elements.service_id.value;
    if (!date || !sid) return;
    const select = form.elements.start_time;
    select.innerHTML = '<option value="">Đang tải khung giờ...</option>';
    try {
      const r = await API.get(
        `/api/services/${sid}/availability?date=${encodeURIComponent(date)}`,
      );
      select.innerHTML = r.data.length
        ? '<option value="">Chọn khung giờ</option>' +
          r.data
            .map(
              (s) =>
                `<option value="${s.start_time}">${s.start_time} – ${s.end_time}</option>`,
            )
            .join("")
        : '<option value="">Không còn khung giờ trống</option>';
    } catch (e) {
      select.innerHTML = '<option value="">Không tải được lịch trống</option>';
      setMessage($("#booking-message"), e.message, true);
    }
  }
  async function submitBooking(e) {
    e.preventDefault();
    if (!state.user) {
      openModal("auth-modal");
      return;
    }
    const f = e.currentTarget;
    try {
      const r = await API.post("/api/bookings", {
        service_id: Number(f.elements.service_id.value),
        date: f.elements.date.value,
        start_time: f.elements.start_time.value,
      });
      closeModals();
      toast(r.message);
      location.href = "/thank-you";
    } catch (err) {
      setMessage($("#booking-message"), err.message, true);
    }
  }

  async function loadProfile() {
    $("#profile-guest").classList.toggle("hidden", Boolean(state.user));
    $("#profile-content").classList.toggle("hidden", !state.user);
    if (!state.user) return;

    try {
      await syncUser();
      const p = state.profile;
      if (!p?.user) return;

      // Thông tin tài khoản
      $("#profile-name").value = p.user.name;
      $("#profile-email").value = p.user.email;
      $("#profile-phone").value = p.user.phone || "";
      $("#profile-address").value = p.user.address || "";

      // Hồ sơ đăng ký làm chủ cơ sở
      const app = p.applications?.[0];
      const form = $("#application-form");
      const canApply =
        !app || ["rejected", "changes_requested"].includes(app.status);

      $("#application-badge").textContent = app
        ? statusName(app.status)
        : "Chưa đăng ký";

      $("#application-badge").className =
        "status-pill " + statusClass(app?.status);

      $("#application-state").innerHTML = app
        ? `<div class="application-notice"><b>${esc(statusName(app.status))}</b>${esc(app.review_note || (app.status === "pending" ? "Hồ sơ đang chờ quản trị viên xem xét." : app.status === "approved" ? "Bạn có thể mở khu vực quản lý cơ sở." : ""))}</div>`
        : "";

      form.classList.toggle("hidden", !canApply);

      if (canApply && app) {
        for (const key of [
          "business_name",
          "category",
          "address",
          "phone",
          "description",
        ]) {
          if (form.elements[key]) {
            form.elements[key].value = app[key] || "";
          }
        }
      }

      // Lịch sử hoạt động
      try {
        const a = await API.get("/api/activity/me");

        $("#activity-list").innerHTML = a.data.length
          ? a.data
              .map(
                (x) =>
                  `<div class="compact-row">
                <div>
                  <b>${esc(activityLabel(x.action))}</b>
                  <small>${esc(x.created_at)} · ${esc(x.entity_type || "hệ thống")}</small>
                </div>
              </div>`,
              )
              .join("")
          : '<p class="muted">Chưa có hoạt động được ghi nhận.</p>';
      } catch {
        $("#activity-list").innerHTML =
          '<p class="muted">Không tải được lịch sử hoạt động.</p>';
      }

      // Hội viên hiện có
      const m = await API.get("/api/memberships/me");

      $("#membership-list").innerHTML =
        m.data
          .map((x) => {
            const benefits = x.benefits
              ? `<p class="muted">Ưu đãi: ${esc(x.benefits)}</p>`
              : "";

            const action =
              x.points !== null
                ? `<span class="status-pill">${Number(x.points)} điểm</span>`
                : `<button class="btn btn-outline btn-small"
              data-join-membership="${Number(x.id)}">Tham gia</button>`;

            return `<div class="membership-card">
          <b>${esc(x.name)}</b>
          <p>${esc(x.description || "Chương trình hội viên")}</p>
          ${benefits}
          <small>${x.business_name ? `Cơ sở: ${esc(x.business_name)}` : "Hội viên ServiceHub"}</small>
          <div style="margin-top:12px">${action}</div>
        </div>`;
          })
          .join("") || '<p class="muted">Chưa có chương trình hội viên.</p>';

      updateAuthUI();
      await loadNotifications();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function submitApplication(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      await API.post("/api/business-applications", data);
      setMessage($("#application-message"), "Đã gửi hồ sơ thành công.");
      e.currentTarget.reset();
      await loadProfile();
      toast("Hồ sơ đã được gửi để xét duyệt.");
    } catch (err) {
      setMessage($("#application-message"), err.message, true);
    }
  }
  async function loadBookings() {
    if (!state.user) {
      $("#booking-list").innerHTML =
        '<div class="empty-state"><h2>Đăng nhập để xem lịch đặt</h2><button class="btn btn-dark" id="bookings-login">Đăng nhập</button></div>';
      return;
    }
    try {
      const reviewCustomerId = state.user.id;
      const r = await API.get("/api/bookings/me");
      if (state.user?.id !== reviewCustomerId) return;
      $("#booking-list").innerHTML = r.data.length
        ? r.data
            .map(
              (b) =>
                `<article class="booking-card"><div><h3>${esc(b.service_name)}</h3><p>${esc(b.business_name)} · ${esc(b.business_address)}</p><p>Ngày ${esc(b.booking_date)} · ${esc(b.start_time)}–${esc(b.end_time)}</p><p>Giá: <b>${money(b.price)}</b></p></div><div class="booking-right"><span class="status-pill ${statusClass(b.status)}">${esc(statusName(b.status))}</span><div class="row-actions">${
                  ["pending", "confirmed"].includes(b.status)
                    ? `
      <button class="btn btn-outline btn-small"
              data-cancel-booking="${b.id}">
        Hủy lịch
      </button>
    `
                    : ""
                }</div></div></article>`,
            )
            .join("")
        : '<div class="empty-state"><h2>Bạn chưa có lịch đặt</h2><p>Khám phá dịch vụ và đặt lịch đầu tiên của bạn.</p><button class="btn btn-dark" data-view="services">Khám phá dịch vụ</button></div>';
      await renderBookingReviews(
        r.data,
        $$("#booking-list .booking-card"),
        reviewCustomerId
      );
    } catch (e) {
      toast(e.message, true);
    }
  }
  // S4R-03: Hiển thị đánh giá cho lịch đặt đã hoàn thành
async function renderBookingReviews(bookings, cards, customerId) {
  const eligible = bookings
    .map((booking, index) => ({
      booking,
      card: cards[index]
    }))
    .filter(({ booking, card }) =>
      booking.status === "completed" && card
    );

  if (!eligible.length) return;

  const current = () => state.user?.id === customerId;

  const slots = eligible.map(({ booking, card }) => {
    const slot = document.createElement("section");

    slot.className = "customer-review";
    slot.setAttribute(
      "aria-label",
      `Đánh giá lịch đặt ${booking.id}`
    );

    slot.textContent = "Đang tải đánh giá…";
    card.append(slot);

    return { booking, slot };
  });

  try {
    const { data } = await API.get("/api/reviews/me");

    if (!current()) return;

    const reviews = new Map(
      data.map((review) => [
        Number(review.booking_id),
        review
      ])
    );

    slots.forEach(({ booking, slot }) => {
      if (slot.isConnected) {
        renderReviewForm(
          slot,
          booking,
          reviews.get(Number(booking.id)),
          current
        );
      }
    });

  } catch (error) {
    if (!current()) return;

    slots.forEach(({ slot }) => {
      if (slot.isConnected) {
        slot.textContent =
          error.status === 401
            ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
            : `Không tải được đánh giá: ${error.message}. Hãy mở lại Lịch đặt để thử lại.`;
      }
    });
  }
}


// S4R-03: Form viết và chỉnh sửa đánh giá
function renderReviewForm(slot, booking, review, current) {
  slot.replaceChildren();

  const heading = document.createElement("h4");

  heading.textContent = review
    ? "Đánh giá của bạn"
    : "Đánh giá dịch vụ";

  slot.append(heading);

  // Hiển thị đánh giá cũ
  if (review) {
    const summary = document.createElement("p");

    summary.className = "review-summary";

    summary.textContent =
      `${review.rating}/5 sao` +
      (review.comment ? ` · ${review.comment}` : "");

    slot.append(summary);

    // Không cho sửa đánh giá bị ẩn
    if (Number(review.is_visible) !== 1) {
      const notice = document.createElement("p");

      notice.className = "muted";
      notice.textContent =
        "Đánh giá đang bị ẩn; không thể chỉnh sửa.";

      slot.append(notice);
      return;
    }
  }

  const toggle = document.createElement("button");

  toggle.type = "button";
  toggle.className = "btn btn-outline btn-small";

  toggle.textContent = review
    ? "Chỉnh sửa đánh giá"
    : "Viết đánh giá";

  toggle.setAttribute("aria-expanded", "false");

  const form = document.createElement("form");

  form.className = "customer-review-form hidden";
  form.noValidate = true;

  form.innerHTML = `
    <fieldset class="review-rating">
      <legend>Chọn số sao (bắt buộc)</legend>

      ${[1, 2, 3, 4, 5].map((n) => `
        <label>
          <input
            type="radio"
            name="rating"
            value="${n}"
          >
          <span>★ ${n}</span>
        </label>
      `).join("")}

    </fieldset>

    <label>
      Bình luận (tối đa 1000 ký tự)

      <textarea
        name="comment"
        rows="3"
        maxlength="1000"
        placeholder="Chia sẻ trải nghiệm của bạn"
      ></textarea>
    </label>

    <p
      class="form-message"
      role="status"
      aria-live="polite"
    ></p>

    <button
      class="btn btn-dark btn-small"
      type="submit"
    >
      ${review ? "Lưu đánh giá" : "Gửi đánh giá"}
    </button>
  `;

  // Điền dữ liệu cũ khi chỉnh sửa
  if (review) {
    form.elements.rating.value = String(review.rating);
    form.elements.comment.value = review.comment || "";
  }

  // Mở hoặc đóng form
  toggle.addEventListener("click", () => {
    const opening = form.classList.contains("hidden");

    form.classList.toggle("hidden", !opening);

    toggle.setAttribute(
      "aria-expanded",
      String(opening)
    );

    if (opening) {
      form.querySelector('input[name="rating"]')?.focus();
    }
  });

  const message = form.querySelector(".form-message");
  const submit = form.querySelector('button[type="submit"]');

  let saving = false;

  // Gửi dữ liệu đánh giá
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (saving) return;

    const rating = Number(form.elements.rating.value);

    const comment = form.elements.comment.value.trim();

    // Kiểm tra số sao
    if (
      !Number.isInteger(rating) ||
      rating < 1 ||
      rating > 5
    ) {
      return setMessage(
        message,
        "Vui lòng chọn từ 1 đến 5 sao.",
        true
      );
    }

    // Kiểm tra nội dung
    if (comment.length > 1000) {
      return setMessage(
        message,
        "Bình luận không được vượt quá 1000 ký tự.",
        true
      );
    }

    // Kiểm tra đăng nhập
    if (!current() || !API.hasToken()) {
      return setMessage(
        message,
        "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.",
        true
      );
    }

    saving = true;
    submit.disabled = true;

    setMessage(message, "Đang lưu đánh giá…");

    try {
      const result = review
        ? await API.put(
            `/api/reviews/${Number(review.id)}`,
            { rating, comment }
          )
        : await API.post("/api/reviews", {
            booking_id: Number(booking.id),
            rating,
            comment
          });

      if (!current() || !slot.isConnected) return;

      toast(result.message || "Đã lưu đánh giá.");

      renderReviewForm(
        slot,
        booking,
        result.data,
        current
      );

    } catch (error) {
      setMessage(
        message,
        error.status === 401
          ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
          : error.message,
        true
      );

    } finally {
      saving = false;
      submit.disabled = false;
    }
  });

  slot.append(toggle, form);
}
  async function cancelBooking(id) {
    if (!confirm("Bạn có chắc muốn hủy lịch đặt này?")) return;
    try {
      const r = await API.post(`/api/bookings/${id}/cancel`, {});
      toast(r.message);
      loadBookings();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function loadOwner() {
    if (!state.user) {
      $("#owner-locked").classList.remove("hidden");
      $("#owner-content").classList.add("hidden");
      return;
    }
    try {
      await syncUser();
      const businesses = state.profile?.businesses || [];
      if (!businesses.length) {
        $("#owner-locked").classList.remove("hidden");
        $("#owner-content").classList.add("hidden");
        return;
      }
      $("#owner-locked").classList.add("hidden");
      $("#owner-content").classList.remove("hidden");
      const select = $("#owner-business-select");
      const old = state.businessId;
      select.innerHTML = businesses
        .map((b) => `<option value="${b.id}">${esc(b.name)}</option>`)
        .join("");
      state.businessId = businesses.some((b) => Number(b.id) === Number(old))
        ? Number(old)
        : Number(businesses[0].id);
      select.value = state.businessId;
      const b = businesses.find(
        (x) => Number(x.id) === Number(state.businessId),
      );
      const bf = $("#owner-business-form");
      for (const k of ["name", "category", "address", "phone", "description"])
        bf.elements[k].value = b[k] || "";
      $("#business-banner-preview").innerHTML = b.banner_path
        ? `<img class="business-banner" src="${esc(b.banner_path)}" alt="Banner ${esc(b.name)}">`
        : "";
      const [services, bookings, membership, members] = await Promise.all([
        API.get(`/api/owner/services?business_id=${state.businessId}`),
        API.get(`/api/owner/bookings?business_id=${state.businessId}`),
        API.get(`/api/owner/membership?business_id=${state.businessId}`),
        API.get(`/api/owner/members?business_id=${state.businessId}`),
      ]);
      const mf = $("#owner-membership-form");
      for (const k of [
        "name",
        "description",
        "benefits",
        "points_per_currency",
      ])
        mf.elements[k].value =
          membership.data[k] ?? (k === "points_per_currency" ? 1 : "");
      mf.elements.auto_approve_bookings.checked =
        !!membership.data.auto_approve_bookings;
      mf.elements.active.checked = !!membership.data.active;
      $("#owner-member-list").innerHTML = members.data.length
        ? members.data
            .map(
              (m) =>
                `<div class="compact-row"><div><b>${esc(m.member_name)}</b><small>${esc(m.program_name)} · Ngày tham gia: ${esc(m.joined_at)} · ${Number(m.points) || 0} điểm</small></div></div>`,
            )
            .join("")
        : '<p class="muted">Cơ sở này chưa có hội viên tham gia.</p>';
      $("#owner-metrics").innerHTML = [
        ["Dịch vụ", services.data.filter((s) => s.active).length],
        ["Tổng lịch đặt", bookings.data.length],
        [
          "Chờ xác nhận",
          bookings.data.filter((x) => x.status === "pending").length,
        ],
        [
          "Đã hoàn thành",
          bookings.data.filter((x) => x.status === "completed").length,
        ],
      ]
        .map(
          (x) =>
            `<div class="metric-card"><span>${x[0]}</span><strong>${x[1]}</strong></div>`,
        )
        .join("");
      $("#owner-services").innerHTML =
        services.data
          .map(
            (s) =>
              `<div class="compact-row service-owner-row"><div class="service-owner-info">${s.image_path ? `<img class="service-owner-thumb" src="${esc(s.image_path)}" alt="Ảnh dịch vụ ${esc(s.name)}">` : '<div class="service-owner-thumb service-owner-thumb-empty" aria-label="Chưa có ảnh">Ảnh</div>'}<div><b>${esc(s.name)} · ${money(s.price)}</b><small>${esc(s.category)} · ${s.duration_minutes} phút · ${s.active ? "Đang hoạt động" : "Đã tạm ngừng"}</small><label class="service-image-picker">${s.image_path ? "Đổi ảnh dịch vụ" : "Thêm ảnh dịch vụ"}<input type="file" accept="image/png,image/jpeg,image/webp" data-service-image-input="${s.id}" aria-label="Chọn ảnh riêng cho ${esc(s.name)}"></label></div></div><div class="row-actions"><button class="btn btn-outline btn-small" data-edit-service="${s.id}">Sửa</button><button class="btn btn-outline btn-small" data-toggle-service="${s.id}" data-active="${s.active}">${s.active ? "Ngừng" : "Mở lại"}</button></div></div>`,
          )
          .join("") ||
        '<p class="muted">Chưa có dịch vụ. Thêm dịch vụ bằng biểu mẫu phía trên.</p>';
      $("#owner-bookings").innerHTML =
        bookings.data
          .map(
            (b) =>
              `<article class="booking-card"><div><h3>${esc(b.service_name)}</h3><p>Khách: ${esc(b.customer_name)} · ${esc(b.customer_phone || "")}</p><p>${esc(b.booking_date)} · ${esc(b.start_time)}–${esc(b.end_time)} · ${money(b.price)}</p></div><div class="booking-right"><span class="status-pill ${statusClass(b.status)}">${esc(statusName(b.status))}</span><div class="row-actions">${b.status === "pending" ? `<button class="btn btn-dark btn-small" data-owner-booking="confirm" data-id="${b.id}">Xác nhận</button>` : ""}${b.status === "confirmed" ? `<button class="btn btn-dark btn-small" data-owner-booking="complete" data-id="${b.id}">Hoàn thành</button>` : ""}${["pending", "confirmed"].includes(b.status) ? `<button class="btn btn-outline btn-small" data-owner-booking="cancel" data-id="${b.id}">Hủy</button>` : ""}</div></div></article>`,
          )
          .join("") || '<p class="muted">Chưa có lịch đặt nào.</p>';
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function saveBusinessProfile(e) {
    e.preventDefault();
    const f = e.currentTarget;
    const data = Object.fromEntries(new FormData(f).entries());
    try {
      const r = await API.put(
        `/api/owner/businesses/${state.businessId}`,
        data,
      );
      setMessage($("#owner-business-message"), r.message);
      toast(r.message);
      await syncUser();
      await loadOwner();
    } catch (err) {
      setMessage($("#owner-business-message"), err.message, true);
    }
  }
  async function saveOwnerMembership(e) {
    e.preventDefault();
    const f = e.currentTarget;
    const data = {
      business_id: state.businessId,
      name: f.elements.name.value,
      description: f.elements.description.value,
      benefits: f.elements.benefits.value,
      points_per_currency: Number(f.elements.points_per_currency.value),
      auto_approve_bookings: f.elements.auto_approve_bookings.checked,
      active: f.elements.active.checked,
    };
    try {
      const r = await API.put("/api/owner/membership", data);
      setMessage($("#owner-membership-message"), r.message);
      toast(r.message);
      await loadOwner();
    } catch (err) {
      setMessage($("#owner-membership-message"), err.message, true);
    }
  }
  async function saveService(e) {
    e.preventDefault();
    const f = e.currentTarget;
    const raw = Object.fromEntries(new FormData(f).entries());
    const payload = {
      business_id: state.businessId,
      name: raw.name,
      category: raw.category,
      price: Number(raw.price),
      duration_minutes: Number(raw.duration_minutes),
      description: raw.description,
    };
    try {
      if (raw.id) await API.put(`/api/owner/services/${raw.id}`, payload);
      else await API.post("/api/owner/services", payload);
      f.reset();
      f.elements.id.value = "";
      f.elements.duration_minutes.value = 60;
      toast("Đã lưu dịch vụ.");
      loadOwner();
    } catch (err) {
      toast(err.message, true);
    }
  }
  async function toggleService(id, active) {
    try {
      await API.put(`/api/owner/services/${id}`, { active: !active });
      toast("Đã cập nhật trạng thái dịch vụ.");
      loadOwner();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function ownerBooking(action, id) {
    try {
      await API.post(`/api/owner/bookings/${state.businessId}/${action}`, {
        booking_id: Number(id),
      });
      toast("Đã cập nhật lịch đặt.");
      loadOwner();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function uploadServiceImage(input) {
    const file = input.files?.[0],
      serviceId = Number(input.dataset.serviceImageInput);
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      toast("Chỉ hỗ trợ ảnh PNG, JPG hoặc WebP.", true);
      input.value = "";
      return;
    }
    if (file.size === 0 || file.size > 5 * 1024 * 1024) {
      toast(file.size === 0 ? "Tệp ảnh đang trống." : "Ảnh tối đa 5 MB.", true);
      input.value = "";
      return;
    }
    input.disabled = true;
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("Không đọc được tệp ảnh."));
        reader.readAsDataURL(file);
      });
      const r = await API.post(`/api/owner/services/${serviceId}/image`, {
        filename: file.name,
        data_url: dataUrl,
      });
      toast(r.message);
      await loadOwner();
      await loadServices();
    } catch (err) {
      toast(err.message || "Không tải được ảnh dịch vụ.", true);
    } finally {
      input.disabled = false;
      input.value = "";
    }
  }
  async function uploadImage(e) {
    e.preventDefault();
    const form = e.currentTarget,
      input = $("#business-image"),
      file = input.files?.[0],
      button = form.querySelector('button[type="submit"]');
    if (form.dataset.uploading === "1") return;
    if (!file) {
      setMessage(
        $("#media-message"),
        "Bạn hãy chọn ảnh trước khi tải lên.",
        true,
      );
      return;
    }
    if (!state.businessId) {
      setMessage(
        $("#media-message"),
        "Không xác định được cơ sở cần cập nhật. Hãy tải lại trang quản lý.",
        true,
      );
      return;
    }
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setMessage(
        $("#media-message"),
        "Chỉ hỗ trợ ảnh PNG, JPG hoặc WebP.",
        true,
      );
      return;
    }
    if (file.size === 0) {
      setMessage($("#media-message"), "Tệp ảnh đang trống.", true);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setMessage($("#media-message"), "Ảnh tối đa 5 MB.", true);
      return;
    }
    form.dataset.uploading = "1";
    if (button) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = "Đang tải ảnh...";
    }
    setMessage($("#media-message"), "Đang tải ảnh lên máy chủ...");
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () =>
          reject(new Error("Không đọc được tệp ảnh. Hãy chọn lại ảnh."));
        reader.onabort = () => reject(new Error("Đã hủy đọc tệp ảnh."));
        reader.readAsDataURL(file);
      });
      const r = await API.post("/api/media/upload", {
        business_id: Number(state.businessId),
        filename: file.name,
        data_url: dataUrl,
      });
      setMessage($("#media-message"), r.message);
      toast(r.message);
      // Refresh owner profile and public service catalogue so the banner is reflected everywhere.
      await syncUser();
      await Promise.all([loadOwner(), loadServices()]);
      const preview = $("#image-preview");
      if (preview) {
        preview.src = r.data.url + `?v=${Date.now()}`;
        preview.classList.remove("hidden");
      }
      input.value = "";
    } catch (err) {
      setMessage(
        $("#media-message"),
        err.message || "Không tải được ảnh. Hãy thử lại.",
        true,
      );
      toast(err.message || "Không tải được ảnh.", true);
    } finally {
      delete form.dataset.uploading;
      if (button) {
        button.disabled = false;
        button.textContent = button.dataset.originalText || "Tải ảnh lên";
      }
    }
  }
  async function refreshNotificationBadge() {
    if (!state.user) return;
    try {
      const r = await API.get("/api/notifications/unread-count");
      const count = Number(r.data.unread || 0),
        badge = $("#notification-badge");
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.classList.toggle("hidden", count === 0);
      $("#notification-shortcut").setAttribute(
        "aria-label",
        count ? `Xem ${count} thông báo chưa đọc` : "Xem thông báo",
      );
    } catch {
      /* A badge failure should not interrupt other views. */
    }
  }
  async function loadNotifications() {
    if (!state.user) return;
    try {
      const r = await API.get("/api/notifications");
      $("#notification-list").innerHTML = r.data.length
        ? r.data
            .map(
              (n) =>
                `<article class="notification-row ${n.is_read ? "" : "unread"}"><div><b>${esc(n.title)}</b><p>${esc(n.message)}</p><small>${esc(n.created_at)}</small></div>${n.is_read ? '<span class="status-pill">Đã đọc</span>' : `<button type="button" class="btn btn-outline btn-small" data-notification-read="${n.id}">Đánh dấu đã đọc</button>`}</article>`,
            )
            .join("")
        : '<p class="muted">Bạn chưa có thông báo nào.</p>';
      await refreshNotificationBadge();
    } catch (e) {
      $("#notification-list").innerHTML =
        '<p class="muted">Không thể tải thông báo.</p>';
    }
  }
  async function markNotificationRead(id) {
    try {
      await API.post(`/api/notifications/${id}/read`, {});
      await loadNotifications();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function markAllNotificationsRead() {
    try {
      const r = await API.post("/api/notifications/read-all", {});
      toast(r.message);
      await loadNotifications();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function loadAdmin() {
    if (!state.user?.is_admin) {
      $("#admin-locked").classList.remove("hidden");
      $("#admin-content").classList.add("hidden");
      return;
    }
    try {
      const [stats, apps, reports, businesses, audit] = await Promise.all([
        API.get("/api/admin/stats"),
        API.get("/api/admin/applications"),
        API.get("/api/admin/reports"),
        API.get("/api/admin/businesses"),
        API.get("/api/admin/audit"),
      ]);
      $("#admin-locked").classList.add("hidden");
      $("#admin-content").classList.remove("hidden");
      $("#admin-stats").innerHTML = [
        ["Người dùng", stats.data.users],
        ["Cơ sở", stats.data.businesses],
        ["Hồ sơ chờ duyệt", stats.data.pending_applications],
        ["Lịch đặt", stats.data.bookings],
      ]
        .map(
          (x) =>
            `<div class="metric-card"><span>${x[0]}</span><strong>${x[1]}</strong></div>`,
        )
        .join("");
      $("#application-review-list").innerHTML =
        apps.data
          .map(
            (a) =>
              `<article class="booking-card"><div><h3>${esc(a.business_name)} <span class="status-pill ${statusClass(a.status)}">${esc(statusName(a.status))}</span></h3><p>Người đăng ký: ${esc(a.user_name)} · ${esc(a.user_email)}</p><p>${esc(a.category)} · ${esc(a.address)} · ${esc(a.phone)}</p><p>${esc(a.description || "Không có mô tả")}</p>${a.review_note ? `<p>Ghi chú: ${esc(a.review_note)}</p>` : ""}</div><div class="booking-right"><div class="row-actions">${a.status === "pending" ? `<button class="btn btn-dark btn-small" data-review="approve" data-id="${a.id}">Chấp thuận</button><button class="btn btn-outline btn-small" data-review="changes" data-id="${a.id}">Yêu cầu bổ sung</button><button class="btn btn-outline btn-small" data-review="reject" data-id="${a.id}">Từ chối</button>` : ""}</div></div></article>`,
          )
          .join("") || '<p class="muted">Chưa có hồ sơ đăng ký.</p>';
      $("#admin-businesses").innerHTML =
        businesses.data
          .map(
            (b) =>
              `<div class="compact-row"><div><b>${esc(b.name)}</b><small>${esc(b.category)} · Chủ: ${esc(b.owner_name)} · ${Number(b.service_count)} dịch vụ · ${b.status === "active" ? "Đang hoạt động" : "Đang tạm dừng"}</small></div><button class="btn btn-outline btn-small" data-admin-business-id="${b.id}" data-admin-business-status="${b.status === "active" ? "suspended" : "active"}">${b.status === "active" ? "Tạm dừng" : "Kích hoạt"}</button></div>`,
          )
          .join("") || '<p class="muted">Chưa có cơ sở.</p>';
      const counts = reports.data.booking_statuses || {};
      $("#admin-reports").innerHTML = [
        ["Cơ sở hoạt động", reports.data.active_businesses],
        ["Cơ sở tạm dừng", reports.data.suspended_businesses],
        ["Dịch vụ hoạt động", reports.data.active_services],
        ["Lượt tham gia hội viên", reports.data.memberships],
        ["Chờ xác nhận", counts.pending || 0],
        ["Đã xác nhận", counts.confirmed || 0],
        ["Hoàn thành", counts.completed || 0],
        ["Đã hủy", counts.cancelled || 0],
      ]
        .map(
          ([label, value]) =>
            `<div class="metric-card"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`,
        )
        .join("");
      $("#admin-audit").innerHTML =
        audit.data
          .map(
            (a) =>
              `<div class="compact-row"><div><b>${esc(activityLabel(a.action))}</b><small>${esc(a.actor_name || "Hệ thống")} · ${esc(a.entity_type || "")} #${esc(a.entity_id || "")} · ${esc(a.created_at)}</small></div></div>`,
          )
          .join("") || '<p class="muted">Chưa có hoạt động.</p>';
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function changeBusinessStatus(id, status) {
    if (
      !confirm(
        status === "suspended"
          ? "Tạm dừng cơ sở này? Các dịch vụ của cơ sở sẽ không hiện trên trang khám phá."
          : "Kích hoạt lại cơ sở này?",
      )
    )
      return;
    try {
      const r = await API.post(`/api/admin/businesses/${id}/status`, {
        status,
      });
      toast(r.message);
      await loadAdmin();
      await loadServices();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function reviewApplication(action, id) {
    let note = "";
    if (action !== "approve") {
      note = prompt(
        action === "changes"
          ? "Nhập thông tin cần bổ sung:"
          : "Nhập lý do từ chối:",
      );
      if (!note) return;
    }
    try {
      const r = await API.post(`/api/admin/applications/${id}/${action}`, {
        note,
      });
      toast(r.message);
      loadAdmin();
    } catch (e) {
      toast(e.message, true);
    }
  }
  async function joinMembership(id) {
    if (!API.hasToken()) {
      closeModals();
      openModal("auth-modal");
      toast("Đăng nhập để đăng ký hội viên.");
      return;
    }
    try {
      const r = await API.post(`/api/memberships/${id}/join`, {});
      toast(r.message);
      await loadProfile();
      const bid = $("#business-detail-title")?.dataset.businessId;
      if (bid) await openBusinessDetails(bid);
    } catch (e) {
      toast(e.message, true);
    }
  }
  function bindEvents() {
    bindDiscoveryEvents();
    document.addEventListener("click", (e) => {
      const view = e.target.closest("[data-view]");
      if (view) {
        e.preventDefault();
        showView(view.dataset.view);
        return;
      }
      if (
        e.target.closest("#open-auth") ||
        e.target.closest("#profile-login") ||
        e.target.closest("#bookings-login")
      ) {
        openModal("auth-modal");
        return;
      }
      if (e.target.closest("#notification-shortcut")) {
        showView("profile");
        $("#notifications-panel").scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
        return;
      }
      if (e.target.closest("#logout-btn")) {
        API.post("/api/auth/logout", {}).catch(() => {});
        API.clearSession();
        state.user = null;
        state.profile = null;
        updateAuthUI();
        toast("Đã đăng xuất.");
        showView("home");
        return;
      }
      const close = e.target.closest("[data-close-modal]");
      if (close) {
        closeModals();
        return;
      }
      const mode = e.target.closest("[data-auth-mode]");
      if (mode) {
        authMode(mode.dataset.authMode);
        return;
      }
      const detail = e.target.closest("[data-business-detail]");
      if (detail) {
        openBusinessDetails(detail.dataset.businessDetail);
        return;
      }
      const book = e.target.closest("[data-book-service]");
      if (book) {
        closeModals();
        beginBooking(book.dataset.bookService);
        return;
      }
      const cancel = e.target.closest("[data-cancel-booking]");
      if (cancel) {
        cancelBooking(cancel.dataset.cancelBooking);
        return;
      }
      const edit = e.target.closest("[data-edit-service]");
      if (edit) {
        API.get(`/api/owner/services?business_id=${state.businessId}`)
          .then((r) => {
            const s = r.data.find(
              (x) => Number(x.id) === Number(edit.dataset.editService),
            );
            if (!s) return;
            const f = $("#service-form");
            for (const k of [
              "id",
              "name",
              "category",
              "price",
              "duration_minutes",
              "description",
            ])
              f.elements[k].value = s[k] ?? "";
            f.scrollIntoView({ behavior: "smooth", block: "center" });
          })
          .catch((err) => toast(err.message, true));
        return;
      }
      const toggle = e.target.closest("[data-toggle-service]");
      if (toggle) {
        toggleService(
          toggle.dataset.toggleService,
          toggle.dataset.active === "1",
        );
        return;
      }
      const ob = e.target.closest("[data-owner-booking]");
      if (ob) {
        ownerBooking(ob.dataset.ownerBooking, ob.dataset.id);
        return;
      }
      const rev = e.target.closest("[data-review]");
      if (rev) {
        reviewApplication(rev.dataset.review, rev.dataset.id);
        return;
      }
      const notification = e.target.closest("[data-notification-read]");
      if (notification) {
        markNotificationRead(notification.dataset.notificationRead);
        return;
      }
      const businessStatus = e.target.closest("[data-admin-business-status]");
      if (businessStatus) {
        changeBusinessStatus(
          businessStatus.dataset.adminBusinessId,
          businessStatus.dataset.adminBusinessStatus,
        );
        return;
      }
      const join = e.target.closest("[data-join-membership]");
      if (join) {
        joinMembership(join.dataset.joinMembership);
        return;
      }
      const scroll = e.target.closest("[data-scroll]");
      if (scroll) {
        $(scroll.dataset.scroll)?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    });

    $("#notification-read-all").addEventListener(
      "click",
      markAllNotificationsRead,
    );
    $("#auth-form").addEventListener("submit", submitAuth);
    $("#application-form").addEventListener("submit", submitApplication);
    $("#profile-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await API.put("/api/me", {
          name: $("#profile-name").value,
          phone: $("#profile-phone").value,
          address: $("#profile-address").value,
        });
        await syncUser();
        setMessage($("#profile-message"), "Đã lưu thay đổi.");
      } catch (err) {
        setMessage($("#profile-message"), err.message, true);
      }
    });

    $("#booking-form").addEventListener("submit", submitBooking);
    $("#booking-form").elements.date.addEventListener(
      "change",
      loadAvailability,
    );
    $("#service-search").addEventListener("input", () => {
      showSuggestions();
    });
    $("#service-search").addEventListener("focus", showSuggestions);
    $("#service-search").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        hideSuggestions();
        loadServices();
      }
      if (e.key === "Escape") hideSuggestions();
    });
    $("#search-btn").addEventListener("click", loadServices);
    $("#category-filter").addEventListener("change", loadServices);
    $("#search-suggestions").addEventListener("click", (e) => {
      const b = e.target.closest("[data-suggestion]");
      if (!b) return;
      $("#service-search").value = b.dataset.suggestion;
      hideSuggestions();
      loadServices();
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-wrap")) hideSuggestions();
    });
    $("#service-results").addEventListener("click", (e) => {
      if (e.target.closest("#clear-service-search")) {
        $("#service-search").value = "";
        $("#category-filter").value = "";
        loadServices();
      }
    });
    $("#owner-services").addEventListener("change", (e) => {
      const input = e.target.closest("[data-service-image-input]");
      if (input) uploadServiceImage(input);
    });
    $("#owner-business-select").addEventListener("change", (e) => {
      state.businessId = Number(e.target.value);
      loadOwner();
    });
    $("#owner-business-form").addEventListener("submit", saveBusinessProfile);
    $("#owner-membership-form").addEventListener("submit", saveOwnerMembership);
    $("#service-form").addEventListener("submit", saveService);
    $("#service-form-reset").addEventListener("click", () => {
      $("#service-form").reset();
      $("#service-form").elements.id.value = "";
      $("#service-form").elements.duration_minutes.value = 60;
    });
    $("#refresh-owner-bookings").addEventListener("click", loadOwner);
    $("#media-form").addEventListener("submit", uploadImage);
    $("#business-image").addEventListener("change", (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const img = $("#image-preview");
      img.src = URL.createObjectURL(f);
      img.classList.remove("hidden");
    });
    $("#admin-refresh").addEventListener("click", loadAdmin);
    $("#mobile-menu").addEventListener("click", () =>
      $(".main-nav").classList.toggle("open"),
    );
  }
  async function init() {

    bindEvents();
    renderDiscoveryStep();
    authMode("login");
    await syncUser();
    await loadServices();
    const view = location.hash.replace("#", "");
    if (
      ["home", "services", "bookings", "profile", "owner", "admin"].includes(
        view,
      )
    )
      showView(view);
  }
  window.ServiceHub = { showView, loadProfile, loadServices };
  document.addEventListener("DOMContentLoaded", init);
})();
