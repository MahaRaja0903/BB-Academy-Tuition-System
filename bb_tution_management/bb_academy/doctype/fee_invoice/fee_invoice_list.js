// No Fee invoices (an emergency waiver) stand out in the list; everything else
// keeps the standard Draft / Submitted / Cancelled indicator.
frappe.listview_settings["Fee Invoice"] = {
	add_fields: ["no_fee", "docstatus"],
	get_indicator(doc) {
		if (doc.no_fee && doc.docstatus === 1) {
			return [__("No Fee"), "orange", "no_fee,=,1"];
		}
	},
};
