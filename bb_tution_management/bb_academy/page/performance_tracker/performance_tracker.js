// The Student Performance Manager now lives in the attendance PWA at
// /attendance_manager/performance — it is the only build that implements the
// per-category model (Study / Test / Maths Test / Behaviour) that
// bb_academy/performance.py serves. This desk page kept the earlier
// checkbox-per-category prototype and its API is gone, so it forwards on
// instead of rendering a screen that can no longer save anything.
const PERFORMANCE_MANAGER_ROUTE = '/attendance_manager/performance'

frappe.pages['performance-tracker'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Student Performance Manager',
		single_column: true,
	})

	page.set_primary_action(__('Open Performance Manager'), () => {
		window.location.href = PERFORMANCE_MANAGER_ROUTE
	})

	$(wrapper).find('.layout-main-section').html(`
		<div class="text-center" style="padding: 60px 20px;">
			<div style="font-size: 40px; color: var(--gray-400); margin-bottom: 14px;">
				<i class="fa fa-star"></i>
			</div>
			<h4 style="margin-bottom: 8px;">${__('The Performance Manager has moved')}</h4>
			<p class="text-muted" style="max-width: 460px; margin: 0 auto 20px;">
				${__(
					'Record Study, Test, Maths Test and Behaviour from the Performance Manager — the same Standard, Batch, Gender and date filters as the Attendance Manager.'
				)}
			</p>
			<a class="btn btn-primary" href="${PERFORMANCE_MANAGER_ROUTE}">
				${__('Open Performance Manager')}
			</a>
		</div>
	`)
}
