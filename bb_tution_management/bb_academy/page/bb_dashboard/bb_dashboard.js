/* ═══════════════════════════════════════════════════════════════════════════
   BB Academy Dashboard — page controller

   Notes for future edits:
   • One API call (`get_dashboard`) fills the whole page.
   • Icons come from the sprite in `_sprite()`. Do NOT use frappe.utils.icon()
     here — it resolves names to `#icon-<name>`, and the desk sprite only ships
     6 such symbols, so every name this page needs renders blank.
   • No inline onclick anywhere. Handlers are delegated off [data-bb-*]
     attributes so document names containing quotes can't break the markup.
   • Chart colours are validated (see bb_dashboard.css header). Single-series
     bars use one hue; status colours always ship with a text label beside them.
   ═══════════════════════════════════════════════════════════════════════════ */

frappe.pages["bb-dashboard"].on_page_show = function (wrapper) {
	if (!wrapper._bb) {
		wrapper._bb = new BBDashboard(wrapper);
	} else {
		wrapper._bb.refresh();
	}
};

const BB_API = "bb_tution_management.bb_academy.page.bb_dashboard.bb_dashboard";

const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

/* Decorative accent hues for chrome — icon badges, card rules, tiles.
   These are the eight validated categorical hues (see bb_dashboard.css header):
   each sits inside the lightness band, clears the chroma floor, and holds 3:1
   against both card surfaces. They are assigned per ENTITY and never cycled by
   rank, so a tile keeps its colour as numbers move.

   They are chrome only. Data marks (bar fills, status tracks) stay single-hue —
   colour there would claim a meaning the data does not have. */
const BB_ACCENTS = {
	blue: "blue",
	violet: "violet",
	aqua: "aqua",
	orange: "orange",
	magenta: "magenta",
	green: "green",
	yellow: "yellow",
	red: "red",
};

const prefersReducedMotion = () =>
	window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

class BBDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("BB Academy"),
			single_column: true,
		});

		this.page.set_primary_action(__("Refresh"), () => this.refresh());
		this.page.add_inner_button(__("New Enquiry"), () => frappe.new_doc("Student Enquiry Form"));
		this.page.add_inner_button(__("New Admission"), () => frappe.new_doc("Student Admission Form"));
		this.page.add_inner_button(__("New Invoice"), () => frappe.new_doc("Fee Invoice"));

		this.$body = $(this.page.body).addClass("bb-dash-root");
		this.charts = [];

		this._build_shell();
		this._bind_events();
		this._bind_resize();
		this._load();
		this._start_auto_refresh();
	}

	/* frappe-charts sizes its SVG once, at construction — it does not reflow.
	   Re-render the trend chart on resize/orientation change so it stays right
	   when a phone is rotated or the desk sidebar is toggled. */
	_bind_resize() {
		let timer;
		this._on_resize = () => {
			clearTimeout(timer);
			timer = setTimeout(() => {
				if (!this.$body.is(":visible") || !this._trend_rows) return;
				this._render_trend(this._trend_rows);
			}, 250);
		};
		window.addEventListener("resize", this._on_resize);
		window.addEventListener("orientationchange", this._on_resize);
	}

	/* ── icon sprite ────────────────────────────────────────────────────── */

	_sprite() {
		/* Two icon builders:
		   duo() → duotone: a soft filled mass + a crisp stroked outline, both
		           inheriting currentColor. This is what makes the coloured
		           badges read as rich rather than flat line art.
		   ln()  → plain stroked line icon, for small inline use. */
		const duo = (id, fill, line, w = 24) =>
			`<symbol id="bbd-${id}" viewBox="0 0 ${w} ${w}">
				<g fill="currentColor" class="bb-ico__mass">${fill}</g>
				<g fill="none" stroke="currentColor" stroke-width="1.7"
					stroke-linecap="round" stroke-linejoin="round">${line}</g>
			</symbol>`;

		const ln = (id, body, w = 24) =>
			`<symbol id="bbd-${id}" viewBox="0 0 ${w} ${w}" fill="none" stroke="currentColor"
				stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${body}</symbol>`;

		return `<svg xmlns="http://www.w3.org/2000/svg" class="bb-sprite" aria-hidden="true" focusable="false">
			${duo(
				"users",
				'<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2Z"/>',
				'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
			)}
			${duo(
				"user-plus",
				'<circle cx="8" cy="7" r="4"/><path d="M1 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2Z"/>',
				'<path d="M15 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>'
			)}
			${duo(
				"enquiry",
				'<path d="M21 11.5A8.5 8.5 0 0 1 12.5 20a8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7A8.4 8.4 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3h.5a8.5 8.5 0 0 1 8 8Z"/>',
				'<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8A8.5 8.5 0 0 1 12.5 20a8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7A8.4 8.4 0 0 1 4 11.5 8.5 8.5 0 0 1 8.7 3.9a8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M9 11.5h.01M12.5 11.5h.01M16 11.5h.01"/>'
			)}
			${duo(
				"rupee",
				'<circle cx="12" cy="12" r="9"/>',
				'<circle cx="12" cy="12" r="9"/><path d="M9 8h6M9 11h6"/><path d="M13.5 8c0 3.2-2 3-4.5 3l5 5.5"/>'
			)}
			${duo(
				"wallet",
				'<rect x="2" y="6" width="20" height="14" rx="3"/>',
				'<rect x="2" y="6" width="20" height="14" rx="3"/><path d="M2 10.5h20"/><circle cx="17.5" cy="15.5" r="1.6"/>'
			)}
			${duo(
				"receipt",
				'<path d="M6 2h12a1 1 0 0 1 1 1v19l-3.3-2-3.7 2-3.7-2L5 22V3a1 1 0 0 1 1-1Z"/>',
				'<path d="M6 2h12a1 1 0 0 1 1 1v19l-3.3-2-3.7 2-3.7-2L5 22V3a1 1 0 0 1 1-1Z"/><path d="M9 7h6M9 11h6M9 15h3"/>'
			)}
			${duo(
				"trending-up",
				'<path d="M3 19h18V7.5L13.5 15l-4-4Z"/>',
				'<path d="M22 7l-8.5 8.5-4-4L2 19"/><path d="M16 7h6v6"/>'
			)}
			${duo(
				"chart",
				'<path d="M4 13h3v8H4zM10.5 8h3v13h-3zM17 4h3v17h-3z"/>',
				'<path d="M3 21h18"/><path d="M5.5 21v-8M12 21V7.5M18.5 21V4"/>'
			)}
			${duo(
				"cake",
				'<path d="M4 13a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8H4Z"/>',
				'<path d="M20 21v-8a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8"/><path d="M2 21h20"/><path d="M7 11V8M12 11V8M17 11V8"/><path d="M4.5 16c2 1.4 3.8 1.4 5.7 0 1.9-1.4 3.8-1.4 5.7 0 1.4 1 2.6 1.3 4.1.4"/>'
			)}
			${duo(
				"phone",
				'<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>',
				'<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>'
			)}
			${duo(
				"alert",
				'<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
				'<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>'
			)}
			${duo(
				"layers",
				'<path d="M12 2 2 7l10 5 10-5Z"/>',
				'<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>'
			)}
			${duo(
				"cap",
				'<path d="M22 10 12 5 2 10l10 5Z"/>',
				'<path d="M22 10 12 5 2 10l10 5 10-5Z"/><path d="M6 12.5V17c0 1.7 2.7 3 6 3s6-1.3 6-3v-4.5"/><path d="M22 10v6"/>'
			)}
			${duo(
				"book",
				'<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v16H6.5A2.5 2.5 0 0 0 4 20.5Z"/>',
				'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/><path d="M9 7h7"/>'
			)}
			${duo(
				"gift",
				'<path d="M3 8h18v4H3zM5 12h14v9H5z"/>',
				'<path d="M20 12v9H4v-9"/><path d="M2 7h20v5H2z"/><path d="M12 21V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7Z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7Z"/>'
			)}
			${duo(
				"trophy",
				'<path d="M8 4h8v6a4 4 0 0 1-8 0Z"/>',
				'<path d="M8 4h8v6a4 4 0 0 1-8 0Z"/><path d="M8 6H5.5a3 3 0 0 0 3 3.4M16 6h2.5a3 3 0 0 1-3 3.4"/><path d="M12 14v3"/><path d="M9 21h6"/><path d="M10 21c0-2 .9-4 2-4s2 2 2 4"/>'
			)}
			${duo(
				"settings",
				'<circle cx="12" cy="12" r="8"/>',
				'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>'
			)}
			${duo(
				"school",
				'<path d="M4 9.5 12 5l8 4.5V21H4Z"/>',
				'<path d="M2 21h20"/><path d="M4 21V9.5L12 5l8 4.5V21"/><path d="M9.5 21v-4.5h5V21"/><path d="M12 5V2.5h3.5v2"/>'
			)}
			${duo(
				"transfer",
				'<circle cx="12" cy="12" r="9"/>',
				'<path d="M4 8h13l-3-3M20 16H7l3 3"/>'
			)}
			${ln("arrow-right", '<path d="M5 12h14M13 5l7 7-7 7"/>')}
			${ln("plus", '<path d="M12 5v14M5 12h14"/>')}
			${ln("check", '<path d="M20 6 9 17l-5-5"/>')}
			${ln("clock", '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>')}
			${ln(
				"file-text",
				'<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/>'
			)}
			${ln("sparkle", '<path d="M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4Z"/>')}
		</svg>`;
	}

	_ico(name, cls = "") {
		return `<svg class="bb-ico ${cls}" aria-hidden="true"><use href="#bbd-${name}"></use></svg>`;
	}

	/* ── shell ──────────────────────────────────────────────────────────── */

	/** Card header with a coloured duotone icon badge. `right` is optional
	 *  trailing markup (a note or a "View all" button). */
	_head(icon, title, accent, right = "") {
		return `<div class="bb-card__head">
			<span class="bb-badge-grad bb-badge-grad--sm">${this._ico(icon)}</span>
			<h3 class="bb-card__title">${title}</h3>
			${right}
		</div>`;
	}

	_build_shell() {
		const note = (t) => `<span class="bb-card__note">${t}</span>`;
		const viewAll = (dt) =>
			`<button class="bb-link" data-bb-list="${esc(dt)}">${__("View all")}</button>`;

		this.$body.html(`
			${this._sprite()}
			<div class="bb-dash">
				<div data-ref="hero"></div>
				<div data-ref="alert-strip"></div>
				<div class="bb-kpi-grid" data-ref="kpis">${this._skel_kpis(4)}</div>

				<div class="bb-card bb-card--accent bb-a--violet bb-rise" style="--bb-i:0">
					${this._head("sparkle", __("Quick Actions"), "violet")}
					<div class="bb-card__body bb-actions" data-ref="actions"></div>
				</div>

				<div class="bb-grid bb-grid--2-1" data-ref="grid-charts">
					<div class="bb-card bb-card--accent bb-a--blue bb-rise" style="--bb-i:1">
						${this._head("trending-up", __("Monthly Collection"), "blue", note(__("Last 12 months")))}
						<div class="bb-card__body bb-chart-scroll">
							<div class="bb-chart-host" data-ref="chart-trend">
								<div class="bb-skel bb-skel--chart"></div>
							</div>
						</div>
					</div>
					<div class="bb-card bb-card--accent bb-a--violet bb-rise" style="--bb-i:2">
						${this._head("receipt", __("Invoice Status"), "violet")}
						<div class="bb-card__body" data-ref="invoice-status">
							<div class="bb-skel bb-skel--rows"></div>
						</div>
					</div>
				</div>

				<div class="bb-grid bb-grid--2">
					<div class="bb-card bb-card--accent bb-a--aqua bb-rise" style="--bb-i:3">
						${this._head("book", __("Students by Standard"), "aqua", note(__("Active only")))}
						<div class="bb-card__body" data-ref="standards"></div>
					</div>
					<div class="bb-card bb-card--accent bb-a--orange bb-rise" style="--bb-i:4">
						${this._head("enquiry", __("Enquiry Sources"), "orange", note(__("All time")))}
						<div class="bb-card__body" data-ref="sources"></div>
					</div>
				</div>

				<div class="bb-grid bb-grid--2">
					<div class="bb-card bb-card--accent bb-a--magenta bb-rise" style="--bb-i:5">
						${this._head("cake", __("Birthdays Today"), "magenta")}
						<div class="bb-card__body bb-card__body--flush" data-ref="birthdays"></div>
					</div>
					<div class="bb-card bb-card--accent bb-a--yellow bb-rise" style="--bb-i:6">
						${this._head("phone", __("Follow-ups Due"), "yellow", viewAll("Student Enquiry Form"))}
						<div class="bb-card__body bb-card__body--flush" data-ref="followups"></div>
					</div>
					<div class="bb-card bb-card--accent bb-a--green bb-rise" style="--bb-i:7">
						${this._head("wallet", __("Recent Collections"), "green", viewAll("Fee Invoice"))}
						<div class="bb-card__body bb-card__body--flush" data-ref="payments"></div>
					</div>
					<div class="bb-card bb-card--accent bb-a--red bb-rise" style="--bb-i:8">
						${this._head("alert", __("Outstanding Invoices"), "red", viewAll("Fee Invoice"))}
						<div class="bb-card__body bb-card__body--flush" data-ref="outstanding"></div>
					</div>
				</div>

				<div class="bb-card bb-card--accent bb-a--blue bb-rise" style="--bb-i:9">
					${this._head("chart", __("Reports"), "blue")}
					<div class="bb-card__body bb-reports" data-ref="reports"></div>
				</div>
			</div>
		`);

		this._render_actions();
		this._render_reports();
	}

	/* ── count-up ───────────────────────────────────────────────────────── */

	/** Animate a number into place. `fmt` renders each frame, so currency
	 *  tiles count up formatted rather than flashing a raw float. */
	_count_up($el, target, fmt) {
		const to = flt(target);
		if (prefersReducedMotion() || !to) {
			$el.text(fmt(to));
			return;
		}
		const dur = 650;
		const t0 = performance.now();
		const step = (now) => {
			const p = Math.min((now - t0) / dur, 1);
			const eased = 1 - Math.pow(1 - p, 3); // ease-out cubic
			$el.text(fmt(to * eased));
			if (p < 1) requestAnimationFrame(step);
			else $el.text(fmt(to));
		};
		requestAnimationFrame(step);
	}

	_skel_kpis(n) {
		return Array.from(
			{ length: n },
			() => `<div class="bb-kpi"><div class="bb-skel bb-skel--rows"></div></div>`
		).join("");
	}

	$ref(name) {
		return this.$body.find(`[data-ref="${name}"]`);
	}

	/* ── delegated events ───────────────────────────────────────────────── */

	_bind_events() {
		this.$body.on("click", "[data-bb-doc]", (e) => {
			const $t = $(e.currentTarget);
			frappe.set_route("Form", $t.attr("data-bb-doctype"), $t.attr("data-bb-doc"));
		});

		this.$body.on("click", "[data-bb-list]", (e) => {
			const $t = $(e.currentTarget);
			const raw = $t.attr("data-bb-filters");
			frappe.set_route("List", $t.attr("data-bb-list"), raw ? JSON.parse(raw) : {});
		});

		this.$body.on("click", "[data-bb-new]", (e) =>
			frappe.new_doc($(e.currentTarget).attr("data-bb-new"))
		);

		this.$body.on("click", "[data-bb-report]", (e) =>
			frappe.set_route("query-report", $(e.currentTarget).attr("data-bb-report"))
		);

		// Keyboard access for the clickable tiles/rows.
		this.$body.on("keydown", '[role="button"]', (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				$(e.currentTarget).trigger("click");
			}
		});
	}

	/* ── data ───────────────────────────────────────────────────────────── */

	async _load() {
		try {
			const d = await frappe.xcall(`${BB_API}.get_dashboard`);
			this.data = d;
			this.currency = (d.meta && d.meta.currency) || "INR";
			this.perms = (d.meta && d.meta.permissions) || {};

			// Undo any collapsing done by a previous onboarding render, so the
			// first refresh after the site gets real records shows everything.
			this.$body.find(".bb-card, .bb-grid").show();

			// MUST come after that reset — it un-hides every card, including
			// the ones permissions just took away.
			this._apply_permissions();

			this._render_hero(d);
			this._render_actions(d.counts);

			if (!d.meta.has_data) {
				this._render_onboarding();
				return;
			}

			this._render_alerts(d);
			this._render_kpis(d.kpi);
			this._render_trend(d.collection_trend);
			this._render_invoice_status(d.invoice_status, d.kpi);
			this._render_standards(d.students_by_standard);
			this._render_sources(d.enquiry_sources);
			this._render_birthdays(d.birthdays);
			this._render_followups(d.followups);
			this._render_payments(d.recent_payments);
			this._render_outstanding(d.outstanding_invoices);
		} catch (err) {
			console.error("BB Dashboard load failed:", err);
			this.$ref("kpis").html(
				`<div class="bb-error">
					${this._ico("alert")}
					<div>
						<strong>${__("Could not load dashboard data")}</strong>
						<div class="bb-error__detail">${esc(
							(err && (err.message || err.exc_type)) || __("Unknown error")
						)}</div>
					</div>
				</div>`
			);
		}
	}

	refresh() {
		this.$body.find(".bb-dash").addClass("bb-busy");
		return this._load().then(() => this.$body.find(".bb-dash").removeClass("bb-busy"));
	}

	_start_auto_refresh() {
		this._timer = setInterval(() => {
			// Skip when the tab is backgrounded or the page isn't on screen.
			if (document.visibilityState !== "visible") return;
			if (!this.$body.is(":visible")) return;
			this._load();
		}, 5 * 60 * 1000);
	}

	destroy() {
		clearInterval(this._timer);
		window.removeEventListener("resize", this._on_resize);
		window.removeEventListener("orientationchange", this._on_resize);
		this.charts.forEach((c) => c && c.destroy && c.destroy());
	}

	/* ── permissions ────────────────────────────────────────────────────── */

	/**
	 * Server-supplied permission flag from meta.permissions.
	 *
	 * This decides only what gets DRAWN. The real enforcement lives in
	 * bb_dashboard.py, which withholds the figures themselves — a restricted
	 * user calling the endpoint directly gets nothing back either.
	 *
	 * Defaults to allowed when the flag is absent, so an older payload degrades
	 * to the previous behaviour rather than blanking the page.
	 */
	can(flag) {
		return !this.perms || this.perms[flag] !== false;
	}

	/** Show/hide whole cards according to the server's permission flags. */
	_apply_permissions() {
		const finance = this.can("finance_summary");

		// Monthly Collection chart
		this.$ref("chart-trend").closest(".bb-card").toggle(finance);
		// Without it, Invoice Status would sit alone in the narrow 1fr column.
		this.$ref("grid-charts").toggleClass("bb-grid--solo", !finance);

		// Reports
		this.$ref("reports").closest(".bb-card").toggle(this.can("reports"));
	}

	/* ── formatting ─────────────────────────────────────────────────────── */

	/* `format_currency` and `get_currency_symbol` are window globals assigned by
	   frappe/utils/number_format.js — they are NOT on frappe.model. */
	money(v) {
		return format_currency(flt(v), this.currency);
	}

	/** Compact money for tight spots: ₹1.2L, ₹85k. */
	money_short(v) {
		const n = flt(v);
		const sym = get_currency_symbol(this.currency) || "";
		const abs = Math.abs(n);
		if (abs >= 1e7) return `${sym}${(n / 1e7).toFixed(2)}Cr`;
		if (abs >= 1e5) return `${sym}${(n / 1e5).toFixed(2)}L`;
		if (abs >= 1e3) return `${sym}${(n / 1e3).toFixed(1)}k`;
		return `${sym}${n.toFixed(0)}`;
	}

	date(v) {
		return v ? frappe.datetime.str_to_user(v) : "";
	}

	/* ── hero ───────────────────────────────────────────────────────────── */

	_render_hero(d) {
		const k = d.kpi;
		const hour = new Date().getHours();
		const greeting =
			hour < 12 ? __("Good morning") : hour < 17 ? __("Good afternoon") : __("Good evening");
		const name = esc(frappe.session.user_fullname || "");

		const collected = flt(k.total_collected);
		const billed = flt(k.total_billed);
		const pending = flt(k.total_pending);
		const pct = billed ? Math.min(100, (collected / billed) * 100) : 0;

		// Month-on-month delta on collections.
		let delta = "";
		if (flt(k.last_month_collection) > 0) {
			const change =
				((flt(k.monthly_collection) - flt(k.last_month_collection)) /
					flt(k.last_month_collection)) *
				100;
			const up = change >= 0;
			delta = `<span class="bb-delta bb-delta--${up ? "up" : "down"}">
				${up ? "↑" : "↓"} ${Math.abs(change).toFixed(1)}% ${__("vs last month")}
			</span>`;
		}

		this.$ref("hero").html(`
			<div class="bb-hero">
				<div class="bb-hero__deco" aria-hidden="true">
					${this._ico("cap")}${this._ico("book")}${this._ico("trophy")}${this._ico("chart")}
				</div>
				<div class="bb-hero__top">
					<div>
						<div class="bb-hero__greeting">${greeting}${name ? ", " + name : ""}</div>
						<h2 class="bb-hero__title">${esc(d.meta.month_label)}</h2>
					</div>
					<div class="bb-hero__figures">
						<div class="bb-hero__fig">
							<div class="bb-hero__fig-label">${__("Collected today")}</div>
							<div class="bb-hero__fig-value">${this.money(k.todays_collections)}</div>
						</div>
						${
							this.can("finance_summary")
								? `<div class="bb-hero__fig">
							<div class="bb-hero__fig-label">${__("This month")}</div>
							<div class="bb-hero__fig-value">${this.money(k.monthly_collection)}</div>
							${delta}
						</div>`
								: ""
						}
					</div>
				</div>

				${
					billed
						? `<div class="bb-hero__progress">
					<div class="bb-hero__progress-head">
						<span>${__("Fees collected")} — <strong>${flt(k.collection_rate).toFixed(
							1
						)}%</strong> ${__("of")} ${this.money(billed)}</span>
						<span class="bb-hero__progress-pending">${this.money(pending)} ${__("outstanding")}</span>
					</div>
					<div class="bb-meter" role="img"
						aria-label="${__("Collected")} ${this.money(collected)} ${__("of")} ${this.money(billed)}">
						<div class="bb-meter__fill" style="width:${pct}%"></div>
					</div>
				</div>`
						: ""
				}
			</div>
		`);
	}

	/* ── onboarding (fresh site, no records yet) ────────────────────────── */

	_render_onboarding() {
		this.$ref("alert-strip").empty();
		this.$ref("kpis").removeClass("bb-kpi-grid").html(`
			<div class="bb-onboard">
				<div class="bb-onboard__icon">${this._ico("cap")}</div>
				<h3>${__("No records yet")}</h3>
				<p>${__(
					"Every figure below reads zero because this site has no students, invoices or payments yet. Set up the basics in order and the dashboard fills in."
				)}</p>
				<ol class="bb-onboard__steps">
					<li>
						<span class="bb-onboard__num">1</span>
						<div>
							<strong>${__("Create Standards")}</strong>
							<span>${__("Classes and their starting payment")}</span>
						</div>
						<button class="bb-btn bb-btn--sm" data-bb-new="Standard">${__("Create")}</button>
					</li>
					<li>
						<span class="bb-onboard__num">2</span>
						<div>
							<strong>${__("Add Batches")}</strong>
							<span>${__("Timings and teachers")}</span>
						</div>
						<button class="bb-btn bb-btn--sm" data-bb-new="Batch">${__("Create")}</button>
					</li>
					<li>
						<span class="bb-onboard__num">3</span>
						<div>
							<strong>${__("Admit Students")}</strong>
							<span>${__("Via enquiry or directly")}</span>
						</div>
						<button class="bb-btn bb-btn--sm" data-bb-new="Student Admission Form">${__("Create")}</button>
					</li>
					<li>
						<span class="bb-onboard__num">4</span>
						<div>
							<strong>${__("Raise Fee Invoices")}</strong>
							<span>${__("Individually or in bulk")}</span>
						</div>
						<button class="bb-btn bb-btn--sm" data-bb-new="Fee Invoice">${__("Create")}</button>
					</li>
				</ol>
			</div>
		`);

		// Nothing to chart yet — collapse the data cards rather than show empty axes.
		[
			"chart-trend",
			"invoice-status",
			"standards",
			"sources",
			"birthdays",
			"followups",
			"payments",
			"outstanding",
		].forEach((r) => this.$ref(r).closest(".bb-card").hide());
		this.$body.find(".bb-grid").filter((_, el) => !$(el).children(":visible").length).hide();
	}

	/* ── alert strip ────────────────────────────────────────────────────── */

	_render_alerts(d) {
		const items = [];
		if (d.followups.length) {
			const overdue = d.followups.filter((f) => flt(f.overdue_days) > 0).length;
			items.push({
				tone: overdue ? "warn" : "info",
				icon: "phone",
				text: overdue
					? __("{0} enquiry follow-ups are overdue", [overdue])
					: __("{0} follow-ups due today", [d.followups.length]),
				doctype: "Student Enquiry Form",
			});
		}
		if (flt(d.kpi.total_pending) > 0) {
			items.push({
				tone: "crit",
				icon: "alert",
				text: __("{0} outstanding across {1} invoices", [
					this.money(d.kpi.total_pending),
					d.kpi.unpaid_invoices,
				]),
				doctype: "Fee Invoice",
			});
		}
		if (d.birthdays.length) {
			items.push({
				tone: "info",
				icon: "gift",
				text: __("{0} student birthdays today", [d.birthdays.length]),
				doctype: "Student",
			});
		}

		if (!items.length) {
			this.$ref("alert-strip").empty();
			return;
		}

		this.$ref("alert-strip").html(
			`<div class="bb-alerts">${items
				.map(
					(i) => `
				<button class="bb-alert bb-alert--${i.tone}" data-bb-list="${esc(i.doctype)}">
					${this._ico(i.icon)}<span>${i.text}</span>${this._ico("arrow-right", "bb-ico--end")}
				</button>`
				)
				.join("")}</div>`
		);
	}

	/* ── KPI tiles ──────────────────────────────────────────────────────── */

	_render_kpis(k) {
		const pending = flt(k.total_pending);

		/* `accent` is the tile's identity colour and never changes with the
		   numbers. `pill` carries state (good / warn / crit) and always ships
		   with its own text, so state is never colour-alone. */
		const tiles = [
			{
				icon: "users",
				accent: BB_ACCENTS.blue,
				label: __("Active Students"),
				count: k.active_students,
				meta:
					k.total_students > k.active_students
						? __("{0} enrolled in total", [k.total_students])
						: __("All enrolled students active"),
				list: "Student",
				filters: { status: "Active" },
			},
			{
				icon: "user-plus",
				accent: BB_ACCENTS.aqua,
				label: __("New Admissions"),
				count: k.new_admissions,
				meta: __("Submitted this month"),
				list: "Student Admission Form",
				filters: { docstatus: 1 },
			},
			{
				icon: "enquiry",
				accent: BB_ACCENTS.orange,
				label: __("Open Enquiries"),
				count: k.open_enquiries,
				meta: __("Enquiries not yet converted"),
				pill: k.open_enquiries
					? { tone: "warn", text: __("Needs follow-up") }
					: { tone: "good", text: __("All caught up") },
				list: "Student Enquiry Form",
				filters: { status: ["in", ["Open", "Follow-up"]] },
			},
			{
				requires: "finance_summary",
				icon: "wallet",
				accent: BB_ACCENTS.green,
				label: __("Collected This Month"),
				money: k.monthly_collection,
				title: this.money(k.monthly_collection),
				meta: __("Billed {0} this month", [this.money_short(k.billed_this_month)]),
				list: "Fee Invoice",
				filters: { docstatus: 1 },
			},
			{
				icon: "rupee",
				accent: BB_ACCENTS.red,
				label: __("Outstanding Fees"),
				money: pending,
				title: this.money(pending),
				meta: pending
					? __("Across {0} of {1} invoices", [k.unpaid_invoices, k.total_invoices])
					: __("Nothing pending"),
				pill: pending
					? { tone: "crit", text: __("Action needed") }
					: { tone: "good", text: __("All settled") },
				report: "Pending Balance Report",
			},
		];

		this.$ref("kpis")
			.addClass("bb-kpi-grid")
			.html(
				tiles
					.filter((t) => !t.requires || this.can(t.requires))
					.map((t, i) => {
						const attrs = t.report
							? `data-bb-report="${esc(t.report)}"`
							: `data-bb-list="${esc(t.list)}" data-bb-filters='${esc(
									JSON.stringify(t.filters || {})
							  )}'`;
						const isMoney = t.money !== undefined;
						const seed = isMoney ? flt(t.money) : flt(t.count);
						return `
				<div class="bb-kpi bb-a--${t.accent} bb-rise" style="--bb-i:${i}" ${attrs}
					role="button" tabindex="0" ${t.title ? `title="${esc(t.title)}"` : ""}>
					<span class="bb-kpi__glow" aria-hidden="true"></span>
					<div class="bb-kpi__top">
						<span class="bb-badge-grad">${this._ico(t.icon)}</span>
						<span class="bb-kpi__label">${t.label}</span>
					</div>
					<div class="bb-kpi__value" data-bb-count="${esc(seed)}"
						data-bb-fmt="${isMoney ? "money" : "int"}">${
							isMoney ? this.money_short(seed) : esc(seed)
						}</div>
					<div class="bb-kpi__meta">
						${
							t.pill
								? `<span class="bb-pill bb-pill--${t.pill.tone}">
										<span class="bb-dot bb-dot--${t.pill.tone}"></span>${t.pill.text}
								   </span>`
								: ""
						}
						<span class="bb-kpi__meta-text">${t.meta}</span>
					</div>
				</div>`;
					})
					.join("")
			);

		// Animate the figures in once the markup is on the page.
		this.$ref("kpis")
			.find("[data-bb-count]")
			.each((_, el) => {
				const $el = $(el);
				const money = $el.attr("data-bb-fmt") === "money";
				this._count_up($el, $el.attr("data-bb-count"), (v) =>
					money ? this.money_short(v) : String(Math.round(v))
				);
			});
	}

	/* ── charts ─────────────────────────────────────────────────────────── */

	_render_trend(rows) {
		this._trend_rows = rows; // kept so _bind_resize can re-draw at a new width
		const $el = this.$ref("chart-trend");
		if (!rows || !rows.length || !rows.some((r) => flt(r.amount) > 0)) {
			$el.html(this._empty("chart", __("No collections recorded yet")));
			return;
		}
		this.charts.forEach((c) => c && c.destroy && c.destroy());
		this.charts = [];
		$el.empty();

		const style = getComputedStyle(this.$body.find(".bb-dash")[0]);
		const series = style.getPropertyValue("--bb-series").trim() || "#2a78d6";

		this.charts.push(
			new frappe.Chart($el[0], {
				data: {
					labels: rows.map((r) => r.month),
					datasets: [{ name: __("Collection"), values: rows.map((r) => flt(r.amount)) }],
				},
				type: "bar",
				height: 260,
				colors: [series],
				barOptions: { spaceRatio: 0.45 },
				axisOptions: { xIsSeries: true, shortenYAxisNumbers: true, xAxisMode: "tick" },
				tooltipOptions: { formatTooltipY: (v) => this.money(v) },
			})
		);
	}

	/**
	 * Invoice status as labelled horizontal bars, not a donut.
	 * Paid/Unpaid would be a red-vs-green pair — indistinguishable under
	 * deuteranopia (validated ΔE 4.1), so every row carries a dot AND a text
	 * label AND its count; colour is redundant, never the only cue.
	 */
	_render_invoice_status(rows, k) {
		const $el = this.$ref("invoice-status");
		if (!rows || !rows.length) {
			$el.html(this._empty("receipt", __("No submitted invoices yet")));
			return;
		}

		const toneOf = { Paid: "good", "Partially Paid": "warn", Unpaid: "crit" };
		const max = Math.max(...rows.map((r) => flt(r.count)));

		$el.html(`
			<div class="bb-statlist">
				${rows
					.map((r) => {
						const tone = toneOf[r.status] || "series";
						const w = max ? (flt(r.count) / max) * 100 : 0;
						return `
					<div class="bb-statrow">
						<div class="bb-statrow__head">
							<span class="bb-dot bb-dot--${tone}"></span>
							<span class="bb-statrow__label">${esc(r.status)}</span>
							<span class="bb-statrow__count">${esc(r.count)}</span>
						</div>
						<div class="bb-track">
							<div class="bb-track__fill bb-track__fill--${tone}" style="width:${w}%"></div>
						</div>
						<div class="bb-statrow__foot">
							${__("Billed")} ${this.money(r.billed)}${
							flt(r.outstanding)
								? ` · ${__("Outstanding")} <strong>${this.money(r.outstanding)}</strong>`
								: ""
						}
						</div>
					</div>`;
					})
					.join("")}
			</div>
			<div class="bb-card__footnote">
				${__("Status is derived from grand total minus paid amount.")}
			</div>
		`);
	}

	/** Single-hue horizontal bars with direct value labels. */
	_render_bars(refName, rows, keyField, emptyIcon, emptyText, opts = {}) {
		const $el = this.$ref(refName);
		if (!rows || !rows.length) {
			$el.html(this._empty(emptyIcon, emptyText));
			return;
		}
		const shown = rows.slice(0, 8);
		const max = Math.max(...shown.map((r) => flt(r.count)));
		const total = rows.reduce((s, r) => s + flt(r.count), 0);

		$el.html(`
			<div class="bb-barlist">
				${shown
					.map((r) => {
						const label = r[keyField] || __("Unassigned");
						const w = max ? (flt(r.count) / max) * 100 : 0;
						const share = total ? ((flt(r.count) / total) * 100).toFixed(0) : 0;
						const extra =
							opts.showOpen && flt(r.open_count)
								? ` · ${flt(r.open_count)} ${__("open")}`
								: "";
						return `
					<div class="bb-bar" title="${esc(label)}: ${esc(r.count)} (${share}%)${esc(extra)}"
						${
							opts.list
								? `data-bb-list="${esc(opts.list)}" data-bb-filters='${esc(
										JSON.stringify({ [opts.filterField]: label })
								  )}' role="button" tabindex="0"`
								: ""
						}>
						<div class="bb-bar__label">${esc(label)}</div>
						<div class="bb-bar__track">
							<div class="bb-bar__fill" style="width:${Math.max(w, 2)}%"></div>
						</div>
						<div class="bb-bar__value">${esc(r.count)}</div>
					</div>`;
					})
					.join("")}
			</div>
			${
				rows.length > shown.length
					? `<div class="bb-card__footnote">${__("Showing top {0} of {1}", [
							shown.length,
							rows.length,
					  ])}</div>`
					: ""
			}
		`);
	}

	_render_standards(rows) {
		this._render_bars("standards", rows, "standard", "users", __("No active students yet"), {
			list: "Student",
			filterField: "standard",
		});
	}

	_render_sources(rows) {
		this._render_bars("sources", rows, "source", "enquiry", __("No enquiries yet"), {
			showOpen: true,
		});
	}

	/* ── list panels ────────────────────────────────────────────────────── */

	_row({ doctype, name, title, sub, end, endTone, avatar, tone }) {
		return `
			<div class="bb-row ${tone ? "bb-row--" + tone : ""}"
				data-bb-doctype="${esc(doctype)}" data-bb-doc="${esc(name)}"
				role="button" tabindex="0">
				${avatar ? `<span class="bb-avatar">${esc(avatar)}</span>` : ""}
				<div class="bb-row__body">
					<div class="bb-row__title">${esc(title)}</div>
					<div class="bb-row__sub">${sub}</div>
				</div>
				${end ? `<div class="bb-row__end ${endTone ? "bb-row__end--" + endTone : ""}">${end}</div>` : ""}
			</div>`;
	}

	_render_birthdays(rows) {
		const $el = this.$ref("birthdays");
		if (!rows.length) {
			$el.html(this._empty("cake", __("No birthdays today")));
			return;
		}
		$el.html(
			rows
				.map((s) => {
					const nm = s.student_name || s.name;
					const bits = [s.standard, s.current_batch].filter(Boolean).map(esc);
					return this._row({
						doctype: "Student",
						name: s.name,
						title: nm,
						sub: bits.join(" · ") || __("No standard assigned"),
						avatar: String(nm).charAt(0).toUpperCase(),
						end: `<span class="bb-badge bb-badge--info">${__("Today")}</span>`,
					});
				})
				.join("")
		);
	}

	_render_followups(rows) {
		const $el = this.$ref("followups");
		if (!rows.length) {
			$el.html(this._empty("check", __("No follow-ups due")));
			return;
		}
		$el.html(
			rows
				.map((e) => {
					const days = flt(e.overdue_days);
					const bits = [e.parent_mobile, e.standard].filter(Boolean).map(esc);
					return this._row({
						doctype: "Student Enquiry Form",
						name: e.name,
						title: e.applicant_name || e.name,
						sub: bits.join(" · ") || __("No contact number"),
						tone: days > 0 ? "warn" : "",
						end:
							days > 0
								? `<span class="bb-badge bb-badge--warn">${__("{0}d overdue", [days])}</span>`
								: `<span class="bb-badge">${__("Today")}</span>`,
					});
				})
				.join("")
		);
	}

	/** Recently paid invoices. Rows come from Fee Invoice, not Fees Payment
	 *  Entry — see the note at the top of bb_dashboard.py. */
	_render_payments(rows) {
		const $el = this.$ref("payments");
		if (!rows.length) {
			$el.html(this._empty("wallet", __("No collections recorded")));
			return;
		}
		$el.html(
			rows
				.map((p) => {
					const settled = flt(p.outstanding) <= 0;
					return this._row({
						doctype: "Fee Invoice",
						name: p.name,
						title: p.student_name || p.student || p.name,
						sub: `${esc(this.date(p.invoice_date))} · <span class="bb-chip${
							settled ? "" : " bb-chip--warn"
						}">${
							settled
								? __("Settled")
								: __("{0} due", [this.money_short(p.outstanding)])
						}</span>`,
						end: this.money(p.paid_amount),
						endTone: "good",
					});
				})
				.join("")
		);
	}

	_render_outstanding(rows) {
		const $el = this.$ref("outstanding");
		if (!rows.length) {
			$el.html(this._empty("check", __("Every invoice is settled")));
			return;
		}
		$el.html(
			rows
				.map((inv) => {
					const age = flt(inv.age_days);
					const partial = flt(inv.paid_amount) > 0;
					return this._row({
						doctype: "Fee Invoice",
						name: inv.name,
						title: inv.student_name || inv.student || inv.name,
						sub: `${esc(this.date(inv.invoice_date))} · ${
							age > 0 ? __("{0} days old", [age]) : __("Raised today")
						}${
							partial
								? ` · <span class="bb-chip bb-chip--warn">${__("Part paid")}</span>`
								: ""
						}`,
						tone: age > 30 ? "crit" : "",
						end: this.money(inv.outstanding),
						endTone: "crit",
					});
				})
				.join("")
		);
	}

	/* ── static sections ────────────────────────────────────────────────── */

	/**
	 * Quick Actions. Two shapes, distinguished by their label:
	 *   "New …" / "Create …"  → opens a blank form  (newDoc)
	 *   a plural noun         → opens the list, and carries a record count (list)
	 *
	 * Fees Payment Entry and Bulk Fee Invoice Tool are deliberately absent: the
	 * team does not use those screens. Payments are recorded on the Fee Invoice
	 * itself (fee_invoice.js rolls the fees_details rows into paid_amount).
	 * Don't re-add them without checking that first.
	 *
	 * `counts` arrives with the dashboard payload, so this runs twice — once
	 * bare from _build_shell, then again with the badges once data lands.
	 */
	_render_actions(counts) {
		const c = counts || {};
		const A = BB_ACCENTS;
		const actions = [
			{ label: __("New Enquiry"), icon: "enquiry", accent: A.orange, newDoc: "Student Enquiry Form" },
			{ label: __("New Admission"), icon: "user-plus", accent: A.aqua, newDoc: "Student Admission Form" },
			{ label: __("Create Invoice"), icon: "receipt", accent: A.violet, newDoc: "Fee Invoice" },
			{
				label: __("Schools"),
				icon: "school",
				accent: A.blue,
				list: "School",
				count: c.schools,
				title:
					c.schools_total !== undefined
						? __("{0} active of {1} schools", [c.schools, c.schools_total])
						: null,
			},
			{
				label: __("Batch Transitions"),
				icon: "transfer",
				accent: A.yellow,
				list: "Student Batch Transition",
				count: c.batch_transitions,
				title:
					c.batch_transitions !== undefined
						? __("{0} submitted transitions", [c.batch_transitions])
						: null,
			},
			{ label: __("SMS Settings"), icon: "settings", accent: A.magenta, form: "BB SMS Settings" },
		];

		this.$ref("actions").html(
			actions
				.map((a) => {
					let attr;
					if (a.newDoc) attr = `data-bb-new="${esc(a.newDoc)}"`;
					else if (a.list) attr = `data-bb-list="${esc(a.list)}"`;
					else attr = `data-bb-doctype="${esc(a.form)}" data-bb-doc="${esc(a.form)}"`;

					const badge =
						a.count === undefined || a.count === null
							? ""
							: `<span class="bb-action__count">${esc(a.count)}</span>`;

					return `<button class="bb-action bb-a--${a.accent}" ${attr}
						${a.title ? `title="${esc(a.title)}"` : ""}>
						<span class="bb-badge-grad">${this._ico(a.icon)}</span>
						<span class="bb-action__label">${a.label}</span>
						${badge}
					</button>`;
				})
				.join("")
		);
	}

	_render_reports() {
		const A = BB_ACCENTS;
		const reports = [
			{ name: __("Pending Balance"), desc: __("Outstanding fee balances"), icon: "rupee", accent: A.red, route: "Pending Balance Report" },
			{ name: __("Payment Report"), desc: __("Detailed payment entries"), icon: "wallet", accent: A.green, route: "Payment Wise Report" },
			{ name: __("Student Report"), desc: __("Student master data"), icon: "users", accent: A.blue, route: "Student Wise Report" },
			{ name: __("Birthday Report"), desc: __("Birthdays by month"), icon: "gift", accent: A.magenta, route: "Birthday Report" },
			{ name: __("Promotion Report"), desc: __("Batch transfers"), icon: "trophy", accent: A.yellow, route: "Promote and Demote Report" },
		];

		this.$ref("reports").html(
			reports
				.map(
					(r) => `
			<button class="bb-report bb-a--${r.accent}" data-bb-report="${esc(r.route)}">
				<span class="bb-badge-grad">${this._ico(r.icon)}</span>
				<span class="bb-report__text">
					<span class="bb-report__name">${r.name}</span>
					<span class="bb-report__desc">${r.desc}</span>
				</span>
				${this._ico("arrow-right", "bb-ico--end")}
			</button>`
				)
				.join("")
		);
	}

	_empty(iconName, text) {
		return `<div class="bb-empty">
			<span class="bb-empty__icon">${this._ico(iconName)}</span>
			<span class="bb-empty__text">${text}</span>
		</div>`;
	}
}
