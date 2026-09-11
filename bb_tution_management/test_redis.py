import frappe
def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    meta_cache = frappe.cache.get_value("meta:BB SMS Settings")
    if meta_cache:
        print("FOUND IN REDIS!")
    else:
        print("NOT IN REDIS!")
        
    doc_cache = frappe.cache.get_value("document_cache::DocType::BB SMS Settings")
    if doc_cache:
        print("FOUND DOCTYPE CACHE!")
