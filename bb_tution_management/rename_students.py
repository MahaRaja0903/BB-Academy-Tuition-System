import frappe

def execute():
    try:
        # Get all students ordered by admission_date ascending
        students = frappe.get_all("Student", fields=["name", "admission_date"], order_by="admission_date asc, creation asc")
        
        year_counters = {}
        for student in students:
            if not student.admission_date:
                year = "2026"
            else:
                year = str(student.admission_date.year)
                
            if year not in year_counters:
                year_counters[year] = 1
                
            new_name = f"BB-{year}-{year_counters[year]:04d}"
            year_counters[year] += 1
            
            if student.name != new_name:
                print(f"Renaming {student.name} to {new_name}...")
                
                if frappe.db.exists("Student", new_name):
                    print(f"Target name {new_name} already exists, skipping or handling differently...")
                    continue
                
                frappe.rename_doc("Student", student.name, new_name, force=True)
                
                # Update admission_number field in Student
                frappe.db.set_value("Student", new_name, "admission_number", new_name)
                
                # Update admission_number in Student Admission Form
                frappe.db.sql("""
                    UPDATE `tabStudent Admission Form` 
                    SET admission_number = %s 
                    WHERE admission_number = %s
                """, (new_name, student.name))
        
        # Update the naming series counter for future creation
        for year, next_idx in year_counters.items():
            series_prefix = f"BB-{year}-"
            frappe.db.sql("""
                INSERT INTO `tabSeries` (name, current)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE current = %s
            """, (series_prefix, next_idx - 1, next_idx - 1))
            
        frappe.db.commit()
        print("Successfully renamed all students and updated series counters.")
    except Exception as e:
        frappe.db.rollback()
        print(f"Error: {e}")

