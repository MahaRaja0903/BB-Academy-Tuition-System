import frappe
from bb_tution_management.bb_academy.doctype.bulk_fee_invoice_tool.bulk_fee_invoice_tool import generate_invoices

def run():
    print("Generating invoices...")
    count = generate_invoices('April to April - 10TH STD', 'April')
    print(f"Created count: {count}")
