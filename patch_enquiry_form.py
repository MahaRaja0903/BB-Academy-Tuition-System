with open("bb_tution_management/bb_academy/doctype/student_enquiry_form/student_enquiry_form.py", "r") as f:
    content = f.read()

pattern = '''		"mother_mobile_number": enquiry.mother_number,'''
replacement = '''		"mother_mobile_number": enquiry.mother_number,
		"guardian_name": enquiry.guardian_name,
		"guardian_mobile_number": enquiry.guardian_number,
		"guardian_occupation": enquiry.guardian_occupation,
		"relation_with_guardian": enquiry.relation_with_guardian,'''

content = content.replace(pattern, replacement)

with open("bb_tution_management/bb_academy/doctype/student_enquiry_form/student_enquiry_form.py", "w") as f:
    f.write(content)

