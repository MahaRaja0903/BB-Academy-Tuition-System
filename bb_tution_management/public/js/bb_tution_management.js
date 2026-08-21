/* ═══════════════════════════════════════════════════════════════════════
   BB Academy — Global Desk Script
   ───────────────────────────────────────────────────────────────────────
   Overrides the default routing behavior to force the custom dashboard
   as the primary home page, circumventing Frappe's Workspace-only logic.
   ═══════════════════════════════════════════════════════════════════════ */

// Ensure this runs after the router is initialized
$(document).on('ready', function() {
	if (!frappe.router) return;

	// 1. Force the logo link in the navbar to point to our dashboard
	// We bind to route change to ensure it stays overridden if Vue re-renders the navbar
	frappe.router.on('change', () => {
		const $brand = $('.navbar-brand');
		if ($brand.length) {
			$brand.attr('href', '/app/bb-dashboard');
		}
	});

	// Initial set
	setTimeout(() => {
		$('.navbar-brand').attr('href', '/app/bb-dashboard');
	}, 100);

	// 2. Intercept the router's "empty" path resolution
	// Frappe v14+ defaults `/app` to a workspace. We override make_url to point to our page.
	const original_make_url = frappe.router.make_url;
	frappe.router.make_url = function(params) {
		if (!params || params.length === 0 || params.join("") === "") {
			return "/app/bb-dashboard";
		}
		return original_make_url.apply(this, arguments);
	};
});

/* ═══════════════════════════════════════════════════════════════════════
   BB Academy — PWA Registration
   ═══════════════════════════════════════════════════════════════════════ */
$(document).on('ready', function() {
    // Inject Manifest Link
    if (!$("link[rel='manifest']").length) {
        $('<link>')
            .appendTo('head')
            .attr({
                type: 'application/manifest+json',
                rel: 'manifest',
                href: '/assets/bb_tution_management/manifest.json'
            });
    }

    // Inject Theme Color
    if (!$("meta[name='theme-color']").length) {
        $('<meta>')
            .appendTo('head')
            .attr({
                name: 'theme-color',
                content: '#FFD700'
            });
    }

    // Register Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/api/method/bb_tution_management.api.sw', { scope: '/' })
                .then(function(registration) {
                    console.log('BB Academy PWA SW registered with scope:', registration.scope);
                }, function(err) {
                    console.log('BB Academy PWA SW registration failed:', err);
                });
        });
    }
});
