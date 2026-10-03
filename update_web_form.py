import json

def update_web_form(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    fields = data.get("web_form_fields", [])
    
    if not any(f.get("fieldname") == "guardian_name" for f in fields):
        insert_idx = -1
        for i, field in enumerate(fields):
            if field.get("fieldname") == "preferred_mobile_number":
                field["options"] = "\nFather\nMother\nGuardian"
                
            if field.get("fieldname") == "mother_mobile_number":
                insert_idx = i
                
        new_fields = [
            {
                "fieldname": "guardian_name",
                "fieldtype": "Data",
                "label": "Guardian Name",
                "reqd": 0,
                "hidden": 0
            },
            {
                "fieldname": "relation_with_guardian",
                "fieldtype": "Select",
                "label": "Relation With Guardian",
                "options": "\nGrand Mother\nGrand Father\nUncle\nAunt\nBrother\nSister\nOther",
                "reqd": 0,
                "hidden": 0
            },
            {
                "fieldname": "guardian_occupation",
                "fieldtype": "Data",
                "label": "Guardian Occupation",
                "reqd": 0,
                "hidden": 0
            },
            {
                "fieldname": "guardian_mobile_number",
                "fieldtype": "Data",
                "label": "Guardian Mobile Number",
                "reqd": 0,
                "hidden": 0
            }
        ]
        
        if insert_idx != -1:
            for i, nf in enumerate(new_fields):
                fields.insert(insert_idx + 1 + i, nf)
        else:
            fields.extend(new_fields)
            
        data["web_form_fields"] = fields
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=1)

update_web_form("bb_tution_management/bb_academy/web_form/student_admission_form/student_admission_form.json")
