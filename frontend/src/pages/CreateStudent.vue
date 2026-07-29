<template>
  <div class="space-y-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <router-link to="/students" class="p-2 border border-gray-200 bg-white rounded-lg text-gray-600 hover:bg-gray-50 transition-colors shadow-2xs">
        <FeatherIcon name="arrow-left" class="w-4 h-4" />
      </router-link>
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Add New Student</h2>
        <p class="text-sm text-gray-500 mt-0.5">Fill in the details to register a new student</p>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="bg-red-50 border-2 border-red-300 rounded-xl p-4 flex items-start gap-3">
      <FeatherIcon name="alert-circle" class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div class="flex-1">
        <h4 class="text-sm font-semibold text-red-900">Error</h4>
        <p class="text-sm text-red-700 mt-1">{{ errorMessage }}</p>
      </div>
    </div>

    <!-- Form -->
    <form @submit.prevent="handleSubmit" class="bg-white rounded-xl border border-gray-200 shadow-2xs">
      <!-- Student Details -->
      <div class="p-6 border-b border-gray-100">
        <h3 class="text-lg font-bold text-gray-900 mb-4">Student Details</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Admission Number <span class="text-red-500">*</span></label>
            <input
              v-model="formData.admission_number"
              type="text"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="e.g., ADM-2026-001"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Student Name <span class="text-red-500">*</span></label>
            <input
              v-model="formData.student_name"
              type="text"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="Enter full name"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Admission Date <span class="text-red-500">*</span></label>
            <input
              v-model="formData.admission_date"
              type="date"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Date of Birth</label>
            <input
              v-model="formData.date_of_birth"
              type="date"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Gender</label>
            <select
              v-model="formData.gender"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
            >
              <option value="">Select Gender</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Status <span class="text-red-500">*</span></label>
            <select
              v-model="formData.status"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
            >
              <option value="Active">Active</option>
              <option value="Completed">Completed</option>
              <option value="Dropped">Dropped</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Academic Details -->
      <div class="p-6 border-b border-gray-100">
        <h3 class="text-lg font-bold text-gray-900 mb-4">Academic Details</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Standard <span class="text-red-500">*</span></label>
            <input
              v-model="formData.standard"
              type="text"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="e.g., 10 Commerce"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Current Batch <span class="text-red-500">*</span></label>
            <input
              v-model="formData.current_batch"
              type="text"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="e.g., Batch 1"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Academic Year <span class="text-red-500">*</span></label>
            <input
              v-model="formData.academic_year"
              type="text"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="e.g., 2025-2026"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">School Name</label>
            <input
              v-model="formData.school_name"
              type="text"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="Enter school name"
            />
          </div>
        </div>
      </div>

      <!-- Parent Details -->
      <div class="p-6 border-b border-gray-100">
        <h3 class="text-lg font-bold text-gray-900 mb-4">Parent Details</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Father Name</label>
            <input
              v-model="formData.father_name"
              type="text"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="Enter father's name"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Mother Name</label>
            <input
              v-model="formData.mother_name"
              type="text"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="Enter mother's name"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Parent Mobile <span class="text-red-500">*</span></label>
            <input
              v-model="formData.parent_mobile"
              type="tel"
              required
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="10-digit mobile number"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">WhatsApp Number</label>
            <input
              v-model="formData.whatsapp_number"
              type="tel"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
              placeholder="10-digit WhatsApp number"
            />
          </div>
        </div>
      </div>

      <!-- Address -->
      <div class="p-6 border-b border-gray-100">
        <h3 class="text-lg font-bold text-gray-900 mb-4">Address</h3>
        <textarea
          v-model="formData.address"
          rows="3"
          class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-gray-900"
          placeholder="Enter complete address"
        ></textarea>
      </div>

      <!-- Actions -->
      <div class="p-6 bg-gray-50 flex items-center justify-end gap-3">
        <router-link
          to="/students"
          class="px-6 py-2.5 border-2 border-gray-300 rounded-lg text-gray-700 font-semibold hover:bg-gray-100 transition-colors"
        >
          Cancel
        </router-link>
        <button
          type="submit"
          :disabled="isSubmitting"
          class="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-700 hover:to-emerald-600 text-white font-semibold rounded-lg shadow-lg transition-all disabled:opacity-50 flex items-center gap-2"
        >
          <FeatherIcon v-if="isSubmitting" name="loader" class="w-4 h-4 animate-spin" />
          <span>{{ isSubmitting ? 'Creating...' : 'Create Student' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'

const router = useRouter()
const isSubmitting = ref(false)
const errorMessage = ref('')

const formData = ref({
  admission_number: '',
  student_name: '',
  admission_date: new Date().toISOString().split('T')[0],
  date_of_birth: '',
  gender: '',
  status: 'Active',
  academic_year: '',
  standard: '',
  current_batch: '',
  father_name: '',
  mother_name: '',
  parent_mobile: '',
  whatsapp_number: '',
  school_name: '',
  address: '',
})

const createStudentResource = createResource({
  url: 'frappe.client.insert',
  onSuccess(data) {
    isSubmitting.value = false
    router.push(`/students/${data.name}`)
  },
  onError(error) {
    isSubmitting.value = false
    errorMessage.value = error.messages?.[0] || error.message || 'Failed to create student'
  },
})

const handleSubmit = async () => {
  errorMessage.value = ''
  isSubmitting.value = true

  createStudentResource.submit({
    doc: {
      doctype: 'Student',
      ...formData.value,
    },
  })
}
</script>
