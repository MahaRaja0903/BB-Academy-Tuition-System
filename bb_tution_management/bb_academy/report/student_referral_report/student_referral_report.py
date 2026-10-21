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
            "fieldname": "referrer_name",
            "label": _("Referrer Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "standard",
            "label": _("Standard"),
            "fieldtype": "Link",
            "options": "Standard",
            "width": 120
        },
        {
            "fieldname": "batch",
            "label": _("Batch"),
            "fieldtype": "Link",
            "options": "Batch",
            "width": 140
        },
        {
            "fieldname": "total_referrals",
            "label": _("Total Referrals"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "total_coupons",
            "label": _("Total Coupons"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "used_coupons",
            "label": _("Used Coupons"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "available_coupons",
            "label": _("Available Coupons"),
            "fieldtype": "Int",
            "width": 140
        },
        {
            "fieldname": "expired_coupons",
            "label": _("Expired Coupons"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "available_amount",
            "label": _("Available Amount"),
            "fieldtype": "Currency",
            "width": 140
        }
    ]

def get_data(filters):
    filters = filters or {}
    conditions = ""
    if filters.get("referrer"):
        conditions += " AND s1.referred_by = %(referrer)s"
    if filters.get("standard"):
        conditions += " AND ref.standard = %(standard)s"
    if filters.get("batch"):
        conditions += " AND ref.current_batch = %(batch)s"

    query = f"""
        SELECT
            s1.referred_by as referrer,
            ref.student_name as referrer_name,
            ref.standard as standard,
            ref.current_batch as batch,
            COUNT(s1.name) as total_referrals
        FROM `tabStudent` s1
        LEFT JOIN `tabStudent` ref ON ref.name = s1.referred_by
        WHERE s1.referred_by IS NOT NULL AND s1.referred_by != '' {conditions}
        GROUP BY s1.referred_by, ref.student_name, ref.standard, ref.current_batch
        ORDER BY total_referrals DESC
    """

    data = frappe.db.sql(query, filters, as_dict=1)
    coupons = get_coupon_summary([d.referrer for d in data])

    for d in data:
        d.update(coupons.get(d.referrer, {}))
        for key in ("total_coupons", "used_coupons", "available_coupons", "expired_coupons", "available_amount"):
            d[key] = d.get(key) or 0

    return filter_by_coupon_status(data, filters.get("coupon_status"))

def filter_by_coupon_status(data, status):
    if not status:
        return data

    key = {
        "Has Available Coupons": "available_coupons",
        "Has Used Coupons": "used_coupons",
        "Has Expired Coupons": "expired_coupons",
    }.get(status)

    if key:
        return [d for d in data if d[key] > 0]
    if status == "No Coupons":
        return [d for d in data if not d.total_coupons]
    return data

def get_coupon_summary(referrers):
    """Coupon counts per referrer from the Student's coupon_code_details. A coupon
    is available while unused and not past its valid till date (same rule as
    the Fee Invoice coupon picker)."""
    if not referrers:
        return {}

    rows = frappe.db.sql("""
        SELECT
            parent as referrer,
            COUNT(name) as total_coupons,
            SUM(CASE WHEN used = 1 THEN 1 ELSE 0 END) as used_coupons,
            SUM(CASE WHEN used = 0 AND (valid_till IS NULL OR valid_till >= CURDATE()) THEN 1 ELSE 0 END) as available_coupons,
            SUM(CASE WHEN used = 0 AND valid_till < CURDATE() THEN 1 ELSE 0 END) as expired_coupons,
            SUM(CASE WHEN used = 0 AND (valid_till IS NULL OR valid_till >= CURDATE()) THEN IFNULL(amount, 0) ELSE 0 END) as available_amount
        FROM `tabReferral Coupon Code Detail`
        WHERE parenttype = 'Student' AND parentfield = 'coupon_code_details'
            AND IFNULL(referral_coupon_code, '') != '' AND parent IN %(referrers)s
        GROUP BY parent
    """, {"referrers": referrers}, as_dict=1)

    return {r.referrer: r for r in rows}
