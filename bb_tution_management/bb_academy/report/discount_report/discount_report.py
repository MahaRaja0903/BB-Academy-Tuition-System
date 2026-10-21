# Copyright (c) 2026, Maha Raja  and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "fee_invoice",
            "label": _("Fee Invoice"),
            "fieldtype": "Link",
            "options": "Fee Invoice",
            "width": 150
        },
        {
            "fieldname": "invoice_date",
            "label": _("Invoice Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "student",
            "label": _("Student"),
            "fieldtype": "Link",
            "options": "Student",
            "width": 130
        },
        {
            "fieldname": "student_name",
            "label": _("Student Name"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "standard",
            "label": _("Standard"),
            "fieldtype": "Link",
            "options": "Standard",
            "width": 110
        },
        {
            "fieldname": "batch",
            "label": _("Batch"),
            "fieldtype": "Link",
            "options": "Batch",
            "width": 90
        },
        {
            "fieldname": "discount_months",
            "label": _("Discount Months"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "monthly_fee",
            "label": _("Actual Amount"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "discount_amount",
            "label": _("Discount Amount"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "discount_reason",
            "label": _("Discount Reason"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "discount_reason_remarks",
            "label": _("Remarks"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "grand_total",
            "label": _("Grand Total"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "paid_amount",
            "label": _("Paid Amount"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    # Only manual discounts: discount_amount is applied only when Add Discount
    # is ticked, and referral coupons are left out.
    data = frappe.db.sql(f"""
        SELECT
            fi.name as fee_invoice,
            fi.invoice_date,
            fi.student,
            fi.student_name,
            s.standard,
            s.current_batch as batch,
            fi.monthly_fee,
            fi.discount_amount,
            fi.discount_reason,
            fi.discount_reason_remarks,
            fi.grand_total,
            fi.paid_amount,
            fi.status
        FROM `tabFee Invoice` fi
        LEFT JOIN `tabStudent` s ON s.name = fi.student
        WHERE fi.docstatus = 1
            AND fi.add_discount = 1 AND fi.discount_amount > 0
            {conditions}
        ORDER BY fi.invoice_date DESC, fi.name DESC
    """, filters, as_dict=1)

    months = get_discount_months([d.fee_invoice for d in data])
    for d in data:
        d.discount_months = months.get(d.fee_invoice)

    return data

def get_discount_months(invoices):
    """The months on each invoice that carry a discount, e.g. "June, July"."""
    if not invoices:
        return {}

    rows = frappe.db.sql("""
        SELECT parent, GROUP_CONCAT(month ORDER BY idx SEPARATOR ', ') as months
        FROM `tabFees Invoice Details`
        WHERE parenttype = 'Fee Invoice' AND parentfield = 'fees_details'
            AND discount_amount > 0 AND parent IN %(invoices)s
        GROUP BY parent
    """, {"invoices": invoices}, as_dict=1)

    return {r.parent: r.months for r in rows}

def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " AND fi.invoice_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND fi.invoice_date <= %(to_date)s"
    if filters.get("student"):
        conditions += " AND fi.student = %(student)s"
    if filters.get("standard"):
        conditions += " AND s.standard = %(standard)s"
    if filters.get("batch"):
        conditions += " AND s.current_batch = %(batch)s"
    if filters.get("status"):
        conditions += " AND fi.status = %(status)s"
    if filters.get("discount_reason"):
        conditions += " AND fi.discount_reason = %(discount_reason)s"

    return conditions
