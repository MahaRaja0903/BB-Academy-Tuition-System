import re

filepath = "bb_tution_management/bb_academy/doctype/student/student.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. Replace the for loop to use enumerate
old_loop = "for month_num in academic_months:"
new_loop = "for idx, month_num in enumerate(academic_months):"
content = content.replace(old_loop, new_loop)

# 2. Replace the old month_pos / admission_pos logic
old_logic = """				# Determine if the student had joined by this month
				if month_num in academic_months:
					# Find position of this month and admission month in the
					# academic calendar to compare correctly across year boundary
					month_pos = academic_months.index(month_num)
					try:
						admission_pos = academic_months.index(admission_month_num)
					except ValueError:
						# Admission month not in academic calendar – treat as joined
						admission_pos = 0

					if month_pos < admission_pos:"""

new_logic = """				# Determine if the student had joined by this month
				if True:
					month_pos = idx
					admission_pos = (ad_date.year - start_date.year) * 12 + (ad_date.month - start_date.month)

					if month_pos < admission_pos:"""

content = content.replace(old_logic, new_logic)

with open(filepath, "w") as f:
    f.write(content)
