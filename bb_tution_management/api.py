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
const CACHE_NAME = 'bb-attendance-manager-pwa-v1';
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
