/* ═══════════════════════════════════════════════════════════════════════
   BB Academy Dashboard — Page Controller
   ───────────────────────────────────────────────────────────────────────
   • Single-class controller, no framework dependencies beyond Frappe.
   • All API calls use the batched endpoint where possible.
   • KPI numbers animate (count-up) on load.
   • Auto-refreshes "Today's Collections" and "Open Enquiries" every 5 min.
   ═══════════════════════════════════════════════════════════════════════ */

frappe.pages["bb-dashboard"].on_page_show = function (wrapper) {
	if (!wrapper._bb_init) {
		wrapper._bb = new BBDashboard(wrapper);
		wrapper._bb_init = true;
	} else {
		wrapper._bb.refresh();
	}
};

/* ── Helpers ────────────────────────────────────────────────────────── */

const API = "bb_tution_management.bb_academy.page.bb_dashboard.bb_dashboard";

function icon(name) {
	// Use Frappe's built-in icon helper (feather-based)
	return frappe.utils.icon(name, "sm");
}

/* ── Main Class ─────────────────────────────────────────────────────── */

class BBDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "BB Academy",
			single_column: true,
		});

		// Header buttons
		this.page.set_primary_action(
			"Refresh",
			() => this.refresh(),
			"refresh-cw"
		);

		this.page.add_inner_button("New Enquiry", () =>
			frappe.new_doc("Student Enquiry Form")
		);
		this.page.add_inner_button("New Admission", () =>
			frappe.new_doc("Student Admission Form")
		);
		this.page.add_inner_button("Fee Invoice", () =>
			frappe.new_doc("Fee Invoice")
		);
		this.page.add_inner_button("Record Payment", () =>
			frappe.new_doc("Fees Payment Entry")
		);

		this.$body = $(this.page.body);
		this.$body.attr("data-page-container", "bb-dashboard");

		this._build_shell();
		this._load_all();
		this._start_auto_refresh();
	}

	/* ── Shell (skeleton) ──────────────────────────────────────────── */

	_build_shell() {
		this.$body.html(`
			<div class="bb-dash">

				<!-- KPIs -->
				<section class="bb-dash__section">
					<div class="bb-dash__section-head">
						<h2 class="bb-dash__section-title">Overview</h2>
						<span class="bb-dash__timestamp" data-ref="timestamp"></span>
					</div>
					<div class="bb-kpi-grid" data-ref="kpi-grid">
						${this._skel_kpi(6)}
					</div>
				</section>

				<!-- Charts row 1 -->
				<section class="bb-dash__section">
					<div class="bb-chart-grid">
						<div class="bb-card bb-stagger-1">
							<h3 class="bb-card__header">Monthly Collection</h3>
							<div class="bb-card__chart" data-ref="chart-collection">
								<div class="bb-skel bb-skel--chart"></div>
							</div>
						</div>
						<div class="bb-card bb-stagger-2">
							<h3 class="bb-card__header">Invoice Status</h3>
							<div class="bb-card__chart" data-ref="chart-invoices">
								<div class="bb-skel bb-skel--chart"></div>
							</div>
						</div>
					</div>
				</section>

				<!-- Charts row 2 -->
				<section class="bb-dash__section">
					<div class="bb-chart-grid">
						<div class="bb-card bb-stagger-3">
							<h3 class="bb-card__header">Students by Standard</h3>
							<div class="bb-card__chart" data-ref="chart-standards">
								<div class="bb-skel bb-skel--chart"></div>
							</div>
						</div>
						<div class="bb-card bb-stagger-4">
							<h3 class="bb-card__header">Enquiry Sources</h3>
							<div class="bb-card__chart" data-ref="chart-sources">
								<div class="bb-skel bb-skel--chart"></div>
							</div>
						</div>
					</div>
				</section>

				<!-- Quick actions -->
				<section class="bb-dash__section">
					<div class="bb-dash__section-head">
						<h2 class="bb-dash__section-title">Quick Actions</h2>
					</div>
					<div class="bb-actions" data-ref="actions"></div>
				</section>

				<!-- Info panels -->
				<section class="bb-dash__section">
					<div class="bb-panels-grid">
						<div class="bb-panel bb-stagger-1">
							<h3 class="bb-panel__header">Today's Birthdays</h3>
							<div class="bb-panel__body" data-ref="panel-birthdays">
								${this._skel_rows(3)}
							</div>
						</div>
						<div class="bb-panel bb-stagger-2">
							<h3 class="bb-panel__header">Pending Follow-ups</h3>
							<div class="bb-panel__body" data-ref="panel-followups">
								${this._skel_rows(3)}
							</div>
						</div>
						<div class="bb-panel bb-stagger-3">
							<h3 class="bb-panel__header">Recent Payments</h3>
							<div class="bb-panel__body" data-ref="panel-payments">
								${this._skel_rows(3)}
							</div>
						</div>
						<div class="bb-panel bb-stagger-4">
							<h3 class="bb-panel__header">Overdue Invoices</h3>
							<div class="bb-panel__body" data-ref="panel-overdue">
								${this._skel_rows(3)}
							</div>
						</div>
					</div>
				</section>

				<!-- Reports -->
				<section class="bb-dash__section">
					<div class="bb-dash__section-head">
						<h2 class="bb-dash__section-title">Reports</h2>
					</div>
					<div class="bb-reports-grid" data-ref="reports"></div>
				</section>

			</div>
		`);

		this._render_actions();
		this._render_reports();
	}

	_skel_kpi(n) {
		let h = "";
		for (let i = 0; i < n; i++) {
			h += `
				<div class="bb-kpi bb-stagger-${i + 1}">
					<div class="bb-skel bb-skel--label" style="width:50%"></div>
					<div class="bb-skel bb-skel--value"></div>
					<div class="bb-skel bb-skel--label" style="width:40%"></div>
				</div>`;
		}
		return h;
	}

	_skel_rows(n) {
		let h = "";
		for (let i = 0; i < n; i++) {
			h += `<div class="bb-skel bb-skel--row"></div>`;
		}
		return h;
	}

	/* ── Static sections ───────────────────────────────────────────── */

	_render_actions() {
		const actions = [
			{ label: "New Enquiry", icon: "edit", action: () => frappe.new_doc("Student Enquiry Form") },
			{ label: "New Admission", icon: "file-text", action: () => frappe.new_doc("Student Admission Form") },
			{ label: "Create Invoice", icon: "file", action: () => frappe.new_doc("Fee Invoice") },
			{ label: "Record Payment", icon: "credit-card", action: () => frappe.new_doc("Fees Payment Entry") },
			{ label: "Bulk Invoicing", icon: "layers", action: () => frappe.set_route("Form", "Bulk Fee Invoice Tool") },
			{ label: "SMS Settings", icon: "message-circle", action: () => frappe.set_route("Form", "BB SMS Settings") },
		];

		const $el = this.$body.find('[data-ref="actions"]');
		actions.forEach((a) => {
			const $btn = $(`<button class="bb-action">${icon(a.icon)}<span>${a.label}</span></button>`);
			$btn.on("click", a.action);
			$el.append($btn);
		});
	}

	_render_reports() {
		const reports = [
			{ name: "Pending Balance", desc: "Outstanding fee balances", icon: "bar-chart-2", route: "Pending Balance Report" },
			{ name: "Payment Report", desc: "Detailed payment entries", icon: "credit-card", route: "Payment Wise Report" },
			{ name: "Student Report", desc: "Student master data", icon: "users", route: "Student Wise Report" },
			{ name: "Birthday Report", desc: "Birthdays by month", icon: "gift", route: "Birthday Report" },
			{ name: "Promotion Report", desc: "Batch transfers", icon: "trending-up", route: "Promote and Demote Report" },
		];

		const $el = this.$body.find('[data-ref="reports"]');
		reports.forEach((r) => {
			const $card = $(`
				<div class="bb-report">
					<div class="bb-report__icon">${icon(r.icon)}</div>
					<div class="bb-report__info">
						<div class="bb-report__name">${r.name}</div>
						<div class="bb-report__desc">${r.desc}</div>
					</div>
					<div class="bb-report__arrow">${icon("arrow-right")}</div>
				</div>
			`);
			$card.on("click", () => frappe.set_route("query-report", r.route));
			$el.append($card);
		});
	}

	/* ── Data loading ──────────────────────────────────────────────── */

	async _load_all() {
		try {
			const [kpis, trend, invoices, standards, sources, payments, birthdays, followups, overdue] =
				await Promise.all([
					frappe.xcall(`${API}.get_dashboard_data`),
					frappe.xcall(`${API}.get_collection_trend`),
					frappe.xcall(`${API}.get_invoice_status_breakdown`),
					frappe.xcall(`${API}.get_students_by_standard`),
					frappe.xcall(`${API}.get_enquiry_sources`),
					frappe.xcall(`${API}.get_recent_payments`),
					frappe.xcall(`${API}.get_todays_birthdays`),
					frappe.xcall(`${API}.get_pending_followups`),
					frappe.xcall(`${API}.get_overdue_invoices`),
				]);

			this._render_kpis(kpis);
			this._render_chart_collection(trend);
			this._render_chart_invoices(invoices);
			this._render_chart_standards(standards);
			this._render_chart_sources(sources);
			this._render_panel_payments(payments);
			this._render_panel_birthdays(birthdays);
			this._render_panel_followups(followups);
			this._render_panel_overdue(overdue);

			this.$body.find('[data-ref="timestamp"]').text(
				"Updated " + frappe.datetime.now_time().substring(0, 5)
			);

			// Store for partial refresh
			this._last_kpis = kpis;
		} catch (err) {
			console.error("BB Dashboard load error:", err);
			frappe.show_alert({
				message: "Dashboard failed to load. Try refreshing.",
				indicator: "red",
			});
		}
	}

	/* ── Partial auto-refresh (every 5 min) ────────────────────────── */

	_start_auto_refresh() {
		this._auto_timer = setInterval(() => this._refresh_volatile(), 5 * 60 * 1000);
	}

	async _refresh_volatile() {
		try {
			const data = await frappe.xcall(`${API}.get_dashboard_data`);
			// Only update the two volatile cards
			const $grid = this.$body.find('[data-ref="kpi-grid"]');
			this._update_kpi_value($grid.find('[data-kpi="open_enquiries"]'), data.open_enquiries);
			this._update_kpi_value($grid.find('[data-kpi="todays_collections"]'),
				this._fmt_inr(data.todays_collections));
			// Update monthly sub-label
			$grid.find('[data-kpi="todays_collections"] .bb-kpi__meta-text').text(
				"Month: " + this._fmt_inr(data.monthly_collection)
			);
			this.$body.find('[data-ref="timestamp"]').text(
				"Updated " + frappe.datetime.now_time().substring(0, 5)
			);
		} catch (e) {
			// Silent fail for background refresh
		}
	}

	_update_kpi_value($card, newVal) {
		$card.find(".bb-kpi__value").text(newVal);
	}

	/* ── Full refresh ──────────────────────────────────────────────── */

	refresh() {
		this.$body.find(".bb-dash").addClass("bb-refreshing");
		this._load_all().then(() => {
			this.$body.find(".bb-dash").removeClass("bb-refreshing");
		});
	}

	destroy() {
		if (this._auto_timer) clearInterval(this._auto_timer);
	}

	/* ── KPI Rendering ─────────────────────────────────────────────── */

	_render_kpis(d) {
		// Month-over-month trend
		let trend = null;
		if (d.last_month_collection > 0) {
			const pct = ((d.monthly_collection - d.last_month_collection) / d.last_month_collection * 100).toFixed(1);
			trend = { pct: Math.abs(pct), dir: pct >= 0 ? "up" : "down" };
		}

		const cards = [
			{
				key: "active_students",
				label: "ACTIVE STUDENTS",
				value: d.active_students,
				meta: d.total_students > 0 ? `${d.total_students} total enrolled` : null,
				dot: "green",
				route: "student?status=Active",
			},
			{
				key: "new_admissions",
				label: "NEW ADMISSIONS",
				value: d.new_admissions,
				meta: "This month",
				dot: null,
				route: "student-admission-form?docstatus=1",
			},
			{
				key: "open_enquiries",
				label: "OPEN ENQUIRIES",
				value: d.open_enquiries,
				meta: null,
				dot: d.open_enquiries > 0 ? "amber" : "green",
				zeroMsg: "All caught up",
				route: 'student-enquiry-form?status=["in",["Open","Follow-up"]]',
			},
			{
				key: "unpaid_invoices",
				label: "UNPAID INVOICES",
				value: d.unpaid_invoices,
				meta: null,
				dot: d.unpaid_invoices > 0 ? "red" : "green",
				zeroMsg: "All clear",
				route: 'fee-invoice?status=["in",["Unpaid","Partially Paid"]]&docstatus=1',
			},
			{
				key: "total_pending",
				label: "TOTAL PENDING",
				value: this._fmt_inr(d.total_pending),
				isCurrency: true,
				meta: null,
				dot: d.total_pending > 0 ? "red" : "green",
				zeroMsg: "Nothing pending",
				route: "query-report/Pending Balance Report",
			},
			{
				key: "todays_collections",
				label: "TODAY'S COLLECTION",
				value: this._fmt_inr(d.todays_collections),
				isCurrency: true,
				meta: "Month: " + this._fmt_inr(d.monthly_collection),
				dot: "green",
				trend: trend,
				zeroMsg: "No collections yet",
				route: null,
			},
		];

		let html = "";
		cards.forEach((c, i) => {
			const isZero = (c.isCurrency ? (parseFloat(String(c.value).replace(/[^\d.]/g, "")) === 0) : c.value === 0);
			const displayValue = (isZero && c.zeroMsg) ? "0" : c.value;
			const metaText = (isZero && c.zeroMsg) ? c.zeroMsg : (c.meta || "");

			const dotHtml = c.dot
				? `<span class="bb-kpi__dot bb-kpi__dot--${isZero && c.zeroMsg ? 'green' : c.dot}"></span>`
				: "";

			const trendHtml = c.trend
				? `<span class="bb-kpi__trend bb-kpi__trend--${c.trend.dir}">
					${c.trend.dir === "up" ? "↑" : "↓"} ${c.trend.pct}%
				   </span>`
				: "";

			const clickAttr = c.route
				? `onclick="frappe.set_route('${c.route}')" role="button" tabindex="0"`
				: "";

			html += `
				<div class="bb-kpi bb-stagger-${i + 1}" data-kpi="${c.key}" ${clickAttr}>
					<div class="bb-kpi__label">${c.label}</div>
					<div class="bb-kpi__value" data-count-to="${c.isCurrency ? '' : c.value}">${displayValue}</div>
					<div class="bb-kpi__meta">
						${dotHtml}
						<span class="bb-kpi__meta-text">${metaText}</span>
						${trendHtml}
					</div>
				</div>`;
		});

		this.$body.find('[data-ref="kpi-grid"]').html(html);

		// Animate count-up for integer values
		this.$body.find(".bb-kpi__value[data-count-to]").each(function () {
			const target = parseInt($(this).attr("data-count-to"));
			if (isNaN(target) || target === 0) return;
			const $el = $(this);
			const duration = 400;
			const start = performance.now();
			const step = (now) => {
				const elapsed = now - start;
				const progress = Math.min(elapsed / duration, 1);
				// Ease-out cubic
				const eased = 1 - Math.pow(1 - progress, 3);
				$el.text(Math.round(eased * target));
				if (progress < 1) requestAnimationFrame(step);
			};
			requestAnimationFrame(step);
		});
	}

	/* ── Currency formatting (Indian grouping) ─────────────────────── */

	_fmt_inr(amount) {
		if (!amount || amount === 0) return "₹0";
		// Use Frappe's format if available, fallback to manual Indian grouping
		try {
			return frappe.format(amount, { fieldtype: "Currency" });
		} catch (e) {
			return "₹" + Number(amount).toLocaleString("en-IN", {
				minimumFractionDigits: 0,
				maximumFractionDigits: 0,
			});
		}
	}

	/* ── Chart Renderers ───────────────────────────────────────────── */

	_render_chart_collection(data) {
		const $el = this.$body.find('[data-ref="chart-collection"]');
		if (!data || !data.length) {
			$el.html('<div class="bb-no-data">No collection data yet</div>');
			return;
		}
		$el.empty();
		new frappe.Chart($el[0], {
			data: {
				labels: data.map((d) => d.month),
				datasets: [{ name: "Collection", values: data.map((d) => d.amount) }],
			},
			type: "bar",
			height: 280,
			colors: ["#4F46E5"],
			barOptions: { spaceRatio: 0.4 },
			axisOptions: { xIsSeries: true, shortenYAxisNumbers: true },
			tooltipOptions: {
				formatTooltipY: (v) => this._fmt_inr(v),
			},
		});
	}

	_render_chart_invoices(data) {
		const $el = this.$body.find('[data-ref="chart-invoices"]');
		if (!data || !data.length) {
			$el.html('<div class="bb-no-data">No invoices yet</div>');
			return;
		}
		$el.empty();
		const cmap = {
			Paid: "#16A34A",
			Unpaid: "#DC2626",
			"Partially Paid": "#D97706",
			Cancelled: "#6B7280",
		};
		new frappe.Chart($el[0], {
			data: {
				labels: data.map((d) => d.status),
				datasets: [{ name: "Invoices", values: data.map((d) => d.count) }],
			},
			type: "pie",
			height: 280,
			colors: data.map((d) => cmap[d.status] || "#4F46E5"),
		});
	}

	_render_chart_standards(data) {
		const $el = this.$body.find('[data-ref="chart-standards"]');
		if (!data || !data.length) {
			$el.html('<div class="bb-no-data">No student data yet</div>');
			return;
		}
		$el.empty();
		new frappe.Chart($el[0], {
			data: {
				labels: data.map((d) => d.standard || "Unassigned"),
				datasets: [{ name: "Students", values: data.map((d) => d.count) }],
			},
			type: "bar",
			height: 280,
			colors: ["#4F46E5"],
			barOptions: { spaceRatio: 0.4 },
		});
	}

	_render_chart_sources(data) {
		const $el = this.$body.find('[data-ref="chart-sources"]');
		if (!data || !data.length) {
			$el.html('<div class="bb-no-data">No enquiry data yet</div>');
			return;
		}
		$el.empty();
		new frappe.Chart($el[0], {
			data: {
				labels: data.map((d) => d.source || "Unknown"),
				datasets: [{ name: "Enquiries", values: data.map((d) => d.count) }],
			},
			type: "pie",
			height: 280,
			colors: ["#4F46E5", "#16A34A", "#D97706", "#DC2626", "#6B7280", "#8B5CF6"],
		});
	}

	/* ── Panel Renderers ───────────────────────────────────────────── */

	_render_panel_payments(data) {
		const $el = this.$body.find('[data-ref="panel-payments"]');
		if (!data || !data.length) {
			$el.html(this._empty_state("check", "No recent payments"));
			return;
		}
		const modeColor = { Cash: "green", UPI: "accent", Bank: "accent", Card: "amber" };
		let html = "";
		data.forEach((p) => {
			html += `
				<div class="bb-list-item" onclick="frappe.set_route('Form','Fees Payment Entry','${p.name}')">
					<div class="bb-list-item__body">
						<div class="bb-list-item__title">${frappe.utils.escape_html(p.student_name)}</div>
						<div class="bb-list-item__sub">
							${p.payment_date}
							<span class="bb-badge bb-badge--${modeColor[p.payment_mode] || "accent"}">${p.payment_mode}</span>
						</div>
					</div>
					<div class="bb-list-item__end">${this._fmt_inr(p.amount)}</div>
				</div>`;
		});
		$el.html(html);
	}

	_render_panel_birthdays(data) {
		const $el = this.$body.find('[data-ref="panel-birthdays"]');
		if (!data || !data.length) {
			$el.html(this._empty_state("check", "No birthdays today"));
			return;
		}
		let html = "";
		data.forEach((s) => {
			html += `
				<div class="bb-list-item" onclick="frappe.set_route('Form','Student','${s.name}')">
					<div class="bb-list-item__avatar">${frappe.utils.escape_html(s.student_name.charAt(0))}</div>
					<div class="bb-list-item__body">
						<div class="bb-list-item__title">${frappe.utils.escape_html(s.student_name)}</div>
						<div class="bb-list-item__sub">${s.standard || ""} ${s.current_batch ? "· " + s.current_batch : ""}</div>
					</div>
				</div>`;
		});
		$el.html(html);
	}

	_render_panel_followups(data) {
		const $el = this.$body.find('[data-ref="panel-followups"]');
		if (!data || !data.length) {
			$el.html(this._empty_state("check", "All caught up"));
			return;
		}
		const today = frappe.datetime.get_today();
		let html = "";
		data.forEach((e) => {
			const overdue = e.next_follow_up_date < today;
			html += `
				<div class="bb-list-item ${overdue ? "bb-list-item--alert" : ""}"
				     onclick="frappe.set_route('Form','Student Enquiry Form','${e.name}')">
					<div class="bb-list-item__body">
						<div class="bb-list-item__title">${frappe.utils.escape_html(e.applicant_name)}</div>
						<div class="bb-list-item__sub">
							${e.parent_mobile || ""}
							${e.standard ? " · " + e.standard : ""}
							${overdue ? ' <span class="bb-badge bb-badge--red">OVERDUE</span>' : ""}
						</div>
					</div>
					<div class="bb-list-item__end">${e.next_follow_up_date}</div>
				</div>`;
		});
		$el.html(html);
	}

	_render_panel_overdue(data) {
		const $el = this.$body.find('[data-ref="panel-overdue"]');
		if (!data || !data.length) {
			$el.html(this._empty_state("check", "All invoices on track"));
			return;
		}
		let html = "";
		data.forEach((inv) => {
			html += `
				<div class="bb-list-item bb-list-item--alert"
				     onclick="frappe.set_route('Form','Fee Invoice','${inv.name}')">
					<div class="bb-list-item__body">
						<div class="bb-list-item__title">${frappe.utils.escape_html(inv.student_name)}</div>
						<div class="bb-list-item__sub">${inv.fee_month || ""} · Due: ${inv.due_date}</div>
					</div>
					<div class="bb-list-item__end bb-list-item__end--danger">${this._fmt_inr(inv.outstanding_amount)}</div>
				</div>`;
		});
		$el.html(html);
	}

	/* ── Empty state helper ────────────────────────────────────────── */

	_empty_state(iconName, text) {
		return `
			<div class="bb-empty">
				<div class="bb-empty__icon">${icon(iconName)}</div>
				<div class="bb-empty__text">${text}</div>
			</div>`;
	}
}
