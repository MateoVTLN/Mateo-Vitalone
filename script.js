/* ════════════════════════════════════════════════════════════
   Matéo Vitalone — Portfolio scripts
   Shared UI (nav, reveal, CV button) + page modules
   ════════════════════════════════════════════════════════════ */

/* ── Navigation: hamburger + dropdown + active link ────────── */
(function initNav() {
    const nav    = document.querySelector(".site-nav");
    const toggle = document.querySelector(".nav-toggle");
    if (!nav) return;

    if (toggle) {
        toggle.addEventListener("click", () => nav.classList.toggle("open"));
    }

    document.querySelectorAll(".nav-drop > button").forEach(btn => {
        btn.addEventListener("click", e => {
            e.stopPropagation();
            btn.parentElement.classList.toggle("open");
        });
    });
    document.addEventListener("click", e => {
        document.querySelectorAll(".nav-drop.open").forEach(d => {
            if (!d.contains(e.target)) d.classList.remove("open");
        });
    });

    const here = location.pathname.split("/").pop() || "index.html";
    document.querySelectorAll(".site-nav a").forEach(a => {
        const target = a.getAttribute("href");
        if (target === here) {
            a.classList.add("active");
            const drop = a.closest(".nav-drop");
            if (drop) drop.querySelector("button").classList.add("active");
        }
    });
})();

/* ── Reveal on scroll ──────────────────────────────────────── */
(function initReveal() {
    const els = document.querySelectorAll(".reveal");
    if (!els.length || !("IntersectionObserver" in window)) {
        els.forEach(el => el.classList.add("visible"));
        return;
    }
    const io = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                io.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });
    els.forEach(el => io.observe(el));
})();

/* ── CV button: grey out until the PDF exists ──────────────── */
(function initCvButton() {
    const btns = document.querySelectorAll("[data-cv-check]");
    if (!btns.length || !location.protocol.startsWith("http")) return;
    fetch(btns[0].getAttribute("href"), { method: "HEAD" })
        .then(r => { if (!r.ok) throw new Error(); })
        .catch(() => btns.forEach(b => {
            b.setAttribute("aria-disabled", "true");
            b.title = "CV coming soon";
        }));
})();

/* ── Shared formatting helpers ─────────────────────────────── */
const SPORT_ICONS = {
    Run: "🏃", TrailRun: "⛰️", Walk: "🚶", Hike: "🥾", Ride: "🚴",
    MountainBikeRide: "🚵", Swim: "🏊", WeightTraining: "🏋️",
    Workout: "💪", Rowing: "🚣", NordicSki: "⛷️", AlpineSki: "🎿",
};
const PACE_SPORTS = ["Run", "Walk", "Hike", "Trail Run", "TrailRun"];

function fmtKm(m)        { return (m / 1000).toFixed(1); }
function fmtDate(iso)    { return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }); }
function fmtDuration(s)  {
    const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
    return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m} min`;
}
function fmtLongDuration(s) {
    const h = Math.floor(s / 3600);
    return h >= 100 ? `${h} h` : `${h}h ${String(Math.round((s % 3600) / 60)).padStart(2, "0")}m`;
}
function fmtPace(avgSpeed) {
    if (!avgSpeed) return null;
    const secs = Math.round(1000 / avgSpeed);
    return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")} /km`;
}
function sportIcon(a)    { return SPORT_ICONS[(a.sport_type || a.type || "").replace(/\s/g, "")] || "🏅"; }
function stravaUrl(a)    { return `https://www.strava.com/activities/${a.id}`; }

/* ── Google polyline decoder ───────────────────────────────── */
function decodePolyline(str, precision = 5) {
    let index = 0, lat = 0, lng = 0;
    const coordinates = [], factor = Math.pow(10, precision);
    while (index < str.length) {
        let b, shift = 0, result = 0;
        do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
        lat += (result & 1) ? ~(result >> 1) : (result >> 1);
        shift = 0; result = 0;
        do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
        lng += (result & 1) ? ~(result >> 1) : (result >> 1);
        coordinates.push([lat / factor, lng / factor]);
    }
    return coordinates;
}

const DARK_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIB = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

/* ── Home: latest activities strip ─────────────────────────── */
if (document.getElementById("home-activity-list")) {
    fetch("activities.json")
        .then(r => r.json())
        .then(activities => {
            const container = document.getElementById("home-activity-list");
            container.innerHTML = "";
            activities.slice(0, 3).forEach(a => {
                const pace = PACE_SPORTS.includes(a.sport_type || a.type) ? fmtPace(a.average_speed) : null;
                container.innerHTML += `
                    <div class="activity-card-small">
                        <div class="act-type">${a.sport_type || a.type}</div>
                        <div class="act-name">${a.name}</div>
                        <div class="act-meta">
                            <span>📍 ${fmtKm(a.distance)} km</span>
                            <span>⏱ ${fmtDuration(a.moving_time)}</span>
                            ${pace ? `<span>⚡ ${pace}</span>` : ""}
                            <span>📅 ${fmtDate(a.start_date)}</span>
                        </div>
                    </div>`;
            });
        })
        .catch(() => {
            document.getElementById("home-activity-list").innerHTML =
                "<p style='color:var(--text-faint);font-size:13px;'>Could not load activities.</p>";
        });
}

/* ── Home: gallery carousel ────────────────────────────────── */
const carouselMedia = [
    "images/stage_flare.jpg",
    "images/concert_muzik.jpg",
    "images/bio_stage.jpg",
    "images/sg_hero.jpeg",
    "images/bio_sg_marshall.jpg",
    "images/folk_result.jpg",
    "images/bio_marshall_work.jpg",
];

(function initCarousel() {
    const inner   = document.getElementById("carousel-inner");
    const dotsBox = document.getElementById("carousel-dots");
    const btnPrev = document.getElementById("carousel-prev");
    const btnNext = document.getElementById("carousel-next");
    if (!inner || !carouselMedia.length) return;

    let current = 0;
    let autoTimer;

    carouselMedia.forEach(src => {
        let el;
        if (src.endsWith(".mp4") || src.endsWith(".webm")) {
            el = document.createElement("video");
            el.src = src; el.muted = true; el.playsInline = true;
        } else {
            el = document.createElement("img");
            el.src = src; el.alt = ""; el.loading = "lazy";
        }
        inner.appendChild(el);
        dotsBox.appendChild(document.createElement("span"));
    });

    const items  = inner.querySelectorAll("img, video");
    const dotEls = dotsBox.querySelectorAll("span");

    function show(index) {
        items.forEach(el => {
            el.classList.remove("active");
            if (el.tagName === "VIDEO") { el.pause(); el.currentTime = 0; }
        });
        dotEls.forEach(d => d.classList.remove("active"));
        items[index].classList.add("active");
        dotEls[index].classList.add("active");
        clearTimeout(autoTimer);
        if (items[index].tagName === "VIDEO") {
            items[index].play().catch(() => {});
            items[index].onended = () => step(1);
        } else {
            autoTimer = setTimeout(() => step(1), 5000);
        }
    }
    function step(dir) {
        current = (current + dir + items.length) % items.length;
        show(current);
    }

    btnPrev.addEventListener("click", () => step(-1));
    btnNext.addEventListener("click", () => step(1));
    dotEls.forEach((d, i) => d.addEventListener("click", () => { current = i; show(i); }));
    show(0);
})();

/* ── Academic gallery ──────────────────────────────────────── */
(function initAcademic() {
    const grid = document.getElementById("academic-grid");
    if (!grid || typeof ACADEMIC_WORKS === "undefined") return;

    const filterRow = document.getElementById("academic-filters");
    const tags = [...new Set(ACADEMIC_WORKS.flatMap(w => w.tags))].sort();
    let active = "All";

    function render() {
        const works = ACADEMIC_WORKS
            .filter(w => active === "All" || w.tags.includes(active))
            .sort((a, b) => b.year - a.year);
        grid.innerHTML = works.map(w => `
            <article class="academic-card reveal visible">
                <div class="academic-meta">
                    <span class="year-badge">${w.year}</span>
                    <span>${w.course}</span>
                </div>
                <h3>${w.title}</h3>
                <p class="abstract">${w.abstract}</p>
                <div class="card-tags">${w.tags.map(t => `<span class="tag">${t}</span>`).join("")}</div>
                <div class="academic-actions">
                    ${w.pdf
                        ? `<a class="btn btn-primary" href="${w.pdf}" target="_blank" rel="noopener">Report (PDF)</a>`
                        : `<span class="pending-badge">📄 Report coming soon</span>`}
                    ${w.code ? `<a class="btn btn-ghost" href="${w.code}" target="_blank" rel="noopener">View code</a>` : ""}
                </div>
            </article>`).join("");
        if (!works.length) {
            grid.innerHTML = "<p style='color:var(--text-faint)'>No works in this category yet.</p>";
        }
    }

    if (filterRow) {
        filterRow.innerHTML = ["All", ...tags].map(t =>
            `<button class="chip${t === "All" ? " active" : ""}" data-tag="${t}">${t}</button>`).join("");
        filterRow.addEventListener("click", e => {
            const chip = e.target.closest(".chip");
            if (!chip) return;
            active = chip.dataset.tag;
            filterRow.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === chip));
            render();
        });
    }
    render();
})();

/* ════════════════════════════════════════════════════════════
   SPORT DASHBOARD (sport.html)
   ════════════════════════════════════════════════════════════ */
(function initSport() {
    if (!document.getElementById("sport-dashboard")) return;

    fetch("activities.json")
        .then(r => r.json())
        .then(buildDashboard)
        .catch(() => {
            document.getElementById("sport-dashboard").innerHTML =
                "<p style='color:var(--text-faint)'>Could not load activities.</p>";
        });

    let allActivities = [];
    let typeFilter = "All";
    let shown = 12;
    let routesMap, routeLayers = [];
    let modalMap;

    function buildDashboard(activities) {
        allActivities = activities.filter(a => a && a.id);
        renderStats();
        renderRecords();
        renderFilters();
        initRoutesMap();
        renderFeed();
        initModal();
    }

    const filtered = () => allActivities.filter(a =>
        typeFilter === "All" || (a.sport_type || a.type) === typeFilter);

    /* ── Totals ── */
    function renderStats() {
        const box = document.getElementById("stat-row");
        const dist  = allActivities.reduce((s, a) => s + (a.distance || 0), 0);
        const time  = allActivities.reduce((s, a) => s + (a.moving_time || 0), 0);
        const elev  = allActivities.reduce((s, a) => s + (a.total_elevation_gain || 0), 0);
        const since = allActivities.length
            ? new Date(allActivities[allActivities.length - 1].start_date).getFullYear()
            : "";

        box.innerHTML = `
            <div class="stat-tile"><div class="stat-label">Activities</div>
                <div class="stat-value">${allActivities.length}</div>
                <div class="stat-sub">since ${since}</div></div>
            <div class="stat-tile"><div class="stat-label">Total distance</div>
                <div class="stat-value">${Math.round(dist / 1000).toLocaleString("en")}<small>km</small></div></div>
            <div class="stat-tile"><div class="stat-label">Moving time</div>
                <div class="stat-value">${Math.floor(time / 3600).toLocaleString("en")}<small>h</small></div></div>
            <div class="stat-tile"><div class="stat-label">Elevation gain</div>
                <div class="stat-value">${Math.round(elev).toLocaleString("en")}<small>m</small></div></div>`;
    }

    /* ── Records ── */
    function renderRecords() {
        const box = document.getElementById("records-grid");
        const runs = allActivities.filter(a =>
            (a.sport_type || a.type) === "Run" && a.distance >= 3000 && a.average_speed);

        const recs = [];
        const longest = maxBy(allActivities, a => a.distance);
        if (longest) recs.push(["Longest activity", `${fmtKm(longest.distance)} km`, longest]);

        const fastest = maxBy(runs, a => a.average_speed);
        if (fastest) recs.push(["Fastest run pace (≥3 km)", fmtPace(fastest.average_speed), fastest]);

        const climb = maxBy(allActivities, a => a.total_elevation_gain);
        if (climb && climb.total_elevation_gain > 0)
            recs.push(["Biggest climb", `${Math.round(climb.total_elevation_gain)} m`, climb]);

        const duration = maxBy(allActivities, a => a.moving_time);
        if (duration) recs.push(["Longest effort", fmtLongDuration(duration.moving_time), duration]);

        box.innerHTML = recs.map(([label, value, a]) => `
            <div class="record-card">
                <div class="record-label">${label}</div>
                <div class="record-value">${value}</div>
                <div class="record-meta"><a href="${stravaUrl(a)}" target="_blank" rel="noopener">${a.name}</a> · ${fmtDate(a.start_date)}</div>
            </div>`).join("");
    }

    function maxBy(arr, fn) {
        return arr.reduce((best, x) => (best === null || fn(x) > fn(best)) ? x : best, null);
    }

    /* ── Filters ── */
    function renderFilters() {
        const row = document.getElementById("sport-filters");
        const counts = {};
        allActivities.forEach(a => {
            const t = a.sport_type || a.type || "Other";
            counts[t] = (counts[t] || 0) + 1;
        });
        const types = Object.entries(counts).sort((a, b) => b[1] - a[1]);
        row.innerHTML = `<button class="chip active" data-type="All">All (${allActivities.length})</button>` +
            types.map(([t, n]) => `<button class="chip" data-type="${t}">${t} (${n})</button>`).join("");
        row.addEventListener("click", e => {
            const chip = e.target.closest(".chip");
            if (!chip) return;
            typeFilter = chip.dataset.type;
            shown = 12;
            row.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === chip));
            renderFeed();
            drawRoutes();
        });
    }

    /* ── All-routes map ── */
    function initRoutesMap() {
        const el = document.getElementById("all-routes-map");
        if (!el || typeof L === "undefined") return;
        routesMap = L.map(el, { scrollWheelZoom: false });
        L.tileLayer(DARK_TILES, { maxZoom: 18, attribution: TILE_ATTRIB }).addTo(routesMap);
        drawRoutes();
    }

    function drawRoutes() {
        if (!routesMap) return;
        routeLayers.forEach(l => routesMap.removeLayer(l));
        routeLayers = [];
        let bounds = null;
        filtered().forEach(a => {
            const poly = a.map && a.map.summary_polyline;
            if (!poly) return;
            const coords = decodePolyline(poly);
            if (!coords.length) return;
            const line = L.polyline(coords, { color: "#fc4c02", weight: 2.5, opacity: 0.65 });
            line.on("mouseover", () => line.setStyle({ weight: 4.5, opacity: 1 }));
            line.on("mouseout",  () => line.setStyle({ weight: 2.5, opacity: 0.65 }));
            line.bindTooltip(`${a.name} · ${fmtKm(a.distance)} km`, { sticky: true });
            line.on("click", () => openModal(a));
            line.addTo(routesMap);
            routeLayers.push(line);
            bounds = bounds ? bounds.extend(line.getBounds()) : L.latLngBounds(line.getBounds().getSouthWest(), line.getBounds().getNorthEast());
        });
        if (bounds) routesMap.fitBounds(bounds, { padding: [30, 30] });
    }

    /* ── Activity feed ── */
    function renderFeed() {
        const feed = document.getElementById("activity-feed");
        const list = filtered();
        feed.innerHTML = list.slice(0, shown).map((a, i) => {
            const pace = PACE_SPORTS.includes(a.sport_type || a.type) ? fmtPace(a.average_speed) : null;
            const photos = (a.photos_urls || []).length;
            return `
            <div class="activity-row" data-idx="${i}">
                <div class="row-type">${sportIcon(a)}</div>
                <div class="row-main">
                    <div class="row-name">${a.name}</div>
                    <div class="row-meta">
                        <span>📅 ${fmtDate(a.start_date)}</span>
                        <span>📍 ${fmtKm(a.distance)} km</span>
                        <span>⏱ ${fmtDuration(a.moving_time)}</span>
                        ${pace ? `<span>⚡ ${pace}</span>` : ""}
                        ${a.average_heartrate ? `<span>💓 ${Math.round(a.average_heartrate)} bpm</span>` : ""}
                    </div>
                </div>
                <div class="row-extra">
                    ${photos ? `<span class="photo-dot">📷 ${photos}</span>` : ""}
                </div>
            </div>`;
        }).join("");

        feed.querySelectorAll(".activity-row").forEach(row => {
            row.addEventListener("click", () => openModal(list[+row.dataset.idx]));
        });

        const moreWrap = document.getElementById("load-more-wrap");
        moreWrap.style.display = list.length > shown ? "" : "none";
    }

    document.getElementById("load-more")?.addEventListener("click", () => {
        shown += 12;
        renderFeed();
    });

    /* ── Modal ── */
    function initModal() {
        const modal = document.getElementById("activity-modal");
        modal.addEventListener("click", e => {
            if (e.target === modal || e.target.closest(".modal-close")) closeModal();
        });
        document.addEventListener("keydown", e => {
            if (e.key === "Escape") closeModal();
        });
    }

    function openModal(a) {
        const modal = document.getElementById("activity-modal");
        const pace = PACE_SPORTS.includes(a.sport_type || a.type) ? fmtPace(a.average_speed) : null;
        const speed = !pace && a.average_speed ? `${(a.average_speed * 3.6).toFixed(1)} km/h` : null;

        document.getElementById("modal-title").textContent = a.name;
        document.getElementById("modal-date").textContent =
            `${a.sport_type || a.type} · ${fmtDate(a.start_date)}`;

        const stats = [
            ["Distance", `${fmtKm(a.distance)} km`],
            ["Moving time", fmtDuration(a.moving_time)],
            pace  ? ["Pace", pace] : null,
            speed ? ["Avg speed", speed] : null,
            a.total_elevation_gain ? ["Elevation", `${Math.round(a.total_elevation_gain)} m`] : null,
            a.average_heartrate ? ["Avg HR", `${Math.round(a.average_heartrate)} bpm`] : null,
            a.max_heartrate ? ["Max HR", `${Math.round(a.max_heartrate)} bpm`] : null,
        ].filter(Boolean);
        document.getElementById("modal-stats").innerHTML = stats.map(([l, v]) =>
            `<div class="modal-stat"><div class="ms-label">${l}</div><div class="ms-value">${v}</div></div>`).join("");

        /* photos */
        const gallery = document.getElementById("modal-gallery");
        const photos = a.photos_urls || [];
        if (photos.length) {
            gallery.innerHTML = `
                <div class="photo-slider" id="modal-slider">
                    ${photos.map(u => `<img src="${u}" alt="${a.name}">`).join("")}
                    ${photos.length > 1 ? `
                        <button class="slider-btn prev">&#10094;</button>
                        <button class="slider-btn next">&#10095;</button>
                        <span class="slider-count"></span>` : ""}
                </div>`;
            initSlider("modal-slider");
        } else {
            gallery.innerHTML = "";
        }

        /* map */
        const mapEl = document.getElementById("modal-map");
        if (modalMap) { modalMap.remove(); modalMap = null; }
        const poly = a.map && a.map.summary_polyline;
        if (poly && typeof L !== "undefined") {
            mapEl.style.display = "";
            modal.classList.add("open");
            modalMap = L.map(mapEl, { zoomControl: false, scrollWheelZoom: false });
            L.tileLayer(DARK_TILES, { maxZoom: 18, attribution: TILE_ATTRIB }).addTo(modalMap);
            const line = L.polyline(decodePolyline(poly), { color: "#fc4c02", weight: 3.5 });
            line.addTo(modalMap);
            modalMap.fitBounds(line.getBounds(), { padding: [16, 16] });
            setTimeout(() => modalMap.invalidateSize(), 60);
        } else {
            mapEl.style.display = "none";
            modal.classList.add("open");
        }

        document.getElementById("modal-strava").href = stravaUrl(a);
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        document.getElementById("activity-modal").classList.remove("open");
        if (modalMap) { modalMap.remove(); modalMap = null; }
        document.body.style.overflow = "";
    }
})();

/* ── Photo slider (shared) ─────────────────────────────────── */
function initSlider(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    const imgs  = slider.querySelectorAll("img");
    const count = slider.querySelector(".slider-count");
    const btnP  = slider.querySelector(".slider-btn.prev");
    const btnN  = slider.querySelector(".slider-btn.next");
    if (!imgs.length) return;

    let current = 0;
    function show(i) {
        imgs.forEach(img => img.classList.remove("active"));
        imgs[i].classList.add("active");
        if (count) count.textContent = `${i + 1} / ${imgs.length}`;
    }
    if (imgs.length > 1) {
        btnP.addEventListener("click", () => { current = (current - 1 + imgs.length) % imgs.length; show(current); });
        btnN.addEventListener("click", () => { current = (current + 1) % imgs.length; show(current); });
    }
    show(0);
}
