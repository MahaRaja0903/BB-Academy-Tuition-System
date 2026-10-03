import frappe
from werkzeug.wrappers import Response

@frappe.whitelist(allow_guest=True)
def sw():
    js_content = """
const CACHE_NAME = 'bb-academy-pwa-v1';
const urlsToCache = [
  '/',
  '/app',
  '/login'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});
"""
    return Response(js_content, mimetype="application/javascript", headers={"Service-Worker-Allowed": "/"})


@frappe.whitelist(allow_guest=True)
def sw_attendance():
    js_content = """
const CACHE_NAME = 'bb-student-manager-pwa-v1';
const urlsToCache = [
  '/attendance_manager',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))
    )
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
"""
    return Response(js_content, mimetype="application/javascript", headers={"Service-Worker-Allowed": "/attendance_manager/"})

@frappe.whitelist(allow_guest=True)
def get_student_details_for_form(student_id):
    if not frappe.db.exists("Student", student_id):
        return {"status": "error", "message": "Student not found."}
        
    student = frappe.get_doc("Student", student_id)
    return {
        "status": "success",
        "data": {
            "student_name": student.student_name,
            "standard": student.standard,
            "current_batch": student.current_batch,
            "father_occupation": student.father_occupation,
            "mother_occupation": student.mother_occupation,
            "skills_any": student.skills_any,
            "achievement": student.achievement,
            "preferred_mobile_number": student.preferred_mobile_number
        }
    }

@frappe.whitelist(allow_guest=True)
def update_student_parent_info(student_id, father_occupation, mother_occupation, latitude=None, longitude=None, skills_any=None, achievement=None, preferred_mobile_number=None):
    if not frappe.db.exists("Student", student_id):
        return {"status": "error", "message": "Student not found."}
        
    doc = frappe.get_doc("Student", student_id)
    doc.father_occupation = father_occupation
    doc.mother_occupation = mother_occupation
    
    if skills_any is not None:
        doc.skills_any = skills_any
    if achievement is not None:
        doc.achievement = achievement
    if preferred_mobile_number is not None:
        doc.preferred_mobile_number = preferred_mobile_number
        
    if latitude and longitude:
        doc.latitude = latitude
        doc.longitude = longitude
        
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"status": "success", "message": "Information updated successfully."}
