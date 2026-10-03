with open("bb_tution_management/bb_academy/web_form/student_admission_form/student_admission_form.js", "r") as f:
    content = f.read()

pattern = '''							if (enq.mother_mobile_number) promises.push(frappe.web_form.set_value("mother_mobile_number", enq.mother_mobile_number));'''
replacement = '''							if (enq.mother_mobile_number) promises.push(frappe.web_form.set_value("mother_mobile_number", enq.mother_mobile_number));
							if (enq.guardian_name) promises.push(frappe.web_form.set_value("guardian_name", enq.guardian_name));
							if (enq.guardian_mobile_number) promises.push(frappe.web_form.set_value("guardian_mobile_number", enq.guardian_mobile_number));
							if (enq.guardian_occupation) promises.push(frappe.web_form.set_value("guardian_occupation", enq.guardian_occupation));
							if (enq.relation_with_guardian) promises.push(frappe.web_form.set_value("relation_with_guardian", enq.relation_with_guardian));'''

content = content.replace(pattern, replacement)

with open("bb_tution_management/bb_academy/web_form/student_admission_form/student_admission_form.js", "w") as f:
    f.write(content)

