import re

with open('fee_invoice.py', 'r') as f:
    content = f.read()

# Update calculate_outstanding
content = re.sub(
    r'self\.balance_amount = max\(0\.0, final_total - flt\(self\.paid_amount\)\)',
    r'self.balance_amount = max(0.0, final_total - flt(self.paid_amount) - flt(self.coupon_amount))',
    content
)

# Update coupon validation inside calculate_outstanding
content = re.sub(
    r'if flt\(self\.coupon_amount\) > flt\(self\.paid_amount\):\n\s+frappe\.throw\(\n\s+_\("Coupon Amount \(\{0\}\) cannot be more than the Paid Amount \(\{1\}\)\."\)\.format\(\n\s+self\.coupon_amount, self\.paid_amount\n\s+\)\n\s+\)',
    r'if flt(self.coupon_amount) > final_total:\n\t\t\tfrappe.throw(\n\t\t\t\t_("Coupon Amount ({0}) cannot be more than the Grand Total ({1}).").format(\n\t\t\t\t\tself.coupon_amount, final_total\n\t\t\t\t)\n\t\t\t)',
    content
)

# Update cash_to_collect
content = re.sub(
    r'return max\(0\.0, flt\(self\.paid_amount\) - flt\(self\.coupon_amount\)\)',
    r'return max(0.0, flt(self.paid_amount))',
    content
)

# Update update_student_payment_detail to distribute coupon_amount
# Find where detail_paid is calculated and row.amount_paid is set
old_update = """				detail_paid = flt(detail.paid_amount)
				if detail_paid == 0 and len(self.get("fees_details", [])) == 1:
					detail_paid = flt(self.paid_amount)

				row.amount_paid = max(0.0, flt(row.amount_paid) + sign * detail_paid)"""

new_update = """				detail_paid = flt(detail.paid_amount)
				if detail_paid == 0 and len(self.get("fees_details", [])) == 1:
					detail_paid = flt(self.paid_amount)

				# Distribute coupon to cover the shortfall on the row
				shortfall = flt(detail.amount_need_to_pay) - detail_paid
				coupon_applied_to_row = 0.0
				if shortfall > 0 and coupon_remaining > 0:
					coupon_applied_to_row = min(shortfall, coupon_remaining)
					coupon_remaining -= coupon_applied_to_row

				row.amount_paid = max(0.0, flt(row.amount_paid) + sign * (detail_paid + coupon_applied_to_row))"""

# add coupon_remaining = flt(self.coupon_amount) before the loop
old_loop_start = """		else:
			for detail in self.get("fees_details", []):"""
new_loop_start = """		else:
			coupon_remaining = flt(self.coupon_amount)
			for detail in self.get("fees_details", []):"""

content = content.replace(old_update, new_update)
content = content.replace(old_loop_start, new_loop_start)

with open('fee_invoice.py', 'w') as f:
    f.write(content)
