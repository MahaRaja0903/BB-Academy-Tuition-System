import re

file_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace self.referred_by_student_id with self.referred_by or handle both
# Wait, let's check what it uses.
old = '"referred_by": self.referred_by_student_id,'
new = '"referred_by": self.referred_by or self.referred_by_student_id,'
content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)

