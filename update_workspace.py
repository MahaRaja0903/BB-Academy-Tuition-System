import frappe
import json

def update_workspace():
    ws = frappe.get_doc("Workspace", "BB Academy")
    
    # Check if Attendance is already there
    has_attendance = any(l.label == "Attendance" for l in ws.links)
    if has_attendance:
        print("Attendance already exists in workspace")
        return
        
    # Append to links
    links_to_add = [
        {"type": "Card Break", "label": "Attendance", "hidden": 0, "link_type": "DocType"},
        {"type": "Link", "label": "Attendance Manager", "link_type": "Page", "link_to": "attendance-manager", "hidden": 0},
        {"type": "Link", "label": "Attendance Dashboard", "link_type": "Page", "link_to": "attendance-dashboard", "hidden": 0},
        {"type": "Link", "label": "Attendance Holiday", "link_type": "DocType", "link_to": "Attendance Holiday", "hidden": 0},
        {"type": "Link", "label": "Student Attendance", "link_type": "DocType", "link_to": "Student Attendance", "hidden": 0},
        
        {"type": "Card Break", "label": "Attendance Reports", "hidden": 0, "link_type": "DocType"},
        {"type": "Link", "label": "Daily Attendance", "link_type": "Report", "link_to": "Daily Attendance Report", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Student History", "link_type": "Report", "link_to": "Student Attendance History", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Monthly Report", "link_type": "Report", "link_to": "Monthly Attendance Report", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Batch Summary", "link_type": "Report", "link_to": "Standard and Batch Attendance Summary", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Absent Report", "link_type": "Report", "link_to": "Absent Student Report", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Late Report", "link_type": "Report", "link_to": "Late Entry Report", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Defaulters", "link_type": "Report", "link_to": "Attendance Defaulters", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Monthly Register", "link_type": "Report", "link_to": "Monthly Attendance Register", "is_query_report": 1, "hidden": 0},
        {"type": "Link", "label": "Holiday Report", "link_type": "Report", "link_to": "Attendance Holiday Report", "is_query_report": 1, "hidden": 0}
    ]
    
    for l in links_to_add:
        ws.append("links", l)
        
    # Update content blocks
    try:
        content = json.loads(ws.content)
        content.append({"id": "attManagerCard", "type": "card", "data": {"card_name": "Attendance", "col": 4}})
        content.append({"id": "attReportCard", "type": "card", "data": {"card_name": "Attendance Reports", "col": 4}})
        ws.content = json.dumps(content)
    except Exception as e:
        print("Error parsing content:", e)
        
    ws.save()
    print("Workspace updated")

if __name__ == "__main__":
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    try:
        update_workspace()
        frappe.db.commit()
    finally:
        frappe.destroy()
