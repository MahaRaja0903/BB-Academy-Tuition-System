// Copyright (c) 2026, BB Academy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Invoice", {
	setup(frm) {
		frm.set_query("standard", function() {
			return {
				order_by: "academic_order asc"
			};
		});
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.trigger("status");
		}
		// Render student fee tracking on refresh if student is set
		if (frm.doc.student) {
			frm.trigger("render_fee_tracking");
		}
	},
	student(frm) {
		if (frm.doc.student) {
			frappe.db.get_value(
				"Student",
				frm.doc.student,
				["standard", "current_batch", "monthly_fee", "starting_payment", "fees_due_date"],
				(r) => {
					if (r) {

						
						let currentDate = new Date();
						let monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
						let currentMonth = monthNames[currentDate.getMonth()];

						if (r.fees_due_date) {
							let year = currentDate.getFullYear();
							let month = ("0" + (currentDate.getMonth() + 1)).slice(-2);
							let day = ("0" + r.fees_due_date).slice(-2);
							frm.set_value("due_date", `${year}-${month}-${day}`);
						}

						if (frm.doc.is_starting_fee) {
							frm.set_value("monthly_fee", r.starting_payment || 0);
						} else {
							frm.set_value("monthly_fee", r.monthly_fee || 0);
						}
					}
				}
			);
			// Render fee tracking UI
			frm.trigger("render_fee_tracking");
		}
	},
	is_starting_fee(frm) {
		if (frm.doc.student && frm.doc.student_detail_json) {
			let data = JSON.parse(frm.doc.student_detail_json);
			if (frm.doc.is_starting_fee) {
				frm.set_value("monthly_fee", data.starting_payment || 0);
			} else {
				frm.set_value("monthly_fee", data.monthly_fee || 0);
			}
		} else if (frm.doc.student) {
			frm.trigger("student");
		}
		
		if (frm.doc.is_starting_fee) {
			let existing = frm.doc.fees_details || [];
			let exists = existing.some(d => d.month === "Starting Payment");
			if (!exists) {
				let row = frm.add_child("fees_details");
				row.month = "Starting Payment";
				
				if (frm.doc.student_detail_json) {
					let data = JSON.parse(frm.doc.student_detail_json);
					let s_row = (data.payment_details || []).find(r => r.month === "Starting Payment");
					row.paid_amount = s_row ? s_row.pending : (data.starting_payment || 0);
				}
				frm.refresh_field("fees_details");
			}
		} else {
			let existing = frm.doc.fees_details || [];
			let new_details = existing.filter(d => d.month !== "Starting Payment");
			if (new_details.length !== existing.length) {
				frm.doc.fees_details = new_details;
				frm.refresh_field("fees_details");
			}
		}
	},
	render_fee_tracking(frm) {
		if (!frm.doc.student) {
			frm.fields_dict.student_html.$wrapper.html("");
			return;
		}
		frappe.call({
			method: "bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice.get_student_fee_data",
			args: { student: frm.doc.student },
			callback: function(r) {
				if (r.message) {
					let data = r.message;
					// Store as JSON
					if (frm.doc.docstatus === 0){
						frm.set_value("student_detail_json", JSON.stringify(data));
					}
					
					// Auto check is_starting_fee if not paid or pending
					if (frm.doc.docstatus === 0 && !frm.doc.is_starting_fee) {
						let starting_row = (data.payment_details || []).find(row => row.month === "Starting Payment");
						let should_check = false;
						
						if (!starting_row && (data.starting_payment || 0) > 0) {
							should_check = true;
						} else if (starting_row && starting_row.pending > 0) {
							should_check = true;
						}

						if (should_check) {
							frm.set_value("is_starting_fee", 1);
						}
					}
					
					// Build and render HTML
					let student_html = build_student_details_html(data);
					let fees_paid_html = build_fees_paid_details_html(data);
					
					frm.fields_dict.student_html.$wrapper.html(student_html);
					if (frm.fields_dict.fees_paid_details_html) {
						frm.fields_dict.fees_paid_details_html.$wrapper.html(fees_paid_html);
					}
				}
			}
		});
	},
	monthly_fee: function(frm) {
		calculate_totals(frm);
	},
	add_discount: function(frm) {
		if (!frm.doc.add_discount) {
			frm.set_value('discount_amount', 0);
		}
		calculate_totals(frm);
	},
	discount_amount: function(frm) {
		calculate_totals(frm);
	},
	apply_gst_18: function(frm) {
		calculate_totals(frm);
	}
});

function calculate_totals(frm) {
	let monthly_fee = frm.doc.monthly_fee || 0;
	let discount = frm.doc.add_discount ? (frm.doc.discount_amount || 0) : 0;
	
	let net_total = monthly_fee - discount;
	let gst_amount = 0;
	
	if (frm.doc.apply_gst_18) {
		gst_amount = net_total * 0.18;
	}
	
	frm.set_value('gst_amount', gst_amount);
	
	let grand_total = net_total + gst_amount;
	frm.set_value('grand_total', grand_total);
}

function get_shared_styles() {
	return `
<style>
	.sft-container {
		font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: #333;
		padding: 24px 0;
	}

	/* Student Card */
	.sft-student-card {
		display: flex;
		align-items: center;
		background: #ffffff;
		border-radius: 16px;
		padding: 24px;
		box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
		border: 1px solid #f3f4f6;
		margin-bottom: 24px;
		gap: 24px;
	}
	.sft-student-img {
		width: 90px;
		height: 90px;
		border-radius: 50%;
		object-fit: cover;
		background-color: #e5e7eb;
		border: 4px solid #f3f4f6;
		flex-shrink: 0;
	}
	.sft-student-info { flex: 1; }
	.sft-student-name {
		font-size: 22px;
		font-weight: 700;
		color: #111827;
		margin: 0 0 10px 0;
	}
	.sft-student-meta {
		display: flex;
		gap: 24px;
		flex-wrap: wrap;
	}
	.sft-meta-item { display: flex; flex-direction: column; }
	.sft-meta-label {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #9ca3af;
		font-weight: 600;
		margin-bottom: 3px;
	}
	.sft-meta-value {
		font-size: 14px;
		color: #374151;
		font-weight: 600;
	}

	/* Summary + Legend Row */
	.sft-summary-row {
		display: flex;
		justify-content: space-between;
		align-items: stretch;
		margin-bottom: 24px;
		gap: 16px;
		flex-wrap: wrap;
	}
	.sft-summary-box { display: flex; gap: 12px; }
	.sft-stat-card {
		background: #fff;
		padding: 14px 22px;
		border-radius: 12px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
		border: 1px solid #e5e7eb;
		text-align: center;
		min-width: 100px;
	}
	.sft-stat-val {
		font-size: 22px;
		font-weight: 700;
	}
	.sft-stat-val.green { color: #10b981; }
	.sft-stat-val.red { color: #ef4444; }
	.sft-stat-val.orange { color: #f59e0b; }
	.sft-stat-label {
		font-size: 11px;
		color: #6b7280;
		font-weight: 600;
		text-transform: uppercase;
		margin-top: 2px;
	}
	.sft-legend {
		display: flex;
		gap: 14px;
		background: #fff;
		padding: 14px 20px;
		border-radius: 12px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
		border: 1px solid #e5e7eb;
		align-items: center;
		flex-wrap: wrap;
	}
	.sft-legend-item {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: #4b5563;
		font-weight: 500;
	}
	.sft-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
	.sft-dot-early { background-color: #10b981; }
	.sft-dot-mid { background-color: #f59e0b; }
	.sft-dot-late { background-color: #ef4444; }
	.sft-dot-unpaid { background-color: #fee2e2; border: 1px solid #f87171; }
	.sft-dot-notjoined { background-color: #d1d5db; }

	/* Grid */
	.sft-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
	}
	@media (max-width: 1100px) { .sft-grid { grid-template-columns: repeat(3, 1fr); } }
	@media (max-width: 768px) {
		.sft-grid { grid-template-columns: repeat(2, 1fr); }
		.sft-student-card { flex-direction: column; text-align: center; }
		.sft-student-meta { justify-content: center; }
	}
	@media (max-width: 480px) { .sft-grid { grid-template-columns: 1fr; } }

	/* Month Cards */
	.sft-month-card {
		background: #fff;
		border-radius: 14px;
		padding: 18px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.04);
		border: 1px solid #f3f4f6;
		transition: transform 0.2s ease, box-shadow 0.2s ease;
		position: relative;
		cursor: default;
	}
	.sft-month-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 8px 16px -4px rgba(0,0,0,0.1);
	}
	.sft-mc-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
	}
	.sft-mc-month { font-size: 18px; font-weight: 700; color: #1f2937; }
	.sft-mc-icon {
		width: 28px; height: 28px;
		border-radius: 50%;
		display: flex; align-items: center; justify-content: center;
		font-size: 13px;
	}
	.sft-mc-status {
		display: inline-block;
		padding: 3px 10px;
		border-radius: 20px;
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		margin-bottom: 10px;
	}
	.sft-mc-details {
		font-size: 12px;
		color: #6b7280;
		display: flex; flex-direction: column; gap: 3px;
	}
	.sft-mc-details span { display: flex; align-items: center; gap: 5px; }

	/* Card status classes */
	.card-notjoined { background-color: #f9fafb; border-color: #e5e7eb; }
	.card-notjoined .sft-mc-month { color: #9ca3af; }
	.card-notjoined .sft-mc-status { background: #f3f4f6; color: #6b7280; }
	.card-notjoined .sft-mc-icon { background: #d1d5db; color: #fff; }
	
	.card-notpaid { background-color: #fffbfb; border-color: #fecaca; }
	.card-notpaid .sft-mc-status { background: #fee2e2; color: #b91c1c; }
	.card-notpaid .sft-mc-icon { background: #ef4444; color: #fff; }

	.card-early .sft-mc-status { background: #d1fae5; color: #065f46; }
	.card-early .sft-mc-icon { background: #10b981; color: #fff; }

	.card-mid .sft-mc-status { background: #fef3c7; color: #92400e; }
	.card-mid .sft-mc-icon { background: #f59e0b; color: #fff; }

	.card-late .sft-mc-status { background: #fee2e2; color: #991b1b; }
	.card-late .sft-mc-icon { background: #ef4444; color: #fff; }

	.card-partial .sft-mc-status { background: #e0e7ff; color: #3730a3; }
	.card-partial .sft-mc-icon { background: #6366f1; color: #fff; }

	/* Tooltip */
	.sft-tooltip-text {
		visibility: hidden;
		width: max-content;
		background-color: #1f2937;
		color: #fff;
		text-align: center;
		border-radius: 6px;
		padding: 6px 12px;
		position: absolute;
		z-index: 1;
		bottom: calc(100% + 8px);
		left: 50%;
		transform: translateX(-50%);
		opacity: 0;
		transition: opacity 0.25s;
		font-size: 12px;
		font-weight: 500;
		white-space: nowrap;
		pointer-events: none;
	}
	.sft-tooltip-text::after {
		content: "";
		position: absolute;
		top: 100%;
		left: 50%;
		margin-left: -5px;
		border-width: 5px;
		border-style: solid;
		border-color: #1f2937 transparent transparent transparent;
	}
	.sft-month-card:hover .sft-tooltip-text {
		visibility: visible;
		opacity: 1;
	}
</style>`;
}

function build_student_details_html(data) {
	const MONTHS = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'];
	
	// Build payment lookup
	let payDict = {};
	(data.payment_details || []).forEach(row => {
		payDict[row.month] = row;
	});

	// Calculate admission academic index (April=0 ... March=11)
	let adAcIndex = 0;
	if (data.admission_date) {
		let adDate = new Date(data.admission_date);
		let m = adDate.getMonth() + 1; // 1-12
		adAcIndex = m >= 4 ? m - 4 : m + 8;
	}

	// Summary calculations
	let paid = 0, remaining = 0, late = 0;
	MONTHS.forEach((m, idx) => {
		let p = payDict[m];
		let status = 'Not Paid';
		if (p && p.status) {
			status = p.status;
		} else if (idx < adAcIndex) {
			status = 'Not Joined';
		}
		if (status === 'Paid') {
			paid++;
			if (p && p.date) {
				let d = new Date(p.date).getDate();
				if (d > 15) late++;
			}
		} else if (status === 'Not Paid' || status === 'Partial') {
			remaining++;
		}
	});

	let formatDate = (dateStr) => {
		if (!dateStr) return 'N/A';
		let d = new Date(dateStr);
		return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
	};

	let formatCurrency = (val) => {
		return '₹ ' + Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
	};

	let imgSrc = data.image || '/assets/frappe/images/default-avatar.png';

	let starting_row = payDict["Starting Payment"];
	let starting_paid = starting_row ? starting_row.amount_paid : 0;
	let starting_pending = starting_row ? starting_row.pending : (data.starting_payment || 0);

	let startingPaymentHtml = '';
	if (data.starting_payment > 0) {
		startingPaymentHtml = `
		<div style="margin-top: 16px; padding-top: 16px; border-top: 1px dashed #e5e7eb; display: flex; gap: 24px; flex-wrap: wrap;">
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Amount</span>
				<span class="sft-meta-value" style="color: #374151; font-size: 15px;">${formatCurrency(data.starting_payment)}</span>
			</div>
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Paid</span>
				<span class="sft-meta-value" style="color: #10b981; font-size: 15px;">${formatCurrency(starting_paid)}</span>
			</div>
			<div class="sft-meta-item">
				<span class="sft-meta-label" style="color: #6b7280;">Starting Pending</span>
				<span class="sft-meta-value" style="color: #ef4444; font-size: 15px;">${formatCurrency(starting_pending)}</span>
			</div>
		</div>`;
	}

	return `
${get_shared_styles()}
<div class="sft-container" style="padding-bottom: 0;">
	<!-- Student Card -->
	<div class="sft-student-card" style="margin-bottom: 24px;">
		<img src="${imgSrc}" alt="Student" class="sft-student-img" onerror="this.src='/assets/frappe/images/default-avatar.png'">
		<div class="sft-student-info">
			<h2 class="sft-student-name">${data.student_name || ''}</h2>
			<div class="sft-student-meta">
				<div class="sft-meta-item">
					<span class="sft-meta-label">Admission Date</span>
					<span class="sft-meta-value">${formatDate(data.admission_date)}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Standard</span>
					<span class="sft-meta-value">${data.standard || '-'}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Current Batch</span>
					<span class="sft-meta-value">${data.current_batch || '-'}</span>
				</div>
				<div class="sft-meta-item">
					<span class="sft-meta-label">Academic Year</span>
					<span class="sft-meta-value">${data.academic_year || 'Current'}</span>
				</div>
			</div>
			${startingPaymentHtml}
		</div>
	</div>

	<!-- Summary + Legend -->
	<div class="sft-summary-row" style="margin-bottom: 0;">
		<div class="sft-summary-box">
			<div class="sft-stat-card">
				<div class="sft-stat-val green">${paid}</div>
				<div class="sft-stat-label">Months Paid</div>
			</div>
			<div class="sft-stat-card">
				<div class="sft-stat-val red">${remaining}</div>
				<div class="sft-stat-label">Remaining</div>
			</div>
			<div class="sft-stat-card">
				<div class="sft-stat-val orange">${late}</div>
				<div class="sft-stat-label">Late Payments</div>
			</div>
		</div>
		<div class="sft-legend">
			<div class="sft-legend-item"><div class="sft-dot sft-dot-early"></div>Early (&lt;10th)</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-mid"></div>Mid (10–15)</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-late"></div>Late (&gt;15th)</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-unpaid"></div>Pending</div>
			<div class="sft-legend-item"><div class="sft-dot sft-dot-notjoined"></div>Not Joined</div>
		</div>
	</div>
</div>
`;
}

function build_fees_paid_details_html(data) {
	const MONTHS = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'];
	const SHORT = { April: 'Apr', May: 'May', June: 'Jun', July: 'Jul', August: 'Aug', September: 'Sep', October: 'Oct', November: 'Nov', December: 'Dec', January: 'Jan', February: 'Feb', March: 'Mar' };

	// Build payment lookup
	let payDict = {};
	(data.payment_details || []).forEach(row => {
		payDict[row.month] = row;
	});

	// Calculate admission academic index (April=0 ... March=11)
	let adAcIndex = 0;
	if (data.admission_date) {
		let adDate = new Date(data.admission_date);
		let m = adDate.getMonth() + 1; // 1-12
		adAcIndex = m >= 4 ? m - 4 : m + 8;
	}

	let formatDate = (dateStr) => {
		if (!dateStr) return 'N/A';
		let d = new Date(dateStr);
		return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
	};

	// Build month cards
	let monthCardsHtml = '';
	MONTHS.forEach((m, idx) => {
		let p = payDict[m];
		let status = 'Not Paid';
		let pdDate = null;
		let cardClass = 'card-notpaid';
		let icon = '⏳';

		if (p && p.status) {
			status = p.status;
			pdDate = p.date;
		} else if (idx < adAcIndex) {
			status = 'Not Joined';
		}

		if (status === 'Not Joined') {
			cardClass = 'card-notjoined';
			icon = '🚫';
		} else if (status === 'Paid') {
			icon = '✔';
			if (pdDate) {
				let d = new Date(pdDate).getDate();
				if (d < 10) cardClass = 'card-early';
				else if (d <= 15) cardClass = 'card-mid';
				else cardClass = 'card-late';
			} else {
				cardClass = 'card-early';
			}
		} else if (status === 'Partial') {
			cardClass = 'card-partial';
			icon = '◐';
		}

		let tooltipHtml = '';
		if (pdDate && (status === 'Paid' || status === 'Partial')) {
			tooltipHtml = `<div class="sft-tooltip-text">Paid on ${formatDate(pdDate)}</div>`;
		}

		let formatCurrency = (val) => {
			return '₹ ' + Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
		};

		let detailLines = '';
		if (status !== 'Not Joined') {
			detailLines += `<span>🏠 ${data.current_batch || '-'}</span>`;
		}
		if ((status === 'Paid' || status === 'Partial') && pdDate) {
			detailLines += `<span>📅 ${formatDate(pdDate)}</span>`;
		} else if (status === 'Not Paid') {
			detailLines += `<span>⚠️ Payment Pending</span>`;
		} else if (status === 'Not Joined') {
			detailLines += `<span>—</span>`;
		}
		if ((status === 'Paid' || status === 'Partial') && p) {
			detailLines += `<span>💰 ${formatCurrency(p.amount_paid)}</span>`;
		}

		monthCardsHtml += `
			<div class="sft-month-card ${cardClass}">
				${tooltipHtml}
				<div class="sft-mc-header">
					<div class="sft-mc-month">${SHORT[m]}</div>
					<div class="sft-mc-icon">${icon}</div>
				</div>
				<div class="sft-mc-status">${status}</div>
				<div class="sft-mc-details">${detailLines}</div>
			</div>
		`;
	});

	return `
${get_shared_styles()}
<div class="sft-container" style="padding-top: 0;">
	<!-- Month Grid -->
	<div class="sft-grid">
		${monthCardsHtml}
	</div>
</div>
`;
}

