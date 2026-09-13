<template>
  <nav class="att-bottom-nav">
    <div class="att-bottom-nav-inner">
      <router-link
        v-for="group in NAV_GROUPS"
        :key="group.key"
        :to="{ name: landingRoute(group) }"
        class="att-nav-item"
        :class="{ 'is-active': group.key === activeKey }"
        :title="group.title"
      >
        <i class="fa" :class="group.icon"></i>
        <span>{{ group.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { NAV_GROUPS, groupForRoute, landingRoute } from '@/data/navigation'

const route = useRoute()

// A tab stays lit for every page of its group, so opening Student Profile keeps
// Performance highlighted rather than lighting nothing at all.
const activeKey = computed(() => groupForRoute(route.name)?.key)
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
  /* Sized from the tab count, so adding a tab needs no CSS change. */
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
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

/* Five tabs: the label still has to shrink before it wraps on a narrow phone. */
@media (max-width: 480px) {
  .att-nav-item { font-size: 9.5px; padding: 8px 1px; letter-spacing: -0.01em; }
  .att-nav-item i { font-size: 16px; }
}

.att-nav-item:hover { background: var(--fg-hover-color, var(--gray-100)); }

.att-nav-item.is-active {
  color: var(--blue-600);
  border-top-color: var(--blue-600);
  background: var(--bg-blue);
}
</style>
