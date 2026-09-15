// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

const SWR_COLORS = {
	boys: "#3b82f6",
	girls: "#ec4899",
	total: "#6366f1",
	active: "#22c55e",
	completed: "#0ea5e9",
	discontinued: "#ef4444",
	suspended: "#f59e0b",
	palette: [
		"#6366f1", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444", "#ec4899",
		"#8b5cf6", "#14b8a6", "#84cc16", "#f97316", "#e11d48", "#0ea5e9",
	],
};

frappe.query_reports["Student Wise Report"] = {
	"filters": [
		{
			"fieldname": "standard",
			"label": __("Standard"),
			"fieldtype": "Link",
			"options": "Standard"
		},
		{
			"fieldname": "current_batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch"
		},
		{
			"fieldname": "academic_year",
			"label": __("Academic Year"),
			"fieldtype": "Link",
			"options": "Academic Year"
		},
		{
			"fieldname": "gender",
			"label": __("Gender"),
			"fieldtype": "Select",
			"options": "\nBoys\nGirls"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nActive\nCompleted\nDiscontinued\nSuspended"
		}
	],

	onload: function (report) {
		swr_inject_styles();

		// The datatable hook does not fire when a filter returns no rows,
		// so clear the dashboard alongside the "nothing to show" message.
		if (!report.__swr_patched) {
			report.__swr_patched = true;
			const original = report.toggle_nothing_to_show.bind(report);
			report.toggle_nothing_to_show = function (flag) {
				if (flag) swr_clear_dashboard();
				return original(flag);
			};
		}
	},

	after_datatable_render: function () {
		swr_render_dashboard(frappe.query_report);
	}
};

function swr_get_wrapper(report) {
	let $wrapper = report.page.main.find(".swr-dashboard");
	if (!$wrapper.length) {
		$wrapper = $('<div class="swr-dashboard"></div>').insertBefore(report.$report);
	}
	return $wrapper;
}

function swr_clear_dashboard() {
	$(".swr-dashboard").empty().hide();
}

function swr_render_dashboard(report) {
	swr_inject_styles();
	const rows = (report && report.data) || [];
	const $wrapper = swr_get_wrapper(report);
	$wrapper.empty();

	if (!rows.length) {
		$wrapper.hide();
		return;
	}
	$wrapper.show();

	const stats = swr_build_stats(rows);

	$wrapper.append(swr_summary_html(stats));
	const $grid = $('<div class="swr-grid"></div>').appendTo($wrapper);

	swr_stacked_chart($grid, __("Students by Standard"), __("Boys vs Girls in each standard"), stats.by_standard);
	swr_donut_chart($grid, __("Gender Split"), __("Share of boys and girls"), [
		{ label: __("Boys"), value: stats.boys, color: SWR_COLORS.boys },
		{ label: __("Girls"), value: stats.girls, color: SWR_COLORS.girls },
		{ label: __("Not Set"), value: stats.gender_not_set, color: "#94a3b8" },
	]);
	swr_donut_chart($grid, __("Status Split"), __("Where students stand today"), [
		{ label: __("Active"), value: stats.status.Active || 0, color: SWR_COLORS.active },
		{ label: __("Completed"), value: stats.status.Completed || 0, color: SWR_COLORS.completed },
		{ label: __("Discontinued"), value: stats.status.Discontinued || 0, color: SWR_COLORS.discontinued },
		{ label: __("Suspended"), value: stats.status.Suspended || 0, color: SWR_COLORS.suspended },
	]);
	swr_batch_strength_chart($grid, stats);
	swr_discontinued_chart($grid, __("Discontinued by Standard"), __("Standard"), stats.discontinued_by_standard);
	swr_discontinued_chart($grid, __("Discontinued by Batch"), __("Batch"), stats.discontinued_by_batch);
	swr_breakdown_table($grid, stats);
}

function swr_build_stats(rows) {
	const NOT_SET = __("Not Set");
	const stats = {
		total: rows.length,
		boys: 0,
		girls: 0,
		gender_not_set: 0,
		status: {},
		by_standard: {},
		by_batch: {},
		discontinued_by_standard: {},
		discontinued_by_batch: {},
		by_standard_batch: {},
	};

	const bucket = (map, key) => {
		if (!map[key]) map[key] = { total: 0, boys: 0, girls: 0, other: 0, discontinued: 0 };
		return map[key];
	};

	rows.forEach((row) => {
		const gender = row.gender || "";
		const status = row.status || NOT_SET;
		const standard = row.standard || NOT_SET;
		const batch = row.current_batch || NOT_SET;

		if (gender === "Boys") stats.boys++;
		else if (gender === "Girls") stats.girls++;
		else stats.gender_not_set++;

		stats.status[status] = (stats.status[status] || 0) + 1;

		if (!stats.by_standard_batch[standard]) stats.by_standard_batch[standard] = {};

		const buckets = [
			bucket(stats.by_standard, standard),
			bucket(stats.by_batch, batch),
			bucket(stats.by_standard_batch[standard], batch),
		];
		buckets.forEach((b) => {
			b.total++;
			if (gender === "Boys") b.boys++;
			else if (gender === "Girls") b.girls++;
			else b.other++;
			if (status === "Discontinued") b.discontinued++;
		});

		if (status === "Discontinued") {
			stats.discontinued_by_standard[standard] = (stats.discontinued_by_standard[standard] || 0) + 1;
			stats.discontinued_by_batch[batch] = (stats.discontinued_by_batch[batch] || 0) + 1;
		}
	});

	return stats;
}

function swr_sorted_keys(map) {
	return Object.keys(map).sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }));
}

function swr_summary_html(stats) {
	const discontinued = stats.status.Discontinued || 0;
	const pct = (n) => (stats.total ? Math.round((n / stats.total) * 100) : 0);

	const cards = [
		{ label: __("Total Students"), value: stats.total, sub: __("matching current filters"), color: SWR_COLORS.total, icon: "🎓" },
		{ label: __("Boys"), value: stats.boys, sub: `${pct(stats.boys)}% ${__("of total")}`, color: SWR_COLORS.boys, icon: "👦" },
		{ label: __("Girls"), value: stats.girls, sub: `${pct(stats.girls)}% ${__("of total")}`, color: SWR_COLORS.girls, icon: "👧" },
		{ label: __("Standards"), value: Object.keys(stats.by_standard).length, sub: __("distinct standards"), color: "#8b5cf6", icon: "📚" },
		{ label: __("Batches"), value: Object.keys(stats.by_batch).length, sub: __("distinct batches"), color: "#14b8a6", icon: "🗂️" },
		{ label: __("Active"), value: stats.status.Active || 0, sub: `${pct(stats.status.Active || 0)}% ${__("of total")}`, color: SWR_COLORS.active, icon: "✅" },
		{ label: __("Discontinued"), value: discontinued, sub: `${pct(discontinued)}% ${__("of total")}`, color: SWR_COLORS.discontinued, icon: "⚠️" },
	];

	const html = cards.map((c) => `
		<div class="swr-card" style="--swr-accent: ${c.color}">
			<div class="swr-card-icon">${c.icon}</div>
			<div class="swr-card-body">
				<div class="swr-card-label">${frappe.utils.escape_html(c.label)}</div>
				<div class="swr-card-value">${frappe.utils.escape_html(String(c.value))}</div>
				<div class="swr-card-sub">${frappe.utils.escape_html(c.sub)}</div>
			</div>
		</div>
	`).join("");

	return `<div class="swr-cards">${html}</div>`;
}

function swr_chart_card($grid, title, subtitle, label_count) {
	const $card = $(`
		<div class="swr-chart-card">
			<div class="swr-chart-head">
				<div class="swr-chart-title">${frappe.utils.escape_html(title)}</div>
				<div class="swr-chart-sub">${frappe.utils.escape_html(subtitle || "")}</div>
			</div>
			<div class="swr-chart-scroll"><div class="swr-chart-inner"></div></div>
		</div>
	`).appendTo($grid);

	// Keep bars readable: scroll horizontally instead of squeezing many labels.
	if (label_count > 8) {
		$card.find(".swr-chart-inner").css("min-width", `${label_count * 68}px`);
	}
	return $card.find(".swr-chart-inner")[0];
}

function swr_empty_card($grid, title, message) {
	$grid.append(`
		<div class="swr-chart-card">
			<div class="swr-chart-head">
				<div class="swr-chart-title">${frappe.utils.escape_html(title)}</div>
			</div>
			<div class="swr-chart-empty">${frappe.utils.escape_html(message)}</div>
		</div>
	`);
}

function swr_stacked_chart($grid, title, subtitle, map) {
	const labels = swr_sorted_keys(map);
	if (!labels.length) return swr_empty_card($grid, title, __("No data"));

	const el = swr_chart_card($grid, title, subtitle, labels.length);
	const datasets = [
		{ name: __("Boys"), values: labels.map((l) => map[l].boys), chartType: "bar" },
		{ name: __("Girls"), values: labels.map((l) => map[l].girls), chartType: "bar" },
	];
	if (labels.some((l) => map[l].other)) {
		datasets.push({ name: __("Not Set"), values: labels.map((l) => map[l].other), chartType: "bar" });
	}

	new frappe.Chart(el, {
		data: { labels: labels, datasets: datasets },
		type: "bar",
		height: 240,
		colors: [SWR_COLORS.boys, SWR_COLORS.girls, "#94a3b8"],
		barOptions: { stacked: 1, spaceRatio: 0.4 },
		axisOptions: { xAxisMode: "tick", xIsSeries: 0 },
		tooltipOptions: {
			formatTooltipY: (d) => `${d} ${d === 1 ? __("student") : __("students")}`,
		},
	});
}

function swr_donut_chart($grid, title, subtitle, entries) {
	const visible = entries.filter((e) => e.value > 0);
	if (!visible.length) return swr_empty_card($grid, title, __("No data"));

	const total = visible.reduce((sum, e) => sum + e.value, 0);
	const el = swr_chart_card($grid, title, subtitle, 0);

	new frappe.Chart(el, {
		data: {
			labels: visible.map((e) => `${e.label} (${e.value} · ${Math.round((e.value / total) * 100)}%)`),
			datasets: [{ values: visible.map((e) => e.value) }],
		},
		type: "donut",
		height: 240,
		colors: visible.map((e) => e.color),
		maxSlices: visible.length,
		tooltipOptions: {
			formatTooltipY: (d) => `${d} ${d === 1 ? __("student") : __("students")}`,
		},
	});
}

function swr_batch_strength_chart($grid, stats) {
	// One entry per Standard + Batch pair, e.g. "10 - Batch 2".
	const entries = [];
	swr_sorted_keys(stats.by_standard_batch).forEach((standard) => {
		swr_sorted_keys(stats.by_standard_batch[standard]).forEach((batch) => {
			const b = stats.by_standard_batch[standard][batch];
			entries.push({ label: `${standard} - ${batch}`, standard: standard, batch: batch, counts: b });
		});
	});

	if (!entries.length) return swr_empty_card($grid, __("Batch Strength"), __("No data"));

	const $card = $(`
		<div class="swr-chart-card swr-wide-card">
			<div class="swr-chart-head">
				<div class="swr-chart-title">${__("Batch Strength by Standard")}</div>
				<div class="swr-chart-sub">${__("Strength of every batch, split into boys and girls")}</div>
			</div>
			<div class="swr-chart-scroll"><div class="swr-chart-inner"></div></div>
			<div class="swr-strength-list"></div>
		</div>
	`).appendTo($grid);

	const $inner = $card.find(".swr-chart-inner");
	if (entries.length > 8) {
		$inner.css("min-width", `${entries.length * 84}px`);
	}

	const datasets = [
		{ name: __("Boys"), values: entries.map((e) => e.counts.boys) },
		{ name: __("Girls"), values: entries.map((e) => e.counts.girls) },
	];
	if (entries.some((e) => e.counts.other)) {
		datasets.push({ name: __("Not Set"), values: entries.map((e) => e.counts.other) });
	}

	new frappe.Chart($inner[0], {
		data: { labels: entries.map((e) => e.label), datasets: datasets },
		type: "bar",
		height: 250,
		colors: [SWR_COLORS.boys, SWR_COLORS.girls, "#94a3b8"],
		barOptions: { stacked: 1, spaceRatio: 0.4 },
		axisOptions: { xAxisMode: "tick", xIsSeries: 0 },
		tooltipOptions: {
			formatTooltipY: (d) => `${d} ${d === 1 ? __("student") : __("students")}`,
		},
	});

	// Spelled-out strength per batch, so no hovering is needed.
	const rows = entries.map((e) => {
		const c = e.counts;
		return `
			<div class="swr-strength-row">
				<span class="swr-strength-name">
					<b>${frappe.utils.escape_html(e.standard)}</b>
					<span class="swr-strength-sep">/</span>
					${frappe.utils.escape_html(e.batch)}
				</span>
				<span class="swr-strength-total">${c.total} ${c.total === 1 ? __("student") : __("students")}</span>
				<span class="swr-pill swr-pill-boys">${c.boys} ${__("Boys")}</span>
				<span class="swr-pill swr-pill-girls">${c.girls} ${__("Girls")}</span>
				${c.other ? `<span class="swr-pill swr-pill-muted">${c.other} ${__("Not Set")}</span>` : ""}
				${c.discontinued ? `<span class="swr-pill swr-pill-drop">${c.discontinued} ${__("Discontinued")}</span>` : ""}
			</div>
		`;
	}).join("");

	$card.find(".swr-strength-list").html(rows);
}

function swr_discontinued_chart($grid, title, group_label, map) {
	const labels = swr_sorted_keys(map);
	const total = labels.reduce((sum, l) => sum + map[l], 0);

	if (!total) {
		return swr_empty_card($grid, title, __("No discontinued students for the current filters"));
	}

	const $card = $(`
		<div class="swr-chart-card">
			<div class="swr-chart-head">
				<div class="swr-chart-title">${frappe.utils.escape_html(title)}</div>
				<div class="swr-chart-sub swr-chart-sub-strong">
					${total} ${total === 1 ? __("student discontinued") : __("students discontinued")}
				</div>
			</div>
			<div class="swr-chart-scroll"><div class="swr-chart-inner"></div></div>
			<div class="swr-count-list"></div>
		</div>
	`).appendTo($grid);

	const $inner = $card.find(".swr-chart-inner");
	if (labels.length > 8) {
		$inner.css("min-width", `${labels.length * 68}px`);
	}

	new frappe.Chart($inner[0], {
		data: {
			labels: labels,
			datasets: [{ name: __("Discontinued"), values: labels.map((l) => map[l]) }],
		},
		type: "bar",
		height: 220,
		colors: [SWR_COLORS.discontinued],
		barOptions: { spaceRatio: 0.5 },
		valuesOverPoints: 1,
		axisOptions: { xAxisMode: "tick", xIsSeries: 0 },
		tooltipOptions: {
			formatTooltipY: (d) => `${d} ${d === 1 ? __("student") : __("students")}`,
		},
	});

	// Plain ranked counts, so the numbers can be read without hovering the chart.
	const ranked = labels.slice().sort((a, b) => map[b] - map[a]);
	const max = map[ranked[0]];
	const rows = ranked.map((l) => `
		<div class="swr-count-row">
			<span class="swr-count-name" title="${frappe.utils.escape_html(l)}">${frappe.utils.escape_html(l)}</span>
			<span class="swr-count-track"><span class="swr-count-fill" style="width: ${Math.round((map[l] / max) * 100)}%"></span></span>
			<span class="swr-count-value">${map[l]}</span>
		</div>
	`).join("");

	$card.find(".swr-count-list").html(`
		<div class="swr-count-head">
			<span>${frappe.utils.escape_html(group_label)}</span>
			<span>${__("Discontinued")}</span>
		</div>
		${rows}
	`);
}

function swr_breakdown_table($grid, stats) {
	const standards = swr_sorted_keys(stats.by_standard_batch);
	if (!standards.length) return;

	const cell = (b) => `
		<td class="swr-num swr-strong">${b.total}</td>
		<td class="swr-num swr-boys">${b.boys}</td>
		<td class="swr-num swr-girls">${b.girls}</td>
		<td class="swr-num ${b.discontinued ? "swr-drop" : "swr-zero"}">${b.discontinued}</td>
	`;

	const body = standards.map((standard) => {
		const batches = swr_sorted_keys(stats.by_standard_batch[standard]);
		const std_total = stats.by_standard[standard];

		const group_head = `
			<tr class="swr-bd-group">
				<td colspan="2">${frappe.utils.escape_html(standard)}
					<span class="swr-bd-count">${batches.length} ${batches.length === 1 ? __("batch") : __("batches")}</span>
				</td>
				${cell(std_total)}
			</tr>
		`;

		const batch_rows = batches.map((batch) => {
			const b = stats.by_standard_batch[standard][batch];
			return `
				<tr>
					<td class="swr-bd-indent"></td>
					<td class="swr-bd-batch">${frappe.utils.escape_html(batch)}</td>
					${cell(b)}
				</tr>
			`;
		}).join("");

		return group_head + batch_rows;
	}).join("");

	const grand = {
		total: stats.total,
		boys: stats.boys,
		girls: stats.girls,
		discontinued: stats.status.Discontinued || 0,
	};

	$grid.append(`
		<div class="swr-chart-card swr-bd-card">
			<div class="swr-chart-head">
				<div class="swr-chart-title">${__("Breakdown by Standard and Batch")}</div>
				<div class="swr-chart-sub">${__("How many students sit in each batch of each standard")}</div>
			</div>
			<div class="swr-bd-scroll">
				<table class="swr-bd-table">
					<thead>
						<tr>
							<th colspan="2">${__("Standard / Batch")}</th>
							<th class="swr-num">${__("Students")}</th>
							<th class="swr-num">${__("Boys")}</th>
							<th class="swr-num">${__("Girls")}</th>
							<th class="swr-num">${__("Discontinued")}</th>
						</tr>
					</thead>
					<tbody>${body}</tbody>
					<tfoot>
						<tr>
							<td colspan="2">${__("Total")}</td>
							${cell(grand)}
						</tr>
					</tfoot>
				</table>
			</div>
		</div>
	`);
}

function swr_inject_styles() {
	if (document.getElementById("swr-dashboard-styles")) return;

	const style = document.createElement("style");
	style.id = "swr-dashboard-styles";
	style.textContent = `
		.swr-dashboard { margin: 0 0 18px 0; }
		.swr-cards {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
			gap: 12px;
			margin-bottom: 16px;
		}
		.swr-card {
			display: flex;
			align-items: center;
			gap: 10px;
			padding: 12px 14px;
			border-radius: 10px;
			background: var(--card-bg, var(--fg-color, #fff));
			border: 1px solid var(--border-color, #e5e7eb);
			border-left: 4px solid var(--swr-accent);
			box-shadow: var(--card-shadow, none);
		}
		.swr-card-icon { font-size: 20px; line-height: 1; }
		.swr-card-body { min-width: 0; }
		.swr-card-label {
			font-size: 11px;
			font-weight: 600;
			letter-spacing: .04em;
			text-transform: uppercase;
			color: var(--text-muted, #6b7280);
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}
		.swr-card-value {
			font-size: 24px;
			font-weight: 700;
			line-height: 1.2;
			color: var(--swr-accent);
		}
		.swr-card-sub { font-size: 11px; color: var(--text-muted, #6b7280); }

		.swr-grid {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
			gap: 12px;
		}
		.swr-chart-card {
			background: var(--card-bg, var(--fg-color, #fff));
			border: 1px solid var(--border-color, #e5e7eb);
			border-radius: 10px;
			padding: 12px 14px 4px;
			overflow: hidden;
		}
		.swr-chart-head { margin-bottom: 2px; }
		.swr-chart-title { font-size: 13px; font-weight: 600; color: var(--text-color, #1f272e); }
		.swr-chart-sub { font-size: 11px; color: var(--text-muted, #6b7280); }
		.swr-chart-scroll { overflow-x: auto; overflow-y: hidden; }
		.swr-chart-empty {
			padding: 48px 0;
			text-align: center;
			font-size: 12px;
			color: var(--text-muted, #6b7280);
		}
		.swr-chart-card .chart-container { margin-bottom: 0; }

		.swr-chart-sub-strong { font-weight: 600; color: var(--text-color, #1f272e); }
		.swr-count-list {
			border-top: 1px solid var(--border-color, #e5e7eb);
			margin-top: 6px;
			padding: 8px 0 10px;
			max-height: 170px;
			overflow-y: auto;
		}
		.swr-count-head {
			display: flex;
			justify-content: space-between;
			font-size: 10px;
			font-weight: 600;
			letter-spacing: .05em;
			text-transform: uppercase;
			color: var(--text-muted, #6b7280);
			margin-bottom: 6px;
		}
		.swr-count-row {
			display: flex;
			align-items: center;
			gap: 8px;
			padding: 3px 0;
			font-size: 12px;
		}
		.swr-count-name {
			flex: 0 0 34%;
			color: var(--text-color, #1f272e);
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}
		.swr-count-track {
			flex: 1 1 auto;
			height: 8px;
			border-radius: 4px;
			background: var(--control-bg, #f1f5f9);
			overflow: hidden;
		}
		.swr-count-fill {
			display: block;
			height: 100%;
			border-radius: 4px;
			background: #ef4444;
		}
		.swr-count-value {
			flex: 0 0 34px;
			text-align: right;
			font-weight: 700;
			color: #ef4444;
		}

		.swr-wide-card { grid-column: 1 / -1; }
		.swr-strength-list {
			border-top: 1px solid var(--border-color, #e5e7eb);
			margin-top: 6px;
			padding: 8px 0 4px;
			max-height: 220px;
			overflow-y: auto;
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(330px, 1fr));
			gap: 2px 18px;
		}
		.swr-strength-row {
			display: flex;
			align-items: center;
			gap: 6px;
			flex-wrap: wrap;
			padding: 4px 0;
			font-size: 12px;
		}
		.swr-strength-name {
			flex: 0 0 auto;
			min-width: 110px;
			color: var(--text-color, #1f272e);
		}
		.swr-strength-sep { color: var(--text-muted, #9ca3af); margin: 0 2px; }
		.swr-strength-total {
			flex: 0 0 auto;
			font-weight: 700;
			color: var(--text-color, #1f272e);
			margin-right: 2px;
		}
		.swr-pill {
			display: inline-block;
			padding: 1px 7px;
			border-radius: 10px;
			font-size: 11px;
			font-weight: 600;
			white-space: nowrap;
		}
		.swr-pill-boys { background: rgba(59, 130, 246, .13); color: #2563eb; }
		.swr-pill-girls { background: rgba(236, 72, 153, .13); color: #db2777; }
		.swr-pill-muted { background: rgba(148, 163, 184, .18); color: #64748b; }
		.swr-pill-drop { background: rgba(239, 68, 68, .13); color: #dc2626; }

		.swr-bd-card { grid-column: 1 / -1; padding-bottom: 12px; }
		.swr-bd-scroll { max-height: 360px; overflow: auto; margin-top: 8px; }
		.swr-bd-table { width: 100%; border-collapse: collapse; font-size: 12px; }
		.swr-bd-table th {
			position: sticky;
			top: 0;
			z-index: 1;
			background: var(--card-bg, var(--fg-color, #fff));
			text-align: left;
			font-size: 10px;
			font-weight: 600;
			letter-spacing: .05em;
			text-transform: uppercase;
			color: var(--text-muted, #6b7280);
			padding: 6px 8px;
			border-bottom: 1px solid var(--border-color, #e5e7eb);
		}
		.swr-bd-table td {
			padding: 5px 8px;
			border-bottom: 1px solid var(--border-color, #e5e7eb);
			color: var(--text-color, #1f272e);
		}
		.swr-bd-table tr.swr-bd-group td {
			background: var(--control-bg, #f8fafc);
			font-weight: 600;
		}
		.swr-bd-count {
			margin-left: 6px;
			font-size: 10px;
			font-weight: 500;
			color: var(--text-muted, #6b7280);
		}
		.swr-bd-indent { width: 18px; }
		.swr-bd-batch { color: var(--text-muted, #6b7280); }
		.swr-bd-table .swr-num { text-align: right; width: 84px; white-space: nowrap; }
		.swr-bd-table .swr-strong { font-weight: 700; }
		.swr-bd-table .swr-boys { color: #3b82f6; }
		.swr-bd-table .swr-girls { color: #ec4899; }
		.swr-bd-table .swr-drop { color: #ef4444; font-weight: 700; }
		.swr-bd-table .swr-zero { color: var(--text-muted, #9ca3af); }
		.swr-bd-table tfoot td {
			border-top: 2px solid var(--border-color, #e5e7eb);
			border-bottom: none;
			font-weight: 700;
			background: var(--card-bg, var(--fg-color, #fff));
		}
	`;
	document.head.appendChild(style);
}
