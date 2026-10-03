with open("bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py", "r") as f:
    content = f.read()

pattern = '''		"mother_mobile_number": doc.mother_number'''
replacement = '''		"mother_mobile_number": doc.mother_number,
		"guardian_name": doc.guardian_name,
		"guardian_mobile_number": doc.guardian_number,
		"guardian_occupation": doc.guardian_occupation,
		"relation_with_guardian": doc.relation_with_guardian'''

content = content.replace(pattern, replacement)

with open("bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.py", "w") as f:
    f.write(content)

