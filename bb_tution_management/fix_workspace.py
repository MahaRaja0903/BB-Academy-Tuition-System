import frappe
import json
import os

workspace_path = "/home/maharajan/Dont-quit/apps/bb_tution_management/bb_tution_management/bb_tution_management/workspace/bb_academy/bb_academy.json"

with open(workspace_path, "r") as f:
    data = json.load(f)

for link in data.get("links", []):
    if link.get("label") in ["Pending Balance Report", "Student Wise Report", "Payment Wise Report", "Promote and Demote Report"]:
        link["is_query_report"] = 1

with open(workspace_path, "w") as f:
    json.dump(data, f, indent=1)

# Now update the db record if it exists
if frappe.db.exists("Workspace", "BB Academy"):
    doc = frappe.get_doc("Workspace", "BB Academy")
    for link in doc.links:
        if link.label in ["Pending Balance Report", "Student Wise Report", "Payment Wise Report", "Promote and Demote Report"]:
            link.is_query_report = 1
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Updated Workspace links in DB.")
else:
    print("Workspace not found in DB.")
