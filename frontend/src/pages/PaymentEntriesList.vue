<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 tracking-tight">Payment Entries</h2>
        <p class="text-sm text-gray-500 mt-0.5">View tuition fee payment transactions</p>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="paymentsResource.reload()"
          class="p-2 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg text-gray-600 transition-colors shadow-2xs"
        >
          <FeatherIcon name="refresh-cw" class="w-4 h-4" :class="{ 'animate-spin': paymentsResource.loading }" />
        </button>
        <router-link
          to="/payment-entries/new"
          class="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors"
        >
          <FeatherIcon name="plus" class="w-4 h-4" />
          <span>Add Payment</span>
        </router-link>
      </div>
    </div>

    <!-- Payments Data Table -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
      <div v-if="paymentsResource.loading" class="p-12 text-center text-gray-400">
        <FeatherIcon name="loader" class="w-6 h-6 animate-spin mx-auto mb-2 text-amber-600" />
        <span>Loading payment entries...</span>
      </div>

      <div v-else-if="paymentsResource.data && paymentsResource.data.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <th class="py-3.5 px-6">Payment ID</th>
              <th class="py-3.5 px-6">Student</th>
              <th class="py-3.5 px-6">Payment Date</th>
              <th class="py-3.5 px-6">Amount</th>
              <th class="py-3.5 px-6">Payment Mode</th>
              <th class="py-3.5 px-6">Reference #</th>
              <th class="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 font-normal">
            <tr
              v-for="payment in paymentsResource.data"
              :key="payment.name"
              class="hover:bg-amber-50/20 transition-colors"
            >
              <td class="py-4 px-6 font-mono text-xs font-medium text-gray-900">
                {{ payment.name }}
              </td>
              <td class="py-4 px-6 font-medium text-gray-800">
                {{ payment.student || '-' }}
              </td>
              <td class="py-4 px-6 text-gray-500 text-sm">
                {{ payment.payment_date || '-' }}
              </td>
              <td class="py-4 px-6 font-semibold text-emerald-600">
                ₹{{ payment.amount || 0 }}
              </td>
              <td class="py-4 px-6 text-gray-700">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-700">
                  {{ payment.payment_mode || 'Cash' }}
                </span>
              </td>
              <td class="py-4 px-6 text-gray-500 text-xs font-mono">
                {{ payment.reference_number || '-' }}
              </td>
              <td class="py-4 px-6 text-right">
                <a
                  :href="`/app/payment-entry/${payment.name}`"
                  target="_blank"
                  class="inline-flex items-center gap-1 text-xs font-medium text-amber-600 hover:text-amber-700 bg-amber-50 hover:bg-amber-100 px-3 py-1 rounded-md transition-colors"
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
        <FeatherIcon name="credit-card" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-base font-medium text-gray-600">No payment entries recorded</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const paymentsResource = createListResource({
  doctype: 'Payment Entry',
  fields: ['name', 'student', 'payment_date', 'amount', 'payment_mode', 'reference_number'],
  limit: 100,
  auto: true,
})
</script>
