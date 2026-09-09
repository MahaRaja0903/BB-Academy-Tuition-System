import re

file_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py"
with open(file_path, "r") as f:
    content = f.read()

validation_code = """
		for row in self.get("fees__invoice_details"):
			if flt(row.paid_amount) <= 0:
				frappe.throw(_("Row #{0}: Paid Amount cannot be 0 in Fees Invoice Details.").format(row.idx))
"""

# We'll inject this right into before_submit
old = """	def before_submit(self):
		self.validate_payment_method()
		self.validate_fees_paid()"""

new = f"""	def before_submit(self):
		self.validate_payment_method()
		self.validate_fees_paid()
{validation_code}"""

content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)

