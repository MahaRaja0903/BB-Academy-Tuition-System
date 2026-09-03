import frappe
def test():
    from bb_tution_management.bb_academy.report.payment_report.payment_report import execute
    try:
        columns, data, *_ = execute()
        for row in data[:2]:
            if not row.get("is_summary"):
                print("Payment Time:", row.get("payment_time"), "type:", type(row.get("payment_time")))
    except Exception as e:
        import traceback
        traceback.print_exc()

