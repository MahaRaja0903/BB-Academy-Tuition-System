import json

def update_doctype(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    fields = data.get("fields", [])
    
    if not any(f.get("fieldname") == "guardian_name" for f in fields):
        insert_idx = -1
        for i, field in enumerate(fields):
            if field.get("fieldname") == "mother_number":
                insert_idx = i
                
        new_fields = [
            {
                "fieldname": "guardian_name",
                "fieldtype": "Data",
                "label": "Guardian Name"
            },
            {
                "fieldname": "relation_with_guardian",
                "fieldtype": "Select",
                "label": "Relation With Guardian",
                "options": "\nGrand Mother\nGrand Father\nUncle\nAunt\nBrother\nSister\nOther"
            },
            {
                "fieldname": "guardian_occupation",
                "fieldtype": "Data",
                "label": "Guardian Occupation"
            },
            {
                "fieldname": "guardian_number",
                "fieldtype": "Data",
                "label": "Guardian Number"
            }
        ]
        
        if insert_idx != -1:
            for i, nf in enumerate(new_fields):
                fields.insert(insert_idx + 1 + i, nf)
        else:
            fields.extend(new_fields)
            
        data["fields"] = fields
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=1)

update_doctype("bb_tution_management/bb_academy/doctype/student_enquiry_form/student_enquiry_form.json")
