<template>
  <header class="h-16 bg-white border-b border-gray-200 px-6 flex items-center justify-between shadow-2xs">
    <div class="flex items-center gap-4">
      <h1 class="text-xl font-bold text-gray-800 tracking-tight">{{ title }}</h1>
    </div>

    <!-- Right Header Utilities -->
    <div class="flex items-center gap-3">
      <!-- Search Input -->
      <div class="relative w-64">
        <FeatherIcon name="search" class="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search students, invoices..."
          class="w-full pl-9 pr-4 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
        />
      </div>

      <!-- Quick Desk Shortcut -->
      <a 
        href="/app"
        target="_blank"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 text-gray-700 bg-white hover:bg-gray-50 text-xs font-medium rounded-lg shadow-2xs transition-colors"
      >
        <FeatherIcon name="external-link" class="w-3.5 h-3.5" />
        <span>Frappe Desk</span>
      </a>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => route.meta?.title || 'Tuition Portal')
</script>
