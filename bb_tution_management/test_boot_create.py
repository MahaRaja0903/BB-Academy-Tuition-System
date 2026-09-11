import frappe
from frappe.boot import get_bootinfo

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    frappe.set_user("Administrator")
    bootinfo = get_bootinfo()
    print("DocType in can_create:", "DocType" in bootinfo.user.can_create)
