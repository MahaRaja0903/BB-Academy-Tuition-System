# Copyright (c) 2026, Maha Raja and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "student",
            "label": _("Student"),
            "fieldtype": "Link",
            "options": "Student",
            "width": 120
        },
        {
            "fieldname": "student_name",
            "label": _("Student Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "reason",
            "label": _("Reason"),
            "fieldtype": "Data",
            "width": 250
        }
    ]

def get_data(filters):
    conditions = []
    values = {}
    
    if filters and filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters.get("status")
    else:
        conditions.append("status IN ('Discontinued', 'Suspended')")
        
    condition_str = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    students = frappe.db.sql(f"""
        SELECT 
            name as student, 
            student_name, 
            status,
            discontinued__date,
            suspended_date,
            discontinued_reason,
            suspended_reason
        FROM `tabStudent`
        {condition_str}
        ORDER BY creation DESC
    """, values, as_dict=1)

    data = []
    for s in students:
        if s.status == "Discontinued":
            date = s.discontinued__date
            reason = s.discontinued_reason
        elif s.status == "Suspended":
            date = s.suspended_date
            reason = s.suspended_reason
        else:
            date = None
            reason = None

        data.append({
            "student": s.student,
            "student_name": s.student_name,
            "status": s.status,
            "date": date,
            "reason": reason
        })
        
    return data
