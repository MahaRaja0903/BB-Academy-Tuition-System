<template>
  <div class="flex h-screen w-screen overflow-hidden bg-gray-50">
    <AppSidebar />
    <div class="flex-1 flex flex-col h-full overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-y-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
</script>
