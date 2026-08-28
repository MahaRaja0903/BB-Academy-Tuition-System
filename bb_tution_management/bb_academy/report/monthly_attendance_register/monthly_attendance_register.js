
frappe.query_reports["Monthly Attendance Register"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"},
        {"fieldname":"gender", "label":"Gender", "fieldtype":"Select", "options":"\nBoys\nGirls"}
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname && column.fieldname.startsWith("day_") && value) {
            if (value === "P") {
                value = "<span style='color: green; font-weight: bold;'>P</span>";
            } else if (value === "A") {
                value = "<span style='color: red; font-weight: bold;'>A</span>";
            } else if (value === "L") {
                value = "<span style='color: orange; font-weight: bold;'>L</span>";
            } else if (value === "H") {
                value = "<span style='color: blue; font-weight: bold;'>H</span>";
            }
        }
        return value;
    }
};
