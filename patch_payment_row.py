import re

filepath = "bb_tution_management/bb_academy/doctype/fee_invoice/fee_invoice.py"
with open(filepath, "r") as f:
    content = f.read()

old_func = """def get_payment_row(student_doc, month, from_end=False):
	rows = student_doc.get("payment_details", [])
	if from_end:
		rows = reversed(rows)
	for row in rows:
		if row.month == month:
			return row
	return None"""

new_func = """def get_payment_row(student_doc, month, from_end=False, is_submit=None):
	rows = list(student_doc.get("payment_details", []))
	if from_end:
		rows.reverse()
	
	matches = [r for r in rows if r.month == month]
	if not matches:
		return None
		
	if len(matches) == 1:
		return matches[0]
		
	# Handle duplicate months (e.g. April 2026 and April 2027)
	if is_submit is True:
		for r in matches:
			if r.status not in ["Paid", "Paid By Starting Payment"]:
				return r
		return matches[0]
	elif is_submit is False:
		for r in reversed(matches):
			if r.status in ["Paid", "Paid By Starting Payment"] or r.amount_paid > 0:
				return r
		return matches[-1]
	else:
		for r in matches:
			if r.status not in ["Paid", "Paid By Starting Payment"]:
				return r
		return matches[-1]"""

content = content.replace(old_func, new_func)

# Also update update_student_payment_detail to pass is_submit
old_settle = """		def settle(month, status, from_end=False):
			if not month:
				return
			row = get_payment_row(student, month, from_end=from_end)"""

new_settle = """		def settle(month, status, from_end=False):
			if not month:
				return
			row = get_payment_row(student, month, from_end=from_end, is_submit=is_submit)"""
content = content.replace(old_settle, new_settle)

old_detail = """				row = get_payment_row(student, month)
				if not row:
					row = student.append("payment_details", {"month": month, "amount_paid": 0.0})"""

new_detail = """				row = get_payment_row(student, month, is_submit=is_submit)
				if not row:
					row = student.append("payment_details", {"month": month, "amount_paid": 0.0})"""
content = content.replace(old_detail, new_detail)

with open(filepath, "w") as f:
    f.write(content)

