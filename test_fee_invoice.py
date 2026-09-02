import frappe
from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import get_academic_months, get_advance_months

frappe.init(site="dreamtech-bench.local") # try to initialize if possible, maybe we don't need this if we just mock.
