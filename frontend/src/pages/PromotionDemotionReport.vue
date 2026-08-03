<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Student Promotion & Demotion Report</h2>
        <p class="text-sm text-gray-500 mt-0.5">Track and filter student batch movements</p>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="batchHistoryResource.reload()"
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
          title="Refresh Data"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': batchHistoryResource.loading }" />
        </button>
      </div>
    </div>

    <!-- Filters Section -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs p-5">
      <div class="flex flex-col sm:flex-row gap-4 items-end">
        <div class="flex-1 w-full">
          <label class="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">Month</label>
          <input 
            type="month" 
            v-model="filters.month"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
          />
        </div>
        
        <div class="flex-1 w-full">
          <label class="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">Student ID</label>
          <input 
            type="text" 
            v-model="filters.student"
            placeholder="Search by student..."
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
          />
        </div>

        <div class="flex-1 w-full">
          <label class="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">Status</label>
          <select 
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors bg-white"
          >
            <option value="">All Statuses</option>
            <option value="Promotion">Promotion</option>
            <option value="Demotion">Demotion</option>
          </select>
        </div>

        <div class="flex-none">
          <button 
            @click="clearFilters"
            class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition-colors"
          >
            Clear Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Summary Stats Card -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="flex items-center p-4 bg-white border border-emerald-100 rounded-xl shadow-2xs">
        <div class="p-3 bg-emerald-100 text-emerald-600 rounded-lg mr-4">
          <FeatherIcon name="trending-up" class="w-6 h-6" />
        </div>
        <div>
          <p class="text-sm font-medium text-gray-500">Total Promotions</p>
          <h4 class="text-2xl font-bold text-gray-900">{{ summaryStats.promotions }}</h4>
        </div>
      </div>
      
      <div class="flex items-center p-4 bg-white border border-rose-100 rounded-xl shadow-2xs">
        <div class="p-3 bg-rose-100 text-rose-600 rounded-lg mr-4">
          <FeatherIcon name="trending-down" class="w-6 h-6" />
        </div>
        <div>
          <p class="text-sm font-medium text-gray-500">Total Demotions</p>
          <h4 class="text-2xl font-bold text-gray-900">{{ summaryStats.demotions }}</h4>
        </div>
      </div>
    </div>

    <!-- Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="batchHistoryResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
        <span>Loading report data...</span>
      </div>

      <div v-else-if="filteredData.length > 0" class="overflow-x-auto max-h-[500px]">
        <table class="w-full text-left text-sm border-collapse">
          <thead class="sticky top-0 bg-white shadow-sm z-10">
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">ID</th>
              <th class="py-3.5 px-6">Student</th>
              <th class="py-3.5 px-6">Effective Date</th>
              <th class="py-3.5 px-6">Status</th>
              <th class="py-3.5 px-6">Previous Batch</th>
              <th class="py-3.5 px-6">New Batch</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="history in filteredData"
              :key="history.name"
              class="hover:bg-indigo-50/20 transition-colors"
            >
              <td class="py-3 px-6 font-mono text-xs font-medium text-gray-900">
                {{ history.name }}
              </td>
              <td class="py-3 px-6 font-medium text-gray-800">
                {{ history.student || '-' }}
              </td>
              <td class="py-3 px-6 text-gray-600">
                {{ history.effective_date || '-' }}
              </td>
              <td class="py-3 px-6">
                <span 
                  class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border"
                  :class="history.status === 'Promotion' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'"
                >
                  {{ history.status || 'Unknown' }}
                </span>
              </td>
              <td class="py-3 px-6 text-gray-500">
                {{ history.previous_batch || '-' }}
              </td>
              <td class="py-3 px-6 text-gray-900 font-medium">
                {{ history.new_batch || '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="p-12 text-center text-gray-400">
        <FeatherIcon name="search" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No data matches your filters</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { createListResource } from 'frappe-ui'

const filters = reactive({
  month: '',
  student: '',
  status: ''
})

const clearFilters = () => {
  filters.month = ''
  filters.student = ''
  filters.status = ''
}

const batchHistoryResource = createListResource({
  doctype: 'Student Batch History',
  fields: ['name', 'student', 'previous_batch', 'new_batch', 'effective_date', 'status'],
  limit: 1000,
  auto: true,
})

const filteredData = computed(() => {
  let data = batchHistoryResource.data || []
  
  if (filters.month) {
    data = data.filter(item => {
      if (!item.effective_date) return false
      return item.effective_date.startsWith(filters.month)
    })
  }
  
  if (filters.student) {
    const studentSearch = filters.student.toLowerCase()
    data = data.filter(item => 
      item.student && item.student.toLowerCase().includes(studentSearch)
    )
  }
  
  if (filters.status) {
    data = data.filter(item => item.status === filters.status)
  }
  
  return data
})

const summaryStats = computed(() => {
  let promotions = 0
  let demotions = 0
  
  filteredData.value.forEach(history => {
    if (history.status === 'Promotion') promotions++
    if (history.status === 'Demotion') demotions++
  })
  
  return { promotions, demotions }
})
</script>
