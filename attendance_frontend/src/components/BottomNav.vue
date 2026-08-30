<template>
  <nav class="att-bottom-nav">
    <div class="att-bottom-nav-inner">
      <router-link
        v-for="tab in tabs"
        :key="tab.name"
        :to="{ name: tab.name }"
        class="att-nav-item"
        :class="{ 'is-active': isActive(tab.name) }"
      >
        <i class="fa" :class="tab.icon"></i>
        <span>{{ tab.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { name: 'AttendanceManager', label: 'Attendance', icon: 'fa-check-circle' },
  { name: 'AttendanceDashboard', label: 'Dashboard', icon: 'fa-bar-chart' },
  { name: 'LatePermission', label: 'Late / Early', icon: 'fa-clock-o' },
  { name: 'AttendanceReports', label: 'Reports', icon: 'fa-list-alt' },
]

function isActive(name) {
  return route.name === name
}
</script>

<style>
.att-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 40;
  background: var(--card-bg);
  border-top: 1px solid var(--border-color);
  padding-bottom: env(safe-area-inset-bottom);
  box-shadow: 0 -1px 2px rgba(0, 0, 0, 0.06);
}

.att-bottom-nav-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

.att-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 8px 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-decoration: none;
  border-top: 2px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}

.att-nav-item i { font-size: 17px; }

.att-nav-item:hover { background: var(--fg-hover-color, var(--gray-100)); }

.att-nav-item.is-active {
  color: var(--blue-600);
  border-top-color: var(--blue-600);
  background: var(--bg-blue);
}
</style>
