<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Students Directory</h2>
        <p class="text-sm text-gray-500 mt-0.5">Manage and view registered tuition students</p>
      </div>

      <div class="flex items-center gap-3">
        <div class="relative w-64">
          <FeatherIcon name="search" class="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by name or ID..."
            class="w-full pl-9 pr-4 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-2xs"
          />
        </div>
        <button
          @click="studentsResource.reload()"
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
          title="Refresh List"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': studentsResource.loading }" />
        </button>
        <router-link
          to="/students/new"
          class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors"
        >
          <FeatherIcon name="plus" class="w-4 h-4" />
          <span>Add Student</span>
        </router-link>
      </div>
    </div>

    <!-- Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="studentsResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
        <span>Loading student records...</span>
      </div>

      <div v-else-if="filteredStudents.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">ID</th>
              <th class="py-3.5 px-6">Student Name</th>
              <th class="py-3.5 px-6">Parent Mobile</th>
              <th class="py-3.5 px-6">Admission Date</th>
              <th class="py-3.5 px-6">Status</th>
              <th class="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="student in filteredStudents"
              :key="student.name"
              class="hover:bg-emerald-50/20 transition-colors"
            >
              <td class="py-4 px-6 font-mono text-xs font-medium text-gray-500">
                {{ student.name }}
              </td>
              <td class="py-4 px-6 font-medium text-gray-900">
                <router-link :to="`/students/${student.name}`" class="hover:text-emerald-600">
                  {{ student.student_name }}
                </router-link>
              </td>
              <td class="py-4 px-6 text-gray-600">
                {{ student.parent_mobile || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-500 text-sm">
                {{ student.admission_date || '-' }}
              </td>
              <td class="py-4 px-6">
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
              </td>
              <td class="py-4 px-6 text-right">
                <router-link
                  :to="`/students/${student.name}`"
                  class="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1 rounded-md transition-colors"
                >
                  <span>View</span>
                  <FeatherIcon name="arrow-right" class="w-3 h-3" />
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="p-12 text-center text-gray-400">
        <FeatherIcon name="users" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No students found</p>
        <p class="text-xs text-gray-400 mt-1">Try adjusting your search criteria or register a new student.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createListResource } from 'frappe-ui'

const searchQuery = ref('')

const studentsResource = createListResource({
  doctype: 'Student',
  fields: ['name', 'student_name', 'parent_mobile', 'admission_date', 'status', 'whatsapp_number'],
  limit: 50,
  auto: true,
})

const filteredStudents = computed(() => {
  if (!studentsResource.data) return []
  if (!searchQuery.value.trim()) return studentsResource.data

  const q = searchQuery.value.toLowerCase()
  return studentsResource.data.filter(s =>
    s.name?.toLowerCase().includes(q) ||
    s.student_name?.toLowerCase().includes(q) ||
    s.parent_mobile?.includes(q)
  )
})
</script>
