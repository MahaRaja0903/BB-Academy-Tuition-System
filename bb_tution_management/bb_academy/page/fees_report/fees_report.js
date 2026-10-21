/* Starting Payment & Monthly Fees report: page controller.

   • One API call (`get_summary`) fills the page; the Year and Month filters re-run it.
   • Three sections (Starting Payment, Monthly Fees, Grand Consolidated Total),
     each with Total / Paid / Pending cards.
   • Clicking a card opens the student-wise rows behind it (`get_breakdown`).
   • No inline onclick. Clicks are delegated from [data-fr-*] attributes. */

frappe.pages["fees-report"].on_page_load = function (wrapper) {
	wrapper._fr = new FeesReport(wrapper);
};

frappe.pages["fees-report"].on_page_show = function (wrapper) {
	if (wrapper._fr && wrapper._fr._loaded) wrapper._fr.refresh();
};

const FR_API = "bb_tution_management.bb_academy.page.fees_report.fees_report";

const FR_MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
];

const FR_SECTIONS = [
	{ key: "starting", title: __("Starting Payment") },
	{ key: "monthly", title: __("Monthly Fees") },
	{ key: "overall", title: __("Grand Consolidated Total"), card: __("Overall") },
];

const FR_CARDS = [
	{
		kind: "total",
		label: __("Total"),
		rows: [
			[__("Total Amount"), "total_amount", true],
			[__("Total Count"), "total_count", false],
		],
	},
	{
		kind: "paid",
		label: __("Paid"),
		rows: [
			[__("Paid Amount"), "paid_amount", true],
			[__("Paid Count"), "paid_count", false],
		],
	},
	{
		kind: "pending",
		label: __("Pending"),
		rows: [
			[__("Pending Amount"), "pending_amount", true],
			[__("Not Paid Count"), "not_paid_count", false],
		],
	},
];

class FeesReport {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Fees Report"),
			single_column: true,
		});
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");

		// page.body also holds the filter bar, so render into our own container.
		this.$body = $('<div class="fr-root"></div>').appendTo(this.page.body);
		this._make_filters();
		this._bind_events();
		this.refresh();
	}

	_make_filters() {
		const this_year = String(new Date().getFullYear());
		this.f_year = this.page.add_field({
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			options: [{ value: "", label: __("All Years") }, this_year],
			default: this_year,
			change: () => this.refresh(),
		});
		this.f_month = this.page.add_field({
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [{ value: "", label: __("All Months") }].concat(
				FR_MONTHS.map((m, i) => ({ value: String(i + 1), label: __(m) }))
			),
			default: "",
			change: () => this.refresh(),
		});
	}

	_set_year_options(years) {
		const current = this.f_year.get_value();
		const opts = [{ value: "", label: __("All Years") }].concat(years.map((y) => String(y)));
		this.f_year.df.options = opts;
		this.f_year.refresh();
		this.f_year.set_input(current);
	}

	_filters() {
		return { year: this.f_year.get_value() || "", month: this.f_month.get_value() || "" };
	}

	// The starting payment is not narrowed by month (see get_summary), so its
	// section always reads "All Months".
	_period_label(section) {
		const { year, month } = this._filters();
		const m = month && section !== "starting" ? __(FR_MONTHS[cint(month) - 1]) : __("All Months");
		return `${m} · ${year || __("All Years")}`;
	}

	refresh() {
		const args = this._filters();
		const token = (this._token = (this._token || 0) + 1);
		this.$body.addClass("fr-loading");
		frappe
			.call({ method: `${FR_API}.get_summary`, args })
			.then((r) => {
				if (token !== this._token) return;
				const res = r.message || {};
				this._set_year_options(res.years || []);
				this.render(res.data || {});
				this._loaded = true;
			})
			.always(() => this.$body.removeClass("fr-loading"));
	}

	render(data) {
		const money = (v) => format_currency(flt(v), frappe.defaults.get_default("currency"), 0);
		const sections = FR_SECTIONS.map((sec, i) => {
			const block = data[sec.key] || {};
			const cards = FR_CARDS.map((card) => {
				const rows = card.rows
					.map(
						([label, field, is_money]) => `
						<div class="fr-row">
							<span class="fr-label">${label}:</span>
							<span class="fr-value">${is_money ? money(block[field]) : cint(block[field])}</span>
						</div>`
					)
					.join("");
				return `
					<button type="button" class="fr-card fr-${card.kind}"
						data-fr-section="${sec.key}" data-fr-kind="${card.kind}"
						title="${__("Click to see students")}">
						<div class="fr-card-head">${(sec.card || sec.title).toUpperCase()} • ${card.label.toUpperCase()}</div>
						<div class="fr-card-body">${rows}</div>
					</button>`;
			}).join("");
			return `
				<div class="fr-section">
					<div class="fr-section-title">${String(i + 1).padStart(2, "0")}. ${sec.title.toUpperCase()}
						${sec.key === "starting" && this._filters().month
							? `<span class="fr-section-note">${__("All Months")}</span>` : ""}</div>
					<div class="fr-cards">${cards}</div>
				</div>`;
		}).join("");

		this.$body.html(`
			<div class="fr-header">
				<div class="fr-title">${__("Starting Payment & Monthly Fees - Report")}</div>
				<div class="fr-subtitle">${__("Financial Summary & Collection Tracking Dashboard")}
					<span class="fr-period">${this._period_label()}</span></div>
			</div>
			${sections}
		`);
	}

	_bind_events() {
		this.$body.on("click", "[data-fr-section]", (e) => {
			const $c = $(e.currentTarget);
			this.show_breakdown($c.attr("data-fr-section"), $c.attr("data-fr-kind"));
		});
	}

	show_breakdown(section, kind) {
		const sec = FR_SECTIONS.find((s) => s.key === section);
		const card = FR_CARDS.find((c) => c.kind === kind);
		frappe
			.call({ method: `${FR_API}.get_breakdown`, args: { section, kind, ...this._filters() } })
			.then((r) => {
				const rows = r.message || [];
				const money = (v) => format_currency(flt(v), frappe.defaults.get_default("currency"), 0);
				const uniq = (list) => [...new Set(list.filter(Boolean))].sort();
				const render = (list) =>
					list.length
						? `<table class="table table-bordered table-condensed fr-table">
						<thead><tr>
							<th>#</th><th>${__("Student")}</th><th>${__("Standard")}</th><th>${__("Batch")}</th><th>${__("Gender")}</th>
							<th>${__("Fee")}</th><th>${__("Period")}</th><th>${__("Status")}</th><th>${__("Payment Date")}</th>
							<th class="text-right">${__("Paid")}</th><th class="text-right">${__("Pending")}</th>
						</tr></thead>
						<tbody>${list
							.map(
								(d, i) => `<tr>
								<td>${i + 1}</td>
								<td><a href="/app/student/${encodeURIComponent(d.student)}">${frappe.utils.escape_html(d.student_name || d.student)}</a></td>
								<td>${frappe.utils.escape_html(d.standard || "")}</td>
								<td>${frappe.utils.escape_html(d.batch || "")}</td>
								<td>${frappe.utils.escape_html(d.gender || "")}</td>
								<td>${d.fee}</td>
								<td>${d.period}</td>
								<td>${frappe.utils.escape_html(d.status || "")}</td>
								<td>${d.paid_date ? frappe.datetime.str_to_user(d.paid_date) : ""}</td>
								<td class="text-right">${money(d.paid)}</td>
								<td class="text-right">${money(d.pending)}</td>
							</tr>`
							)
							.join("")}</tbody>
					</table>`
						: `<div class="text-muted text-center" style="padding:20px">${__("No records")}</div>`;

				const refresh = () => {
					const standard = d.get_value("standard");
					const gender = d.get_value("gender");
					let batch = d.get_value("batch");
					// Batch choices follow the selected Standard.
					const batches = uniq(rows.filter((x) => !standard || x.standard === standard).map((x) => x.batch));
					d.set_df_property("batch", "options", ["", ...batches]);
					if (batch && !batches.includes(batch)) {
						batch = "";
						d.set_value("batch", "");
					}
					d.fields_dict.body.$wrapper.html(
						render(
							rows.filter(
								(x) =>
									(!standard || x.standard === standard) &&
									(!batch || x.batch === batch) &&
									(!gender || x.gender === gender)
							)
						)
					);
				};

				const d = new frappe.ui.Dialog({
					title: `${sec.card || sec.title} • ${card.label} (${this._period_label(section)})`,
					size: "extra-large",
					fields: [
						{
							fieldtype: "Select",
							fieldname: "standard",
							label: __("Standard"),
							options: ["", ...uniq(rows.map((x) => x.standard))],
							change: () => refresh(),
						},
						{ fieldtype: "Column Break" },
						{
							fieldtype: "Select",
							fieldname: "batch",
							label: __("Batch"),
							options: ["", ...uniq(rows.map((x) => x.batch))],
							change: () => refresh(),
						},
						{ fieldtype: "Column Break" },
						{
							fieldtype: "Select",
							fieldname: "gender",
							label: __("Gender"),
							options: ["", ...uniq(rows.map((x) => x.gender))],
							change: () => refresh(),
						},
						{ fieldtype: "Section Break" },
						{ fieldtype: "HTML", fieldname: "body" },
					],
				});
				refresh();
				d.show();
			});
	}
}
