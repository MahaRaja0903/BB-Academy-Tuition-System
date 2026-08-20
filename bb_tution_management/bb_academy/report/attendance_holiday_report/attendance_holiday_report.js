
frappe.query_reports["Attendance Holiday Report"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.year_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.year_end(), "reqd": 1},
        {"fieldname":"holiday_type", "label":"Holiday Type", "fieldtype":"Select", "options":"\nRain\nGovernment Holiday\nSchool Holiday\nEmergency\nOther"},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"}
    ]
};
