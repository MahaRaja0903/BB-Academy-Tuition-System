<template>
  <div class="space-y-6">
    <!-- Breadcrumb Header -->
    <div class="flex items-center gap-3">
      <router-link to="/students" class="p-2 border border-gray-200 bg-white rounded-lg text-gray-600 hover:bg-gray-50 transition-colors shadow-2xs">
        <FeatherIcon name="arrow-left" class="w-4 h-4" />
      </router-link>
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">
          {{ student.doc ? student.doc.student_name : 'Student Profile' }}
        </h2>
        <p class="text-xs font-mono text-gray-500 mt-0.5">{{ studentId }}</p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="student.loading" class="p-12 text-center text-gray-400 bg-white rounded-xl border border-gray-200">
      <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
      <span>Loading profile...</span>
    </div>

    <!-- Student Detail Card Grid -->
    <div v-else-if="student.doc" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main Profile Box (2 cols) -->
      <div class="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6 shadow-2xs space-y-6">
        <div class="flex items-center gap-4 pb-6 border-b border-gray-100">
          <div class="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-600 to-emerald-500 text-white font-bold text-2xl flex items-center justify-center shadow-lg">
            {{ (student.doc.student_name || 'S').charAt(0).toUpperCase() }}
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900">{{ student.doc.student_name }}</h3>
            <span
              :class="{
                'bg-emerald-50 text-emerald-700 border-emerald-200': student.doc.status === 'Active',
                'bg-blue-50 text-blue-700 border-blue-200': student.doc.status === 'Completed',
                'bg-red-50 text-red-700 border-red-200': student.doc.status === 'Dropped'
              }"
              class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border mt-1"
            >
              {{ student.doc.status || 'Active' }}
            </span>
          </div>
        </div>

        <div class="space-y-6">
          <!-- Student Details -->
          <div>
            <h4 class="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Student Information</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Student Name</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.student_name || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Admission Number</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.admission_number || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Date of Birth</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.date_of_birth || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Gender</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.gender || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Admission Date</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.admission_date || '-' }}</p>
              </div>
            </div>
          </div>

          <!-- Parent Details -->
          <div class="border-t border-gray-100 pt-6">
            <h4 class="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Parent Information</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Father Name</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.father_name || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Mother Name</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.mother_name || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Parent Mobile</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.parent_mobile || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">WhatsApp Number</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.whatsapp_number || '-' }}</p>
              </div>
            </div>
          </div>

          <!-- Academic Details -->
          <div class="border-t border-gray-100 pt-6">
            <h4 class="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Academic Information</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Academic Year</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.academic_year || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Standard</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.standard || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Current Batch</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.current_batch || '-' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">School Name</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.school_name || '-' }}</p>
              </div>
            </div>
          </div>

          <!-- Fee Details -->
          <div class="border-t border-gray-100 pt-6">
            <h4 class="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Fee Information</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Monthly Fee</label>
                <p class="text-sm font-medium text-gray-800 mt-1">₹ {{ student.doc.monthly_fee || '0' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Starting Payment</label>
                <p class="text-sm font-medium text-gray-800 mt-1">₹ {{ student.doc.starting_payment || '0' }}</p>
              </div>
              <div>
                <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Fees Due Date</label>
                <p class="text-sm font-medium text-gray-800 mt-1">{{ student.doc.fees_due_date ? `Day ${student.doc.fees_due_date}` : '-' }}</p>
              </div>
            </div>
          </div>

          <!-- Address -->
          <div class="border-t border-gray-100 pt-6">
            <h4 class="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Address</h4>
            <p class="text-sm font-medium text-gray-800">{{ student.doc.address || '-' }}</p>
          </div>
        </div>
      </div>

      <!-- Quick Desk Actions Box -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 shadow-2xs space-y-4 h-fit">
        <h3 class="font-semibold text-gray-900 border-b border-gray-100 pb-3">Actions</h3>
        <a 
          :href="`/app/student/${studentId}`" 
          target="_blank"
          class="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-2xs transition-colors"
        >
          <FeatherIcon name="edit" class="w-4 h-4" />
          <span>Edit in Desk</span>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createDocumentResource } from 'frappe-ui'

const route = useRoute()
const studentId = computed(() => route.params.name)

const student = createDocumentResource({
  doctype: 'Student',
  name: studentId,
  auto: true,
})

// Reload when route changes
watch(studentId, (newId) => {
  if (newId && student) {
    student.reload()
  }
})
</script>
