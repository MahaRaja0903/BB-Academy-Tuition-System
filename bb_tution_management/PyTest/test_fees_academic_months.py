import frappe
from bb_tution_management.bb_academy.doctype.fee_invoice.fee_invoice import get_student_fee_data

def run():
    students = frappe.get_all("Student", fields=["name", "academic_year"])
    if students:
        for s in students:
            if s.academic_year == "April to April - 10TH STD":
                print("Student:", s.name)
                data = get_student_fee_data(s.name)
                print("Months:", data.get("academic_months"))
                print("Payment Details:", [d.get("month") for d in data.get("payment_details")])
                break
