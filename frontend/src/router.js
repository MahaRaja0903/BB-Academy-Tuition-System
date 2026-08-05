import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/components/Layouts/AppLayout.vue'
import Dashboard from '@/pages/Dashboard.vue'
import StudentsList from '@/pages/StudentsList.vue'
import FeeInvoicesList from '@/pages/FeeInvoicesList.vue'
import StudentEnquiriesList from '@/pages/StudentEnquiriesList.vue'
import StudentDetail from '@/pages/StudentDetail.vue'
import StudentBatchHistoryList from '@/pages/StudentBatchHistoryList.vue'
import StudentAdmissionFormsList from '@/pages/StudentAdmissionFormsList.vue'
import CreateStudent from '@/pages/CreateStudent.vue'
import PromotionDemotionReport from '@/pages/PromotionDemotionReport.vue'
import StudentWiseReport from '@/pages/StudentWiseReport.vue'
import Login from '@/pages/Login.vue'
import { sessionUser } from '@/data/session'
import { userResource } from '@/data/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: 'Login - BB Academy', guestOnly: true },
  },
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: 'Dashboard' },
      },
      {
        path: 'students',
        name: 'StudentsList',
        component: StudentsList,
        meta: { title: 'Students' },
      },
      {
        path: 'students/new',
        name: 'CreateStudent',
        component: CreateStudent,
        meta: { title: 'Create Student' },
      },
      {
        path: 'students/:name',
        name: 'StudentDetail',
        component: StudentDetail,
        meta: { title: 'Student Detail' },
      },
      {
        path: 'fee-invoices',
        name: 'FeeInvoicesList',
        component: FeeInvoicesList,
        meta: { title: 'Fee Invoices' },
      },
      {
        path: 'student-enquiries',
        name: 'StudentEnquiriesList',
        component: StudentEnquiriesList,
        meta: { title: 'Student Enquiries' },
      },
      {
        path: 'student-batch-history',
        name: 'StudentBatchHistoryList',
        component: StudentBatchHistoryList,
        meta: { title: 'Student Batch History' },
      },
      {
        path: 'student-admission-forms',
        name: 'StudentAdmissionFormsList',
        component: StudentAdmissionFormsList,
        meta: { title: 'Student Admission Forms' },
      },
      {
        path: 'promotion-demotion-report',
        name: 'PromotionDemotionReport',
        component: PromotionDemotionReport,
        meta: { title: 'Promotion & Demotion Report' },
      },
      {
        path: 'student-wise-report',
        name: 'StudentWiseReport',
        component: StudentWiseReport,
        meta: { title: 'Student Wise Report' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.DEV ? '/' : '/tuition_app'),
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
  try {
    const user = await fetchUserWithTimeout()

    if (to.meta.requiresAuth && !user) {
      next({ name: 'Login' })
    } else if (to.meta.guestOnly && user) {
      next({ name: 'Dashboard' })
    } else {
      next()
    }
  } catch (error) {
    console.error('Router guard error:', error)
    // If there's an error and trying to access protected route, go to login
    if (to.meta.requiresAuth) {
      next({ name: 'Login' })
    } else {
      next()
    }
  }
})

export default router
