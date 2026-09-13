<template>
  <div class="att-shell">
    <header class="att-shell-header">
      <div class="att-shell-header-inner">
        <div class="att-shell-brand">
          <img :src="LOGO_URL" alt="" />
          <div>
            <div class="att-shell-title">BB Student Manager</div>
            <div class="att-shell-sub">{{ group?.title || route.meta.title }}</div>
          </div>
        </div>
        <button type="button" class="att-shell-logout" title="Log out" @click="session.logout.submit()">
          <i class="fa fa-sign-out"></i>
        </button>
      </div>

      <!-- Only a group that holds more than one page needs a sub-tab strip; the
           single-page groups go straight from the bottom bar to their content. -->
      <div v-if="group && group.children.length > 1" class="att-shell-subnav">
        <div class="att-shell-subnav-inner">
          <router-link
            v-for="child in group.children"
            :key="child.name"
            :to="{ name: child.name }"
            class="att-subnav-item"
            :class="{ 'is-active': route.name === child.name }"
          >
            <i class="fa" :class="child.icon"></i>
            <span>{{ child.label }}</span>
          </router-link>
        </div>
      </div>
    </header>

    <main class="att-shell-main">
      <div class="att-shell-container">
        <router-view />
      </div>
    </main>

    <BottomNav />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BottomNav from '@/components/BottomNav.vue'
import { session } from '@/data/session'
import { LOGO_URL } from '@/data/assets'
import { groupForRoute } from '@/data/navigation'

const route = useRoute()

const group = computed(() => groupForRoute(route.name))
</script>

<style>
.att-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--gray-50);
}

.att-shell-header {
  position: sticky;
  top: 0;
  z-index: 30;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  padding-top: env(safe-area-inset-top);
}

.att-shell-header-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.att-shell-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.att-shell-brand img {
  width: 30px;
  height: 30px;
  border-radius: var(--border-radius, 6px);
  flex: 0 0 auto;
}

.att-shell-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--heading-color);
  line-height: 1.2;
}

.att-shell-sub {
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.2;
}

.att-shell-subnav {
  border-top: 1px solid var(--border-color);
  background: var(--card-bg);
}

.att-shell-subnav-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  gap: 4px;
  padding: 0 10px;
  overflow-x: auto;
}

.att-subnav-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  color: var(--text-muted);
  text-decoration: none;
  border-bottom: 2px solid transparent;
}

.att-subnav-item i { font-size: 13px; }

.att-subnav-item:hover { color: var(--text-color); }

.att-subnav-item.is-active {
  color: var(--blue-600);
  border-bottom-color: var(--blue-600);
}

.att-shell-logout {
  border: 1px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-muted);
  border-radius: var(--border-radius, 6px);
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.att-shell-logout:hover {
  background: var(--bg-red);
  color: var(--text-on-red);
  border-color: var(--red-200);
}

.att-shell-main {
  flex: 1;
  /* clears the fixed bottom nav */
  padding-bottom: 72px;
}

/* Desk pages sit in a constrained column; without this the PWA stretched
   edge-to-edge on tablet/desktop. */
.att-shell-container {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 767px) {
  .att-shell-main { padding-bottom: 66px; }
}
</style>
