/* ═══════════════════════════════════════════════════════════════════════
   BB Academy — Global Desk Script
   ───────────────────────────────────────────────────────────────────────
   Overrides the default routing behavior to force the custom dashboard
   as the primary home page, circumventing Frappe's Workspace-only logic.
   ═══════════════════════════════════════════════════════════════════════ */

// Ensure this runs after the router is initialized
$(document).on('ready', function() {
	if (!frappe.router) return;

	// 1. Force the logo link in the navbar to point to our dashboard
	// We bind to route change to ensure it stays overridden if Vue re-renders the navbar
	frappe.router.on('change', () => {
		const $brand = $('.navbar-brand');
		if ($brand.length) {
			$brand.attr('href', '/app/bb-dashboard');
		}
	});

	// Initial set
	setTimeout(() => {
		$('.navbar-brand').attr('href', '/app/bb-dashboard');
	}, 100);

	// 2. Intercept the router's "empty" path resolution
	// Frappe v14+ defaults `/app` to a workspace. We override make_url to point to our page.
	const original_make_url = frappe.router.make_url;
	frappe.router.make_url = function(params) {
		if (!params || params.length === 0 || params.join("") === "") {
			return "/app/bb-dashboard";
		}
		return original_make_url.apply(this, arguments);
	};
});

/* ═══════════════════════════════════════════════════════════════════════
   BB Academy — PWA Registration
   ═══════════════════════════════════════════════════════════════════════ */
$(document).on('ready', function() {
    // Inject Manifest Link
    if (!$("link[rel='manifest']").length) {
        $('<link>')
            .appendTo('head')
            .attr({
                type: 'application/manifest+json',
                rel: 'manifest',
                href: '/assets/bb_tution_management/manifest.json'
            });
    }

    // Inject Theme Color
    if (!$("meta[name='theme-color']").length) {
        $('<meta>')
            .appendTo('head')
            .attr({
                name: 'theme-color',
                content: '#FFD700'
            });
    }

    // Register Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/api/method/bb_tution_management.api.sw', { scope: '/' })
                .then(function(registration) {
                    console.log('BB Academy PWA SW registered with scope:', registration.scope);
                }, function(err) {
                    console.log('BB Academy PWA SW registration failed:', err);
                });
        });
    }
});

/* ═══════════════════════════════════════════════════════════════════════
   BB Academy — Edit Fees Amount
   ───────────────────────────────────────────────────────────────────────
   The same dialog is offered on the Student and on the Student Admission
   Form, so it lives here rather than in either form script. Only what
   happens on Update differs, and that step is handed in as `apply`: the
   Student writes straight to the saved record, while the Admission Form is
   still being filled in and only sets the value on the form.
   ═══════════════════════════════════════════════════════════════════════ */
frappe.provide("bb_academy");

// Labels are translated where they are used, not here -- this runs at load time.
bb_academy.EDITABLE_FEES = {
	starting_payment: {
		label: "Starting Amount",
		reason_field: "reason_for_discounting_starting_amount",
	},
	monthly_fee: {
		label: "Monthly Fees",
		reason_field: "reason_for_discounting_monthly_fees",
	},
};

bb_academy.show_edit_fees_dialog = function (frm, apply, on_hide) {
	const dialog = new frappe.ui.Dialog({
		title: __("Edit Fees Amount"),
		fields: [
			{
				fieldname: "fee_type",
				fieldtype: "Select",
				label: __("Which fee do you want to edit?"),
				reqd: 1,
				options: [
					{ value: "", label: "" },
					...Object.keys(bb_academy.EDITABLE_FEES).map((fee_type) => ({
						value: fee_type,
						label: __(bb_academy.EDITABLE_FEES[fee_type].label),
					})),
				],
				onchange: () => on_fee_type_selected(frm, dialog),
			},
			{
				fieldname: "current_amount",
				fieldtype: "Currency",
				label: __("Current Amount"),
				read_only: 1,
				depends_on: "fee_type",
			},
			{
				fieldname: "new_amount",
				fieldtype: "Currency",
				label: __("New Amount"),
				depends_on: "fee_type",
			},
			{ fieldtype: "Section Break", depends_on: "fee_type" },
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				depends_on: "fee_type",
				description: __("Recorded against the student along with the new amount."),
			},
		],
		primary_action_label: __("Update"),
		primary_action: (values) => {
			const config = bb_academy.EDITABLE_FEES[values.fee_type];

			const new_amount = flt(values.new_amount);
			if (new_amount < 0) {
				frappe.msgprint(__("Fees amount cannot be negative."));
				return;
			}

			const reason = (values.reason || "").trim();
			if (!reason) {
				frappe.msgprint(__("Please enter a reason for changing the {0}.", [__(config.label)]));
				return;
			}

			apply({
				dialog: dialog,
				fee_type: values.fee_type,
				config: config,
				new_amount: new_amount,
				reason: reason,
			});
		},
		on_hide: on_hide,
	});

	dialog.show();
};

// Show what the selected fee is currently set to, and pre-fill the reason
// already recorded against it (if any) so it can be reviewed or reworded.
function on_fee_type_selected(frm, dialog) {
	const fee_type = dialog.get_value("fee_type");
	if (!fee_type) {
		dialog.set_value("current_amount", 0);
		dialog.set_value("new_amount", 0);
		dialog.set_value("reason", "");
		return;
	}

	const config = bb_academy.EDITABLE_FEES[fee_type];
	const current_amount = frm.doc[fee_type] || 0;

	dialog.set_value("current_amount", current_amount);
	dialog.set_value("new_amount", current_amount);
	dialog.set_value("reason", frm.doc[config.reason_field] || "");
	dialog.set_df_property("new_amount", "label", __("New {0}", [__(config.label)]));
}

// The alert both forms show once the new amount has taken effect.
bb_academy.show_fee_change_alert = function (config, old_amount, new_amount) {
	const currency = frappe.defaults.get_default("currency");
	frappe.show_alert({
		message: __("{0} updated from {1} to {2}", [
			__(config.label),
			format_currency(old_amount, currency),
			format_currency(new_amount, currency),
		]),
		indicator: "green",
	});
};
