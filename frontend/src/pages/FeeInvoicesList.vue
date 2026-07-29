<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Fee Invoices</h2>
        <p class="text-sm text-gray-500 mt-0.5">Track and manage student fee invoices</p>
      </div>

      <div class="flex items-center gap-3">
        <button 
          @click="invoicesResource.reload()" 
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': invoicesResource.loading }" />
        </button>
      </div>
    </div>

    <!-- Invoices Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="invoicesResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-purple-600" />
        <span>Loading fee invoices...</span>
      </div>

      <div v-else-if="invoicesResource.data && invoicesResource.data.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">Invoice ID</th>
              <th class="py-3.5 px-6">Student</th>
              <th class="py-3.5 px-6">Invoice Date</th>
              <th class="py-3.5 px-6">Monthly Fee</th>
              <th class="py-3.5 px-6">Paid</th>
              <th class="py-3.5 px-6">Outstanding</th>
              <th class="py-3.5 px-6">Status</th>
              <th class="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="invoice in invoicesResource.data"
              :key="invoice.name"
              class="hover:bg-purple-50/20 transition-colors"
            >
              <td class="py-4 px-6 font-mono text-xs font-medium text-gray-900">
                {{ invoice.name }}
              </td>
              <td class="py-4 px-6 font-medium text-gray-800">
                {{ invoice.student || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-500 text-sm">
                {{ invoice.invoice_date || '-' }}
              </td>
              <td class="py-4 px-6 font-semibold text-gray-900">
                ₹{{ invoice.monthly_fee || 0 }}
              </td>
              <td class="py-4 px-6 font-medium text-emerald-600">
                ₹{{ invoice.paid_amount || 0 }}
              </td>
              <td class="py-4 px-6 font-medium text-red-600">
                ₹{{ invoice.outstanding_amount || 0 }}
              </td>
              <td class="py-4 px-6">
                <span
                  :class="{
                    'bg-emerald-50 text-emerald-700 border-emerald-200': invoice.status === 'Paid',
                    'bg-amber-50 text-amber-700 border-amber-200': invoice.status === 'Partially Paid',
                    'bg-red-50 text-red-700 border-red-200': invoice.status === 'Unpaid',
                    'bg-gray-50 text-gray-700 border-gray-200': !invoice.status
                  }"
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
                >
                  {{ invoice.status || 'Draft' }}
                </span>
              </td>
              <td class="py-4 px-6 text-right">
                <a
                  :href="`/app/fee-invoice/${invoice.name}`"
                  target="_blank"
                  class="inline-flex items-center gap-1 text-xs font-medium text-purple-600 hover:text-purple-700 bg-purple-50 hover:bg-purple-100 px-3 py-1 rounded-md transition-colors"
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
        <FeatherIcon name="file-text" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No fee invoices recorded</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const invoicesResource = createListResource({
  doctype: 'Fee Invoice',
  fields: ['name', 'student', 'invoice_date', 'monthly_fee', 'paid_amount', 'outstanding_amount', 'status'],
  limit: 100,
  auto: true,
})
</script>
