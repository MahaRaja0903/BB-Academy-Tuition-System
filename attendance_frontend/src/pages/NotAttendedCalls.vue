<template>
  <div class="pcw-manager ccw-manager">
    <!-- Filters -->
    <div class="pcw-panel">
      <div class="pcw-panel-filters">
        <div class="pcw-field">
          <label><i class="fa fa-calendar"></i> Month</label>
          <input type="month" class="form-control" v-model="month" />
        </div>
        <div class="pcw-field">
          <label><i class="fa fa-sitemap"></i> Called From</label>
          <select class="form-control" v-model="callFor">
            <option value="">All</option>
            <option v-for="s in SOURCES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="pcw-field">
          <label><i class="fa fa-graduation-cap"></i> Standard</label>
          <select class="form-control" v-model="standard">
            <option value="">All Standards</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="pcw-field">
          <label><i class="fa fa-users"></i> Batch</label>
          <select class="form-control" v-model="batch">
            <option value="">All Batches</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Not reached / Reached later / All. A tap narrows the list. -->
    <div class="pcw-kpi-grid ccw-kpi-grid">
      <button
        v-for="k in kpis"
        :key="k.key"
        type="button"
        class="pcw-kpi"
        :class="[k.cls, { 'is-active': view === k.key }]"
        :title="k.title"
        @click="view = k.key"
      >
        <span class="pcw-kpi-label"><i class="fa" :class="k.icon"></i> {{ k.label }}</span>
        <span class="pcw-kpi-value">{{ k.value }}</span>
        <span class="ccw-kpi-sub">{{ k.sub }}</span>
      </button>
    </div>

    <div class="pcw-toolbar">
      <div class="pcw-search-wrap">
        <i class="fa fa-search"></i>
        <input
          type="text"
          class="pcw-search-input"
          placeholder="Search student name or ID"
          v-model="search"
        />
      </div>
      <button type="button" class="pcw-refresh-btn" :disabled="loading" @click="load">
        <i class="fa" :class="loading ? 'fa-spinner fa-spin' : 'fa-refresh'"></i>
        <span>Refresh</span>
      </button>
    </div>

    <template v-if="loading">
      <div v-for="i in 3" :key="`sk${i}`" class="pcw-card">
        <div class="pcw-skeleton-bar" style="width: 45%"></div>
        <div class="pcw-skeleton-bar" style="width: 75%"></div>
      </div>
    </template>

    <template v-else>
      <div v-if="!visible.length" class="pcw-empty-state">
        <div class="pcw-empty-icon"><i class="fa" :class="emptyState.icon"></i></div>
        <h4>{{ emptyState.title }}</h4>
        <p>{{ emptyState.text }}</p>
      </div>

      <article
        v-for="r in visible"
        :key="r.key"
        class="pcw-card ccw-card"
        :class="r.is_pending ? 'ccw-open' : 'ccw-resolved'"
      >
        <header class="pcw-card-head">
          <img v-if="r.image" class="pcw-avatar" :src="r.image" :alt="r.student_name" loading="lazy" />
          <div v-else class="pcw-avatar pcw-avatar-fallback">{{ initials(r.student_name) }}</div>

          <div class="pcw-ident">
            <div class="pcw-name-row">
              <router-link
                class="pcw-name"
                :to="{ name: 'StudentProfile', query: { student: r.student } }"
                title="Open this student's profile"
              >
                {{ r.student_name }}
              </router-link>
            </div>
            <div class="pcw-meta">
              <span class="pcw-meta-id">{{ r.student }}</span>
              <template v-if="r.standard"><span class="pcw-meta-dot">·</span>{{ r.standard }}</template>
              <template v-if="r.batch"><span class="pcw-meta-dot">·</span>{{ r.batch }}</template>
            </div>
            <div class="pcw-badges">
              <span class="pcw-not-attended-badge" title="Calls this month nobody picked up">
                <i class="fa fa-phone-square"></i> Not attended {{ r.count }}×
              </span>
              <span v-if="r.is_pending" class="pcw-complaint-tag">
                <i class="fa fa-clock-o"></i> Not reached · {{ ageText(r.last_called_on) }}
              </span>
              <span v-else class="pcw-meeting-tag is-done">
                <i class="fa fa-check"></i> {{ r.reached.status === 'Closed' ? 'Closed' : 'Reached' }}
              </span>
              <router-link class="ccw-source" :to="sourceRoute(r)">
                <i class="fa" :class="source(r.call_for).icon"></i>
                {{ source(r.call_for).label }}
              </router-link>
            </div>

            <div v-if="r.is_pending && r.phones.length" class="pcw-phones">
              <a
                v-for="p in r.phones"
                :key="p.label"
                class="pcw-phone"
                :href="`tel:${p.number}`"
                :title="`Call ${p.label}`"
              >
                <i class="fa fa-phone"></i>
                <span>{{ p.label }}{{ parentName(r, p.label) ? ` (${parentName(r, p.label)})` : '' }}</span>
                <b>{{ p.number }}</b>
              </a>
            </div>
          </div>
        </header>

        <div class="ccw-block">
          <div class="ccw-block-head"><i class="fa fa-phone-square"></i> Calls nobody picked up</div>
          <ul class="nac-attempts">
            <li v-for="a in r.attempts" :key="a.name">
              <span class="nac-when">{{ formatDateTime(a.called_on) }}</span>
              <span v-if="a.called_by">by <b>{{ a.called_by }}</b></span>
              <span v-if="a.spoken_to">· tried {{ a.spoken_to }}</span>
              <span v-if="a.call_notes" class="nac-notes">— {{ a.call_notes }}</span>
            </li>
          </ul>
        </div>

        <div v-if="r.reached" class="ccw-block ccw-block-solved">
          <div class="ccw-block-head">
            <i class="fa fa-check-circle"></i>
            <template v-if="r.reached.status === 'Closed'">Closed</template>
            <template v-else>
              Reached<template v-if="r.reached.spoken_to"> {{ r.reached.spoken_to }}</template>
            </template>
            <template v-if="r.reached.called_by"> by <b>{{ r.reached.called_by }}</b></template>
            <span class="ccw-when">{{ formatDateTime(r.reached.called_on) }}</span>
          </div>
        </div>

        <div v-if="r.is_pending" class="pcw-actions">
          <router-link class="pcw-btn pcw-btn-primary" :to="sourceRoute(r)">
            <i class="fa fa-phone"></i> Call again on {{ source(r.call_for).label }}
          </router-link>
        </div>
      </article>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday } from '@/data/serverDate'

const SOURCES = [
  { value: 'Attendance', label: 'Attendance Calls', icon: 'fa-phone-square', route: 'AttendanceCalls' },
  { value: 'Pending Calls', label: 'Pending Calls', icon: 'fa-phone', route: 'PendingCalls' },
  { value: 'Mistakes', label: 'Mistakes', icon: 'fa-exclamation-triangle', route: 'StudentMistakes' },
]

const standards = ref([])
const batches = ref([])

const month = ref((serverToday.value || '').slice(0, 7))
const callFor = ref('')
const standard = ref('')
const batch = ref('')
const search = ref('')
// 'pending' | 'reached' | 'all'
const view = ref('pending')

const rows = ref([])
const loading = ref(false)

const listResource = createResource({
  url: 'bb_tution_management.bb_academy.not_attended.get_not_attended_calls',
})
const standardsResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const batchesResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })

function source(callFor) {
  return SOURCES.find((s) => s.value === callFor) || { label: callFor, icon: 'fa-phone', route: 'PendingCalls' }
}

function sourceRoute(r) {
  return { name: source(r.call_for).route }
}

function matchesSearch(r) {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return (r.student_name || '').toLowerCase().includes(q) || (r.student || '').toLowerCase().includes(q)
}

const searched = computed(() => rows.value.filter(matchesSearch))
const pending = computed(() => searched.value.filter((r) => r.is_pending))
const reached = computed(() => searched.value.filter((r) => !r.is_pending))

const visible = computed(
  () => ({ pending: pending.value, reached: reached.value, all: searched.value })[view.value]
)

const kpis = computed(() => [
  {
    key: 'pending',
    label: 'Not Reached Yet',
    icon: 'fa-phone-square',
    sub: 'Still need a call back',
    value: pending.value.length,
    cls: pending.value.length ? 'ccw-kpi-pending' : '',
    title: 'Parents who have not picked up since the last unanswered call',
  },
  {
    key: 'reached',
    label: 'Reached Later',
    icon: 'fa-check-circle',
    sub: 'Picked up on a later call',
    value: reached.value.length,
    cls: 'ccw-kpi-completed',
    title: 'Parents reached (or the card closed) after not attending',
  },
  {
    key: 'all',
    label: 'All Not Attended',
    icon: 'fa-list',
    sub: `${searched.value.reduce((n, r) => n + r.count, 0)} unanswered calls`,
    value: searched.value.length,
    cls: 'pcw-kpi-total',
    title: 'Every student with an unanswered call in the selected month',
  },
])

const emptyState = computed(() => {
  if (search.value.trim() && rows.value.length) {
    return { icon: 'fa-search', title: 'No match', text: 'No student matches that search.' }
  }
  if (view.value === 'pending') {
    return { icon: 'fa-thumbs-o-up', title: 'Everyone reached', text: 'No parent is waiting for a call back.' }
  }
  if (view.value === 'reached') {
    return { icon: 'fa-info-circle', title: 'Nobody reached yet', text: 'No unanswered call was followed up this month.' }
  }
  return { icon: 'fa-info-circle', title: 'No unanswered calls', text: 'Every call this month was picked up.' }
})

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function parentName(r, label) {
  return { Father: r.father_name, Mother: r.mother_name, Guardian: r.guardian_name }[label] || ''
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function ageText(value) {
  if (!value) return ''
  const days = Math.floor((Date.now() - new Date(String(value).replace(' ', 'T')).getTime()) / 86400000)
  if (days <= 0) return 'today'
  return days === 1 ? '1 day' : `${days} days`
}

async function load() {
  loading.value = true
  try {
    const res = await listResource.submit({
      month: month.value || null,
      call_for: callFor.value || null,
      standard: standard.value || null,
      batch: batch.value || null,
    })
    rows.value = res?.rows || []
  } catch (e) {
    rows.value = []
    console.error('Failed to load not attended calls', e)
  } finally {
    loading.value = false
  }
}

watch([month, callFor, standard, batch], load)

onMounted(async () => {
  await loadServerToday()
  if (!month.value) month.value = (serverToday.value || '').slice(0, 7)
  const [s, b] = await Promise.all([
    standardsResource.submit({ doctype: 'Standard' }),
    batchesResource.submit({ doctype: 'Batch' }),
  ])
  standards.value = s || []
  batches.value = b || []
  await load()
})
</script>

<style src="../pending-calls.css"></style>
<style>
.ccw-kpi-grid { --pcw-kpi-cols: 3; }
.ccw-kpi-sub { font-size: 11px; color: var(--text-muted); }
.ccw-kpi-pending { border-left-color: var(--red-500); }
.ccw-kpi-completed { border-left-color: var(--green-500, #22c55e); }
.ccw-card.ccw-open { border-left: 4px solid var(--orange-400, #fb923c); }
.ccw-card.ccw-resolved { border-left: 4px solid var(--green-500, #22c55e); }
.ccw-source {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--text-muted);
  text-decoration: none;
}
.ccw-source:hover { color: var(--text-color); }
.ccw-block {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--pcw-radius-sm, 8px);
  background: var(--subtle-fg, var(--gray-50));
  border: 1px solid var(--border-color);
}
.ccw-block-solved { background: var(--bg-green, #f0fdf4); }
.ccw-block-head { font-size: 12.5px; color: var(--text-color); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.ccw-when { margin-left: auto; font-size: 11.5px; color: var(--text-muted); }
.nac-attempts { margin: 6px 0 0; padding-left: 18px; font-size: 12.5px; line-height: 1.6; color: var(--text-color); }
.nac-attempts li > span + span { margin-left: 4px; }
.nac-when { font-variant-numeric: tabular-nums; }
.nac-notes { color: var(--text-muted); }
@media (max-width: 640px) {
  .ccw-kpi-grid { --pcw-kpi-cols: 1; }
  .ccw-when { margin-left: 0; width: 100%; }
}
</style>
