import re

file_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py"
with open(file_path, "r") as f:
    content = f.read()

old = """	def before_submit(self):
		self.validate_payment_method()
		self.validate_fees_paid()"""

new = """	def before_submit(self):
		if not self.fees_due_date:
			frappe.throw(_("Fees Due Date is required before submission."))
		self.validate_payment_method()
		self.validate_fees_paid()"""

content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)

