/* Admission Trends dashboard: page controller.

   • One API call (`get_trends`) fills the page, and every filter change re-runs it.
   • Filters: admission date range, Standard (multi-select), Gender, Status.
   • Sections: headline tiles, enquiries vs admissions per month, a
     standard × month grid shaded by count, and standards ranked by admissions.
   • Grid cells, bars and tiles link to the Student list behind them.
   • No inline onclick. Clicks are delegated from [data-at-*] attributes. */

frappe.pages["admission-trends"].on_page_load = function (wrapper) {
	wrapper._at = new AdmissionTrends(wrapper);
};

frappe.pages["admission-trends"].on_page_show = function (wrapper) {
	if (wrapper._at && wrapper._at._loaded) wrapper._at.refresh();
};

const AT_API = "bb_tution_management.bb_academy.page.admission_trends.admission_trends";

/* The academic year runs April to March, so the default window is this
   academic year so far. */
function at_default_from() {
	const today = moment();
	const year = today.month() >= 3 ? today.year() : today.year() - 1;
	return `${year}-04-01`;
}

class AdmissionTrends {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Admission Trends"),
			single_column: true,
		});
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.page.add_inner_button(__("Student List"), () => frappe.set_route("List", "Student"));
		this.page.add_inner_button(__("Enquiry Conversion"), () =>
			frappe.set_route("enquiry-conversion")
		);

		// page.body also holds the filter bar, so render into our own container.
		this.$body = $('<div class="at-root"></div>').appendTo(this.page.body);
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
			default: at_default_from(),
			change: () => this.refresh(),
		});
		this.f_to = this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			change: () => this.refresh(),
		});
		this.f_standard = this.page.add_field({
			fieldname: "standards",
			label: __("Select Standards"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => {
				if (!this._standards.length) return frappe.db.get_link_options("Standard", txt);
				txt = (txt || "").toLowerCase();
				return this._standards
					.filter((s) => !txt || s.toLowerCase().includes(txt))
					.map((s) => ({ value: s, description: "" }));
			},
			change: () => this.refresh(),
		});
		this.f_gender = this.page.add_field({
			fieldname: "gender",
			label: __("Gender"),
			fieldtype: "Select",
			options: [
				{ value: "", label: __("Gender: Girls & Boys") },
				{ value: "Girls", label: __("Gender: Girls Only") },
				{ value: "Boys", label: __("Gender: Boys Only") },
			],
			default: "",
			change: () => this.refresh(),
		});
		this.f_status = this.page.add_field({
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				{ value: "All", label: __("Status: All Admitted") },
				{ value: "Active", label: __("Status: Still Active Only") },
			],
			default: "All",
			change: () => this.refresh(),
		});
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
			gender: this.f_gender.get_value() || "",
			status: this.f_status.get_value() || "All",
		};
	}

	/* ── data ───────────────────────────────────────────────────────── */

	refresh() {
		const args = this._filters();
		if (args.from_date && args.to_date && args.from_date > args.to_date) {
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
		this.$body.addClass("at-loading");
		let ok = false;
		frappe.call({
			method: `${AT_API}.get_trends`,
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
				this.$body.removeClass("at-loading");
				if (!ok) {
					this._last_sig = null;
					this._show_state(__("Could not load the figures. Please press Refresh."));
					return;
				}
				// A change that landed while this call ran may have been dropped.
				if (JSON.stringify(this._filters()) !== sig) this.refresh();
			},
		});
	}

	_show_state(message) {
		this._data = null;
		this.$body
			.removeClass("at-loading")
			.html(`<div class="at-canvas"><div class="at-empty">${esc_at(message)}</div></div>`);
	}

	/* ── rendering ─────────────────────────────────────────────────── */

	_render(d) {
		this._data = d;
		const a = this._args;
		const filters_text = [
			this._range_text(a.from_date, a.to_date),
			a.standards.length ? a.standards.map(esc_at).join(", ") : "",
			a.gender ? __("{0} only", [__(a.gender)]) : "",
			a.status === "Active" ? __("Still active only") : "",
		]
			.filter(Boolean)
			.join(" · ");

		const body = d.total
			? `${this._tiles(d)}
			   ${this._month_chart(d)}
			   ${this._grid(d)}
			   ${this._standard_bars(d)}`
			: `<div class="at-empty">${__("No admissions match these filters.")}</div>`;

		this.$body.html(`
			<div class="at-canvas">
				<header class="at-head">
					<h1 class="at-title">${__("Admission Trends")}</h1>
					<div class="at-sub">${__("By admission date")}: ${filters_text}</div>
				</header>
				${body}
			</div>
		`);
	}

	_tiles(d) {
		const peak_i = this._max_index(d.admissions);
		const top_std = d.standards.reduce((best, s) => (s.total > best.total ? s : best), d.standards[0]);
		const girls = d.standards.reduce((n, s) => n + s.Girls, 0);
		const boys = d.standards.reduce((n, s) => n + s.Boys, 0);
		const months_with_data = d.admissions.filter((n) => n).length || 1;

		const tile = (label, value, foot, drill = "") => `
			<div class="at-tile" ${drill}>
				<div class="at-tile__label">${label}</div>
				<div class="at-tile__value">${value}</div>
				<div class="at-tile__foot">${foot}</div>
			</div>`;

		return `
			<div class="at-tiles">
				${tile(
					__("Total Admissions"),
					d.total,
					__("{0} enquiries in the same period", [d.total_enquiries]),
					this._drill_attrs({})
				)}
				${tile(
					__("Peak Month"),
					esc_at(this._month_label(d.months[peak_i], true)),
					__("{0} admissions", [d.admissions[peak_i]]),
					this._drill_attrs({ month: peak_i })
				)}
				${tile(
					__("Top Standard"),
					esc_at(top_std.standard || __("Not set")),
					__("{0} admissions · {1}% of total", [
						top_std.total,
						Math.round((top_std.total * 100) / d.total),
					]),
					this._drill_attrs({ std: top_std.standard })
				)}
				${tile(
					__("Girls / Boys"),
					`${girls} / ${boys}`,
					__("Average {0} admissions per active month", [
						(d.total / months_with_data).toFixed(1),
					])
				)}
			</div>`;
	}

	/* Enquiries and admissions side by side for each month, on one count axis. */
	_month_chart(d) {
		const max = Math.max(1, ...d.admissions, ...d.enquiries);
		const peak_i = this._max_index(d.admissions);
		const bar = (kind, value, i, label) => {
			const h = (value / max) * 100;
			const drill = kind === "adm" && value ? this._drill_attrs({ month: i }) : "";
			return `
				<div class="at-mbar at-mbar--${kind}" ${drill}
					title="${esc_at(this._month_label(d.months[i], true))} · ${label}: ${value}">
					<span class="at-mbar__val">${value || ""}</span>
					<span class="at-mbar__fill" style="height:${h}%"></span>
				</div>`;
		};

		const groups = d.months
			.map(
				(m, i) => `
				<div class="at-mgroup${i === peak_i ? " at-mgroup--peak" : ""}">
					<div class="at-mgroup__bars">
						${bar("enq", d.enquiries[i], i, __("Enquiries"))}
						${bar("adm", d.admissions[i], i, __("Admissions"))}
					</div>
					<div class="at-mgroup__label">${esc_at(this._month_label(m))}${
						i === peak_i ? `<span class="at-peak">${__("Peak")}</span>` : ""
					}</div>
				</div>`
			)
			.join("");

		return `
			<section class="at-card">
				<div class="at-card__head">
					<h2 class="at-card__title">${__("Enquiries vs Admissions by Month")}</h2>
					<div class="at-legend">
						<span><i class="at-swatch at-swatch--enq"></i>${__("Enquiries")}</span>
						<span><i class="at-swatch at-swatch--adm"></i>${__("Admissions")}</span>
					</div>
				</div>
				<div class="at-mchart-scroll">
					<div class="at-mchart" style="--at-months:${d.months.length}">${groups}</div>
				</div>
			</section>`;
	}

	/* Standard × month grid. Shade follows the count, one hue light to dark. */
	_grid(d) {
		const max = Math.max(1, ...d.standards.flatMap((s) => s.months));
		const peak_i = this._max_index(d.admissions);
		const cell = (value, std, i) => {
			if (!value) return `<td class="at-cell at-cell--zero">·</td>`;
			const t = value / max;
			const strong = t > 0.55 ? " at-cell--strong" : "";
			return `<td class="at-cell${strong}" style="--at-t:${Math.round(12 + t * 88)}%"
				${this._drill_attrs({ std, month: i })}
				title="${esc_at(std)} · ${esc_at(this._month_label(d.months[i], true))}: ${value}">${value}</td>`;
		};

		const head = d.months
			.map((m, i) => `<th class="${i === peak_i ? "at-th--peak" : ""}">${esc_at(this._month_label(m))}</th>`)
			.join("");
		const rows = d.standards
			.map(
				(s) => `
				<tr>
					<th class="at-grid__std">${esc_at(s.standard || __("Not set"))}</th>
					${s.months.map((v, i) => cell(v, s.standard, i)).join("")}
					<td class="at-grid__total" ${this._drill_attrs({ std: s.standard })}>${s.total}</td>
				</tr>`
			)
			.join("");
		const foot = d.admissions
			.map((v, i) => `<td class="at-grid__total" ${v ? this._drill_attrs({ month: i }) : ""}>${v}</td>`)
			.join("");

		return `
			<section class="at-card">
				<div class="at-card__head">
					<h2 class="at-card__title">${__("Admissions by Standard and Month")}</h2>
					<div class="at-card__hint">${__("Darker cells had more admissions. Click a number to see the students.")}</div>
				</div>
				<div class="at-grid-scroll">
					<table class="at-grid">
						<thead><tr><th>${__("Standard")}</th>${head}<th>${__("Total")}</th></tr></thead>
						<tbody>${rows}</tbody>
						<tfoot><tr><th>${__("Total")}</th>${foot}<td class="at-grid__total at-grid__grand" ${this._drill_attrs({})}>${d.total}</td></tr></tfoot>
					</table>
				</div>
			</section>`;
	}

	/* Standards ranked by admissions in the range. */
	_standard_bars(d) {
		const ranked = [...d.standards].filter((s) => s.total).sort((x, y) => y.total - x.total);
		const max = Math.max(1, ...ranked.map((s) => s.total));
		const rows = ranked
			.map(
				(s) => `
				<div class="at-hbar" ${this._drill_attrs({ std: s.standard })}
					title="${esc_at(s.standard)}: ${s.total} (${__("Girls")} ${s.Girls}, ${__("Boys")} ${s.Boys})">
					<div class="at-hbar__name">${esc_at(s.standard || __("Not set"))}</div>
					<div class="at-hbar__track"><span class="at-hbar__fill" style="width:${(s.total / max) * 100}%"></span></div>
					<div class="at-hbar__val">${s.total}</div>
					<div class="at-hbar__split">${__("Girls")} ${s.Girls} · ${__("Boys")} ${s.Boys}</div>
				</div>`
			)
			.join("");

		return `
			<section class="at-card">
				<div class="at-card__head">
					<h2 class="at-card__title">${__("Standards Ranked by Admissions")}</h2>
				</div>
				<div class="at-hbars">${rows}</div>
			</section>`;
	}

	/* ── helpers ──────────────────────────────────────────────────── */

	_max_index(arr) {
		let best = 0;
		arr.forEach((v, i) => {
			if (v > arr[best]) best = i;
		});
		return best;
	}

	_month_label(key, long = false) {
		if (!key) return "";
		return moment(`${key}-01`).format(long ? "MMMM YYYY" : "MMM YY");
	}

	_range_text(from, to) {
		const fmt = (v) => moment(v).format("DD MMM YYYY");
		if (!from && !to) return __("All dates");
		if (!to) return __("From {0}", [fmt(from)]);
		if (!from) return __("Up to {0}", [fmt(to)]);
		return `${fmt(from)} ${__("to")} ${fmt(to)}`;
	}

	/* data-at-std / data-at-month on a clickable number. std === undefined
	   means every standard; month undefined means the whole range. */
	_drill_attrs({ std, month }) {
		const parts = ['data-at-drill="1"', 'role="link"', 'tabindex="0"'];
		if (std !== undefined) parts.push(`data-at-std="${esc_at(std)}"`);
		if (month !== undefined) parts.push(`data-at-month="${month}"`);
		return parts.join(" ");
	}

	/* ── drill-down ───────────────────────────────────────────────── */

	_bind_events() {
		const open = (el) => {
			const d = this._data;
			const a = this._args;
			if (!d || !a) return;
			const opts = {};

			const month = el.dataset.atMonth;
			if (month !== undefined) {
				const start = moment(`${d.months[month]}-01`);
				let from = start.format("YYYY-MM-DD");
				let to = start.clone().endOf("month").format("YYYY-MM-DD");
				// Keep to the chosen range when it starts or ends mid-month.
				if (a.from_date && a.from_date > from) from = a.from_date;
				if (a.to_date && a.to_date < to) to = a.to_date;
				opts.admission_date = ["between", [from, to]];
			} else if (a.from_date && a.to_date) {
				opts.admission_date = ["between", [a.from_date, a.to_date]];
			} else if (a.from_date) {
				opts.admission_date = [">=", a.from_date];
			} else if (a.to_date) {
				opts.admission_date = ["<=", a.to_date];
			}

			if (el.dataset.atStd !== undefined) opts.standard = el.dataset.atStd;
			else if (a.standards.length) opts.standard = ["in", a.standards];
			if (a.gender) opts.gender = a.gender;
			if (a.status === "Active") opts.status = "Active";

			frappe.route_options = opts;
			frappe.set_route("List", "Student");
		};

		this.$body.on("click", "[data-at-drill]", function () {
			open(this);
		});
		this.$body.on("keydown", "[data-at-drill]", function (e) {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				open(this);
			}
		});
	}
}

const esc_at = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
