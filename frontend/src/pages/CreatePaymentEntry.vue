<template>
  <div class="space-y-6 max-w-3xl mx-auto">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <router-link to="/payment-entries" class="p-2 border border-gray-200 bg-white rounded-lg text-gray-600 hover:bg-gray-50 transition-colors shadow-2xs">
        <FeatherIcon name="arrow-left" class="w-4 h-4" />
      </router-link>
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Record New Payment</h2>
        <p class="text-sm text-gray-500 mt-0.5">Fill in the payment details</p>
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
      <!-- Payment Details -->
      <div class="p-6 border-b border-gray-100">
        <h3 class="text-lg font-bold text-gray-900 mb-4">Payment Details</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Student <span class="text-red-500">*</span></label>
            <div class="relative">
              <input
                v-model="studentSearch"
                @input="searchStudents"
                type="text"
                required
                class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900"
                placeholder="Search student by name or ID..."
              />
              <div v-if="showStudentDropdown && studentOptions.length" class="absolute z-10 w-full mt-1 bg-white border-2 border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                <button
                  v-for="student in studentOptions"
                  :key="student.name"
                  type="button"
                  @click="selectStudent(student)"
                  class="w-full px-4 py-2.5 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
                >
                  <div class="font-medium text-gray-900">{{ student.student_name }}</div>
                  <div class="text-xs text-gray-500">{{ student.name }}</div>
                </button>
              </div>
            </div>
            <p v-if="formData.student" class="mt-2 text-sm text-emerald-600 font-medium">✓ Selected: {{ formData.student }}</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Fee Invoice <span class="text-red-500">*</span></label>
            <div class="relative">
              <input
                v-model="invoiceSearch"
                @input="searchInvoices"
                type="text"
                required
                :disabled="!formData.student"
                class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900 disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="Search invoice..."
              />
              <div v-if="showInvoiceDropdown && invoiceOptions.length" class="absolute z-10 w-full mt-1 bg-white border-2 border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                <button
                  v-for="invoice in invoiceOptions"
                  :key="invoice.name"
                  type="button"
                  @click="selectInvoice(invoice)"
                  class="w-full px-4 py-2.5 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
                >
                  <div class="font-medium text-gray-900">{{ invoice.name }}</div>
                  <div class="text-xs text-gray-500">Outstanding: ₹{{ invoice.outstanding_amount || 0 }}</div>
                </button>
              </div>
            </div>
            <p v-if="formData.fee_invoice" class="mt-2 text-sm text-emerald-600 font-medium">✓ Selected: {{ formData.fee_invoice }}</p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Payment Date <span class="text-red-500">*</span></label>
              <input
                v-model="formData.payment_date"
                type="date"
                required
                class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Amount <span class="text-red-500">*</span></label>
              <input
                v-model.number="formData.amount"
                type="number"
                step="0.01"
                required
                class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900"
                placeholder="0.00"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Payment Mode <span class="text-red-500">*</span></label>
              <select
                v-model="formData.payment_mode"
                required
                class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900"
              >
                <option value="">Select Payment Mode</option>
                <option value="Cash">Cash</option>
                <option value="Bank Transfer">Bank Transfer</option>
                <option value="UPI">UPI</option>
                <option value="Card">Card</option>
                <option value="Cheque">Cheque</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Reference Number</label>
              <input
                v-model="formData.reference_number"
                type="text"
                class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900"
                placeholder="Transaction/Cheque number"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Remarks</label>
            <textarea
              v-model="formData.remarks"
              rows="3"
              class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-gray-900"
              placeholder="Additional notes or comments"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="p-6 bg-gray-50 flex items-center justify-end gap-3">
        <router-link
          to="/payment-entries"
          class="px-6 py-2.5 border-2 border-gray-300 rounded-lg text-gray-700 font-semibold hover:bg-gray-100 transition-colors"
        >
          Cancel
        </router-link>
        <button
          type="submit"
          :disabled="isSubmitting"
          class="px-6 py-2.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-700 hover:to-amber-600 text-white font-semibold rounded-lg shadow-lg transition-all disabled:opacity-50 flex items-center gap-2"
        >
          <FeatherIcon v-if="isSubmitting" name="loader" class="w-4 h-4 animate-spin" />
          <span>{{ isSubmitting ? 'Recording...' : 'Record Payment' }}</span>
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

const studentSearch = ref('')
const invoiceSearch = ref('')
const showStudentDropdown = ref(false)
const showInvoiceDropdown = ref(false)
const studentOptions = ref([])
const invoiceOptions = ref([])

const formData = ref({
  student: '',
  fee_invoice: '',
  payment_date: new Date().toISOString().split('T')[0],
  amount: '',
  payment_mode: '',
  reference_number: '',
  remarks: '',
})

const studentSearchResource = createResource({
  url: 'frappe.client.get_list',
  onSuccess(data) {
    studentOptions.value = data
    showStudentDropdown.value = true
  },
})

const invoiceSearchResource = createResource({
  url: 'frappe.client.get_list',
  onSuccess(data) {
    invoiceOptions.value = data
    showInvoiceDropdown.value = true
  },
})

const createPaymentResource = createResource({
  url: 'frappe.client.insert',
  onSuccess(data) {
    isSubmitting.value = false
    router.push('/payment-entries')
  },
  onError(error) {
    isSubmitting.value = false
    errorMessage.value = error.messages?.[0] || error.message || 'Failed to create payment entry'
  },
})

const searchStudents = () => {
  if (studentSearch.value.length < 2) {
    showStudentDropdown.value = false
    return
  }

  studentSearchResource.submit({
    doctype: 'Student',
    fields: ['name', 'student_name'],
    filters: [['student_name', 'like', `%${studentSearch.value}%`]],
    limit: 10,
  })
}

const searchInvoices = () => {
  if (invoiceSearch.value.length < 2 || !formData.value.student) {
    showInvoiceDropdown.value = false
    return
  }

  invoiceSearchResource.submit({
    doctype: 'Fee Invoice',
    fields: ['name', 'outstanding_amount'],
    filters: [
      ['student', '=', formData.value.student],
      ['name', 'like', `%${invoiceSearch.value}%`],
    ],
    limit: 10,
  })
}

const selectStudent = (student) => {
  formData.value.student = student.name
  studentSearch.value = student.student_name
  showStudentDropdown.value = false
}

const selectInvoice = (invoice) => {
  formData.value.fee_invoice = invoice.name
  invoiceSearch.value = invoice.name
  showInvoiceDropdown.value = false
}

const handleSubmit = async () => {
  errorMessage.value = ''
  isSubmitting.value = true

  createPaymentResource.submit({
    doc: {
      doctype: 'Payment Entry',
      ...formData.value,
    },
  })
}
</script>
