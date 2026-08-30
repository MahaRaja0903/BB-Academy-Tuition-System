<template>
  <div class="att-shell">
    <header class="att-shell-header">
      <div class="att-shell-header-inner">
        <div class="att-shell-brand">
          <img :src="LOGO_URL" alt="" />
          <div>
            <div class="att-shell-title">BB Attendance Manager</div>
            <div class="att-shell-sub">{{ route.meta.title }}</div>
          </div>
        </div>
        <button type="button" class="att-shell-logout" title="Log out" @click="session.logout.submit()">
          <i class="fa fa-sign-out"></i>
        </button>
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
import { useRoute } from 'vue-router'
import BottomNav from '@/components/BottomNav.vue'
import { session } from '@/data/session'
import { LOGO_URL } from '@/data/assets'

const route = useRoute()
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
