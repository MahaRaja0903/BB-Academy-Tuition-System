import re

with open("bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py", "r") as f:
    code = f.read()

# Add academic year default in validate
validate_code = """	def validate(self):
		if not self.academic_year:
			today = frappe.utils.today()
			if today:
				year = int(today.split('-')[0])
				month = int(today.split('-')[1])
				start_year = year if month >= 6 else year - 1
				end_year = start_year + 1
				self.academic_year = f"{start_year}-{end_year}"
		
		if not self.admission_number and self.name and not self.name.startswith("new-"):
			self.admission_number = self.name

		self.fetch_fees()
		self.validate_admission_number()"""

code = re.sub(r'	def validate\(self\):[\s\S]*?	def fetch_fees\(self\):', validate_code + '\n\n	def fetch_fees(self):', code)

with open("bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py", "w") as f:
    f.write(code)
