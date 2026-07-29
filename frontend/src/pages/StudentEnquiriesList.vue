<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Student Enquiries</h2>
        <p class="text-sm text-gray-500 mt-0.5">Manage new admissions and student enquiries</p>
      </div>

      <div class="flex items-center gap-3">
        <button 
          @click="enquiriesResource.reload()" 
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': enquiriesResource.loading }" />
        </button>
      </div>
    </div>

    <!-- Enquiries Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="enquiriesResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
        <span>Loading enquiries...</span>
      </div>

      <div v-else-if="enquiriesResource.data && enquiriesResource.data.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">Enquiry ID</th>
              <th class="py-3.5 px-6">Applicant Name</th>
              <th class="py-3.5 px-6">Parent Mobile</th>
              <th class="py-3.5 px-6">Standard</th>
              <th class="py-3.5 px-6">Enquiry Date</th>
              <th class="py-3.5 px-6">Status</th>
              <th class="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="enquiry in enquiriesResource.data"
              :key="enquiry.name"
              class="hover:bg-blue-50/20 transition-colors"
            >
              <td class="py-4 px-6 font-mono text-xs font-medium text-gray-900">
                {{ enquiry.name }}
              </td>
              <td class="py-4 px-6 font-medium text-gray-800">
                {{ enquiry.applicant_name || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-600">
                {{ enquiry.parent_mobile || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-700">
                {{ enquiry.standard || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-500 text-sm">
                {{ enquiry.enquiry_date || '-' }}
              </td>
              <td class="py-4 px-6">
                <span
                  :class="{
                    'bg-emerald-50 text-emerald-700 border-emerald-200': enquiry.status === 'Converted',
                    'bg-amber-50 text-amber-700 border-amber-200': enquiry.status === 'Follow-up',
                    'bg-blue-50 text-blue-700 border-blue-200': enquiry.status === 'New',
                    'bg-red-50 text-red-700 border-red-200': enquiry.status === 'Lost',
                    'bg-gray-50 text-gray-700 border-gray-200': !enquiry.status
                  }"
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
                >
                  {{ enquiry.status || 'New' }}
                </span>
              </td>
              <td class="py-4 px-6 text-right">
                <a
                  :href="`/app/student-enquiry-form/${enquiry.name}`"
                  target="_blank"
                  class="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded-md transition-colors"
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
        <FeatherIcon name="help-circle" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No student enquiries recorded</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const enquiriesResource = createListResource({
  doctype: 'Student Enquiry Form',
  fields: ['name', 'applicant_name', 'parent_mobile', 'enquiry_date', 'status', 'standard'],
  limit: 100,
  auto: true,
})
</script>
