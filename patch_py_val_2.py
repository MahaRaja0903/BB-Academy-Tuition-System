import re

file_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py"
with open(file_path, "r") as f:
    content = f.read()

old = """		for row in self.get("fees__invoice_details"):
			if flt(row.paid_amount) <= 0:
				frappe.throw(_("Row #{0}: Paid Amount cannot be 0 in Fees Invoice Details.").format(row.idx))"""

new = """		if not self.is_yearly_payment:
			for row in self.get("fees__invoice_details"):
				if flt(row.paid_amount) <= 0:
					frappe.throw(_("Row #{0}: Paid Amount cannot be 0 in Fees Invoice Details.").format(row.idx))"""

content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)

