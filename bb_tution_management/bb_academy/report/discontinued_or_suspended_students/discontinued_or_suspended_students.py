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
            "fieldname": "standard",
            "label": _("Standard"),
            "fieldtype": "Link",
            "options": "Standard",
            "width": 100
        },
        {
            "fieldname": "current_batch",
            "label": _("Batch"),
            "fieldtype": "Link",
            "options": "Batch",
            "width": 120
        },
        {
            "fieldname": "gender",
            "label": _("Gender"),
            "fieldtype": "Data",
            "width": 80
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
            "fieldname": "month",
            "label": _("Month"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "reason",
            "label": _("Reason"),
            "fieldtype": "Data",
            "width": 250
        }
    ]

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

def get_data(filters):
    filters = filters or {}
    conditions = []
    values = {}

    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters.get("status")
    else:
        conditions.append("status IN ('Discontinued', 'Suspended')")

    for field in ("standard", "current_batch", "gender"):
        if filters.get(field):
            conditions.append(f"{field} = %({field})s")
            values[field] = filters.get(field)

    # Effective date depends on the status
    status_date = "(CASE WHEN status = 'Discontinued' THEN discontinued__date ELSE suspended_date END)"

    if filters.get("month") in MONTHS:
        conditions.append(f"MONTH({status_date}) = %(month)s")
        values["month"] = MONTHS.index(filters.get("month")) + 1

    if filters.get("year"):
        conditions.append(f"YEAR({status_date}) = %(year)s")
        values["year"] = int(filters.get("year"))

    condition_str = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    students = frappe.db.sql(f"""
        SELECT 
            name as student, 
            student_name, 
            standard,
            current_batch,
            gender,
            status,
            discontinued__date,
            suspended_date,
            discontinued_reason,
            suspended_reason
        FROM `tabStudent`
        {condition_str}
        ORDER BY {status_date} DESC, creation DESC
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
            "standard": s.standard,
            "current_batch": s.current_batch,
            "gender": s.gender,
            "status": s.status,
            "date": date,
            "month": f"{MONTHS[date.month - 1]} {date.year}" if date else None,
            "reason": reason
        })
        
    return data
