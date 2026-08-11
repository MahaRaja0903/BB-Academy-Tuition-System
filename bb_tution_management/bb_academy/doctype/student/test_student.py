import frappe
from frappe.tests.utils import FrappeTestCase


class TestStudent(FrappeTestCase):
	def test_scholarship_student_updates_not_paid_to_paid(self):
		student = frappe.new_doc("Student")
		student.admission_number = f"ADM-TEST-SCH-{frappe.generate_hash(length=6)}"
		student.student_name = "Scholarship Test Student"
		student.admission_date = "2026-06-01"
		student.father_mobile_number = "9876543210"
		student.academic_year = "2025-2026"
		student.scholarship_student = 0
		student.reason_for_scholarship = ""

		student.append("payment_details", {
			"month": "April",
			"status": "Not Joined"
		})
		student.append("payment_details", {
			"month": "June",
			"status": "Not Paid"
		})
		student.append("payment_details", {
			"month": "July",
			"status": "Not Paid"
		})

		# Update scholarship_student to 1
		student.scholarship_student = 1
		student.reason_for_scholarship = "Merit Scholarship"
		student.validate()

		status_map = {row.month: row.status for row in student.payment_details}
		self.assertEqual(status_map.get("April"), "Not Joined")
		self.assertEqual(status_map.get("June"), "Paid")
		self.assertEqual(status_map.get("July"), "Paid")

	def test_referral_coupon_code_creation(self):
		# Ensure Academic Year exists with end_date
		ay_name = "2026-2027-TEST"
		if not frappe.db.exists("Academic Year", ay_name):
			ay = frappe.get_doc({
				"doctype": "Academic Year",
				"academic_year_name": ay_name,
				"start_date": "2026-06-01",
				"start_month": "June",
				"end_date": "2027-03-31",
				"end_month": "March",
				"is_active": 1,
			}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Academic Year", ay_name, "end_date", "2027-03-31")

		# Ensure Standard & Batch exist
		if not frappe.db.exists("Standard", "10th Test"):
			frappe.get_doc({"doctype": "Standard", "standard_name": "10th Test", "starting_payment": 1000, "academic_order": 1}).insert(ignore_permissions=True)
		if not frappe.db.exists("Batch", "Batch A Test"):
			frappe.get_doc({"doctype": "Batch", "batch_name": "Batch A Test", "batch_code": "BAT-TEST", "display_order": 1}).insert(ignore_permissions=True)

		# Create referring student (Student A)
		student_a = frappe.get_doc({
			"doctype": "Student",
			"admission_number": f"ADM-REF-A-{frappe.generate_hash(length=6)}",
			"student_name": "Referring Student A",
			"academic_year": ay_name,
			"standard": "10th Test",
			"current_batch": "Batch A Test",
			"admission_date": "2026-06-01",
			"father_mobile_number": "9876543210",
			"status": "Active"
		}).insert(ignore_permissions=True)

		# Create new student (Student B) referred by Student A
		student_b = frappe.get_doc({
			"doctype": "Student",
			"admission_number": f"ADM-REF-B-{frappe.generate_hash(length=6)}",
			"student_name": "Referred Student B",
			"academic_year": ay_name,
			"standard": "10th Test",
			"current_batch": "Batch A Test",
			"admission_date": "2026-06-01",
			"father_mobile_number": "9876543211",
			"referred_by": student_a.name,
			"status": "Active"
		}).insert(ignore_permissions=True)

		# Verify Referral Coupon Code creation
		coupons = frappe.get_all("Referral Coupon Code", filters={"student_id": student_a.name}, fields=["name", "amount", "valid_till"])
		self.assertTrue(len(coupons) > 0)
		latest_coupon = coupons[0]
		self.assertEqual(latest_coupon.amount, 500)
		self.assertEqual(str(latest_coupon.valid_till), "2027-03-31")

		# Reload Student A and check coupon_code_details child table
		student_a.reload()
		matched_rows = [row for row in student_a.coupon_code_details if row.referral_coupon_code == latest_coupon.name]
		self.assertEqual(len(matched_rows), 1)
		self.assertEqual(matched_rows[0].amount, 500)
		self.assertEqual(str(matched_rows[0].valid_till), "2027-03-31")


