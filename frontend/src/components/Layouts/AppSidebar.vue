<template>
  <aside 
    class="relative flex flex-col h-full border-r border-gray-200 transition-all duration-300 ease-in-out bg-white overflow-hidden shadow-sm shadow-gray-200/50"
    :class="isCollapsed ? 'w-16' : 'w-64'"
  >
    <!-- Colorful Background Accent -->
    <div class="absolute inset-0 bg-gradient-to-br from-white via-indigo-50/30 to-emerald-50/20 pointer-events-none"></div>

    <!-- Decorative Top Right Blob -->
    <div class="absolute top-0 right-0 w-32 h-32 bg-indigo-100/50 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>

    <!-- Brand / Title -->
    <div class="relative z-10 h-16 flex items-center justify-between px-4 border-b border-gray-100/50 backdrop-blur-sm">
      <div v-if="!isCollapsed" class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-emerald-400 flex items-center justify-center text-white font-black shadow-md shadow-emerald-500/30 transform transition-transform duration-300 hover:rotate-12 hover:scale-110">
          BB
        </div>
        <span class="font-bold text-gray-800 text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-700 to-emerald-600">BB Tuition</span>
      </div>
      <button 
        @click="isCollapsed = !isCollapsed" 
        class="p-1.5 rounded-xl text-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 transition-all duration-200 mx-auto group"
      >
        <FeatherIcon 
          :name="isCollapsed ? 'chevrons-right' : 'chevrons-left'" 
          class="w-5 h-5 transition-transform duration-300 group-hover:scale-110" 
        />
      </button>
    </div>

    <!-- Navigation Links -->
    <div class="relative z-10 flex-1 overflow-y-auto p-3 scrollbar-hide">
      <SidebarLink :isCollapsed="isCollapsed" />
    </div>

    <!-- User Profile Footer -->
    <div class="relative z-10 p-3 border-t border-gray-100/50 backdrop-blur-sm bg-white/50">
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

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
.scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
