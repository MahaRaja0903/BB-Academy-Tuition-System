import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day

def execute(filters=None):
    columns = [
        {"fieldname": "holiday_date", "label": "Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "holiday_type", "label": "Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "reason", "label": "Reason", "fieldtype": "Data", "width": 250},
        {"fieldname": "scope", "label": "Scope", "fieldtype": "Data", "width": 150},
        {"fieldname": "standard", "label": "Standard", "fieldtype": "Data", "width": 100},
        {"fieldname": "batch", "label": "Batch", "fieldtype": "Data", "width": 100},
        {"fieldname": "owner", "label": "Created By", "fieldtype": "Data", "width": 150}
    ]
    
    cond = ""
    if filters.get("holiday_type"): cond += " AND holiday_type = %(holiday_type)s"
    if filters.get("standard"): cond += " AND (standard = %(standard)s OR scope='Entire School')"
    if filters.get("batch"): cond += " AND (batch = %(batch)s OR scope='Standard' OR scope='Entire School')"
    
    data = frappe.db.sql(f"""
        SELECT holiday_date, holiday_type, reason, scope, standard, batch, owner
        FROM `tabAttendance Holiday`
        WHERE holiday_date BETWEEN %(from_date)s AND %(to_date)s
        {cond}
        ORDER BY holiday_date DESC
    """, filters, as_dict=True)
    
    return columns, data
