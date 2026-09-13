import frappe

# Every dropdown on the attendance / performance screens is filled from one of
# these masters. They hold nothing but a list of names, and the screens are
# unusable without them -- but frappe.client.get_list enforces DocPerm, so a
# Teacher or Receptionist holding no permission on Late Entry Reason got a bare
# 403 and an empty picker. Serving them here keeps the read narrow instead:
# a fixed allowlist of doctypes, a fixed set of fields per doctype, and login
# is still required.
LOOKUPS = {
    "Standard": {"fields": ["name"], "order_by": "name asc"},
    "Batch": {"fields": ["name"], "order_by": "name asc"},
    "Late Entry Reason": {"fields": ["name"], "order_by": "name asc"},
    "Early Exit Reason": {"fields": ["name"], "order_by": "name asc"},
    "Academic Year": {"fields": ["name"], "order_by": "name desc"},
    # Who spoke from the tuition / which staff the parents met, on the
    # Student Mistakes screen.
    "Staff": {"fields": ["name"], "order_by": "name asc"},
    "Student": {
        "fields": ["name", "student_name"],
        "filters": {"status": "Active"},
        "order_by": "student_name asc",
    },
}


@frappe.whitelist()
def get_options(doctype):
    """Rows of one lookup master, without a DocPerm check.

    Returns [{"name": ...}] -- the same shape frappe.client.get_list returned,
    so callers only swap the method they hit.
    """
    spec = LOOKUPS.get(doctype)
    if not spec:
        # Not a refusal to be worked around by the caller -- anything outside
        # the allowlist has to go through the permission-checked APIs.
        frappe.throw(
            frappe._("{0} is not a lookup doctype").format(doctype),
            frappe.PermissionError,
        )

    # A master may not be installed yet on a site mid-migrate. An empty picker
    # is a better answer there than a traceback.
    if not frappe.db.exists("DocType", doctype):
        return []

    return frappe.get_all(
        doctype,
        fields=spec["fields"],
        filters=spec.get("filters") or {},
        order_by=spec.get("order_by"),
        limit_page_length=0,
        ignore_permissions=True,
    )
