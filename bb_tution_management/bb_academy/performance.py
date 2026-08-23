import frappe
from frappe.utils import getdate, today
import json

@frappe.whitelist()
def get_performance_students(standard, batch, date):
    if not frappe.has_permission("Student Performance Tracker", "read"):
        frappe.throw("No permission to read performance")

    date_obj = getdate(date)

    students = frappe.db.sql("""
        SELECT name as student_id, student_name, gender
        FROM `tabStudent`
        WHERE status = 'Active'
          AND standard = %s
          AND current_batch = %s
        ORDER BY name ASC
    """, (standard, batch), as_dict=True)
    
    student_ids = [s.student_id for s in students]
    if not student_ids:
        return {"students": []}
        
    # Get today's performance
    perf_records = frappe.db.sql("""
        SELECT student, study, study_performance, test, test_performance, maths_test, maths_test_performance, discipline, discipline_performance, bad_activities, critical_activities
        FROM `tabStudent Performance Tracker`
        WHERE date = %s
          AND student IN %s
    """, (date_obj, tuple(student_ids)), as_dict=True)
    
    perf_map = {r.student: r for r in perf_records}
    
    result_students = []
    
    for s in students:
        p = perf_map.get(s.student_id)
        if p:
            s.update({
                "has_record": 1,
                "study": p.study,
                "study_performance": p.study_performance,
                "test": p.test,
                "test_performance": p.test_performance,
                "maths_test": p.maths_test,
                "maths_test_performance": p.maths_test_performance,
                "discipline": p.discipline,
                "discipline_performance": p.discipline_performance,
                "bad_activities": p.bad_activities,
                "critical_activities": p.critical_activities
            })
        else:
            s.update({
                "has_record": 0,
                "study": 0, "study_performance": "",
                "test": 0, "test_performance": "",
                "maths_test": 0, "maths_test_performance": "",
                "discipline": 0, "discipline_performance": "",
                "bad_activities": "", "critical_activities": ""
            })
        result_students.append(s)
        
    return {
        "students": result_students
    }

@frappe.whitelist()
def save_student_performance(student, date, data):
    if not frappe.has_permission("Student Performance Tracker", "write"):
        frappe.throw("No permission to write performance")

    if isinstance(data, str):
        data = json.loads(data)

    existing = frappe.db.get_value("Student Performance Tracker", {
        "student": student,
        "date": date
    }, "name")

    if existing:
        doc = frappe.get_doc("Student Performance Tracker", existing)
    else:
        doc = frappe.get_doc({
            "doctype": "Student Performance Tracker",
            "student": student,
            "date": date
        })

    doc.study = data.get("study", 0)
    doc.study_performance = data.get("study_performance", "") if doc.study else ""
    doc.test = data.get("test", 0)
    doc.test_performance = data.get("test_performance", "") if doc.test else ""
    doc.maths_test = data.get("maths_test", 0)
    doc.maths_test_performance = data.get("maths_test_performance", "") if doc.maths_test else ""
    doc.discipline = data.get("discipline", 0)
    doc.discipline_performance = data.get("discipline_performance", "") if doc.discipline else ""
    doc.bad_activities = data.get("bad_activities", "") if doc.discipline_performance == "Bad" else ""
    doc.critical_activities = data.get("critical_activities", "") if doc.discipline_performance == "Critical" else ""
    
    doc.save() if existing else doc.insert()
    return {"status": "success"}

@frappe.whitelist()
def get_activity_lists():
    return {
        "bad_activities": ["Talking in Class", "Not Doing Homework", "Late to Class", "Disrespectful", "Using Phone"],
        "critical_activities": ["Fighting", "Cheating", "Vandalism", "Bullying", "Skipping Class"]
    }
