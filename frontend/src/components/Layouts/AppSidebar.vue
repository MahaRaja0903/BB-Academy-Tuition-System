<template>
  <aside 
    class="flex flex-col h-full bg-white border-r border-gray-200 transition-all duration-300 ease-in-out"
    :class="isCollapsed ? 'w-16' : 'w-64'"
  >
    <!-- Brand / Title -->
    <div class="h-16 flex items-center justify-between px-4 border-b border-gray-100">
      <div v-if="!isCollapsed" class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold">
          BB
        </div>
        <span class="font-bold text-gray-800 text-lg tracking-tight">BB Tuition</span>
      </div>
      <button 
        @click="isCollapsed = !isCollapsed" 
        class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors mx-auto"
      >
        <FeatherIcon :name="isCollapsed ? 'chevrons-right' : 'chevrons-left'" class="w-5 h-5" />
      </button>
    </div>

    <!-- Navigation Links -->
    <div class="flex-1 overflow-y-auto p-3">
      <SidebarLink :isCollapsed="isCollapsed" />
    </div>

    <!-- User Profile Footer -->
    <div class="p-3 border-t border-gray-100">
      <UserDropdown :isCollapsed="isCollapsed" />
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import SidebarLink from './SidebarLink.vue'
import UserDropdown from '../UserDropdown.vue'

const isCollapsed = ref(false)
</script>
