import frappe

def test():
    active_academic_years = frappe.get_all("Academic Year", filters={"is_active": 1}, pluck="name")
    print("Active academic years:", active_academic_years)

    if active_academic_years:
        academic_year = frappe.db.get_value(
            "Standard Detail",
            {
                "parent": ["in", active_academic_years],
                "parenttype": "Academic Year",
                "parentfield": "standard_applicable",
                "standard": "8th Standard"
            },
            "parent"
        )
        print("Fetched Academic Year:", academic_year)
