import re

file_path = "/home/frappe/dreamtech-bench/apps/bb_tution_management/bb_tution_management/bb_academy/doctype/student_admission_form/student_admission_form.js"
with open(file_path, "r") as f:
    content = f.read()

# Add street_name query in setup
setup_query = """		frm.set_query("group", function() {
			if (frm.doc.standard) {
				return {
					query: "bb_tution_management.bb_tution_management.doctype.group.group.get_groups_by_standard",
					filters: {
						standard: frm.doc.standard
					}
				};
			}
		});

		frm.set_query("street_name", function() {
			if (frm.doc.area) {
				return {
					filters: {
						area: frm.doc.area
					}
				};
			}
		});"""
content = content.replace('		frm.set_query("group", function() {\n			if (frm.doc.standard) {\n				return {\n					query: "bb_tution_management.bb_tution_management.doctype.group.group.get_groups_by_standard",\n					filters: {\n						standard: frm.doc.standard\n					}\n				};\n			}\n		});', setup_query)

# Add area trigger
area_trigger = """	standard(frm) {"""
replacement = """	area(frm) {
		frm.set_value("street_name", "");
	},
	standard(frm) {"""
content = content.replace(area_trigger, replacement)

with open(file_path, "w") as f:
    f.write(content)

