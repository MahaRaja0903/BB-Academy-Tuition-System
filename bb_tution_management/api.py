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
