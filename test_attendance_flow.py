import frappe
from bb_tution_management.bb_academy.attendance import get_attendance_students, save_student_attendance, get_attendance_dashboard_data

def test_flow():
    # 1. Test get_attendance_students with empty standard
    print("Testing get_attendance_students...")
    res = get_attendance_students("10th", "Batch A", "2026-08-20")
    print("Result students count:", len(res["students"]))
    
    # 2. Test get_attendance_dashboard_data
    print("Testing get_attendance_dashboard_data...")
    dash = get_attendance_dashboard_data(None, "10th", "Batch A", "2026-08-20")
    print("Dashboard keys:", dash.keys())
    
    print("Flow tests passed.")

if __name__ == "__main__":
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    try:
        test_flow()
    except Exception as e:
        print("Error:", e)
    finally:
        frappe.destroy()
