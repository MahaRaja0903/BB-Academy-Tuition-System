import frappe
def run():
    try:
        from bb_tution_management.bb_academy.report.payment_report.payment_report import execute
        cols, data, *_ = execute()
        print("SUCCESS", data[0])
    except Exception as e:
        import traceback
        traceback.print_exc()
