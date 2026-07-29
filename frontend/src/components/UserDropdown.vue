<template>
  <div class="relative">
    <button 
      @click="isOpen = !isOpen"
      class="flex items-center gap-3 w-full p-2 rounded-lg hover:bg-gray-100 transition-colors"
    >
      <div class="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-semibold text-sm shadow-sm">
        {{ userInitial }}
      </div>
      <div v-if="!isCollapsed" class="flex-1 text-left overflow-hidden">
        <div class="text-sm font-medium text-gray-800 truncate">{{ userName }}</div>
        <div class="text-xs text-gray-500 truncate">{{ userEmail }}</div>
      </div>
      <FeatherIcon v-if="!isCollapsed" name="chevron-down" class="w-4 h-4 text-gray-500" />
    </button>

    <!-- Dropdown Menu -->
    <div 
      v-if="isOpen" 
      class="absolute left-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-50"
    >
      <a 
        href="/app" 
        class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
      >
        <FeatherIcon name="grid" class="w-4 h-4" />
        <span>Desk App</span>
      </a>
      <a 
        href="/api/method/logout" 
        class="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
      >
        <FeatherIcon name="log-out" class="w-4 h-4" />
        <span>Logout</span>
      </a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

defineProps({
  isCollapsed: Boolean
})

const isOpen = ref(false)

const userName = computed(() => window.frappe?.session?.user_fullname || 'Admin User')
const userEmail = computed(() => window.frappe?.session?.user || 'admin@example.com')
const userInitial = computed(() => userName.value.charAt(0).toUpperCase())
</script>
