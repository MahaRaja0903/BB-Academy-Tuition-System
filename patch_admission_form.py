import re

with open("bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py", "r") as f:
    content = f.read()

# For the on_submit student creation
pattern1 = r'"preferred_mobile_number": self\.preferred_mobile_number,'
replacement1 = '"preferred_mobile_number": self.preferred_mobile_number,\n\t\t\t\t"guardian_name": self.guardian_name,\n\t\t\t\t"guardian_mobile_number": self.guardian_mobile_number,\n\t\t\t\t"guardian_occupation": self.guardian_occupation,\n\t\t\t\t"relation_with_guardian": self.relation_with_guardian,'
content = re.sub(pattern1, replacement1, content)

# For original_create_student_record 
pattern2 = r'"mother_name": self\.mother_name,'
replacement2 = '"mother_name": self.mother_name,\n\t\t\t\t"guardian_name": self.guardian_name,\n\t\t\t\t"guardian_mobile_number": self.guardian_mobile_number,\n\t\t\t\t"guardian_occupation": self.guardian_occupation,\n\t\t\t\t"relation_with_guardian": self.relation_with_guardian,'
content = re.sub(pattern2, replacement2, content)

with open("bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py", "w") as f:
    f.write(content)

