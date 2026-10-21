/* Student Count Report: page controller.

   • One API call (`get_report`) fills the page; changing the Academic Year re-runs it.
   • Renders the "Actual Students Count List" sheet: three sections, month
     columns, Highest Count and TOTAL rows.
   • Print gives one section per page, laid out like the paper original. */

frappe.pages["student-count-report"].on_page_load = function (wrapper) {
	wrapper._scr = new StudentCountReport(wrapper);
};

frappe.pages["student-count-report"].on_page_show = function (wrapper) {
	if (wrapper._scr && wrapper._scr._loaded) wrapper._scr.refresh();
};

const SCR_API = "bb_tution_management.bb_academy.page.student_count_report.student_count_report";

class StudentCountReport {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Student Count Report"),
			single_column: true,
		});
		this.page.set_primary_action(__("Print"), () => window.print(), "printer");
		this.page.set_secondary_action(__("Refresh"), () => this.refresh());

		this.$body = $('<div class="scr-root"></div>').appendTo(this.page.body);
		this._make_filters();
		this._default_year().then((year) => {
			if (year) this.f_year.set_value(year);
			else this.refresh();
		});
	}

	_make_filters() {
		this.f_year = this.page.add_field({
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			change: () => this.refresh(),
		});
	}

	/* Prefer a "YYYY-YYYY" year that contains today; the per-standard years
	   ("June to April - 6th to 9th STD") start in the same calendar year anyway. */
	async _default_year() {
		const today = frappe.datetime.get_today();
		const years = await frappe.db.get_list("Academic Year", {
			fields: ["name", "start_date", "end_date"],
			order_by: "start_date desc",
			limit: 50,
		});
		const current = years.filter((y) => y.start_date <= today && y.end_date >= today);
		const pick =
			current.find((y) => /^\d{4}\s*-\s*\d{4}$/.test(y.name)) || current[0] || years[0];
		return pick && pick.name;
	}

	refresh() {
		const year = this.f_year.get_value();
		if (!year) {
			this.$body.html(`<div class="scr-empty">${__("Select an Academic Year.")}</div>`);
			return;
		}
		this.$body.html(`<div class="scr-empty">${__("Loading…")}</div>`);
		frappe
			.xcall(`${SCR_API}.get_report`, { academic_year: year })
			.then((data) => {
				this._loaded = true;
				this.render(data);
			})
			.catch(() => this.$body.html(`<div class="scr-empty">${__("Could not load the report.")}</div>`));
	}

	render(data) {
		this.$body.html(data.sections.map((s) => this._section(s, data.year_label)).join(""));
	}

	_section(section, year_label) {
		const esc = frappe.utils.escape_html;
		const cell = (v) => (v === null || v === undefined ? "" : v);

		const head = section.months
			.map((m) => `<th class="scr-m scr-m-${m.toLowerCase()}">${m}</th>`)
			.join("");

		const rows = section.rows
			.map(
				(r, i) => `<tr>
					<td class="scr-sno">${i + 1}</td>
					<td class="scr-std">${esc(r.label)}</td>
					${r.counts.map((c) => `<td class="scr-n">${cell(c)}</td>`).join("")}
					<td class="scr-n scr-high">${cell(r.highest)}</td>
				</tr>`
			)
			.join("");

		const total = `<tr class="scr-total">
				<td colspan="2">${__("TOTAL")}</td>
				${section.totals.map((t) => `<td class="scr-n">${cell(t)}</td>`).join("")}
				<td class="scr-n scr-high">${cell(section.highest)}</td>
			</tr>`;

		return `<div class="scr-sheet">
			<div class="scr-year">${__("ACADEMIC YEAR")} : ${esc(year_label)}</div>
			<div class="scr-title">${__("ACTUAL STUDENTS COUNT LIST")}</div>
			<div class="scr-title">${__("STD WISE & MONTH WISE")}</div>
			<div class="scr-subtitle">${esc(section.title)}</div>
			<div class="scr-scroll">
				<table class="scr-table">
					<thead><tr>
						<th class="scr-sno">${__("S.No.")}</th>
						<th class="scr-std">${__("STD")}</th>
						${head}
						<th class="scr-high">${__("Highest Count")}</th>
					</tr></thead>
					<tbody>${rows}${total}</tbody>
				</table>
			</div>
		</div>`;
	}
}
