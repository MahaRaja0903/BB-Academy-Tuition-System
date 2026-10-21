<template>
  <div class="pcw-manager">
    <!-- Control panel -->
    <div class="pcw-panel">
      <div class="pcw-panel-filters">
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
        <div class="pcw-field">
          <label><i class="fa fa-venus-mars"></i> Gender</label>
          <select class="form-control" v-model="gender">
            <option value="">All</option>
            <option value="Boys">Boys</option>
            <option value="Girls">Girls</option>
          </select>
        </div>
        <div v-if="view === 'history'" class="pcw-field">
          <label><i class="fa fa-calendar"></i> Month</label>
          <input type="month" class="form-control" v-model="month" />
        </div>
      </div>

      <div class="pcw-panel-view">
        <button
          type="button"
          class="pcw-seg"
          :class="{ 'is-active': view === 'pending' }"
          @click="view = 'pending'"
        >
          <i class="fa fa-phone"></i> Pending
        </button>
        <button
          type="button"
          class="pcw-seg"
          :class="{ 'is-active': view === 'history' }"
          @click="view = 'history'"
        >
          <i class="fa fa-history"></i> Call History
        </button>
      </div>
    </div>

    <!-- Category summary: how many students are owed a call for each category.
         A tap narrows the list to exactly those students. -->
    <div v-if="view === 'pending'" class="pcw-kpi-grid">
      <button
        v-for="k in kpis"
        :key="k.key"
        type="button"
        class="pcw-kpi"
        :class="[k.cls, { 'is-active': categoryFilter === k.category }]"
        :title="k.title"
        @click="toggleCategory(k.category)"
      >
        <span class="pcw-kpi-label">{{ k.label }}</span>
        <span class="pcw-kpi-value">{{ k.value }}</span>
      </button>
    </div>

    <p v-if="view === 'pending' && countFrom" class="pcw-rule">
      <i class="fa fa-info-circle"></i>
      A student is listed once they have <b>{{ threshold }} or more</b> mistakes in any one
      category since the last call about it (counting from {{ prettyDate(countFrom, true) }}). Logging
      the call removes them; the next mistake starts a new count.
    </p>

    <!-- Toolbar -->
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
      <span v-if="view === 'pending' && categoryFilter" class="pcw-filter-chip">
        <span>Showing <strong>{{ categoryFilter }}</strong></span>
        <button type="button" title="Clear filter" @click="categoryFilter = null">
          <i class="fa fa-times"></i>
        </button>
      </span>
      <button type="button" class="pcw-refresh-btn" :disabled="loading" @click="load">
        <i class="fa" :class="loading ? 'fa-spinner fa-spin' : 'fa-refresh'"></i>
        <span>Refresh</span>
      </button>
    </div>

    <!-- Skeletons -->
    <template v-if="loading">
      <div v-for="i in 3" :key="`sk${i}`" class="pcw-card">
        <div class="pcw-skeleton-bar" style="width: 45%"></div>
        <div class="pcw-skeleton-bar" style="width: 75%"></div>
        <div class="pcw-skeleton-bar" style="width: 60%"></div>
      </div>
    </template>

    <!-- ================= Pending ================= -->
    <template v-else-if="view === 'pending'">
      <div v-if="!visibleRecords.length" class="pcw-empty-state">
        <div class="pcw-empty-icon"><i class="fa" :class="emptyState.icon"></i></div>
        <h4>{{ emptyState.title }}</h4>
        <p>{{ emptyState.text }}</p>
      </div>

      <article
        v-for="r in visibleRecords"
        :key="r.student"
        class="pcw-card"
        :class="{ 'is-overdue': r.days_pending >= OVERDUE_DAYS }"
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
              <i
                v-if="r.gender"
                class="fa pcw-gender-icon"
                :class="r.gender === 'Girls' ? 'fa-female pcw-gender-female' : 'fa-male pcw-gender-male'"
                :title="r.gender"
              ></i>
            </div>

            <div class="pcw-meta">
              <span class="pcw-meta-id">{{ r.student }}</span>
              <template v-if="r.standard"><span class="pcw-meta-dot">·</span>{{ r.standard }}</template>
              <template v-if="r.batch"><span class="pcw-meta-dot">·</span>{{ r.batch }}</template>
            </div>

            <div class="pcw-badges">
              <span class="pcw-wait-badge" :title="`Call due since ${prettyDate(r.due_since, true)}`">
                <i class="fa fa-clock-o"></i> {{ waitingText(r.days_pending) }}
              </span>
              <span v-if="r.last_call" class="pcw-last-call">
                Last call {{ formatDateTime(r.last_call.called_on) }}
                <template v-if="r.last_call.categories"> · {{ r.last_call.categories }}</template>
              </span>
            </div>

            <div v-if="r.phones.length" class="pcw-phones">
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
            <div v-else class="pcw-no-phone">
              <i class="fa fa-exclamation-circle"></i> No phone number on the student record.
            </div>
          </div>
        </header>

        <!-- Count per category since the last call -->
        <div class="pcw-tally">
          <span
            v-for="c in r.categories"
            :key="c.category"
            class="pcw-tally-chip"
            :class="{ 'is-due': c.due }"
            :title="
              c.due
                ? `${c.count} ${c.category} mistakes — call due since ${prettyDate(c.due_since, true)}`
                : `${c.count} ${c.category} mistake(s), not yet at ${threshold}`
            "
          >
            {{ c.category }} <b>{{ c.count }}</b>
          </span>
          <button type="button" class="pcw-link-btn" @click="toggleDetail(r)">
            <i class="fa" :class="expanded.has(r.student) ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
            {{ expanded.has(r.student) ? 'Hide' : 'View' }} mistakes
          </button>
        </div>

        <div v-if="expanded.has(r.student)" class="pcw-detail">
          <div v-if="detailLoading === r.student" class="pcw-detail-empty">Loading…</div>
          <table v-else-if="(details[r.student] || []).length" class="pcw-detail-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Category</th>
                <th>Result</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in details[r.student]" :key="m.reference_name">
                <td class="pcw-nowrap">{{ prettyDate(m.date) }}</td>
                <td>{{ m.category }}</td>
                <td><span class="pcw-result-badge" :data-result="m.result">{{ m.result }}</span></td>
                <td class="pcw-detail-what">
                  <span v-if="m.details">{{ m.details }}</span>
                  <em v-if="m.remarks" class="pcw-detail-remarks">{{ m.remarks }}</em>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="pcw-detail-empty">No pending mistakes.</p>
        </div>

        <div class="pcw-actions">
          <button type="button" class="pcw-btn pcw-btn-primary" @click="openCall(r)">
            <i class="fa fa-phone"></i> Log Call
          </button>
        </div>
      </article>
    </template>

    <!-- ================= History ================= -->
    <template v-else>
      <div v-if="!visibleCalls.length" class="pcw-empty-state">
        <div class="pcw-empty-icon"><i class="fa fa-history"></i></div>
        <h4>No calls logged</h4>
        <p>No call home was logged in this month with these filters.</p>
      </div>

      <article v-for="c in visibleCalls" :key="c.name" class="pcw-card pcw-card-history">
        <header class="pcw-history-head">
          <div>
            <router-link
              class="pcw-name"
              :to="{ name: 'StudentProfile', query: { student: c.student } }"
            >
              {{ c.student_name }}
            </router-link>
            <div class="pcw-meta">
              <span class="pcw-meta-id">{{ c.student }}</span>
              <template v-if="c.standard"><span class="pcw-meta-dot">·</span>{{ c.standard }}</template>
              <template v-if="c.batch"><span class="pcw-meta-dot">·</span>{{ c.batch }}</template>
            </div>
          </div>
          <span class="pcw-history-when">{{ formatDateTime(c.called_on) }}</span>
        </header>
        <div class="pcw-done-row">
          <i class="fa fa-phone"></i>
          <span>
            <b>{{ c.called_by }}</b> spoke to <b>{{ c.spoken_to }}</b>
            <template v-if="c.spoken_to_name"> ({{ c.spoken_to_name }})</template>
          </span>
        </div>
        <div class="pcw-tally pcw-tally-flat">
          <span v-for="b in c.breakdown" :key="b.category" class="pcw-tally-chip">
            {{ b.category }} <b>{{ b.count }}</b>
          </span>
        </div>
        <div v-if="c.call_notes" class="pcw-done-notes">“{{ c.call_notes }}”</div>
      </article>
    </template>

    <!-- Call modal -->
    <div v-if="callModal.open" class="pcw-modal-backdrop" @click.self="callModal.open = false">
      <div class="pcw-modal">
        <h3><i class="fa fa-phone"></i> Call Home — {{ callModal.record?.student_name }}</h3>
        <p class="pcw-modal-hint">
          Tick what the parents were told about. Each ticked category's count starts again from
          zero after this call.
        </p>

        <label class="pcw-modal-label">Informed about <span class="pcw-req">*</span></label>
        <div class="pcw-cat-picks">
          <label
            v-for="c in callModal.record?.categories || []"
            :key="c.category"
            class="pcw-cat-pick"
            :class="{ 'is-due': c.due }"
          >
            <input type="checkbox" :value="c.category" v-model="callModal.categories" />
            <span>{{ c.category }}</span>
            <b>{{ c.count }}</b>
          </label>
        </div>

        <label class="pcw-modal-label">Whom did you speak to? <span class="pcw-req">*</span></label>
        <select class="form-control" v-model="callModal.spoken_to">
          <option value="">Select</option>
          <option v-for="o in SPOKEN_TO" :key="o" :value="o">{{ o }}</option>
        </select>

        <label class="pcw-modal-label">Name / number spoken to</label>
        <input type="text" class="form-control" v-model="callModal.spoken_to_name" />

        <label class="pcw-modal-label">When was the call made?</label>
        <input type="datetime-local" class="form-control" v-model="callModal.called_on" />

        <label class="pcw-modal-label">
          Who spoke from the tuition? <span class="pcw-req">*</span>
        </label>
        <select class="form-control" v-model="callModal.called_by">
          <option value="">Select staff</option>
          <option v-for="s in staffList" :key="s.name" :value="s.name">{{ s.name }}</option>
        </select>

        <label class="pcw-modal-label">What was spoken? <span class="pcw-req">*</span></label>
        <textarea class="form-control" rows="3" v-model="callModal.call_notes"></textarea>

        <p v-if="callModal.error" class="pcw-modal-error">{{ callModal.error }}</p>
        <div class="pcw-modal-actions">
          <button class="pcw-btn-lg" @click="callModal.open = false">Cancel</button>
          <button
            class="pcw-btn-lg pcw-btn-primary-lg"
            :disabled="!canSaveCall || callModal.saving"
            @click="saveCall"
          >
            {{ callModal.saving ? 'Saving…' : 'Save Call' }}
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

// Mirrors CATEGORIES in bb_academy/pending_calls.py.
const CATEGORIES = ['H.W', 'Attendance', 'Test', 'Study', 'Class', 'Behaviour']
const SPOKEN_TO = ['Father', 'Mother', 'Guardian', 'Student', 'Other']
// A call still not made this many days after it fell due is flagged red.
const OVERDUE_DAYS = 2

const standards = ref([])
const batches = ref([])
const staffList = ref([])

const view = ref('pending')
const standard = ref('')
const batch = ref('')
const gender = ref('')
const month = ref((serverToday.value || '').slice(0, 7))
const search = ref('')
const categoryFilter = ref(null)

const records = ref([])
const calls = ref([])
const threshold = ref(3)
const countFrom = ref(null)
const loading = ref(false)
const expanded = ref(new Set())
const details = reactive({})
const detailLoading = ref(null)

const callModal = reactive({
  open: false,
  record: null,
  categories: [],
  spoken_to: '',
  spoken_to_name: '',
  called_on: '',
  called_by: '',
  call_notes: '',
  saving: false,
  error: '',
})

function matchesSearch(row) {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return (
    (row.student_name || '').toLowerCase().includes(q) ||
    (row.student || '').toLowerCase().includes(q)
  )
}

const searchedRecords = computed(() => records.value.filter(matchesSearch))

const visibleRecords = computed(() => {
  if (!categoryFilter.value) return searchedRecords.value
  return searchedRecords.value.filter((r) => r.due_categories.includes(categoryFilter.value))
})

const visibleCalls = computed(() => calls.value.filter(matchesSearch))

const kpis = computed(() => {
  const counts = Object.fromEntries(CATEGORIES.map((c) => [c, 0]))
  for (const r of searchedRecords.value) {
    for (const c of r.due_categories) counts[c] += 1
  }
  return [
    {
      key: 'total',
      category: null,
      label: 'Students',
      cls: 'pcw-kpi-total',
      value: searchedRecords.value.length,
      title: 'Show every student waiting for a call',
    },
    ...CATEGORIES.map((c) => ({
      key: c,
      category: c,
      label: c,
      cls: counts[c] ? 'pcw-kpi-due' : '',
      value: counts[c],
      title: `Show only students owed a call for ${c}`,
    })),
  ]
})

function toggleCategory(category) {
  categoryFilter.value = !category || categoryFilter.value === category ? null : category
}

const emptyState = computed(() => {
  if (categoryFilter.value && searchedRecords.value.length) {
    return {
      icon: 'fa-info-circle',
      title: `No call pending for ${categoryFilter.value}`,
      text: 'No student is owed a call for that category with these filters.',
    }
  }
  if (search.value.trim() && records.value.length) {
    return { icon: 'fa-search', title: 'No match', text: 'No pending student matches that search.' }
  }
  return {
    icon: 'fa-thumbs-o-up',
    title: 'No calls pending',
    text: `No student has reached ${threshold.value} mistakes in any category since their last call.`,
  }
})

const canSaveCall = computed(
  () =>
    callModal.categories.length > 0 &&
    !!callModal.spoken_to &&
    !!callModal.called_by &&
    !!(callModal.call_notes || '').trim()
)

const standardsResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const batchesResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const staffResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const pendingResource = createResource({
  url: 'bb_tution_management.bb_academy.pending_calls.get_pending_calls',
})
const historyResource = createResource({
  url: 'bb_tution_management.bb_academy.pending_calls.get_call_history',
})
const detailResource = createResource({
  url: 'bb_tution_management.bb_academy.pending_calls.get_student_mistakes',
})
const logResource = createResource({ url: 'bb_tution_management.bb_academy.pending_calls.log_call' })

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function prettyDate(value, withYear = false) {
  if (!value) return ''
  const d = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    ...(withYear ? { year: 'numeric' } : {}),
  })
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function waitingText(days) {
  if (days <= 0) return 'Due today'
  if (days === 1) return 'Pending 1 day'
  return `Pending ${days} days`
}

function parentName(r, label) {
  return { Father: r.father_name, Mother: r.mother_name, Guardian: r.guardian_name }[label] || ''
}

// `<input type="datetime-local">` speaks "YYYY-MM-DDTHH:MM"; Frappe stores
// "YYYY-MM-DD HH:MM:SS".
function fromInputDateTime(value) {
  if (!value) return null
  return String(value).replace('T', ' ') + ':00'
}

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

const filters = () => ({
  standard: standard.value || null,
  batch: batch.value || null,
  gender: gender.value || null,
})

async function load() {
  loading.value = true
  try {
    if (view.value === 'pending') {
      const res = await pendingResource.submit(filters())
      records.value = res?.records || []
      threshold.value = res?.threshold || 3
      countFrom.value = res?.count_from || null
      // Counts changed under the expanded rows; fetch them afresh when reopened.
      for (const key of Object.keys(details)) delete details[key]
      expanded.value = new Set()
    } else {
      const res = await historyResource.submit({ ...filters(), month: month.value || null })
      calls.value = res?.calls || []
    }
  } catch (e) {
    if (view.value === 'pending') records.value = []
    else calls.value = []
    console.error('Failed to load pending calls', e)
  } finally {
    loading.value = false
  }
}

async function toggleDetail(record) {
  const next = new Set(expanded.value)
  if (next.has(record.student)) {
    next.delete(record.student)
    expanded.value = next
    return
  }
  next.add(record.student)
  expanded.value = next

  if (details[record.student]) return
  detailLoading.value = record.student
  try {
    const res = await detailResource.submit({ student: record.student })
    details[record.student] = res?.mistakes || []
  } catch (e) {
    details[record.student] = []
    console.error('Failed to load pending mistakes', e)
  } finally {
    detailLoading.value = null
  }
}

function openCall(record) {
  Object.assign(callModal, {
    open: true,
    record,
    categories: [...record.due_categories],
    spoken_to: '',
    spoken_to_name: '',
    called_on: nowForInput(),
    called_by: '',
    call_notes: '',
    saving: false,
    error: '',
  })
}

async function saveCall() {
  callModal.saving = true
  callModal.error = ''
  try {
    await logResource.submit({
      student: callModal.record.student,
      categories: JSON.stringify(callModal.categories),
      spoken_to: callModal.spoken_to,
      spoken_to_name: callModal.spoken_to_name,
      called_on: fromInputDateTime(callModal.called_on),
      called_by: callModal.called_by,
      call_notes: callModal.call_notes,
    })
    callModal.open = false
    await load()
  } catch (e) {
    callModal.error = errorText(e)
  } finally {
    callModal.saving = false
  }
}

async function loadLookups() {
  const [s, b, st] = await Promise.all([
    standardsResource.submit({ doctype: 'Standard' }),
    batchesResource.submit({ doctype: 'Batch' }),
    staffResource.submit({ doctype: 'Staff' }),
  ])
  standards.value = s || []
  batches.value = b || []
  staffList.value = st || []
}

watch([view, standard, batch, gender, month], () => {
  categoryFilter.value = null
  load()
})

onMounted(async () => {
  await loadServerToday()
  if (!month.value) month.value = (serverToday.value || '').slice(0, 7)
  await loadLookups()
  await load()
})
</script>

<style>
/* Pending Call Works — the students whose parents are owed a call. */

.pcw-manager {
  --pcw-radius: var(--border-radius-md, 8px);
  --pcw-radius-sm: var(--border-radius, 6px);
  padding: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ---- control panel ---- */
.pcw-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px;
  padding: 16px;
  margin-bottom: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
}

.pcw-panel-filters { display: flex; flex-wrap: wrap; gap: 12px; flex: 1; }

.pcw-field { display: flex; flex-direction: column; gap: 5px; min-width: 150px; flex: 1; }

.pcw-field label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin: 0;
}

.pcw-field label i { margin-right: 4px; }

.pcw-panel-view {
  display: flex;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  overflow: hidden;
}

.pcw-seg {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: var(--card-bg);
  color: var(--text-muted);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.pcw-seg + .pcw-seg { border-left: 1px solid var(--border-color); }
.pcw-seg.is-active { background: var(--blue-500); color: #fff; }

/* ---- category summary ---- */
.pcw-kpi-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
  margin-bottom: 10px;
}

.pcw-kpi {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 12px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--gray-300);
  border-radius: var(--pcw-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.pcw-kpi:hover { border-color: var(--gray-400); }

.pcw-kpi.is-active {
  border-color: var(--gray-600, var(--text-color));
  box-shadow: 0 0 0 1px var(--gray-600, var(--text-color)) inset;
}

.pcw-kpi-total { border-left-color: var(--blue-500); }
.pcw-kpi-due { border-left-color: var(--red-500); }

.pcw-kpi-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.pcw-kpi-value {
  font-size: 21px;
  font-weight: 700;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.pcw-rule {
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-muted);
}

.pcw-rule i { margin-right: 4px; }

/* ---- toolbar ---- */
.pcw-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }

.pcw-search-wrap { position: relative; flex: 1; max-width: 420px; }

.pcw-search-wrap i {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 13px;
}

.pcw-search-input {
  width: 100%;
  padding: 8px 12px 8px 32px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
}

.pcw-filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px 5px 10px;
  font-size: 12px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  white-space: nowrap;
}

.pcw-filter-chip button {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0 4px;
}

.pcw-refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.pcw-refresh-btn:disabled { opacity: 0.6; cursor: default; }

/* ---- card ---- */
.pcw-card {
  padding: 16px;
  margin-bottom: 12px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--orange-500);
  border-radius: var(--pcw-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
}

.pcw-card.is-overdue { border-left-color: var(--red-500); }
.pcw-card-history { border-left-color: var(--green-500); }

.pcw-card-head {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.pcw-avatar {
  width: 88px;
  height: 88px;
  object-fit: cover;
  border-radius: var(--pcw-radius-sm);
  background: var(--gray-200);
}

.pcw-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-600);
  font-weight: 700;
  font-size: 24px;
}

.pcw-ident { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.pcw-name-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

.pcw-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.pcw-name:hover { text-decoration: underline; }
.pcw-gender-icon { font-size: 12px; }
.pcw-gender-female { color: #ff69b4; }
.pcw-gender-male { color: #2196f3; }

.pcw-meta { display: flex; flex-wrap: wrap; gap: 5px; font-size: 12px; color: var(--text-muted); }
.pcw-meta-id { font-weight: 700; font-variant-numeric: tabular-nums; }
.pcw-meta-dot { opacity: 0.5; margin-right: 5px; }

.pcw-badges { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }

.pcw-wait-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
  background: var(--bg-orange, #ffedd5);
  color: var(--text-on-orange, #c2410c);
}

.is-overdue .pcw-wait-badge {
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

.pcw-last-call { font-size: 11.5px; color: var(--text-muted); }

.pcw-phones { display: flex; flex-wrap: wrap; gap: 6px; }

.pcw-phone {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-color);
  text-decoration: none;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
}

.pcw-phone i { color: var(--green-600, #16a34a); }
.pcw-phone b { font-variant-numeric: tabular-nums; }
.pcw-phone:hover { background: var(--subtle-fg, var(--gray-100)); text-decoration: none; }

.pcw-no-phone { font-size: 12px; color: var(--red-600, #dc2626); }

/* ---- tally ---- */
.pcw-tally {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.pcw-tally-flat { border-top: 0; padding-top: 0; margin-top: 8px; }

.pcw-tally-chip {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-100));
  border-radius: 4px;
  padding: 3px 8px;
}

.pcw-tally-chip b { font-weight: 700; color: var(--heading-color); }

.pcw-tally-chip.is-due {
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
  font-weight: 600;
}

.pcw-tally-chip.is-due b { color: inherit; }

.pcw-link-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 6px;
  border: none;
  background: none;
  color: var(--blue-600, #2563eb);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

/* ---- detail ---- */
.pcw-detail {
  margin-top: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  overflow-x: auto;
}

.pcw-detail-empty { padding: 12px; margin: 0; font-size: 12.5px; color: var(--text-muted); }

.pcw-detail-table { width: 100%; border-collapse: collapse; font-size: 12.5px; min-width: 420px; }

.pcw-detail-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-50));
  border-bottom: 1px solid var(--border-color);
}

.pcw-detail-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: top;
}

.pcw-detail-table tr:last-child td { border-bottom: none; }
.pcw-nowrap { white-space: nowrap; font-variant-numeric: tabular-nums; }
.pcw-detail-what { color: var(--text-muted); }
.pcw-detail-remarks { display: block; margin-top: 2px; font-size: 11.5px; }

.pcw-result-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: var(--bg-orange, #ffedd5);
  color: var(--text-on-orange, #c2410c);
}

.pcw-result-badge[data-result='Fail'],
.pcw-result-badge[data-result='Critical'],
.pcw-result-badge[data-result='Absent'] {
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

/* ---- actions ---- */
.pcw-actions { display: flex; justify-content: flex-end; margin-top: 14px; }

.pcw-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  cursor: pointer;
}

.pcw-btn-primary { background: var(--blue-500); border-color: var(--blue-500); color: #fff; }

/* ---- history ---- */
.pcw-history-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.pcw-history-when { font-size: 12px; font-weight: 600; color: var(--text-muted); white-space: nowrap; }

.pcw-done-row { display: flex; gap: 8px; font-size: 12.5px; color: var(--text-color); }
.pcw-done-row i { color: var(--text-muted); margin-top: 2px; }

.pcw-done-notes { margin-top: 8px; font-size: 12px; font-style: italic; color: var(--text-muted); }

/* ---- empty / skeleton ---- */
.pcw-empty-state {
  padding: 44px 20px;
  text-align: center;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius);
}

.pcw-empty-icon { font-size: 34px; color: var(--text-muted); opacity: 0.6; }
.pcw-empty-state h4 { margin: 12px 0 4px; font-size: 15px; color: var(--heading-color); }
.pcw-empty-state p { margin: 0; font-size: 13px; color: var(--text-muted); }

.pcw-skeleton-bar {
  height: 12px;
  margin-bottom: 10px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: pcw-shimmer 1.4s ease infinite;
}

@keyframes pcw-shimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* ---- modal ---- */
.pcw-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.45);
}

.pcw-modal {
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  background: var(--card-bg);
  border-radius: var(--pcw-radius);
  box-shadow: var(--shadow-lg, 0 10px 30px rgba(0, 0, 0, 0.2));
}

.pcw-modal h3 { margin: 0 0 6px; font-size: 16px; font-weight: 700; color: var(--heading-color); }
.pcw-modal-hint { margin: 0 0 6px; font-size: 12.5px; color: var(--text-muted); line-height: 1.5; }

.pcw-modal-label {
  display: block;
  margin: 12px 0 5px;
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.pcw-req { color: var(--red-500); }

.pcw-cat-picks { display: flex; flex-wrap: wrap; gap: 8px; }

.pcw-cat-pick {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  cursor: pointer;
}

.pcw-cat-pick input { width: 16px; height: 16px; accent-color: var(--blue-500); }
.pcw-cat-pick.is-due { border-color: var(--red-300, #fca5a5); }
.pcw-cat-pick.is-due b { color: var(--text-on-red, #b91c1c); }

.pcw-modal-error {
  margin: 12px 0 0;
  padding: 9px 11px;
  font-size: 12.5px;
  border-radius: var(--pcw-radius-sm);
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

.pcw-modal-actions { display: flex; gap: 10px; margin-top: 18px; }

.pcw-btn-lg {
  flex: 1;
  padding: 11px 16px;
  font-size: 13.5px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: var(--pcw-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.pcw-btn-primary-lg { background: var(--blue-500); border-color: var(--blue-500); color: #fff; }
.pcw-btn-primary-lg:disabled { opacity: 0.55; cursor: not-allowed; }

/* ---- tablet ---- */
@media (max-width: 992px) {
  .pcw-kpi-grid { grid-template-columns: repeat(4, 1fr); }
}

/* ---- mobile ---- */
@media (max-width: 767px) {
  .pcw-manager { padding: 10px; }
  .pcw-panel { flex-direction: column; align-items: stretch; padding: 14px; }
  .pcw-panel-filters { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .pcw-field { min-width: 0; }
  .pcw-seg { flex: 1; justify-content: center; }
  .pcw-kpi-grid { grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .pcw-kpi { padding: 8px 10px; }
  .pcw-kpi-value { font-size: 18px; }
  .pcw-toolbar { flex-direction: column; align-items: stretch; }
  .pcw-search-wrap { max-width: none; }
  .pcw-refresh-btn { justify-content: center; }
  .pcw-card-head { grid-template-columns: 72px minmax(0, 1fr); gap: 12px; }
  .pcw-avatar { width: 72px; height: 72px; }
  .pcw-link-btn { margin-left: 0; }
  .pcw-btn { flex: 1; }
}
</style>
