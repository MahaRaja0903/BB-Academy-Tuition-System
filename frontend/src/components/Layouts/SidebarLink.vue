<template>
  <nav class="space-y-1">
    <router-link
      v-for="item in navigationItems"
      :key="item.to"
      :to="item.to"
      class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
      :class="[
        $route.path === item.to || ($route.path.startsWith(item.to) && item.to !== '/')
          ? 'bg-emerald-50 text-emerald-700 font-semibold shadow-xs'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
      ]"
    >
      <FeatherIcon :name="item.icon" class="w-4 h-4 flex-shrink-0" />
      <span v-if="!isCollapsed" class="truncate">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
defineProps({
  isCollapsed: Boolean
})

const navigationItems = [
  { label: 'Dashboard', to: '/', icon: 'grid' },
  { label: 'Students', to: '/students', icon: 'users' },
  { label: 'Fee Invoices', to: '/fee-invoices', icon: 'file-text' },
  { label: 'Enquiries', to: '/student-enquiries', icon: 'help-circle' },
  { label: 'Payment Entries', to: '/payment-entries', icon: 'credit-card' },
  { label: 'Batch History', to: '/student-batch-history', icon: 'git-branch' },
  { label: 'Admission Forms', to: '/student-admission-forms', icon: 'file-plus' },
]
</script>
