<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Student Admission Forms</h2>
        <p class="text-sm text-gray-500 mt-0.5">Manage student admission applications</p>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="admissionFormsResource.reload()"
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': admissionFormsResource.loading }" />
        </button>
      </div>
    </div>

    <!-- Admission Forms Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="admissionFormsResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-teal-600" />
        <span>Loading admission forms...</span>
      </div>

      <div v-else-if="admissionFormsResource.data && admissionFormsResource.data.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">Form ID</th>
              <th class="py-3.5 px-6">Student Name</th>
              <th class="py-3.5 px-6">Admission Number</th>
              <th class="py-3.5 px-6">Standard</th>
              <th class="py-3.5 px-6">Application Date</th>
              <th class="py-3.5 px-6">Status</th>
              <th class="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="form in admissionFormsResource.data"
              :key="form.name"
              class="hover:bg-teal-50/20 transition-colors"
            >
              <td class="py-4 px-6 font-mono text-xs font-medium text-gray-900">
                {{ form.name }}
              </td>
              <td class="py-4 px-6 font-medium text-gray-800">
                {{ form.student_name || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-700 font-mono text-xs">
                {{ form.admission_number || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-700">
                {{ form.standard || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-500 text-sm">
                {{ form.application_date || '-' }}
              </td>
              <td class="py-4 px-6">
                <span
                  :class="{
                    'bg-emerald-50 text-emerald-700 border-emerald-200': form.status === 'Approved',
                    'bg-amber-50 text-amber-700 border-amber-200': form.status === 'Pending',
                    'bg-red-50 text-red-700 border-red-200': form.status === 'Rejected',
                    'bg-blue-50 text-blue-700 border-blue-200': form.status === 'Submitted',
                    'bg-gray-50 text-gray-700 border-gray-200': !form.status
                  }"
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
                >
                  {{ form.status || 'Draft' }}
                </span>
              </td>
              <td class="py-4 px-6 text-right">
                <a
                  :href="`/app/student-admission-form/${form.name}`"
                  target="_blank"
                  class="inline-flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 bg-teal-50 hover:bg-teal-100 px-3 py-1 rounded-md transition-colors"
                >
                  <span>Open</span>
                  <FeatherIcon name="external-link" class="w-3 h-3" />
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="p-12 text-center text-gray-400">
        <FeatherIcon name="file-plus" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No admission forms recorded</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const admissionFormsResource = createListResource({
  doctype: 'Student Admission Form',
  fields: ['name', 'student_name', 'admission_number', 'standard', 'application_date', 'status', 'academic_year'],
  limit: 100,
  auto: true,
})
</script>
