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


# Masters a screen may add to on the spot. Each is a bare list whose docname is
# the value itself, so one Data field is the whole record.
#
# `requires` is the permission that actually governs the add, and it is
# deliberately not a DocPerm on the master itself. These masters are
# administered by System Manager, so an Attendance Manager granting an early
# out holds no create right on Early Exit Reason and would be refused -- the
# same mismatch get_options above exists to work around. Naming a reason is
# part of recording the attendance, so the attendance permission is what is
# checked, and the row is inserted with that authority.
ADDABLE = {
    "Early Exit Reason": {"fieldname": "reason", "requires": ("Student Attendance", "write")},
}


@frappe.whitelist()
def add_option(doctype, value):
    """Add one row to a lookup master, straight from the screen using it.

    Why a student left early is not always on a list somebody drew up months
    ago. Without this the receptionist has to abandon a half-filled form, open
    the desk, create the master and start again.
    """
    spec = ADDABLE.get(doctype)
    if not spec:
        # Anything outside the allowlist has to go through the
        # permission-checked APIs, not this one.
        frappe.throw(
            frappe._("{0} cannot be added to from here").format(doctype),
            frappe.PermissionError,
        )

    required_doctype, required_perm = spec["requires"]
    if not frappe.has_permission(required_doctype, required_perm):
        frappe.throw(frappe._("No permission to add a {0}").format(doctype))

    value = (value or "").strip()
    if not value:
        frappe.throw(frappe._("{0} cannot be blank").format(doctype))

    # The master names itself after the value, so an existing one is simply
    # handed back -- typing a reason that is already on the list picks it
    # rather than failing on a duplicate.
    if frappe.db.exists(doctype, value):
        return {"name": value}

    doc = frappe.get_doc({"doctype": doctype, spec["fieldname"]: value})
    doc.insert(ignore_permissions=True)
    return {"name": doc.name}


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
