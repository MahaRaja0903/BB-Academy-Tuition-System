import frappe

def get_batches():
    return frappe.client.get_list(doctype="Batch", fields=["name"], limit_page_length=0)
