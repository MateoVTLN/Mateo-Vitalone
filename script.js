/* ── STRAVA PREVIEW (3 latest) — index.html ── */
if (document.getElementById("home-activity-list")) {
    fetch("activities.json")
        .then(r => r.json())
        .then(activities => {
            const container = document.getElementById("home-activity-list");
            container.innerHTML = "";
            activities.slice(0, 3).forEach(a => {
                const km   = (a.distance / 1000).toFixed(1);
                const date = new Date(a.start_date).toLocaleDateString("fr-FR");
                const mins = Math.floor(a.moving_time / 60);
                const secs = String(a.moving_time % 60).padStart(2, "0");
                container.innerHTML += `
                    <div class="activity-card-small">
                        <div class="act-type">${a.type}</div>
                        <div class="act-name">${a.name}</div>
                        <div class="act-meta">
                            <span>📍 ${km} km</span>
                            <span>⏱ ${mins}:${secs}</span>
                            <span>📅 ${date}</span>
                        </div>
                    </div>`;
            });
        })
        .catch(() => {
            document.getElementById("home-activity-list").innerHTML =
                "<p style='color:#bfbfbf;font-size:13px;'>Could not load activities.</p>";
        });
}

/* ── ACTIVITIES FULL — sport.html ── */
if (document.getElementById("activity-list")) {
    fetch("activities.json")
        .then(r => r.json())
        .then(activities => {
            const container = document.getElementById("activity-list");
            container.innerHTML = "";

            activities.forEach((a, idx) => {
                const km      = (a.distance / 1000).toFixed(1);
                const date    = new Date(a.start_date).toLocaleDateString("fr-FR");
                const mins    = Math.floor(a.moving_time / 60);
                const secs    = String(a.moving_time % 60).padStart(2, "0");
                const elev    = a.total_elevation_gain;
                const mapId   = `map-${idx}`;
                const slideId = `slider-${idx}`;

                const hasPolyline = a.map && a.map.summary_polyline && a.map.summary_polyline.length > 0;
                const hasPhotos   = Array.isArray(a.photos_urls) && a.photos_urls.length > 0;

                const mapBlock = hasPolyline
                    ? `<div id="${mapId}" class="activity-map"></div>`
                    : "";

                let sliderBlock = "";
                if (hasPhotos) {
                    const imgTags = a.photos_urls.map(url =>
                        `<img src="${url}" alt="${a.name}">`
                    ).join("");
                    const controls = a.photos_urls.length > 1
                        ? `<button class="slider-btn prev">&#10094;</button>
                           <button class="slider-btn next">&#10095;</button>
                           <span class="slider-count"></span>`
                        : "";
                    sliderBlock = `
                        <div id="${slideId}" class="photo-slider">
                            ${imgTags}
                            ${controls}
                        </div>`;
                }

                container.innerHTML += `
                    <div class="activity-card">
                        <div class="activity-type">${a.sport_type || a.type}</div>
                        <h4>${a.name}</h4>
                        <div class="activity-meta">
                            <span>📍 ${km} km</span>
                            <span>⏱ ${mins}:${secs}</span>
                            <span>⬆ ${elev} m</span>
                            <span>📅 ${date}</span>
                        </div>
                        ${mapBlock}
                        ${sliderBlock}
                    </div>`;
            });

            // Init maps and sliders AFTER all HTML is injected
            activities.forEach((a, idx) => {
                const hasPolyline = a.map && a.map.summary_polyline && a.map.summary_polyline.length > 0;
                const hasPhotos   = Array.isArray(a.photos_urls) && a.photos_urls.length > 0;

                if (hasPolyline) {
                    const coords = decodePolyline(a.map.summary_polyline);
                    if (coords.length) {
                        const map = L.map(`map-${idx}`, { zoomControl: false, attributionControl: false });
                        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18 }).addTo(map);
                        const poly = L.polyline(coords, { color: "#FC4C02", weight: 4 });
                        poly.addTo(map);
                        map.fitBounds(poly.getBounds(), { padding: [10, 10] });
                    }
                }

                if (hasPhotos) initSlider(`slider-${idx}`);
            });
        })
        .catch(() => {
            document.getElementById("activity-list").innerHTML =
                "<p style='color:#bfbfbf;'>Could not load activities.</p>";
        });
}

/* ── Carousel d'images — index.html ── */
const carouselMedia = [
    "images/project1.jpg",
    "images/project2.jpg",
    "images/project3.jpg"
    // Ajoute tes images ici
];

(function initCarousel() {
    const inner   = document.getElementById("carousel-inner");
    const dotsBox = document.getElementById("carousel-dots");
    const btnPrev = document.getElementById("carousel-prev");
    const btnNext = document.getElementById("carousel-next");

    if (!inner || !carouselMedia.length) return; // guard: not on this page

    const shuffled = [...carouselMedia].sort(() => Math.random() - 0.5);
    let current = 0;
    let autoTimer;

    shuffled.forEach(src => {
        let el;
        if (src.endsWith(".mp4") || src.endsWith(".webm")) {
            el = document.createElement("video");
            el.src = src;
            el.muted = true;
            el.playsInline = true;
        } else {
            el = document.createElement("img");
            el.src = src;
            el.alt = "";
        }
        inner.appendChild(el);

        const dot = document.createElement("span");
        dotsBox.appendChild(dot);
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
        current = (current + dir + shuffled.length) % shuffled.length;
        show(current);
    }

    btnPrev.addEventListener("click", () => step(-1));
    btnNext.addEventListener("click", () => step(1));
    dotEls.forEach((d, i) => d.addEventListener("click", () => { current = i; show(i); }));

    show(0);
})();

/* ── Polyline decoder ── */
function decodePolyline(str, precision = 5) {
    let index = 0, lat = 0, lng = 0, coordinates = [];
    const factor = Math.pow(10, precision);
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

/* ── Photo slider initializer ── */
function initSlider(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    const imgs  = slider.querySelectorAll("img");
    const count = slider.querySelector(".slider-count");
    const btnP  = slider.querySelector(".slider-btn.prev");
    const btnN  = slider.querySelector(".slider-btn.next");
    if (imgs.length === 0) return;

    let current = 0;

    function show(i) {
        imgs.forEach(img => img.classList.remove("active"));
        imgs[i].classList.add("active");
        if (count) count.textContent = `${i + 1} / ${imgs.length}`;
    }

    if (imgs.length > 1) {
        btnP.addEventListener("click", () => { current = (current - 1 + imgs.length) % imgs.length; show(current); });
        btnN.addEventListener("click", () => { current = (current + 1) % imgs.length; show(current); });
    } else {
        if (btnP) btnP.style.display = "none";
        if (btnN) btnN.style.display = "none";
    }

    show(0);
}