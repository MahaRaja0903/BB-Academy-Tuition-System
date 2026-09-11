import frappe
from frappe.boot import get_bootinfo
import json

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    frappe.set_user("Administrator")
    bootinfo = get_bootinfo()
    print("DUMPING BOOTINFO")
    with open("bootinfo.json", "w") as f:
        f.write(json.dumps(bootinfo, default=str))
