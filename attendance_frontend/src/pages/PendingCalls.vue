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

            <div v-if="missedTags(r).length" class="pcw-badges">
              <span
                v-for="m in missedTags(r)"
                :key="m.key"
                class="pcw-missed-tag"
                :title="`${m.category} reached ${m.from} mistakes (${m.label}) and went past it with no call home`"
              >
                <i class="fa fa-exclamation-triangle"></i> {{ m.category }}: missed call at {{ m.from }}
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
const CATEGORIES = ['H.W', 'Test', 'Study', 'Class', 'Behaviour']
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

// One tag per band a category's count went past with no call.
function missedTags(r) {
  return r.categories.flatMap((c) =>
    (c.missed || []).map((m) => ({ ...m, category: c.category, key: `${c.category}-${m.from}` }))
  )
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

<style src="../pending-calls.css"></style>
