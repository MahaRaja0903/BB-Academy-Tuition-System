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
          <label><i class="fa fa-sitemap"></i> Raised From</label>
          <select class="form-control" v-model="complaintFor">
            <option value="">All</option>
            <option value="Attendance">Attendance Calls</option>
            <option value="Mistakes">Mistakes</option>
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

    <!-- Pending / Completed / Total. A tap narrows the list. -->
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
        v-for="c in visible"
        :key="c.name"
        class="pcw-card ccw-card"
        :class="c.status === 'Open' ? 'ccw-open' : 'ccw-resolved'"
      >
        <header class="pcw-card-head">
          <img v-if="c.image" class="pcw-avatar" :src="c.image" :alt="c.student_name" loading="lazy" />
          <div v-else class="pcw-avatar pcw-avatar-fallback">{{ initials(c.student_name) }}</div>

          <div class="pcw-ident">
            <div class="pcw-name-row">
              <router-link
                class="pcw-name"
                :to="{ name: 'StudentProfile', query: { student: c.student } }"
                title="Open this student's profile"
              >
                {{ c.student_name }}
              </router-link>
            </div>
            <div class="pcw-meta">
              <span class="pcw-meta-id">{{ c.student }}</span>
              <template v-if="c.standard"><span class="pcw-meta-dot">·</span>{{ c.standard }}</template>
              <template v-if="c.batch"><span class="pcw-meta-dot">·</span>{{ c.batch }}</template>
            </div>
            <div class="pcw-badges">
              <span v-if="c.status === 'Open'" class="pcw-complaint-tag">
                <i class="fa fa-clock-o"></i> Pending · {{ ageText(c.received_on) }}
              </span>
              <span v-else class="pcw-meeting-tag is-done"><i class="fa fa-check"></i> Solved</span>
              <router-link class="ccw-source" :to="sourceRoute(c)">
                <i class="fa" :class="c.complaint_for === 'Mistakes' ? 'fa-exclamation-triangle' : 'fa-phone-square'"></i>
                {{ c.complaint_for === 'Mistakes' ? 'Mistakes' : 'Attendance Calls' }}
              </router-link>
            </div>

            <div v-if="c.status === 'Open' && c.phones.length" class="pcw-phones">
              <a
                v-for="p in c.phones"
                :key="p.label"
                class="pcw-phone"
                :href="`tel:${p.number}`"
                :title="`Call ${p.label}`"
              >
                <i class="fa fa-phone"></i>
                <span>{{ p.label }}{{ parentName(c, p.label) ? ` (${parentName(c, p.label)})` : '' }}</span>
                <b>{{ p.number }}</b>
              </a>
            </div>
          </div>
        </header>

        <div class="ccw-block">
          <div class="ccw-block-head">
            <i class="fa fa-bullhorn"></i>
            <b>{{ c.complained_by }}</b> complained
            <span class="ccw-when">
              {{ formatDateTime(c.received_on) }}<template v-if="c.received_by"> · taken by {{ c.received_by }}</template>
            </span>
          </div>
          <p class="ccw-text">{{ c.complaint }}</p>
        </div>

        <div v-if="c.status === 'Resolved'" class="ccw-block ccw-block-solved">
          <div class="ccw-block-head">
            <i class="fa fa-check-circle"></i>
            Solved by <b>{{ c.resolved_by }}</b>
            <template v-if="c.resolution_spoken_to"> with {{ c.resolution_spoken_to }}</template>
            <span class="ccw-when">{{ formatDateTime(c.resolved_on) }}</span>
          </div>
          <p class="ccw-text">{{ c.resolution_notes }}</p>
        </div>

        <div class="pcw-actions">
          <button
            v-if="c.status === 'Open'"
            type="button"
            class="pcw-btn pcw-btn-primary"
            @click="openSolve(c)"
          >
            <i class="fa fa-phone"></i> Call &amp; Solve
          </button>
          <button v-else type="button" class="pcw-btn" @click="reopen(c)">
            <i class="fa fa-undo"></i> Reopen
          </button>
        </div>
      </article>
    </template>

    <!-- Solve modal: the call back -->
    <div v-if="solve.open" class="pcw-modal-backdrop" @click.self="solve.open = false">
      <div class="pcw-modal">
        <h3><i class="fa fa-phone"></i> Solve Complaint — {{ solve.record?.student_name }}</h3>
        <p class="pcw-modal-hint">
          <b>{{ solve.record?.complained_by }}</b> said: “{{ solve.record?.complaint }}”
        </p>

        <label class="pcw-modal-label">Whom did you speak to?</label>
        <div class="pcw-choice-row">
          <button
            v-for="o in WHO"
            :key="o"
            type="button"
            class="pcw-choice"
            :class="{ 'is-active': solve.spoken_to === o }"
            @click="solve.spoken_to = solve.spoken_to === o ? '' : o"
          >
            {{ o }}
          </button>
        </div>

        <label class="pcw-modal-label">Who called from the tuition? <span class="pcw-req">*</span></label>
        <select class="form-control" v-model="solve.resolved_by">
          <option value="">Select staff</option>
          <option v-for="s in staffList" :key="s.name" :value="s.name">{{ s.name }}</option>
        </select>

        <label class="pcw-modal-label">When?</label>
        <input type="datetime-local" class="form-control" v-model="solve.resolved_on" />

        <label class="pcw-modal-label">How was it solved? <span class="pcw-req">*</span></label>
        <textarea class="form-control" rows="3" v-model="solve.notes"></textarea>

        <p v-if="solve.error" class="pcw-modal-error">{{ solve.error }}</p>
        <div class="pcw-modal-actions">
          <button class="pcw-btn-lg" @click="solve.open = false">Cancel</button>
          <button
            class="pcw-btn-lg pcw-btn-primary-lg"
            :disabled="solve.saving || !solve.resolved_by || !solve.notes.trim()"
            @click="saveSolve"
          >
            {{ solve.saving ? 'Saving…' : 'Solved — Close Complaint' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday } from '@/data/serverDate'

const WHO = ['Father', 'Mother', 'Guardian', 'Other']

const standards = ref([])
const batches = ref([])
const staffList = ref([])

const month = ref((serverToday.value || '').slice(0, 7))
const complaintFor = ref('')
const standard = ref('')
const batch = ref('')
const search = ref('')
// 'pending' | 'completed' | 'total'
const view = ref('pending')

const complaints = ref([])
const loading = ref(false)

const listResource = createResource({ url: 'bb_tution_management.bb_academy.complaints.get_complaints' })
const resolveResource = createResource({
  url: 'bb_tution_management.bb_academy.complaints.resolve_complaint',
})
const reopenResource = createResource({
  url: 'bb_tution_management.bb_academy.complaints.reopen_complaint',
})
const standardsResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const batchesResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const staffResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })

function matchesSearch(c) {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return (c.student_name || '').toLowerCase().includes(q) || (c.student || '').toLowerCase().includes(q)
}

function inMonth(value) {
  return !!value && String(value).slice(0, 7) === month.value
}

const searched = computed(() => complaints.value.filter(matchesSearch))
const pending = computed(() => searched.value.filter((c) => c.status === 'Open'))
const completed = computed(() =>
  searched.value.filter((c) => c.status === 'Resolved' && inMonth(c.resolved_on))
)
const total = computed(() => searched.value.filter((c) => c.received_this_month))

const visible = computed(
  () => ({ pending: pending.value, completed: completed.value, total: total.value })[view.value]
)

const kpis = computed(() => [
  {
    key: 'pending',
    label: 'Pending Complaint Calls',
    icon: 'fa-clock-o',
    sub: 'Not solved yet (any month)',
    value: pending.value.length,
    cls: pending.value.length ? 'ccw-kpi-pending' : '',
    title: 'Complaints still waiting for a call back',
  },
  {
    key: 'completed',
    label: 'Completed Complaint Calls',
    icon: 'fa-check-circle',
    sub: 'Solved this month',
    value: completed.value.length,
    cls: 'ccw-kpi-completed',
    title: 'Complaints solved in the selected month',
  },
  {
    key: 'total',
    label: 'Total Complaints',
    icon: 'fa-bullhorn',
    sub: 'Received this month',
    value: total.value.length,
    cls: 'pcw-kpi-total',
    title: 'Every complaint received in the selected month',
  },
])

const emptyState = computed(() => {
  if (search.value.trim() && complaints.value.length) {
    return { icon: 'fa-search', title: 'No match', text: 'No complaint matches that search.' }
  }
  if (view.value === 'pending') {
    return { icon: 'fa-thumbs-o-up', title: 'No pending complaints', text: 'Every complaint has been solved.' }
  }
  if (view.value === 'completed') {
    return { icon: 'fa-info-circle', title: 'Nothing solved yet', text: 'No complaint was solved this month.' }
  }
  return { icon: 'fa-info-circle', title: 'No complaints', text: 'No complaint was received this month.' }
})

const solve = reactive({
  open: false,
  record: null,
  spoken_to: '',
  resolved_by: '',
  resolved_on: '',
  notes: '',
  saving: false,
  error: '',
})

function nowForInput() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}`
}

function errorText(e) {
  return e?.messages?.[0] || e?.message || String(e || 'Something went wrong')
}

function openSolve(record) {
  Object.assign(solve, {
    open: true,
    record,
    spoken_to: record.complained_by !== 'Other' ? record.complained_by : '',
    resolved_by: '',
    resolved_on: nowForInput(),
    notes: '',
    saving: false,
    error: '',
  })
}

async function saveSolve() {
  solve.saving = true
  solve.error = ''
  try {
    await resolveResource.submit({
      name: solve.record.name,
      resolved_by: solve.resolved_by,
      resolution_notes: solve.notes,
      resolution_spoken_to: solve.spoken_to || null,
      resolved_on: solve.resolved_on ? solve.resolved_on.replace('T', ' ') + ':00' : null,
    })
    solve.open = false
    await load()
  } catch (e) {
    solve.error = errorText(e)
  } finally {
    solve.saving = false
  }
}

async function reopen(record) {
  if (!window.confirm(`Reopen the complaint for ${record.student_name}?`)) return
  try {
    await reopenResource.submit({ name: record.name })
    await load()
  } catch (e) {
    window.alert(errorText(e))
  }
}

function sourceRoute(c) {
  return { name: c.complaint_for === 'Mistakes' ? 'StudentMistakes' : 'AttendanceCalls' }
}

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function parentName(c, label) {
  return { Father: c.father_name, Mother: c.mother_name, Guardian: c.guardian_name }[label] || ''
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
      complaint_for: complaintFor.value || null,
      standard: standard.value || null,
      batch: batch.value || null,
    })
    complaints.value = res?.complaints || []
  } catch (e) {
    complaints.value = []
    console.error('Failed to load complaints', e)
  } finally {
    loading.value = false
  }
}

watch([month, complaintFor, standard, batch], load)

onMounted(async () => {
  await loadServerToday()
  if (!month.value) month.value = (serverToday.value || '').slice(0, 7)
  const [s, b, st] = await Promise.all([
    standardsResource.submit({ doctype: 'Standard' }),
    batchesResource.submit({ doctype: 'Batch' }),
    staffResource.submit({ doctype: 'Staff' }),
  ])
  standards.value = s || []
  batches.value = b || []
  staffList.value = st || []
  await load()
})
</script>

<style src="../pending-calls.css"></style>
<style>
.ccw-kpi-grid { --pcw-kpi-cols: 3; }
.ccw-kpi-sub { font-size: 11px; color: var(--text-muted); }
.ccw-kpi-pending { border-left-color: var(--red-500); }
.ccw-kpi-completed { border-left-color: var(--green-500, #22c55e); }
.ccw-card.ccw-open { border-left: 4px solid var(--red-400, #f87171); }
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
.ccw-text { margin: 6px 0 0; font-size: 13px; line-height: 1.5; color: var(--text-color); white-space: pre-wrap; }
@media (max-width: 640px) {
  .ccw-kpi-grid { --pcw-kpi-cols: 1; }
  .ccw-when { margin-left: 0; width: 100%; }
}
</style>
