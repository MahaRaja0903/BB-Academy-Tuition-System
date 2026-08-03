<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
          <FeatherIcon name="file-text" class="w-6 h-6" />
        </div>
        <div>
          <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Student Wise Report</h2>
          <p class="text-sm text-gray-500 mt-0.5">Filter and generate detailed student reports</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="studentsResource.reload()"
          class="p-2.5 border border-gray-200 bg-white hover:bg-indigo-50 hover:border-indigo-200 rounded-xl text-gray-600 hover:text-indigo-600 transition-all shadow-sm"
          title="Refresh Data"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': studentsResource.loading }" />
        </button>
      </div>
    </div>

    <!-- Filters Section -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 relative overflow-hidden">
      <div class="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-bl-full opacity-50 pointer-events-none"></div>
      
      <div class="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <!-- Gender -->
        <div>
          <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Gender</label>
          <select 
            v-model="filters.gender"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-white hover:border-gray-300"
          >
            <option value="">All Genders</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
        </div>

        <!-- Date Range -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Start Date</label>
            <input 
              type="date" 
              v-model="filters.startDate"
              class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all hover:border-gray-300"
            />
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">End Date</label>
            <input 
              type="date" 
              v-model="filters.endDate"
              class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all hover:border-gray-300"
            />
          </div>
        </div>

        <!-- Standard -->
        <div>
          <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Standard</label>
          <input 
            type="text" 
            v-model="filters.standard"
            placeholder="e.g. 10th"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all hover:border-gray-300"
          />
        </div>

        <!-- Batch -->
        <div>
          <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Batch</label>
          <input 
            type="text" 
            v-model="filters.batch"
            placeholder="e.g. Batch A"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all hover:border-gray-300"
          />
        </div>

        <!-- School -->
        <div>
          <label class="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">School</label>
          <div class="flex gap-3">
            <input 
              type="text" 
              v-model="filters.school"
              placeholder="Search school name..."
              class="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all hover:border-gray-300"
            />
            <button 
              @click="clearFilters"
              class="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold rounded-xl transition-colors flex items-center justify-center whitespace-nowrap"
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Table -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden relative">
      <div v-if="studentsResource.loading" class="p-16 text-center text-indigo-400">
        <FeatherIcon name="loader" class="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-500" />
        <span class="font-medium">Generating report...</span>
      </div>

      <div v-else-if="filteredData.length > 0" class="overflow-x-auto max-h-[600px]">
        <table class="w-full text-left text-sm border-collapse">
          <thead class="sticky top-0 bg-white/95 backdrop-blur-sm shadow-sm z-10">
            <tr class="border-b border-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wider">
              <th class="py-4 px-6">ID</th>
              <th class="py-4 px-6">Student Name</th>
              <th class="py-4 px-6">Gender</th>
              <th class="py-4 px-6">Adm. Date</th>
              <th class="py-4 px-6">Standard</th>
              <th class="py-4 px-6">Batch</th>
              <th class="py-4 px-6">School</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 font-medium">
            <tr
              v-for="student in filteredData"
              :key="student.name"
              class="hover:bg-indigo-50/30 transition-colors group"
            >
              <td class="py-3 px-6 font-mono text-xs text-indigo-500">
                {{ student.name }}
              </td>
              <td class="py-3 px-6 text-gray-900">
                {{ student.student_name || '-' }}
              </td>
              <td class="py-3 px-6 text-gray-600">
                <span v-if="student.gender === 'Male'" class="inline-flex items-center gap-1 text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md text-xs border border-blue-100">
                  <FeatherIcon name="user" class="w-3 h-3" /> Male
                </span>
                <span v-else-if="student.gender === 'Female'" class="inline-flex items-center gap-1 text-rose-600 bg-rose-50 px-2 py-0.5 rounded-md text-xs border border-rose-100">
                  <FeatherIcon name="user" class="w-3 h-3" /> Female
                </span>
                <span v-else class="text-gray-500">{{ student.gender || '-' }}</span>
              </td>
              <td class="py-3 px-6 text-gray-600">
                {{ student.admission_date || '-' }}
              </td>
              <td class="py-3 px-6 text-gray-700">
                <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold bg-gray-100 text-gray-700">
                  {{ student.standard || '-' }}
                </span>
              </td>
              <td class="py-3 px-6 text-emerald-700">
                <span v-if="student.current_batch" class="inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold bg-emerald-50 border border-emerald-100">
                  {{ student.current_batch }}
                </span>
                <span v-else class="text-gray-400">-</span>
              </td>
              <td class="py-3 px-6 text-gray-600 max-w-xs truncate" :title="student.school_name">
                {{ student.school_name || '-' }}
              </td>
            </tr>
          </tbody>
        </table>
        
        <!-- Summary Footer inside table wrapper -->
        <div class="bg-gray-50/80 px-6 py-3 border-t border-gray-100 flex items-center justify-between text-sm">
          <span class="text-gray-500 font-medium">Showing <strong class="text-gray-900">{{ filteredData.length }}</strong> students</span>
        </div>
      </div>

      <div v-else class="p-16 text-center text-gray-400">
        <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-3">
          <FeatherIcon name="search" class="w-8 h-8 text-gray-300" />
        </div>
        <p class="text-base font-bold text-gray-600">No students found matching your filters</p>
        <button @click="clearFilters" class="mt-3 text-indigo-600 text-sm font-semibold hover:underline">Clear all filters</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { createListResource } from 'frappe-ui'

const filters = reactive({
  gender: '',
  startDate: '',
  endDate: '',
  standard: '',
  batch: '',
  school: ''
})

const clearFilters = () => {
  filters.gender = ''
  filters.startDate = ''
  filters.endDate = ''
  filters.standard = ''
  filters.batch = ''
  filters.school = ''
}

const studentsResource = createListResource({
  doctype: 'Student',
  fields: ['name', 'student_name', 'gender', 'admission_date', 'standard', 'current_batch', 'school_name', 'status'],
  limit: 1000,
  auto: true,
})

const filteredData = computed(() => {
  let data = studentsResource.data || []
  
  if (filters.gender) {
    data = data.filter(item => item.gender === filters.gender)
  }
  
  if (filters.startDate) {
    data = data.filter(item => {
      if (!item.admission_date) return false
      return new Date(item.admission_date) >= new Date(filters.startDate)
    })
  }
  
  if (filters.endDate) {
    data = data.filter(item => {
      if (!item.admission_date) return false
      return new Date(item.admission_date) <= new Date(filters.endDate)
    })
  }
  
  if (filters.standard) {
    const stdSearch = filters.standard.toLowerCase()
    data = data.filter(item => 
      item.standard && item.standard.toLowerCase().includes(stdSearch)
    )
  }
  
  if (filters.batch) {
    const batchSearch = filters.batch.toLowerCase()
    data = data.filter(item => 
      item.current_batch && item.current_batch.toLowerCase().includes(batchSearch)
    )
  }
  
  if (filters.school) {
    const schoolSearch = filters.school.toLowerCase()
    data = data.filter(item => 
      item.school_name && item.school_name.toLowerCase().includes(schoolSearch)
    )
  }
  
  return data
})
</script>
