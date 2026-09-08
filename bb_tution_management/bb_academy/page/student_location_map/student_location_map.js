// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

/**
 * Student Location Map
 *
 * Plots students on an OpenStreetMap basemap using the Latitude / Longitude
 * typed by hand onto each Student record. Zero-cost by design: Leaflet +
 * OSM raster tiles, no API key, no geocoding, no paid service anywhere.
 *
 * Performance shape (the academy is heading for thousands of students):
 *   - students arrive in paginated bulk requests, never one call per marker;
 *   - every marker object is built exactly once and kept in memory;
 *   - filtering swaps which markers are in the cluster layer, it never
 *     rebuilds the map or the markers;
 *   - popup HTML is built lazily, only when a marker is actually opened.
 */

const SLM_API = "bb_tution_management.bb_academy.page.student_location_map.student_location_map";

// Students are in Chennai, so that is where an empty map opens. It is only a
// starting view — whenever markers exist the map fits itself to their bounds.
const SLM_DEFAULT_CENTER = [13.0827, 80.2707];
const SLM_DEFAULT_ZOOM = 11;

const SLM_PAGE_LENGTH = 1000;

// Leaflet + the marker cluster plugin, from free CDNs. Each asset lists a
// fallback host: if cdnjs is unreachable the loader retries on unpkg before
// giving up and showing the error state.
const SLM_ASSETS = [
	{
		type: "css",
		urls: [
			"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
			"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
		],
	},
	{
		type: "js",
		urls: [
			"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js",
			"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
		],
		test: () => !!window.L,
	},
	{
		type: "css",
		urls: [
			"https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.min.css",
			"https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css",
		],
	},
	{
		type: "js",
		urls: [
			"https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.js",
			"https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js",
		],
		test: () => !!(window.L && window.L.markerClusterGroup),
	},
];

// Marker ring colours. Picked per student from a hash of the ID so the same
// student always looks the same, and a screen full of pins stays readable.
const SLM_PIN_COLORS = [
	"#2f6fed",
	"#17a673",
	"#e8912d",
	"#8b5cf6",
	"#e2504d",
	"#0ea5e9",
	"#d946a6",
	"#0f766e",
];

frappe.pages["student-location-map"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Student Location Map"),
		single_column: true,
	});

	wrapper.student_location_map = new StudentLocationMap(wrapper);
};

frappe.pages["student-location-map"].on_page_show = function (wrapper) {
	// Leaflet measures its container on init; coming back to a page that was
	// hidden leaves it with stale dimensions until it is told to re-measure.
	wrapper.student_location_map && wrapper.student_location_map.refresh_size();
};

class StudentLocationMap {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");

		// Every student the user may see, split by whether they can be plotted.
		this.located = [];
		this.unlocated = [];

		// Marker instances, parallel to `this.located` and built once.
		this.markers = [];

		this.filters = { search: "", gender: "", standard: "", batch: "", area: "" };
		this.destroyed = false;

		this.setup_ui();
		this.bind_events();
		this.start();
	}

	// ── setup ────────────────────────────────────────────────────────────────

	setup_ui() {
		this.wrapper.html(frappe.render_template("student_location_map", {}));

		this.$root = this.wrapper.find(".slm-page");
		this.$mapShell = this.$root.find(".slm-map-shell");
		this.$mapEl = this.$root.find("#slm-map");

		this.$search = this.$root.find("#slm-search");
		this.$gender = this.$root.find("#slm-gender");
		this.$standard = this.$root.find("#slm-standard");
		this.$batch = this.$root.find("#slm-batch");
		this.$area = this.$root.find("#slm-area");

		this.$statTotal = this.$root.find("#slm-stat-total");
		this.$statMapped = this.$root.find("#slm-stat-mapped");
		this.$statMissing = this.$root.find("#slm-stat-missing");
		this.$missingCount = this.$root.find("#slm-missing-count");

		this.$loading = this.$root.find("#slm-loading");
		this.$loadingProgress = this.$root.find("#slm-loading-progress");
		this.$empty = this.$root.find("#slm-empty");
		this.$noResults = this.$root.find("#slm-no-results");
		this.$error = this.$root.find("#slm-error");

		// Frappe embeds a page template inside a single-quoted JS string and does
		// not escape apostrophes, so any translated text containing one has to be
		// set from here rather than written into the .html file.
		this.$search.attr("placeholder", __("Search by student name or ID"));
		this.$root
			.find("#slm-fit")
			.attr({ title: __("Fit all visible students"), "aria-label": __("Fit all visible students") });
		this.$root
			.find("#slm-fullscreen")
			.attr({ title: __("Full screen"), "aria-label": __("Full screen") });

		if (!this.fullscreen_supported()) {
			this.$root.find("#slm-fullscreen").hide();
		}
	}

	bind_events() {
		const rerender = frappe.utils.debounce(() => this.apply_filters({ fit: true }), 180);

		this.$search.on("input", () => {
			this.filters.search = (this.$search.val() || "").trim().toLowerCase();
			rerender();
		});

		this.$gender.on("change", () => {
			this.filters.gender = this.$gender.val() || "";
			this.apply_filters({ fit: true });
		});

		this.$standard.on("change", () => {
			this.filters.standard = this.$standard.val() || "";
			this.apply_filters({ fit: true });
		});

		this.$batch.on("change", () => {
			this.filters.batch = this.$batch.val() || "";
			this.apply_filters({ fit: true });
		});

		this.$area.on("change", () => {
			this.filters.area = this.$area.val() || "";
			this.apply_filters({ fit: true });
		});

		this.$root.on("click", "#slm-reset, #slm-no-results-action", () => this.reset_filters());
		this.$root.on("click", "#slm-show-all", () => this.reset_filters());
		this.$root.on("click", "#slm-missing, #slm-empty-action", () => this.show_missing_dialog());
		this.$root.on("click", "#slm-retry", () => this.start());
		this.$root.on("click", "#slm-fit", () => this.fit_to_visible());
		this.$root.on("click", "#slm-fullscreen", () => this.toggle_fullscreen());

		// The map lives inside the shell, so both the browser leaving full
		// screen and the desk sidebar collapsing need a re-measure.
		this.on_fullscreen_change = () => this.refresh_size();
		document.addEventListener("fullscreenchange", this.on_fullscreen_change);
		document.addEventListener("webkitfullscreenchange", this.on_fullscreen_change);

		this.on_resize = frappe.utils.debounce(() => this.refresh_size(), 200);
		$(window).on("resize.slm", this.on_resize);
	}

	// ── boot sequence ────────────────────────────────────────────────────────

	async start() {
		this.show_state("loading");

		try {
			await this.load_assets();
		} catch (e) {
			// eslint-disable-next-line no-console
			console.error("Student Location Map: map library failed to load", e);
			this.show_error(
				__("The map library could not be loaded."),
				__("Leaflet is served from a public CDN. Check this machine's internet access, then retry.")
			);
			return;
		}

		this.init_map();

		try {
			await this.load_students();
		} catch (e) {
			// eslint-disable-next-line no-console
			console.error("Student Location Map: failed to load students", e);
			this.show_error(__("Could not load student locations."), slm_error_text(e));
			return;
		}

		this.build_filter_options();
		this.build_markers();
		this.apply_filters({ fit: true });
	}

	load_assets() {
		return SLM_ASSETS.reduce(
			(chain, asset) => chain.then(() => slm_load_asset(asset)),
			Promise.resolve()
		);
	}

	init_map() {
		if (this.map) return;

		this.map = L.map(this.$mapEl[0], {
			center: SLM_DEFAULT_CENTER,
			zoom: SLM_DEFAULT_ZOOM,
			zoomControl: true,
			preferCanvas: false,
			worldCopyJump: true,
		});

		// OpenStreetMap standard tiles. Attribution is required by the ODbL
		// and the OSM tile usage policy — do not remove it.
		L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
		}).addTo(this.map);

		this.cluster = L.markerClusterGroup({
			chunkedLoading: true,
			showCoverageOnHover: false,
			maxClusterRadius: 60,
			spiderfyOnMaxZoom: true,
			disableClusteringAtZoom: 18,
			iconCreateFunction: (cluster) => {
				const count = cluster.getChildCount();
				const size = count < 10 ? 40 : count < 100 ? 48 : 56;
				const tone = count < 10 ? "" : count < 100 ? "slm-cluster-md" : "slm-cluster-lg";
				return L.divIcon({
					html: `<div class="slm-cluster-inner">${count}</div>`,
					className: `slm-cluster ${tone}`,
					iconSize: L.point(size, size),
				});
			},
		});

		this.map.addLayer(this.cluster);
		this.refresh_size();
	}

	// ── data ─────────────────────────────────────────────────────────────────

	/**
	 * Pull every student the user is allowed to see, in bulk pages.
	 * One request per 1,000 students — never one per marker.
	 */
	async load_students() {
		this.located = [];
		this.unlocated = [];

		let limit_start = 0;

		// Hard stop so a server that keeps claiming `has_more` cannot spin here.
		for (let page = 0; page < 100; page++) {
			const r = await frappe.call({
				method: `${SLM_API}.get_students`,
				args: { limit_start: limit_start, page_length: SLM_PAGE_LENGTH },
			});

			const data = r && r.message;
			if (!data) throw new Error(__("Empty response from the server."));

			this.located = this.located.concat(data.located || []);
			this.unlocated = this.unlocated.concat(data.unlocated || []);

			const loaded = this.located.length + this.unlocated.length;
			this.$loadingProgress.text(__("Loaded {0} students…", [slm_number(loaded)]));

			if (!data.has_more) break;
			limit_start += data.page_length;
		}

		// Pre-compute the haystack each student is searched against, so typing
		// never re-lowercases thousands of strings on every keystroke.
		[...this.located, ...this.unlocated].forEach((s) => {
			s._search = `${s.name || ""} ${s.student_name || ""}`.toLowerCase();
		});
	}

	build_filter_options() {
		const all = [...this.located, ...this.unlocated];

		const fill = ($select, key, allLabel) => {
			const values = Array.from(
				new Set(all.map((s) => s[key]).filter((v) => v))
			).sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));

			const current = $select.val();
			const options = [`<option value="">${frappe.utils.escape_html(allLabel)}</option>`].concat(
				values.map((v) => {
					const safe = frappe.utils.escape_html(String(v));
					return `<option value="${safe}">${safe}</option>`;
				})
			);

			$select.html(options.join(""));
			// Keep a selection that is still valid (a retry must not silently
			// widen the filters the user had set).
			if (current && values.indexOf(current) !== -1) $select.val(current);
		};

		fill(this.$gender, "gender", __("All Students"));
		fill(this.$standard, "standard", __("All Standards"));
		fill(this.$batch, "batch", __("All Batches"));
		fill(this.$area, "area", __("All Areas"));
	}

	// ── markers ──────────────────────────────────────────────────────────────

	build_markers() {
		// Only ever built once per load; filtering reuses these instances.
		this.cluster.clearLayers();
		this.markers = this.located.map((student) => this.create_marker(student));
		this.visible_signature = null;
	}

	create_marker(student) {
		const color = slm_pin_color(student.name || student.student_name || "");
		const initials = slm_initials(student.student_name || student.name);
		const photo = student.image
			? `<img class="slm-marker-photo" src="${frappe.utils.escape_html(student.image)}"
					alt="" loading="lazy" onerror="this.style.display='none'">`
			: "";

		const icon = L.divIcon({
			className: "slm-marker",
			iconSize: [44, 52],
			iconAnchor: [22, 52],
			popupAnchor: [0, -46],
			tooltipAnchor: [0, -50],
			html: `
				<div class="slm-marker-tail" style="--slm-pin:${color}"></div>
				<div class="slm-marker-pin" style="--slm-pin:${color}">
					<span class="slm-marker-initials">${frappe.utils.escape_html(initials)}</span>
					${photo}
				</div>`,
		});

		const marker = L.marker([student.latitude, student.longitude], {
			icon: icon,
			title: student.student_name || student.name,
			riseOnHover: true,
		});

		// Lazy: the card is only built the first time this marker is opened.
		marker.bindPopup(() => slm_popup_html(student), {
			className: "slm-popup",
			minWidth: 268,
			maxWidth: 300,
			autoPanPadding: [24, 24],
			closeButton: true,
		});

		// Hovering a pin previews the student without having to click it. Also
		// lazy, and non-interactive, so it never gets in the way of the popup.
		marker.bindTooltip(() => slm_tooltip_html(student), {
			className: "slm-tip",
			direction: "top",
			opacity: 1,
			sticky: false,
		});

		marker.slm_student = student;
		return marker;
	}

	// ── filtering ────────────────────────────────────────────────────────────

	matches(student) {
		const f = this.filters;
		if (f.gender && student.gender !== f.gender) return false;
		if (f.standard && student.standard !== f.standard) return false;
		if (f.batch && student.batch !== f.batch) return false;
		if (f.area && student.area !== f.area) return false;
		if (f.search && student._search.indexOf(f.search) === -1) return false;
		return true;
	}

	apply_filters({ fit = false } = {}) {
		if (!this.map) return;

		const visible = [];
		for (let i = 0; i < this.located.length; i++) {
			if (this.matches(this.located[i])) visible.push(this.markers[i]);
		}

		const missing = this.unlocated.filter((s) => this.matches(s));

		this.update_summary(visible.length, missing.length);

		// Swapping the cluster's contents is what a filter change costs — the
		// map, the tile layer and every marker instance survive untouched.
		const signature = `${visible.length}|${this.filters.search}|${this.filters.gender}|${this.filters.standard}|${this.filters.batch}|${this.filters.area}`;
		if (signature !== this.visible_signature) {
			this.visible_signature = signature;
			this.cluster.clearLayers();
			if (visible.length) this.cluster.addLayers(visible);
		}

		if (!this.located.length) {
			this.show_state("empty");
		} else if (!visible.length) {
			this.show_state("no-results");
		} else {
			this.show_state(null);
			if (fit) this.fit_to(visible);
		}
	}

	reset_filters() {
		this.filters = { search: "", gender: "", standard: "", batch: "", area: "" };
		this.$search.val("");
		this.$gender.val("");
		this.$standard.val("");
		this.$batch.val("");
		this.$area.val("");
		this.apply_filters({ fit: true });
	}

	update_summary(mapped, missing) {
		this.$statTotal.text(slm_number(mapped + missing));
		this.$statMapped.text(slm_number(mapped));
		this.$statMissing.text(slm_number(missing));
		this.$missingCount.text(slm_number(missing));
	}

	// ── view helpers ─────────────────────────────────────────────────────────

	fit_to(markers) {
		if (!this.map || !markers || !markers.length) return;
		const bounds = L.latLngBounds(markers.map((m) => m.getLatLng()));
		this.map.fitBounds(bounds, { padding: [48, 48], maxZoom: 16 });
	}

	fit_to_visible() {
		const visible = [];
		for (let i = 0; i < this.located.length; i++) {
			if (this.matches(this.located[i])) visible.push(this.markers[i]);
		}

		if (!visible.length) {
			this.map && this.map.setView(SLM_DEFAULT_CENTER, SLM_DEFAULT_ZOOM);
			return;
		}

		this.fit_to(visible);
	}

	show_state(state) {
		this.$loading.prop("hidden", state !== "loading");
		this.$empty.prop("hidden", state !== "empty");
		this.$noResults.prop("hidden", state !== "no-results");
		this.$error.prop("hidden", state !== "error");
	}

	show_error(title, text) {
		this.$root.find("#slm-error-title").text(title);
		this.$root.find("#slm-error-text").text(text || "");
		this.show_state("error");
	}

	refresh_size() {
		if (!this.map) return;
		// One frame later, so the container has its final size.
		setTimeout(() => this.map && this.map.invalidateSize(), 60);
	}

	fullscreen_supported() {
		const el = this.$mapShell && this.$mapShell[0];
		return !!(el && (el.requestFullscreen || el.webkitRequestFullscreen));
	}

	toggle_fullscreen() {
		const el = this.$mapShell[0];
		const active = document.fullscreenElement || document.webkitFullscreenElement;

		if (active) {
			(document.exitFullscreen || document.webkitExitFullscreen).call(document);
			return;
		}

		const request = el.requestFullscreen || el.webkitRequestFullscreen;
		request && request.call(el);
	}

	// ── students without location ────────────────────────────────────────────

	show_missing_dialog() {
		// The full list is already in memory from the initial load, so opening
		// this costs no request at all.
		const dialog = new frappe.ui.Dialog({
			title: __("Students Without Location"),
			size: "extra-large",
		});

		const $body = $(dialog.body);
		$body.html(`
			<div class="slm-missing-wrap">
				<input type="text" class="slm-missing-search"
					placeholder="${frappe.utils.escape_html(__("Search by student name or ID"))}">
				<div class="slm-missing-scroll"></div>
				<p class="slm-missing-muted" style="margin:0;font-size:12px;">
					${frappe.utils.escape_html(
						__("Open each student and enter Latitude and Longitude to place them on the map.")
					)}
				</p>
			</div>
		`);

		const $scroll = $body.find(".slm-missing-scroll");

		const render = (term) => {
			const needle = (term || "").trim().toLowerCase();
			const rows = this.unlocated.filter(
				(s) => !needle || (s._search || "").indexOf(needle) !== -1
			);
			$scroll.html(slm_missing_table(rows));
		};

		render("");

		$body.find(".slm-missing-search").on(
			"input",
			frappe.utils.debounce(function () {
				render($(this).val());
			}, 180)
		);

		dialog.show();
	}
}

// ── module-level helpers ─────────────────────────────────────────────────────

/**
 * Load one CSS/JS asset, trying each URL in turn.
 * Resolves immediately if the library is already present (page revisits).
 */
function slm_load_asset(asset) {
	if (asset.test && asset.test()) return Promise.resolve();

	const attempt = (index) => {
		if (index >= asset.urls.length) {
			return Promise.reject(new Error(`Could not load ${asset.urls[0]}`));
		}

		const url = asset.urls[index];
		const existing = document.querySelector(
			asset.type === "css" ? `link[href="${url}"]` : `script[src="${url}"]`
		);
		if (existing && existing.dataset.slmLoaded === "1") return Promise.resolve();

		return new Promise((resolve, reject) => {
			let el;
			if (asset.type === "css") {
				el = document.createElement("link");
				el.rel = "stylesheet";
				el.href = url;
			} else {
				el = document.createElement("script");
				el.src = url;
				el.async = false;
			}
			el.onload = () => {
				el.dataset.slmLoaded = "1";
				resolve();
			};
			el.onerror = () => {
				el.remove();
				reject(new Error(`Failed to load ${url}`));
			};
			document.head.appendChild(el);
		}).catch(() => attempt(index + 1));
	};

	return attempt(0).then(() => {
		if (asset.test && !asset.test()) {
			throw new Error("Asset loaded but did not register itself");
		}
	});
}

/** Best available description of a failed request, for the error state. */
function slm_error_text(e) {
	if (!e) return __("The server did not return student data.");
	if (e.responseJSON && e.responseJSON.exception) return String(e.responseJSON.exception);
	if (e.status === 403) {
		return __("You do not have permission to view student locations. Ask an administrator for the Attendance Manager role.");
	}
	if (e.message) return String(e.message);
	return __("The server did not return student data. Check the connection and retry.");
}

/**
 * Group a count for display. Deliberately not frappe.format(): that returns an
 * HTML fragment for Int fields, and these counts go into elements as text.
 */
function slm_number(value) {
	return Number(value || 0).toLocaleString();
}

function slm_initials(name) {
	const parts = String(name || "?")
		.trim()
		.split(/\s+/)
		.filter(Boolean);
	if (!parts.length) return "?";
	if (parts.length === 1) return parts[0].substr(0, 2).toUpperCase();
	return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function slm_pin_color(key) {
	let hash = 0;
	const text = String(key);
	for (let i = 0; i < text.length; i++) {
		hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
	}
	return SLM_PIN_COLORS[hash % SLM_PIN_COLORS.length];
}

/** OpenStreetMap directions — free, no key, works on desktop and mobile. */
function slm_directions_url(lat, lng) {
	const to = `${lat},${lng}`;
	return (
		"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car" +
		`&route=${encodeURIComponent(";" + to)}#map=16/${lat}/${lng}`
	);
}

function slm_popup_html(student) {
	const esc = frappe.utils.escape_html;
	const dash = `<span class="slm-popup-muted">${esc(__("Not set"))}</span>`;
	const value = (v) => (v ? esc(String(v)) : dash);

	const initials = esc(slm_initials(student.student_name || student.name));
	const avatar = student.image
		? `<img src="${esc(student.image)}" alt="" onerror="this.style.display='none'">`
		: "";

	const rows = [
		[__("Gender"), student.gender],
		[__("Standard"), student.standard],
		[__("Batch"), student.batch],
		[__("Area"), student.area],
		[__("Street"), student.street_name],
		[__("Address"), student.address],
	]
		.map(
			([label, val]) => `
				<div class="slm-popup-row">
					<div class="slm-popup-key">${esc(label)}</div>
					<div class="slm-popup-val">${value(val)}</div>
				</div>`
		)
		.join("");

	// The Student form is opened by its real desk route — no second form is
	// ever built for the map.
	const form_url = `/app/student/${encodeURIComponent(student.name)}`;

	return `
		<div class="slm-card-popup">
			<div class="slm-popup-head">
				<div class="slm-popup-avatar">${initials}${avatar}</div>
				<div>
					<div class="slm-popup-name">${esc(student.student_name || student.name)}</div>
					<div class="slm-popup-id">${esc(student.name)}</div>
				</div>
			</div>
			<div class="slm-popup-body">${rows}</div>
			<div class="slm-popup-actions">
				<a class="slm-popup-btn slm-popup-btn-view" href="${form_url}">
					<i class="fa fa-user"></i> ${esc(__("View Student"))}
				</a>
				<a class="slm-popup-btn slm-popup-btn-directions"
					href="${slm_directions_url(student.latitude, student.longitude)}"
					target="_blank" rel="noopener noreferrer">
					<i class="fa fa-location-arrow"></i> ${esc(__("Get Directions"))}
				</a>
			</div>
		</div>`;
}

/**
 * Compact hover preview. Deliberately smaller than the popup: enough to
 * recognise the student and their batch without clicking.
 */
function slm_tooltip_html(student) {
	const esc = frappe.utils.escape_html;
	const initials = esc(slm_initials(student.student_name || student.name));
	const color = slm_pin_color(student.name || student.student_name || "");

	const avatar = student.image
		? `<img src="${esc(student.image)}" alt="" onerror="this.style.display='none'">`
		: "";

	const line = (parts) => {
		const shown = parts.filter((p) => p).map((p) => esc(String(p)));
		return shown.length ? `<div class="slm-tip-line">${shown.join(" &middot; ")}</div>` : "";
	};

	return `
		<div class="slm-tip-card">
			<div class="slm-tip-avatar" style="--slm-pin:${color}">${initials}${avatar}</div>
			<div class="slm-tip-body">
				<div class="slm-tip-name">${esc(student.student_name || student.name)}</div>
				<div class="slm-tip-id">${esc(student.name)}</div>
				${line([student.gender, student.standard, student.batch ? __("Batch {0}", [student.batch]) : ""])}
				${line([student.area, student.street_name])}
			</div>
		</div>`;
}

function slm_missing_table(rows) {
	const esc = frappe.utils.escape_html;

	if (!rows.length) {
		return `<div class="slm-missing-empty">${esc(
			__("Every student in this list already has coordinates.")
		)}</div>`;
	}

	const dash = '<span class="slm-missing-muted">—</span>';
	const cell = (v) => (v ? esc(String(v)) : dash);

	const body = rows
		.map(
			(s) => `
			<tr>
				<td><strong>${esc(s.name)}</strong></td>
				<td>${cell(s.student_name)}</td>
				<td>${cell(s.gender)}</td>
				<td>${cell(s.standard)}</td>
				<td>${cell(s.batch)}</td>
				<td>${cell(s.area)}</td>
				<td>${cell(s.street_name)}</td>
				<td>
					<a class="slm-missing-open" href="/app/student/${encodeURIComponent(s.name)}">
						<i class="fa fa-external-link"></i> ${esc(__("Open Student"))}
					</a>
				</td>
			</tr>`
		)
		.join("");

	return `
		<table class="slm-missing-table">
			<thead>
				<tr>
					<th>${esc(__("Student ID"))}</th>
					<th>${esc(__("Student Name"))}</th>
					<th>${esc(__("Gender"))}</th>
					<th>${esc(__("Standard"))}</th>
					<th>${esc(__("Batch"))}</th>
					<th>${esc(__("Area"))}</th>
					<th>${esc(__("Street"))}</th>
					<th></th>
				</tr>
			</thead>
			<tbody>${body}</tbody>
		</table>`;
}
