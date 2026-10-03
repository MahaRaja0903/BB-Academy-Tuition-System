/* Student Enquiry & Conversion dashboard: page controller.

   • One API call (`get_conversion`) fills the page, and every filter change re-runs it.
   • Filters: enquiry date range and Standard (multi-select) narrow the data.
   • Two split controls shape the columns:
       Standard split: 6th–9th / 10th–12th, each standard, or all together.
       Gender split:   Girls and Boys apart, Girls only, Boys only, or together.
   • Each number is a link to the list behind it: Joined opens Students (by
     Admission Date), the rest open the Student Enquiry Form list.
   • No inline onclick. Clicks are delegated from [data-ec-*] attributes. */

frappe.pages["enquiry-conversion"].on_page_load = function (wrapper) {
	wrapper._ec = new EnquiryConversion(wrapper);
};

frappe.pages["enquiry-conversion"].on_page_show = function (wrapper) {
	if (wrapper._ec && wrapper._ec._loaded) wrapper._ec.refresh();
};

const EC_API = "bb_tution_management.bb_academy.page.enquiry_conversion.enquiry_conversion";

// Default window for the client's review: May to August 2026.
const EC_DEFAULT_FROM = "2026-05-01";
const EC_DEFAULT_TO = "2026-08-31";

class EnquiryConversion {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Enquiry Conversion"),
			single_column: true,
		});
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.page.add_inner_button(__("Enquiry List"), () =>
			frappe.set_route("List", "Student Enquiry Form")
		);

		// page.body also holds the filter bar (page.page_form is prepended into
		// it), so the dashboard renders into its own container; re-rendering
		// page.body itself would wipe the filters.
		this.$body = $('<div class="ec-root"></div>').appendTo(this.page.body);
		this._standards = [];
		this._make_filters();
		this._bind_events();
		this._load_standards().then(() => this.refresh());
	}

	/* ── filters ─────────────────────────────────────────────────────── */

	_make_filters() {
		this.f_from = this.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: EC_DEFAULT_FROM,
			change: () => this.refresh(),
		});
		this.f_to = this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: EC_DEFAULT_TO,
			change: () => this.refresh(),
		});
		this.f_standard = this.page.add_field({
			fieldname: "standards",
			label: __("Select Standards"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => {
				// Fall back to a live lookup if the ordered list hasn't loaded yet.
				if (!this._standards.length) return frappe.db.get_link_options("Standard", txt);
				txt = (txt || "").toLowerCase();
				return this._standards
					.filter((s) => !txt || s.toLowerCase().includes(txt))
					.map((s) => ({ value: s, description: "" }));
			},
			change: () => this._on_standards_change(),
		});
		this.f_std_split = this.page.add_field({
			fieldname: "std_split",
			label: __("Split Standard"),
			fieldtype: "Select",
			options: [
				{ value: "Band", label: __("Standard: 6th–9th / 10th–12th") },
				{ value: "Standard", label: __("Standard: Each Standard") },
				{ value: "None", label: __("Standard: All Together") },
			],
			default: "Band",
			change: () => {
				// A split changed by hand is the user's choice from here on.
				if (!this._setting_split) this._auto_split = false;
				this.refresh();
			},
		});
		this.f_gender_split = this.page.add_field({
			fieldname: "gender_split",
			label: __("Split Gender"),
			fieldtype: "Select",
			options: [
				{ value: "Split", label: __("Gender: Girls & Boys Separately") },
				{ value: "Girls", label: __("Gender: Girls Only") },
				{ value: "Boys", label: __("Gender: Boys Only") },
				{ value: "Combined", label: __("Gender: Girls & Boys Together") },
			],
			default: "Split",
			change: () => this.refresh(),
		});
	}

	/* Picking standards (say 7TH and 8TH) should show each one on its own, not
	   merge them into the 6th–9th band, so the split moves to "Each Standard".
	   Clearing the pick puts the band view back, but only if we were the ones
	   who changed it. A split chosen by hand is left alone either way. */
	_on_standards_change() {
		const picked = (this.f_standard.get_value() || []).length;
		const split = this.f_std_split.get_value();

		if (picked && split === "Band") {
			this._auto_split = true;
			this._set_split("Standard"); // its change handler refreshes
			return;
		}
		if (!picked && split === "Standard" && this._auto_split) {
			this._auto_split = false;
			this._set_split("Band");
			return;
		}
		this.refresh();
	}

	_set_split(value) {
		this._setting_split = true;
		this.f_std_split.set_value(value).then(() => (this._setting_split = false));
	}

	_load_standards() {
		return frappe.db
			.get_list("Standard", {
				fields: ["name"],
				filters: { is_active: 1 },
				order_by: "academic_order asc, name asc",
				limit: 0,
			})
			.then((rows) => {
				this._standards = rows.map((r) => r.name);
			});
	}

	_filters() {
		return {
			from_date: this.f_from.get_value() || null,
			to_date: this.f_to.get_value() || null,
			standards: this.f_standard.get_value() || [],
			std_split: this.f_std_split.get_value() || "Band",
			gender_split: this.f_gender_split.get_value() || "Split",
		};
	}

	/* ── data ───────────────────────────────────────────────────────── */

	refresh() {
		const args = this._filters();
		if (args.from_date && args.to_date && args.from_date > args.to_date) {
			// Never leave the last result up here: it no longer matches the
			// filters on screen, and every other filter change would appear to
			// do nothing until the dates are fixed.
			this._last_sig = null;
			this._seq = (this._seq || 0) + 1; // drop any reply still on its way
			this._show_state(__("From Date is after To Date. Please correct the dates."));
			return;
		}

		// Filter controls fire change events while the page is being built; skip
		// calls that repeat the request already on its way.
		const sig = JSON.stringify(args);
		if (sig === this._last_sig && this._inflight) return;
		this._last_sig = sig;
		this._inflight = true;

		const seq = (this._seq = (this._seq || 0) + 1);
		this.$body.addClass("ec-loading");
		let ok = false;
		frappe.call({
			method: `${EC_API}.get_conversion`,
			args,
			callback: (r) => {
				if (seq !== this._seq) return;
				ok = true;
				this._args = args;
				this._render(r.message || {});
				this._loaded = true;
			},
			always: () => {
				if (seq !== this._seq) return;
				this._inflight = false;
				this.$body.removeClass("ec-loading");
				if (!ok) {
					this._last_sig = null;
					this._show_state(__("Could not load the figures. Please press Refresh."));
					return;
				}
				// Frappe drops a control's change event if it lands while that
				// control is still handling the previous one, so quick filter
				// changes can go unseen. Re-check what the filters say now.
				if (JSON.stringify(this._filters()) !== sig) this.refresh();
			},
		});
	}

	/* Replaces the board with a message, so figures for other filters are never
	   left on screen (or clickable) looking like the current ones. */
	_show_state(message) {
		this._segs = [];
		this.$body.removeClass("ec-loading").html(
			`<div class="ec-canvas"><div class="ec-empty">${esc_ec(message)}</div></div>`
		);
	}

	/* ── rendering ─────────────────────────────────────────────────── */

	_render(data) {
		const segs = data.segments || [];
		const total = data.total || { enquired: 0, joined: 0, not_joined: 0, conversion: 0 };
		const a = this._args;
		this._segs = segs;

		const range_text = this._range_text(a.from_date, a.to_date);
		const std_text = a.standards.length ? ` · ${a.standards.map(esc_ec).join(", ")}` : "";
		const gender_text = { Girls: ` · ${__("Girls only")}`, Boys: ` · ${__("Boys only")}` }[a.gender_split] || "";

		const note = data.unassigned
			? `<p class="ec-note">${__(
					"{0} enquiries or students in this range have no gender or no usable standard for this split, so they are not counted.",
					[data.unassigned]
			  )}</p>`
			: "";

		const columns = segs.length
			? segs.map((s, i) => this._column(s, i)).join("")
			: `<div class="ec-empty">${__("No enquiries match these filters.")}</div>`;

		this.$body.html(`
			<div class="ec-canvas">
				<header class="ec-head">
					<h1 class="ec-title">${__("Student Enquiry &amp; Conversion Performance Dashboard")}</h1>
					<div class="ec-sub">${__("Data")}: ${range_text}${std_text}${gender_text}</div>
				</header>

				<div class="ec-board">
					<div class="ec-labels" aria-hidden="true">
						<div class="ec-labels__spacer"></div>
						<div class="ec-label ec-row-h">
							<i class="fa fa-search ec-label__ico ec-label__ico--enq"></i>
							<span>${__("Enquired Count")}</span>
						</div>
						<div class="ec-label ec-row-h">
							<i class="fa fa-users ec-label__ico ec-label__ico--join"></i>
							<span>${__("Joined Count")}</span>
						</div>
						<div class="ec-label ec-row-h">
							<i class="fa fa-user-times ec-label__ico ec-label__ico--not"></i>
							<span>${__("Not Joined Count")}</span>
						</div>
						<div class="ec-label ec-label--rate">${__("Conversion %")}</div>
					</div>

					<div class="ec-segments-scroll">
						<div class="ec-segments">${columns}</div>
					</div>

					<aside class="ec-side">
						${this._summary(total)}
						<div class="ec-flow" aria-hidden="true"></div>
						<div class="ec-rate-card">
							<div class="ec-rate-card__label">${__("Overall Conversion Rate")}</div>
							<div class="ec-rate-card__value">${this._pct(total.conversion)}</div>
						</div>
					</aside>
				</div>
				${note}
			</div>
		`);
	}

	_column(s, i) {
		const gender_label = { Girls: __("Girls"), Boys: __("Boys") }[s.gender] || __("Girls &amp; Boys");
		const avatar = { Girls: EC_GIRL, Boys: EC_BOY }[s.gender] || EC_PAIR;
		const drill = (kind) =>
			`data-ec-drill="${kind}" data-ec-seg="${i}" role="link" tabindex="0"`;

		return `
			<div class="ec-col">
				<div class="ec-col__head">
					<div class="ec-avatar${s.gender ? "" : " ec-avatar--pair"}">${avatar}</div>
					<div class="ec-col__title">
						${this._std_label(s.label)}<br>${gender_label}
					</div>
				</div>
				<div class="ec-stack">
					<div class="ec-box ec-box--enq ec-row-h" ${drill("all")}>
						<span class="ec-box__tag">${__("Enquired")}</span>${s.enquired}
					</div>
					<div class="ec-box ec-box--join ec-row-h" ${drill("joined")}>
						<span class="ec-box__tag">${__("Joined")}</span>${s.joined}
					</div>
					<div class="ec-box ec-box--not ec-row-h" ${drill("not_joined")}>
						<span class="ec-box__tag">${__("Not Joined")}</span>${s.not_joined}
					</div>
				</div>
				<span class="ec-bracket" aria-hidden="true"></span>
				<div class="ec-col__rate">
					<span class="ec-box__tag">${__("Conversion")}</span>${this._pct(s.conversion)}
				</div>
			</div>`;
	}

	_summary(t) {
		const max = Math.max(t.enquired, 1);
		const bar = (kind, value, label) => `
			<div class="ec-bar" ${
				value ? `data-ec-drill="${kind}" data-ec-seg="total" role="link" tabindex="0"` : ""
			}>
				<div class="ec-bar__value">${value}</div>
				<div class="ec-bar__track">
					<div class="ec-bar__fill ec-bar__fill--${kind}" style="height:${
						(value / max) * 100
					}%"></div>
				</div>
				<div class="ec-bar__label">${label}</div>
			</div>`;
		return `
			<div class="ec-summary">
				<div class="ec-summary__title">${__("Total Summary")}</div>
				<div class="ec-bars">
					${bar("all", t.enquired, __("Total Enquired"))}
					${bar("joined", t.joined, __("Total Joined"))}
					${bar("not_joined", t.not_joined, __("Total Not Joined"))}
				</div>
			</div>`;
	}

	/* "6th to 9th STD" → superscript ordinals, like the printed version. */
	_std_label(label) {
		return esc_ec(label).replace(/(\d+)(st|nd|rd|th)\b/gi, "$1<sup>$2</sup>");
	}

	_pct(v) {
		return `${(Number(v) || 0).toFixed(1)}%`;
	}

	/* Heading text for the chosen dates. Whole months read as months
	   ("May 2026 to August 2026"); anything else shows the exact dates. */
	_range_text(from, to) {
		const f = from && moment(from);
		const t = to && moment(to);
		if (!f && !t) return __("All dates");
		if (!t) return __("From {0}", [f.format("DD MMM YYYY")]);
		if (!f) return __("Up to {0}", [t.format("DD MMM YYYY")]);

		const whole_months =
			f.date() === 1 && t.date() === t.clone().endOf("month").date();
		if (whole_months) {
			return f.isSame(t, "month")
				? f.format("MMMM YYYY")
				: `${f.format("MMMM YYYY")} ${__("to")} ${t.format("MMMM YYYY")}`;
		}
		return `${f.format("DD MMM YYYY")} ${__("to")} ${t.format("DD MMM YYYY")}`;
	}

	/* ── drill-down ───────────────────────────────────────────────── */

	_bind_events() {
		const open = (el) => {
			const kind = el.dataset.ecDrill;
			const idx = el.dataset.ecSeg;
			const a = this._args || this._filters();
			const opts = {};

			// Joined is counted from Students by Admission Date, not from enquiries.
			const joined = kind === "joined";
			const date_field = joined ? "admission_date" : "enquiry_date";
			if (a.from_date && a.to_date) opts[date_field] = ["between", [a.from_date, a.to_date]];
			if (kind === "not_joined") opts.status = ["!=", "Converted"];

			if (idx === "total") {
				if (a.standards.length) opts.standard = ["in", a.standards];
				if (["Girls", "Boys"].includes(a.gender_split)) opts.gender = a.gender_split;
			} else {
				const s = (this._segs || [])[idx];
				if (!s) return;
				if (!s.standards.length) return; // nothing behind a zero column
				if (s.gender) opts.gender = s.gender;
				opts.standard = ["in", s.standards];
			}

			frappe.route_options = opts;
			frappe.set_route("List", joined ? "Student" : "Student Enquiry Form");
		};

		this.$body.on("click", "[data-ec-drill]", function () {
			open(this);
		});
		this.$body.on("keydown", "[data-ec-drill]", function (e) {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				open(this);
			}
		});
	}
}

const esc_ec = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

/* Simple flat avatars matching the brief: female with long hair and a red top,
   male with short hair and a blue shirt. */
const EC_GIRL = `<svg viewBox="0 0 64 64" aria-hidden="true">
	<path d="M14 34c-2-14 5-24 18-24s20 10 18 24c-1 6 1 10 3 13H11c2-3 4-7 3-13Z" fill="#3b2a28"/>
	<path d="M12 64c0-11 8-17 20-17s20 6 20 17Z" fill="#e0575b"/>
	<path d="M26 47h12l-6 8Z" fill="#fff"/>
	<rect x="28" y="38" width="8" height="9" rx="3" fill="#f2c4a5"/>
	<ellipse cx="32" cy="29" rx="11" ry="13" fill="#f8d4b8"/>
	<path d="M21 26c2-8 8-11 13-11 5 0 9 4 9 10-6-1-12-4-15-8-2 4-4 7-7 9Z" fill="#3b2a28"/>
	<circle cx="27.5" cy="30" r="1.3" fill="#2b2b2b"/><circle cx="36.5" cy="30" r="1.3" fill="#2b2b2b"/>
	<path d="M28.5 35.5c2 1.8 5 1.8 7 0" stroke="#c0605a" stroke-width="1.4" fill="none" stroke-linecap="round"/>
</svg>`;

const EC_BOY = `<svg viewBox="0 0 64 64" aria-hidden="true">
	<path d="M12 64c0-11 8-17 20-17s20 6 20 17Z" fill="#5b9bd5"/>
	<path d="M26 47h12l-6 7Z" fill="#fff"/>
	<rect x="28" y="38" width="8" height="9" rx="3" fill="#f2c4a5"/>
	<ellipse cx="32" cy="29" rx="11" ry="12.5" fill="#f8d4b8"/>
	<path d="M20.5 28c-1-10 5-15 12-15 8 0 12 5 11 14-3-3-5-6-6-9-4 3-10 5-17 10Z" fill="#2e2724"/>
	<circle cx="27.5" cy="30" r="1.3" fill="#2b2b2b"/><circle cx="36.5" cy="30" r="1.3" fill="#2b2b2b"/>
	<path d="M28.5 35.5c2 1.8 5 1.8 7 0" stroke="#c0605a" stroke-width="1.4" fill="none" stroke-linecap="round"/>
</svg>`;

/* Girls and Boys counted together: the two avatars side by side. */
const EC_PAIR = `<span class="ec-pair">${EC_GIRL}${EC_BOY}</span>`;
