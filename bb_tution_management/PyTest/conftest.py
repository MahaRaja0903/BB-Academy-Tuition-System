# These are ad-hoc scripts run manually via `bench execute`, not pytest test cases.
# Several of them call frappe.init()/frappe.connect() or hit the database at import
# time, so keep them out of automatic test collection.
collect_ignore_glob = ["test_*.py"]
