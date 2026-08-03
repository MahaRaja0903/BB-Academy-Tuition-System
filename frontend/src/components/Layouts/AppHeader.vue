<template>
  <header class="h-16 bg-white/80 backdrop-blur-md border-b border-gray-100 px-6 flex items-center justify-between shadow-[0_4px_20px_-15px_rgba(0,0,0,0.1)] sticky top-0 z-40">
    <div class="flex items-center gap-4">
      <div class="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
        <FeatherIcon :name="pageIcon" class="w-5 h-5 transition-transform duration-500 hover:scale-125 hover:rotate-12" />
      </div>
      <h1 class="text-xl font-extrabold text-gray-800 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-500">{{ title }}</h1>
    </div>

    <!-- Right Header Utilities -->
    <div class="flex items-center gap-4">
      <!-- Search Input -->
      <div class="relative w-72 group">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <FeatherIcon name="search" class="w-4 h-4 text-gray-400 group-hover:text-indigo-500 transition-colors duration-300" />
        </div>
        <input
          type="text"
          placeholder="Search students, invoices..."
          class="w-full pl-10 pr-4 py-2 text-sm bg-gray-50/50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 hover:bg-white transition-all shadow-sm shadow-gray-100/50"
        />
        <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
          <span class="text-[10px] font-bold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-md border border-gray-200">⌘K</span>
        </div>
      </div>

      <!-- Notifications -->
      <button class="relative p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all duration-300 hover:scale-110 group">
        <FeatherIcon name="bell" class="w-5 h-5 group-hover:animate-bounce" />
        <span class="absolute top-1 right-1 w-2.5 h-2.5 bg-rose-500 border-2 border-white rounded-full"></span>
      </button>

      <!-- Divider -->
      <div class="h-6 w-px bg-gray-200"></div>

      <!-- Quick Desk Shortcut -->
      <a 
        href="/app"
        target="_blank"
        class="group inline-flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-700 bg-white hover:bg-gray-900 hover:text-white text-xs font-semibold rounded-xl shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5"
      >
        <FeatherIcon name="cpu" class="w-4 h-4 group-hover:rotate-180 transition-transform duration-700" />
        <span>Backend</span>
      </a>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => route.meta?.title || 'Tuition Portal')

const pageIcon = computed(() => {
  const path = route.path
  if (path.includes('students')) return 'users'
  if (path.includes('invoices') || path.includes('payment')) return 'credit-card'
  if (path.includes('report') || path.includes('history')) return 'pie-chart'
  return 'grid'
})
</script>
