
frappe.query_reports["Daily Attendance Report"] = {
    "filters": [
        {"fieldname":"attendance_date", "label":"Date", "fieldtype":"Date", "default": frappe.datetime.get_today(), "reqd": 1},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"},
        {"fieldname":"status", "label":"Status", "fieldtype":"Select", "options":"All\nPresent\nAbsent\nLate\nPending", "default": "All"}
    ]
};
