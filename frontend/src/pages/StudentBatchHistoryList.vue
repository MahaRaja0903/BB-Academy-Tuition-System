<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Student Batch History</h2>
        <p class="text-sm text-gray-500 mt-0.5">Track student batch transfers and changes</p>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="batchHistoryResource.reload()"
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': batchHistoryResource.loading }" />
        </button>
      </div>
    </div>

    <!-- Batch History Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="batchHistoryResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
        <span>Loading batch history...</span>
      </div>

      <div v-else-if="batchHistoryResource.data && batchHistoryResource.data.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">ID</th>
              <th class="py-3.5 px-6">Student</th>
              <th class="py-3.5 px-6">Previous Batch</th>
              <th class="py-3.5 px-6">New Batch</th>
              <th class="py-3.5 px-6">Effective Date</th>
              <th class="py-3.5 px-6">Approved By</th>
              <th class="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="history in batchHistoryResource.data"
              :key="history.name"
              class="hover:bg-indigo-50/20 transition-colors"
            >
              <td class="py-4 px-6 font-mono text-xs font-medium text-gray-900">
                {{ history.name }}
              </td>
              <td class="py-4 px-6 font-medium text-gray-800">
                {{ history.student || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-600">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                  {{ history.previous_batch || '-' }}
                </span>
              </td>
              <td class="py-4 px-6 text-gray-600">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ history.new_batch || '-' }}
                </span>
              </td>
              <td class="py-4 px-6 text-gray-500 text-sm">
                {{ history.effective_date || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-700 text-sm">
                {{ history.approved_by || '-' }}
              </td>
              <td class="py-4 px-6 text-right">
                <a
                  :href="`/app/student-batch-history/${history.name}`"
                  target="_blank"
                  class="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1 rounded-md transition-colors"
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
        <FeatherIcon name="git-branch" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No batch history records</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const batchHistoryResource = createListResource({
  doctype: 'Student Batch History',
  fields: ['name', 'student', 'previous_batch', 'new_batch', 'effective_date', 'approved_by', 'reason'],
  limit: 100,
  auto: true,
})
</script>
