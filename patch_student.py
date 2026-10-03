import re

with open("bb_tution_management/bb_academy/doctype/student/student.py", "r") as f:
    content = f.read()

pattern = r'''	def set_preferred_whatsapp_number\(self\):
		if self\.preferred_mobile_number == "Father":
			phone = self\.father_mobile_number
		elif self\.preferred_mobile_number == "Mother":
			phone = self\.mother_mobile_number
		else:
			phone = self\.father_mobile_number or self\.mother_mobile_number'''

replacement = '''	def set_preferred_whatsapp_number(self):
		if self.preferred_mobile_number == "Father":
			phone = self.father_mobile_number
		elif self.preferred_mobile_number == "Mother":
			phone = self.mother_mobile_number
		elif self.preferred_mobile_number == "Guardian":
			phone = self.guardian_mobile_number
		else:
			phone = self.father_mobile_number or self.mother_mobile_number or self.guardian_mobile_number'''

content = content.replace(pattern, replacement)

with open("bb_tution_management/bb_academy/doctype/student/student.py", "w") as f:
    f.write(content)

