import { createRouter, createWebHistory } from 'vue-router'

import AttendanceAppLayout from '@/components/AttendanceAppLayout.vue'
import AttendanceManager from '@/pages/AttendanceManager.vue'
import AttendanceDashboard from '@/pages/AttendanceDashboard.vue'
import LatePermission from '@/pages/LatePermission.vue'
import AttendanceReports from '@/pages/AttendanceReports.vue'
import Login from '@/pages/Login.vue'
import { sessionUser } from '@/data/session'
import { userResource } from '@/data/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: 'Login - BB Attendance Manager', guestOnly: true },
  },
  {
    path: '/',
    component: AttendanceAppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'AttendanceManager',
        component: AttendanceManager,
        meta: { title: 'Attendance Manager' },
      },
      {
        path: 'dashboard',
        name: 'AttendanceDashboard',
        component: AttendanceDashboard,
        meta: { title: 'Attendance Dashboard' },
      },
      {
        path: 'late-permission',
        name: 'LatePermission',
        component: LatePermission,
        meta: { title: 'Late Permission' },
      },
      {
        path: 'reports',
        name: 'AttendanceReports',
        component: AttendanceReports,
        meta: { title: 'Reports' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.DEV ? '/' : '/attendance_manager'),
  routes,
})

const fetchUserWithTimeout = async () => {
  if (!userResource.promise) return sessionUser()
  try {
    const timeout = new Promise((resolve) => setTimeout(() => resolve(null), 1000))
    const user = await Promise.race([userResource.promise, timeout])
    return user || sessionUser()
  } catch (e) {
    return sessionUser()
  }
}

router.beforeEach(async (to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - BB Attendance Manager` : 'BB Attendance Manager'
  try {
    const user = await fetchUserWithTimeout()

    if (to.meta.requiresAuth && !user) {
      next({ name: 'Login' })
    } else if (to.meta.guestOnly && user) {
      next({ name: 'AttendanceManager' })
    } else {
      next()
    }
  } catch (error) {
    console.error('Router guard error:', error)
    if (to.meta.requiresAuth) {
      next({ name: 'Login' })
    } else {
      next()
    }
  }
})

export default router
