# Copyright (c) 2026, Maha Raja and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "fieldname": "referrer",
            "label": _("Referrer Student"),
            "fieldtype": "Link",
            "options": "Student",
            "width": 150
        },
        {
            "fieldname": "referrer_name",
            "label": _("Referrer Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "total_referrals",
            "label": _("Total Referrals"),
            "fieldtype": "Int",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = ""
    if filters and filters.get("referrer"):
        conditions = "AND referred_by = %(referrer)s"
        
    query = f"""
        SELECT 
            referred_by as referrer,
            (SELECT student_name FROM `tabStudent` s2 WHERE s2.name = s1.referred_by) as referrer_name,
            COUNT(name) as total_referrals
        FROM `tabStudent` s1
        WHERE referred_by IS NOT NULL AND referred_by != '' {conditions}
        GROUP BY referred_by
        ORDER BY total_referrals DESC
    """
    
    return frappe.db.sql(query, filters or {}, as_dict=1)

def get_chart(data):
    if not data:
        return None
        
    labels = [d.referrer_name or d.referrer for d in data]
    datapoints = [d.total_referrals for d in data]
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Total Referrals"),
                    "values": datapoints
                }
            ]
        },
        "type": "bar",
        "colors": ["#1abc9c"]
    }
