/* Fee Payment Summary dashboard: page controller.

   • Filters: Year, Month, Students (active only / all).
   • One API call (`get_summary`) fills the page, and every filter change re-runs it.
   • Layout: an overall strip, then one row per standard band × gender with
     three cards — Total, Paid, Pending.
   • Clicking a Paid or Pending card lists the students behind it.
   • No inline onclick. Clicks are delegated from [data-fps-*] attributes. */

frappe.pages["fee-payment-summary"].on_page_load = function (wrapper) {
	wrapper._fps = new FeePaymentSummary(wrapper);
};

frappe.pages["fee-payment-summary"].on_page_show = function (wrapper) {
	if (wrapper._fps && wrapper._fps._loaded) wrapper._fps.refresh();
};

const FPS_API = "bb_tution_management.bb_academy.page.fee_payment_summary.fee_payment_summary";

const FPS_MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
];

class FeePaymentSummary {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Fee Payment Summary"),
			single_column: true,
		});
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.page.add_inner_button(__("Fee Invoices"), () => frappe.set_route("List", "Fee Invoice"));
		this.page.add_inner_button(__("Print"), () => window.print());

		this.$body = $('<div class="fps-root"></div>').appendTo(this.page.body);
		this._bind_events();
		frappe
			.call({ method: `${FPS_API}.get_years` })
			.then((r) => this._make_filters(r.message || []))
			.then(() => this.refresh());
	}

	/* ── filters ─────────────────────────────────────────────────────── */

	_make_filters(years) {
		const now = new Date();
		const this_year = now.getFullYear();
		if (!years.includes(this_year)) years = [this_year, ...years];

		this.f_year = this.page.add_field({
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			options: years.map((y) => ({ value: String(y), label: String(y) })),
			default: String(this_year),
			change: () => this.refresh(),
		});
		this.f_month = this.page.add_field({
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: FPS_MONTHS.map((m, i) => ({ value: String(i + 1), label: __(m) })),
			default: String(now.getMonth() + 1),
			change: () => this.refresh(),
		});
		this.f_status = this.page.add_field({
			fieldname: "student_status",
			label: __("Students"),
			fieldtype: "Select",
			options: [
				{ value: "Active", label: __("Students: Active Only") },
				{ value: "All", label: __("Students: All (incl. Discontinued)") },
			],
			default: "Active",
			change: () => this.refresh(),
		});
	}

	_filters() {
		return {
			year: this.f_year.get_value(),
			month: this.f_month.get_value(),
			student_status: this.f_status.get_value() || "Active",
		};
	}

	/* ── data ───────────────────────────────────────────────────────── */

	refresh() {
		if (!this.f_year) return;
		const args = this._filters();
		const seq = (this._seq = (this._seq || 0) + 1);
		this.$body.addClass("fps-loading");
		frappe.call({
			method: `${FPS_API}.get_summary`,
			args,
			callback: (r) => {
				if (seq !== this._seq) return;
				this._render(r.message || {});
				this._loaded = true;
			},
			error: () => {
				if (seq !== this._seq) return;
				this.$body.html(
					`<div class="fps-empty">${__("Could not load the figures. Please press Refresh.")}</div>`
				);
			},
			always: () => {
				if (seq === this._seq) this.$body.removeClass("fps-loading");
			},
		});
	}

	/* ── rendering ─────────────────────────────────────────────────── */

	_render(d) {
		this._data = d;
		const period = `${__(d.month_name)} ${d.year}`;
		const t = d.totals || {};

		const body = t.total_count
			? `${this._overall(t)}
			   <div class="fps-grid">${d.groups.map((g, i) => this._row(g, i)).join("")}</div>`
			: `<div class="fps-empty">${__("No fee rows fall in {0} for these students.", [esc_fps(period)])}</div>`;

		const note = d.skipped
			? `<div class="fps-note">${__(
					"{0} students without a Boys/Girls gender or a 6th–12th standard are not shown.",
					[d.skipped]
			  )}</div>`
			: "";

		this.$body.html(`
			<div class="fps-canvas">
				<header class="fps-head">
					<h1 class="fps-title">${__("Student Fee Payment Summary")}</h1>
					<div class="fps-sub">${__("Detailed report by grade and gender")} · ${esc_fps(period)}
						${d.student_status === "All" ? " · " + __("all students") : " · " + __("active students")}</div>
				</header>
				${body}
				${note}
				<footer class="fps-foot">
					<span>${__("Report generated on {0}", [frappe.datetime.str_to_user(frappe.datetime.now_datetime())])}</span>
					<span>${__("BB Academy Administration")}</span>
				</footer>
			</div>
		`);
	}

	_overall(t) {
		const pct = t.total_amount ? Math.round((t.paid_amount * 100) / t.total_amount) : 0;
		const stat = (label, value, sub) => `
			<div class="fps-stat">
				<div class="fps-stat__label">${label}</div>
				<div class="fps-stat__value">${value}</div>
				<div class="fps-stat__sub">${sub}</div>
			</div>`;
		return `
			<div class="fps-overall">
				${stat(__("Total Due"), fmt_inr(t.total_amount), __("{0} students", [t.total_count]))}
				${stat(__("Collected"), fmt_inr(t.paid_amount), __("{0} paid", [t.paid_count]))}
				${stat(__("Pending"), fmt_inr(t.pending_amount), __("{0} not paid", [t.not_paid_count]))}
				<div class="fps-stat">
					<div class="fps-stat__label">${__("Collection")}</div>
					<div class="fps-stat__value">${pct}%</div>
					<div class="fps-meter"><span style="width:${pct}%"></span></div>
				</div>
			</div>`;
	}

	_row(g, i) {
		const tone = `fps-tone-${g.band}-${g.gender.toLowerCase()}`;
		const icon = g.gender === "Girls" ? "fa-female" : "fa-male";
		const title = `<div class="fps-card__title"><i class="fa ${icon}"></i>
			${esc_fps(__(g.label))} – ${esc_fps(__(g.gender))}</div>`;
		const line = (glyph, label, value, big) => `
			<div class="fps-line">
				<span class="fps-glyph">${glyph}</span>
				<span class="fps-line__label">${label}</span>
				<span class="fps-line__value ${big ? "is-big" : ""}">${value}</span>
			</div>`;

		return `
			<div class="fps-card ${tone}">
				${title}
				${line("₹", __("Total Amount:"), fmt_inr(g.total_amount), true)}
				${line("#", __("Total Count:"), g.total_count, true)}
			</div>
			<div class="fps-card ${tone} is-clickable" data-fps-list="paid" data-fps-group="${i}"
				title="${__("Show paid students")}">
				${title}
				${line('<i class="fa fa-check"></i>', __("Paid Amount:"), fmt_inr(g.paid_amount))}
				${line('<i class="fa fa-check"></i>', __("Paid Count:"), g.paid_count)}
				${g.paid_count ? `<div class="fps-view">${__("View paid students")} ›</div>` : ""}
			</div>
			<div class="fps-card ${tone} is-clickable" data-fps-list="not_paid" data-fps-group="${i}"
				title="${__("Show students yet to pay")}">
				${title}
				${line("!", __("Pending Amount:"), fmt_inr(g.pending_amount))}
				${line("!", __("Not Paid Count:"), g.not_paid_count)}
				${g.not_paid_count ? `<div class="fps-view">${__("View not paid students")} ›</div>` : ""}
			</div>`;
	}

	/* ── drill-down ─────────────────────────────────────────────────── */

	_bind_events() {
		this.$body.on("click", "[data-fps-list]", (e) => {
			const $el = $(e.currentTarget);
			const g = this._data && this._data.groups[+$el.attr("data-fps-group")];
			if (g) this._show_students(g, $el.attr("data-fps-list"));
		});
	}

	_show_students(g, kind) {
		const list = kind === "paid" ? g.paid_students : g.not_paid_students;
		const heading = kind === "paid" ? __("Paid") : __("Not Paid");
		const not_paid = kind !== "paid";
		const rows = list
			.map(
				(s, n) => `<tr>
					<td>${n + 1}</td>
					<td><a href="/app/student/${encodeURIComponent(s.student)}">${esc_fps(s.student_name || s.student)}</a>
						<div class="text-muted small">${esc_fps(s.student)}</div></td>
					<td>${esc_fps(s.standard)}</td>
					<td>${esc_fps(s.batch)}</td>
					<td>${s.mobile ? `<a href="tel:${esc_fps(s.mobile)}">${esc_fps(s.mobile)}</a>` : ""}</td>
					<td>${esc_fps(__(s.status))}</td>
					<td class="text-right">${fmt_inr(s.billed)}</td>
					${not_paid ? `<td class="text-right">${fmt_inr(s.paid)}</td>` : ""}
					<td class="text-right"><b>${fmt_inr(not_paid ? s.pending : s.paid)}</b></td>
				</tr>`
			)
			.join("");
		const sum = list.reduce((n, s) => n + (not_paid ? s.pending : s.paid), 0);
		const dialog = new frappe.ui.Dialog({
			title: `${__(g.label)} – ${__(g.gender)} · ${heading} (${list.length}) · ${__(this._data.month_name)} ${this._data.year}`,
			size: "extra-large",
		});
		dialog.$body.html(
			list.length
				? `<div class="fps-table-wrap"><table class="table table-sm fps-table">
					<thead><tr>
						<th>#</th><th>${__("Student")}</th><th>${__("Standard")}</th><th>${__("Batch")}</th>
						<th>${__("Mobile")}</th><th>${__("Status")}</th>
						<th class="text-right">${__("Due")}</th>
						${not_paid ? `<th class="text-right">${__("Paid")}</th>` : ""}
						<th class="text-right">${not_paid ? __("Pending") : __("Paid")}</th>
					</tr></thead><tbody>${rows}</tbody>
					<tfoot><tr>
						<th colspan="${not_paid ? 8 : 7}" class="text-right">${__("Total")}</th>
						<th class="text-right">${fmt_inr(sum)}</th>
					</tr></tfoot></table></div>`
				: `<div class="fps-empty">${__("No students.")}</div>`
		);
		dialog.show();
	}
}

const esc_fps = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

/* Indian grouping, no decimals: ₹1,25,000 */
const fmt_inr = (v) =>
	"₹" + Math.round(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
