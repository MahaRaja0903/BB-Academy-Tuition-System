import router from '@/router'
import { createResource } from 'frappe-ui'

export const userResource = createResource({
  url: 'frappe.auth.get_logged_user',
  cache: 'AttendanceUser',
  auto: true,
  onError(error) {
    console.error('User resource error:', error)
    if (error && (error.exc_type === 'AuthenticationError' || !navigator.onLine)) {
      router.push({ name: 'Login' }).catch(() => {})
    }
  },
})
