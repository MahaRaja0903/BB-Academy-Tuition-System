import frappe

def run():
	frappe.db.commit() # start clean
	# 1. Setup - get an active academic year and standard
	academic_year = frappe.db.get_value("Academic Year", {"is_active": 1}, "name")
	if not academic_year:
		print("No active academic year found, please create one.")
		return
	
	standard = frappe.db.get_value("Standard Detail", {"parent": academic_year}, "standard")
	if not standard:
		standard = frappe.db.get_value("Standard", {"is_active": 1}, "name")

	batch = frappe.db.get_value("Batch", {}, "name")
	
	print(f"Using Academic Year: {academic_year}, Standard: {standard}, Batch: {batch}")

	# Non-Yearly Payment
	enquiry1 = frappe.get_doc({
		"doctype": "Student Enquiry Form",
		"applicant_name": "Test Gowtham",
		"academic_year": academic_year,
		"standard": standard,
		"father_number": "9999999991",
		"status": "Open"
	}).insert(ignore_permissions=True)
	
	print(f"Created Enquiry 1: {enquiry1.name}")

	adm1 = frappe.get_doc({
		"doctype": "Student Admission Form",
		"student_enquiry": enquiry1.name,
		"student_name": enquiry1.applicant_name,
		"standard": standard,
		"assigned_batch": batch,
		"is_yearly_payment": 0,
		"starting_payment": 5000,
		"payment_method": "Cash",
		"fees__invoice_details": [{
			"month": "Starting Payment",
			"amount_need_to_pay": 5000,
			"paid_amount": 2500,
			"discount_amount": 0
		}]
	})
	
	adm1.insert(ignore_permissions=True)
	adm1.submit()
	
	print(f"Submitted Admission 1: {adm1.name}")
	
	# Verify
	student1 = frappe.db.get_value("Student", {"student_name": "Test Gowtham"}, "name")
	print(f"Student 1 Created: {student1}")
	invoice1 = frappe.db.get_value("Fee Invoice", {"student": student1}, "name")
	print(f"Invoice 1 Created: {invoice1}")

	# Yearly Payment
	enquiry2 = frappe.get_doc({
		"doctype": "Student Enquiry Form",
		"applicant_name": "Test Shiva",
		"academic_year": academic_year,
		"standard": standard,
		"father_number": "9999999992",
		"status": "Open"
	}).insert(ignore_permissions=True)
	
	print(f"Created Enquiry 2: {enquiry2.name}")

	adm2 = frappe.get_doc({
		"doctype": "Student Admission Form",
		"student_enquiry": enquiry2.name,
		"student_name": enquiry2.applicant_name,
		"standard": standard,
		"assigned_batch": batch,
		"is_yearly_payment": 1,
		"total_year_payment_amount": 60000,
		"yearly_fees_paid_amount": 60000,
		"payment_method": "Split Up",
		"cash": 20000,
		"gpay": 30000,
		"scanner": 10000
	})
	
	adm2.insert(ignore_permissions=True)
	adm2.submit()
	
	print(f"Submitted Admission 2: {adm2.name}")
	
	student2 = frappe.db.get_value("Student", {"student_name": "Test Shiva"}, "name")
	print(f"Student 2 Created: {student2}")
	invoice2 = frappe.db.get_value("Fee Invoice", {"student": student2}, "name")
	print(f"Invoice 2 Created: {invoice2}")
	
	frappe.db.commit()
