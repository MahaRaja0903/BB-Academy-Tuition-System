import json

file_path = "bb_tution_management/bb_academy/doctype/student/student.json"

with open(file_path, "r") as f:
    data = json.load(f)

if "field_order" in data:
    seen = set()
    new_order = []
    for f in data["field_order"]:
        if f not in seen:
            seen.add(f)
            new_order.append(f)
    print(f"Original field_order len: {len(data['field_order'])}, New len: {len(new_order)}")
    data["field_order"] = new_order

with open(file_path, "w") as f:
    json.dump(data, f, indent=1)

print("Done.")
