<template>
  <div class="space-y-6">
    <!-- Welcome Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Tuition Overview</h2>
        <p class="text-sm text-gray-500 mt-0.5">Welcome to BB Tuition Management Portal</p>
      </div>
      <div class="flex gap-3">
        <router-link
          to="/students/new"
          class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors"
        >
          <FeatherIcon name="user-plus" class="w-4 h-4" />
          <span>New Student</span>
        </router-link>
        <router-link
          to="/payment-entries/new"
          class="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors"
        >
          <FeatherIcon name="dollar-sign" class="w-4 h-4" />
          <span>New Payment</span>
        </router-link>
      </div>
    </div>

    <!-- Stat Cards Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <div class="bg-white p-5 rounded-xl border border-gray-200 shadow-2xs">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Students</span>
          <div class="p-2 bg-emerald-50 rounded-lg text-emerald-600">
            <FeatherIcon name="users" class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-3xl font-bold text-gray-900">{{ studentCount }}</div>
          <div class="text-xs text-emerald-600 mt-1 font-medium flex items-center gap-1">
            <FeatherIcon name="trending-up" class="w-3.5 h-3.5" />
            <span>Active Enrolments</span>
          </div>
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-gray-200 shadow-2xs">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Enquiries</span>
          <div class="p-2 bg-blue-50 rounded-lg text-blue-600">
            <FeatherIcon name="help-circle" class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-3xl font-bold text-gray-900">{{ enquiryCount }}</div>
          <div class="text-xs text-gray-500 mt-1">Pending follow-ups</div>
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-gray-200 shadow-2xs">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Fee Invoices</span>
          <div class="p-2 bg-purple-50 rounded-lg text-purple-600">
            <FeatherIcon name="file-text" class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-3xl font-bold text-gray-900">{{ invoiceCount }}</div>
          <div class="text-xs text-purple-600 mt-1 font-medium">Invoices Issued</div>
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-gray-200 shadow-2xs">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Payment Records</span>
          <div class="p-2 bg-amber-50 rounded-lg text-amber-600">
            <FeatherIcon name="credit-card" class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-3xl font-bold text-gray-900">{{ paymentCount }}</div>
          <div class="text-xs text-amber-600 mt-1 font-medium">Payments Processed</div>
        </div>
      </div>
    </div>

    <!-- Quick Shortcuts & Recent Students Table -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Students List (2 columns) -->
      <div class="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="font-semibold text-gray-900">Recent Students</h3>
          <router-link to="/students" class="text-xs font-semibold text-emerald-600 hover:text-emerald-700">View All →</router-link>
        </div>
        
        <div v-if="studentsList.loading" class="p-8 text-center text-gray-400 text-sm">
          Loading students...
        </div>
        
        <div v-else-if="studentsList.data && studentsList.data.length" class="divide-y divide-gray-100">
          <div
            v-for="student in studentsList.data.slice(0, 5)"
            :key="student.name"
            class="px-6 py-3.5 flex items-center justify-between hover:bg-gray-50/50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-emerald-100 text-emerald-700 font-semibold flex items-center justify-center text-sm">
                {{ (student.student_name || student.name).charAt(0).toUpperCase() }}
              </div>
              <div>
                <router-link :to="`/students/${student.name}`" class="text-sm font-medium text-gray-900 hover:text-emerald-600">
                  {{ student.student_name }}
                </router-link>
                <div class="text-xs text-gray-500">{{ student.name }} • {{ student.parent_mobile || 'No phone' }}</div>
              </div>
            </div>
            <span
              :class="{
                'bg-emerald-50 text-emerald-700 border-emerald-200': student.status === 'Active',
                'bg-blue-50 text-blue-700 border-blue-200': student.status === 'Completed',
                'bg-red-50 text-red-700 border-red-200': student.status === 'Dropped'
              }"
              class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
            >
              {{ student.status || 'Active' }}
            </span>
          </div>
        </div>

        <div v-else class="p-8 text-center text-gray-400 text-sm">
          No student records found.
        </div>
      </div>

      <!-- Quick Actions Sidebar -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-2xs p-5 space-y-4">
        <h3 class="font-semibold text-gray-900 border-b border-gray-100 pb-3">Quick Navigation</h3>
        <div class="space-y-2">
          <router-link 
            to="/students" 
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-emerald-200 hover:bg-emerald-50/30 transition-all group"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 bg-emerald-50 text-emerald-600 rounded-lg group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                <FeatherIcon name="users" class="w-4 h-4" />
              </div>
              <span class="text-sm font-medium text-gray-800">Student Directory</span>
            </div>
            <FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400 group-hover:text-emerald-600" />
          </router-link>

          <router-link 
            to="/fee-invoices" 
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-purple-200 hover:bg-purple-50/30 transition-all group"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 bg-purple-50 text-purple-600 rounded-lg group-hover:bg-purple-600 group-hover:text-white transition-colors">
                <FeatherIcon name="file-text" class="w-4 h-4" />
              </div>
              <span class="text-sm font-medium text-gray-800">Fee Invoices</span>
            </div>
            <FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400 group-hover:text-purple-600" />
          </router-link>

          <router-link 
            to="/student-enquiries" 
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all group"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 bg-blue-50 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <FeatherIcon name="help-circle" class="w-4 h-4" />
              </div>
              <span class="text-sm font-medium text-gray-800">Enquiry Forms</span>
            </div>
            <FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
          </router-link>

          <router-link
            to="/payment-entries"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-amber-200 hover:bg-amber-50/30 transition-all group"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 bg-amber-50 text-amber-600 rounded-lg group-hover:bg-amber-600 group-hover:text-white transition-colors">
                <FeatherIcon name="credit-card" class="w-4 h-4" />
              </div>
              <span class="text-sm font-medium text-gray-800">Payments Log</span>
            </div>
            <FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400 group-hover:text-amber-600" />
          </router-link>

          <router-link
            to="/student-batch-history"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all group"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 bg-indigo-50 text-indigo-600 rounded-lg group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <FeatherIcon name="git-branch" class="w-4 h-4" />
              </div>
              <span class="text-sm font-medium text-gray-800">Batch History</span>
            </div>
            <FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400 group-hover:text-indigo-600" />
          </router-link>

          <router-link
            to="/student-admission-forms"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-teal-200 hover:bg-teal-50/30 transition-all group"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 bg-teal-50 text-teal-600 rounded-lg group-hover:bg-teal-600 group-hover:text-white transition-colors">
                <FeatherIcon name="file-plus" class="w-4 h-4" />
              </div>
              <span class="text-sm font-medium text-gray-800">Admission Forms</span>
            </div>
            <FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400 group-hover:text-teal-600" />
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createListResource } from 'frappe-ui'

const studentsList = createListResource({
  doctype: 'Student',
  fields: ['name', 'student_name', 'parent_mobile', 'admission_date', 'status'],
  limit: 10,
  auto: true,
})

const enquiriesList = createListResource({
  doctype: 'Student Enquiry Form',
  fields: ['name'],
  limit: 1000,
  auto: true,
})

const invoicesList = createListResource({
  doctype: 'Fee Invoice',
  fields: ['name'],
  limit: 1000,
  auto: true,
})

const paymentsList = createListResource({
  doctype: 'Payment Entry',
  fields: ['name'],
  limit: 1000,
  auto: true,
})

// Use list_rows for accurate total count, fallback to data length
const studentCount = computed(() => {
  if (studentsList.list && studentsList.list.total_count !== undefined) {
    return studentsList.list.total_count
  }
  return studentsList.data?.length || 0
})

const enquiryCount = computed(() => {
  if (enquiriesList.list && enquiriesList.list.total_count !== undefined) {
    return enquiriesList.list.total_count
  }
  return enquiriesList.data?.length || 0
})

const invoiceCount = computed(() => {
  if (invoicesList.list && invoicesList.list.total_count !== undefined) {
    return invoicesList.list.total_count
  }
  return invoicesList.data?.length || 0
})

const paymentCount = computed(() => {
  if (paymentsList.list && paymentsList.list.total_count !== undefined) {
    return paymentsList.list.total_count
  }
  return paymentsList.data?.length || 0
})
</script>
