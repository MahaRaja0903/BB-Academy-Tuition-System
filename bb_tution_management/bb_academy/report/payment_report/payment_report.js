// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "MultiSelectList",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Standard", txt);
			}
		},
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "MultiSelectList",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Batch", txt);
			}
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nBoys\nGirls"
		},
		{
			"fieldname": "payment_method",
			"label": __("Payment Method"),
			"fieldtype": "Select",
			"options": "\nCash\nGPAY\nScanner"
		},
		{
			"fieldname": "fee_type",
			"label": __("Payment Type"),
			"fieldtype": "Select",
			"options": "\nStarting Payment\nMonthly"
		}
	],

	// The totals at the foot of the table are not payments, so they are set
	// apart from the rows above them.
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (data && data.is_summary) {
			value = `<span style="font-weight: 600">${value}</span>`;
		} else if (data) {
			if (column.fieldname === "payment_method" && data.payment_method === "Split Up") {
				value = `<span style="color: var(--orange-500, orange); font-weight: 600;">${value}</span>`;
			}
			// One invoice can cover the starting payment and a month or two at
			// once, so the label reads "Starting Payment, September" and each
			// part is coloured on its own: a month the student had already paid
			// part of on an earlier invoice is a balance payment, and the
			// starting payment is picked out in blue.
			if (column.fieldname === "payment_type" && data.payment_type) {
				const balance_months = (data.balance_months || "").split(", ");
				value = data.payment_type
					.split(", ")
					.map(part => {
						const text = frappe.utils.escape_html(part);
						if (balance_months.includes(part)) {
							return `<span style="color: var(--green-600, green); font-weight: 600;">${text} (${__("Balance")})</span>`;
						}
						if (part === "Starting Payment") {
							return `<span style="color: var(--blue-500, blue); font-weight: 600;">${text}</span>`;
						}
						return text;
					})
					.join(", ");
			}
			// The staff can edit a student's Starting Payment or Monthly Fee
			// with a reason; showing it here answers "why is this amount low?"
			// without opening the Student. The name is coloured with it so the
			// students on an edited fee can be picked out at a glance -- a colour
			// of its own, not the orange of a Split Up or the blue of a starting
			// payment, both of which can land on the same row.
			if (column.fieldname === "student_name") {
				// The name takes the colour of the card it adds to -- a balance
				// still owed first, then a discount, then a coupon -- so those
				// students stand out without reading across the amount columns.
				let name_color = "";
				if (flt(data.balance_amount) > 0) {
					name_color = PAYMENT_REPORT_CARDS.balance.color;
				} else if (flt(data.discount_amount) > 0) {
					name_color = PAYMENT_REPORT_CARDS.discount.color;
				} else if (flt(data.coupon_amount) > 0) {
					name_color = PAYMENT_REPORT_CARDS.coupon.color;
				}
				if (name_color) {
					value = `<span style="color: ${name_color}; font-weight: 600;">${value}</span>`;
				}

				// Gender has no column of its own; it rides on the name as a
				// small badge, a blue "B" for a boy and a pink "G" for a girl.
				const badges = {
					Boys: { letter: "B", color: "#1e88e5" },
					Girls: { letter: "G", color: "#e91e8c" },
				};
				const badge = badges[data.gender];
				if (badge) {
					value = `${value}<span title="${__(data.gender)}" style="display: inline-block; margin-left: 4px; width: 16px; height: 16px; line-height: 16px; border-radius: 50%; background: ${badge.color}; color: #fff; font-size: 10px; font-weight: 700; text-align: center; vertical-align: middle;">${badge.letter}</span>`;
				}

				// A second payment for a month already part paid -- the student
				// came back to clear the balance.
				if (data.balance_months) {
					const months = frappe.utils.escape_html(data.balance_months);
					value += ` <span title="${__("Balance paid for {0}", [months])}" style="background: var(--green-100, #e4f5e9); color: var(--green-700, #1e7b34); border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 600;">${__("Balance")}</span>`;
				}

				// What the student still owes, or was let off, sits under the
				// name as a tag in the colour of its card.
				const tags = [
					["balance", "balance_amount", __("Balance")],
					["coupon", "coupon_amount", __("Coupon Used")],
					["discount", "discount_amount", __("Discount")],
				]
					.filter(([, fieldname]) => flt(data[fieldname]) > 0)
					.map(
						([key, fieldname, label]) =>
							`<span style="color: ${PAYMENT_REPORT_CARDS[key].color}; border: 1px solid ${PAYMENT_REPORT_CARDS[key].color}; border-radius: 8px; padding: 0 5px; margin-right: 4px; font-weight: 600; white-space: nowrap;">${label}: ${format_currency(data[fieldname])}</span>`
					)
					.join("");

				const reason = data.fee_reason ? frappe.utils.escape_html(data.fee_reason) : "";
				if (tags || reason) {
					const name_style = reason ? "color: var(--purple-500, #9c45e3); font-weight: 600;" : "";
					const reason_html = reason
						? `<span style="color: var(--purple-500, #9c45e3);">${reason}</span>`
						: "";
					value = `<div title="${reason}" style="${name_style} line-height: 1.2; overflow: hidden; text-overflow: ellipsis;">${value}</div>
						<div title="${reason}" style="font-size: 10px; line-height: 1.3; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${tags}${reason_html}</div>`;
				}
			}
		}

		return value;
	},

	// The student name can carry a second line with the reason its fee was
	// edited, which the default row height clips.
	get_datatable_options: function (options) {
		return Object.assign(options, { cellHeight: 46 });
	},

	// Every standard starts out selected. onload runs before the first refresh
	// with the report's _no_refresh flag still set, so setting the value on the
	// control directly seeds the filter without running the report twice.
	onload: function (report) {
		patch_summary_cards(report);

		let filter = report.get_filter("standard");
		if (!filter || (filter.get_value() || []).length) {
			return;
		}

		return frappe.db.get_list("Standard", {
			fields: ["name"],
			order_by: "academic_order asc",
			limit: 0
		}).then(rows => {
			filter.set_value(rows.map(row => row.name));
		});
	}
};

// The summary cards, drawn after the client's reference design: one coloured
// card per figure, each holding its total and its count.
const PAYMENT_REPORT_CARDS = {
	received: { title: __("Received"), icon: "💵", color: "#2e9e48" },
	balance: { title: __("Balance"), icon: "🤲", color: "#d93a3a" },
	discount: { title: __("Offers & Discounts"), icon: "🏷️", color: "#12938f" },
	coupon: { title: __("Coupon Used"), icon: "🎟️", color: "#c99a06" },
	cash: { title: __("Cash"), icon: "💸", color: "#2f8de0" },
	gpay: { title: __("GPay"), icon: "📱", color: "#f26b1d" },
	scanner: { title: __("Scanner"), icon: "🔳", color: "#8e3bb0" },
};

function patch_summary_cards(report) {
	// The query report view is shared by every report, so only this report's
	// summary is drawn differently and the patch is put on once.
	if (report.__payment_cards_patched) return;
	report.__payment_cards_patched = true;

	const render_summary = report.render_summary;
	report.render_summary = function (data) {
		if (this.report_name !== "Payment Report" || !data.every(item => item.card)) {
			return render_summary.call(this, data);
		}
		this.$summary.html(build_summary_cards(data)).show();

		// A count on the Balance, Discount and Coupon cards opens the list of
		// the students behind it.
		this.$summary.find(".pr-card-clickable").on("click", e => {
			show_card_students(this, $(e.currentTarget).attr("data-card"));
		});
	};
}

// The cards whose count can be clicked through to its students, with the
// amount each one is counted on.
const PAYMENT_REPORT_CARD_STUDENTS = {
	balance: { fieldname: "balance_amount", label: __("Balance Amount") },
	discount: { fieldname: "discount_amount", label: __("Discount Amount") },
	coupon: { fieldname: "coupon_amount", label: __("Coupon Amount") },
};

function show_card_students(report, key) {
	const card = PAYMENT_REPORT_CARDS[key];
	const { fieldname, label } = PAYMENT_REPORT_CARD_STUDENTS[key];
	const rows = (report.data || []).filter(row => !row.is_summary && flt(row[fieldname]) > 0);
	const esc = frappe.utils.escape_html;

	const body = rows.length
		? rows
				.map(
					(row, i) => `<tr>
						<td>${i + 1}</td>
						<td>${esc(row.student_name || "")}</td>
						<td>${esc(row.standard || "")}</td>
						<td><a href="/app/fee-invoice/${encodeURIComponent(row.fee_invoice)}" target="_blank">${esc(row.fee_invoice)}</a></td>
						<td class="text-right">${format_currency(row[fieldname])}</td>
					</tr>`
				)
				.join("")
		: `<tr><td colspan="5" class="text-center text-muted">${__("No students")}</td></tr>`;

	const total = rows.reduce((sum, row) => sum + flt(row[fieldname]), 0);

	const dialog = new frappe.ui.Dialog({
		title: __("{0} ({1})", [card.title, rows.length]),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "students" }],
	});

	dialog.fields_dict.students.$wrapper.html(`
		<div style="max-height: 60vh; overflow-y: auto;">
			<table class="table table-bordered table-sm" style="margin: 0;">
				<thead style="position: sticky; top: 0; background: ${card.color}; color: #fff;">
					<tr>
						<th style="width: 40px;">#</th>
						<th>${__("Student Name")}</th>
						<th>${__("Standard")}</th>
						<th>${__("Fee Invoice")}</th>
						<th class="text-right">${esc(label)}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
				<tfoot>
					<tr style="font-weight: 600;">
						<td colspan="4" class="text-right">${__("Total")}</td>
						<td class="text-right">${format_currency(total)}</td>
					</tr>
				</tfoot>
			</table>
		</div>`);
	dialog.show();
}

function build_summary_cards(data) {
	const grouped = {};
	data.forEach(item => (grouped[item.card] = grouped[item.card] || []).push(item));

	const cards = Object.keys(grouped).map((key, index) => {
		const card = PAYMENT_REPORT_CARDS[key] || { title: key, icon: "", color: "#6c7680" };
		// Four cards on the first line, the three payment modes below them.
		const span = index < 4 ? 3 : 4;
		const figures = grouped[key]
			.map(item => {
				const value =
					item.datatype === "Currency"
						? format_currency(item.value, item.currency)
						: frappe.utils.escape_html(String(item.value ?? 0));
				const clickable = item.datatype === "Int" && PAYMENT_REPORT_CARD_STUDENTS[key];
				const attrs = clickable
					? ` class="pr-card-clickable" data-card="${key}" title="${__("Click to see the students")}"`
					: "";
				return `<div${attrs}>
					<div class="pr-card-label">${frappe.utils.escape_html(item.label)}</div>
					<div class="pr-card-value">${value}</div>
				</div>`;
			})
			.join("");

		return `<div class="pr-card" style="--pr-span: ${span}; --pr-color: ${card.color};">
			<div class="pr-card-head"><span class="pr-card-icon">${card.icon}</span>${frappe.utils.escape_html(card.title)}</div>
			<div class="pr-card-body${index < 4 ? "" : " pr-card-center"}">${figures}</div>
		</div>`;
	});

	return `<style>
		.pr-cards { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; width: 100%; padding: 8px 0; }
		.pr-card { grid-column: span var(--pr-span); background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6e9);
			border-radius: 8px; overflow: hidden; box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.1)); }
		.pr-card-head { background: var(--pr-color); color: #fff; font-size: 18px; font-weight: 600; padding: 8px 14px;
			display: flex; align-items: center; gap: 10px; }
		.pr-card-icon { font-size: 26px; line-height: 1; }
		.pr-card-body { padding: 10px 16px 12px; color: var(--text-color, #1f272e); }
		.pr-card-center { text-align: center; }
		.pr-card-label { font-size: 14px; margin-top: 4px; }
		.pr-card-value { font-size: 22px; font-weight: 700; line-height: 1.3; }
		.pr-card-clickable { cursor: pointer; border-radius: 6px; }
		.pr-card-clickable:hover { background: var(--subtle-fg, #f4f5f6); }
		.pr-card-clickable .pr-card-value { color: var(--pr-color); text-decoration: underline dotted; }
		@media (max-width: 991px) { .pr-card { grid-column: span 6; } }
		@media (max-width: 575px) { .pr-card { grid-column: span 12; } }
	</style>
	<div class="pr-cards">${cards.join("")}</div>`;
}
