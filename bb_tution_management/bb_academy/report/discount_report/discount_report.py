# Copyright (c) 2026, Maha Raja  and contributors
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
            "fieldname": "fee_invoice",
            "label": _("Fee Invoice"),
            "fieldtype": "Link",
            "options": "Fee Invoice",
            "width": 150
        },
        {
            "fieldname": "student",
            "label": _("Student"),
            "fieldtype": "Link",
            "options": "Student",
            "width": 150
        },
        {
            "fieldname": "student_name",
            "label": _("Student Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "invoice_date",
            "label": _("Invoice Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "monthly_fee",
            "label": _("Monthly Fee"),
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
            "fieldname": "coupon__code",
            "label": _("Coupon Code"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "coupon_amount",
            "label": _("Coupon Amount"),
            "fieldtype": "Currency",
            "width": 130
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
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql(f"""
        SELECT
            name as fee_invoice,
            student,
            student_name,
            invoice_date,
            status,
            monthly_fee,
            discount_amount,
            coupon__code,
            coupon_amount,
            grand_total,
            paid_amount
        FROM
            `tabFee Invoice`
        WHERE
            docstatus < 2
            AND (discount_amount > 0 OR coupon_amount > 0)
            {conditions}
        ORDER BY
            invoice_date DESC
    """, filters, as_dict=1)

    return data

def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " AND invoice_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND invoice_date <= %(to_date)s"
    if filters.get("student"):
        conditions += " AND student = %(student)s"
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    return conditions
