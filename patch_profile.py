with open("bb_tution_management/bb_academy/student_profile.py", "r") as f:
    content = f.read()

pattern = '''	"mother_mobile_number",'''
replacement = '''	"mother_mobile_number",
	"guardian_name",
	"guardian_mobile_number",
	"guardian_occupation",
	"relation_with_guardian",'''

content = content.replace(pattern, replacement)

with open("bb_tution_management/bb_academy/student_profile.py", "w") as f:
    f.write(content)

