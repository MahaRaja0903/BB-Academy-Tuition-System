with open("bb_tution_management/bb_academy/page/bb_dashboard/bb_dashboard.py", "r") as f:
    content = f.read()

content = content.replace('"mother_name",', '"mother_name",\n\t\t\t"guardian_name",')
content = content.replace('"mother_number",', '"mother_number",\n\t\t\t"guardian_number",')
content = content.replace('r["parent_mobile"] = r.father_number or r.mother_number', 'r["parent_mobile"] = r.father_number or r.mother_number or r.guardian_number')
# wait, wait I already did 'r.father_name or r.mother_name or r.guardian_name'. But let's check if there are other occurrences.

with open("bb_tution_management/bb_academy/page/bb_dashboard/bb_dashboard.py", "w") as f:
    f.write(content)

