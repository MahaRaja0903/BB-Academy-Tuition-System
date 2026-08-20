
frappe.query_reports["Student Attendance History"] = {
    "filters": [
        {"fieldname":"student", "label":"Student", "fieldtype":"Link", "options":"Student", "reqd": 1},
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.get_today(), "reqd": 1}
    ]
};
