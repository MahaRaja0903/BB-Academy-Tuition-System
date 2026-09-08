<template>
  <div class="student-profile">
    <!-- Picker: hidden when printing, since the sheet is for the parent -->
    <div class="prof-picker no-print">
      <div class="prof-picker-row">
        <div class="prof-field">
          <label for="prof-standard"><i class="fa fa-graduation-cap"></i> Standard</label>
          <select id="prof-standard" class="form-control" v-model="standard">
            <option value="">All</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="prof-field">
          <label for="prof-batch"><i class="fa fa-users"></i> Batch</label>
          <select id="prof-batch" class="form-control" v-model="batch">
            <option value="">All</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
        <div class="prof-field prof-field-search">
          <label for="prof-search"><i class="fa fa-search"></i> Find Student</label>
          <input
            id="prof-search"
            type="text"
            class="form-control"
            placeholder="Type a name or student ID"
            v-model="query"
            autocomplete="off"
            @focus="pickerOpen = true"
          />
          <div v-if="pickerOpen && matches.length" class="prof-suggest">
            <button
              v-for="m in matches"
              :key="m.name"
              type="button"
              class="prof-suggest-item"
              @click="selectStudent(m.name)"
            >
              <span class="prof-suggest-name">{{ m.student_name }}</span>
              <span class="prof-suggest-meta">{{ m.name }} · {{ m.standard }} · {{ m.current_batch }}</span>
            </button>
          </div>
          <p v-else-if="pickerOpen && query && !searching" class="prof-suggest-empty">
            No active student matches “{{ query }}”.
          </p>
        </div>
      </div>

      <div class="prof-picker-row">
        <div class="prof-period-chips">
          <button
            v-for="p in PERIODS"
            :key="p.key"
            type="button"
            class="prof-chip"
            :class="{ 'is-active': period === p.key }"
            @click="setPeriod(p.key)"
          >
            {{ p.label }}
          </button>
        </div>
        <div class="prof-field prof-field-date">
          <label for="prof-from">From</label>
          <input id="prof-from" type="date" class="form-control" v-model="fromDate" @change="period = 'custom'" />
        </div>
        <div class="prof-field prof-field-date">
          <label for="prof-to">To</label>
          <input id="prof-to" type="date" class="form-control" v-model="toDate" @change="period = 'custom'" />
        </div>
        <button
          v-if="profile"
          type="button"
          class="prof-print-btn"
          title="Print or save this profile as a PDF"
          @click="printProfile"
        >
          <i class="fa fa-print"></i> Print
        </button>
      </div>
    </div>

    <div v-if="error" class="prof-alert no-print">
      <i class="fa fa-exclamation-circle"></i> {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="prof-card">
      <div class="prof-skeleton">
        <div v-for="i in 5" :key="i" class="prof-skeleton-bar" :style="{ width: `${90 - i * 12}%` }"></div>
      </div>
    </div>

    <!-- Nothing picked yet -->
    <div v-else-if="!profile" class="prof-card prof-empty no-print">
      <div class="prof-empty-icon"><i class="fa fa-id-card-o"></i></div>
      <h3>Student Profile</h3>
      <p>
        Search for a student above to see their attendance and performance for the period —
        a single page you can turn around and show to a parent.
      </p>
    </div>

    <template v-else>
      <!-- ===== Identity ===== -->
      <section class="prof-card prof-identity">
        <div class="prof-identity-photo">
          <img v-if="student.image" :src="student.image" :alt="student.student_name" />
          <div v-else class="prof-photo-fallback">{{ initials(student.student_name) }}</div>
        </div>

        <div class="prof-identity-main">
          <h2>
            {{ student.student_name }}
            <span class="prof-status-badge" :data-status="student.status">{{ student.status }}</span>
          </h2>
          <div class="prof-identity-line">
            <span><i class="fa fa-id-badge"></i> {{ student.name }}</span>
            <span><i class="fa fa-graduation-cap"></i> {{ student.standard }}</span>
            <span><i class="fa fa-users"></i> {{ student.batch }}</span>
            <span v-if="student.gender"><i class="fa fa-venus-mars"></i> {{ student.gender }}</span>
            <span v-if="student.age"><i class="fa fa-birthday-cake"></i> {{ student.age }} yrs</span>
          </div>
          <div class="prof-identity-line prof-identity-parents">
            <span v-if="student.father_name">
              <i class="fa fa-male"></i> {{ student.father_name }}
              <b v-if="student.father_mobile_number">{{ student.father_mobile_number }}</b>
            </span>
            <span v-if="student.mother_name">
              <i class="fa fa-female"></i> {{ student.mother_name }}
              <b v-if="student.mother_mobile_number">{{ student.mother_mobile_number }}</b>
            </span>
          </div>
        </div>

        <div class="prof-identity-period">
          <span class="prof-period-label">Report Period</span>
          <strong>{{ prettyDate(range.from_date) }} — {{ prettyDate(range.to_date) }}</strong>
          <span v-if="student.years_with_us" class="prof-period-sub">
            With us {{ student.years_with_us }} year(s)
          </span>
        </div>
      </section>

      <!-- ===== Plain-language summary ===== -->
      <section v-if="profile.highlights.length" class="prof-card prof-highlights">
        <h3 class="prof-card-title"><i class="fa fa-lightbulb-o"></i> At a Glance</h3>
        <ul>
          <li v-for="(h, i) in profile.highlights" :key="i" :class="`prof-tone-${h.tone}`">
            <i class="fa" :class="h.icon"></i><span>{{ h.text }}</span>
          </li>
        </ul>
      </section>

      <!-- ===== Attendance ===== -->
      <section class="prof-card">
        <h3 class="prof-card-title"><i class="fa fa-calendar-check-o"></i> Attendance</h3>

        <!-- A 0% ring on a period with no register entries reads as "never
             turned up" rather than "nothing recorded", so say the latter. -->
        <p v-if="!attendance.school_days" class="prof-muted">
          No attendance was marked for this student between
          {{ prettyDate(range.from_date) }} and {{ prettyDate(range.to_date) }}.
        </p>

        <div v-else class="prof-attendance-top">
          <div class="prof-ring-wrap" :class="`prof-band-${attendance.band.key}`">
            <svg viewBox="0 0 120 120" class="prof-ring" role="img"
              :aria-label="`${attendance.percentage} percent attendance`">
              <circle class="prof-ring-track" cx="60" cy="60" r="52" />
              <circle
                class="prof-ring-value"
                cx="60"
                cy="60"
                r="52"
                :stroke-dasharray="`${ringDash} ${RING_CIRCUMFERENCE}`"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="prof-ring-centre">
              <span class="prof-ring-pct">{{ attendance.percentage }}%</span>
              <span class="prof-ring-sub">attended</span>
            </div>
          </div>

          <div class="prof-attendance-facts">
            <p class="prof-band-label" :class="`prof-band-${attendance.band.key}`">
              {{ attendance.band.label }}
            </p>
            <p class="prof-attendance-sentence">
              Present on <strong>{{ attendance.attended }}</strong> of
              <strong>{{ attendance.school_days }}</strong> school days in this period.
            </p>
            <div class="prof-stat-row">
              <div class="prof-stat prof-tone-good">
                <span class="prof-stat-value">{{ attendance.present }}</span>
                <span class="prof-stat-label">Present</span>
              </div>
              <div class="prof-stat prof-tone-bad">
                <span class="prof-stat-value">{{ attendance.absent }}</span>
                <span class="prof-stat-label">Absent</span>
              </div>
              <div class="prof-stat prof-tone-warn">
                <span class="prof-stat-value">{{ attendance.late }}</span>
                <span class="prof-stat-label">Late</span>
              </div>
              <div v-if="attendance.early_outs" class="prof-stat prof-tone-info">
                <span class="prof-stat-value">{{ attendance.early_outs }}</span>
                <span class="prof-stat-label">Early Out</span>
              </div>
              <div class="prof-stat prof-tone-good">
                <span class="prof-stat-value">{{ attendance.best_streak }}</span>
                <span class="prof-stat-label">Best Streak</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Month-by-month bars, only worth showing across more than one month -->
        <div v-if="attendance.school_days && attendance.monthly.length > 1" class="prof-trend">
          <div v-for="m in attendance.monthly" :key="m.month" class="prof-trend-col">
            <div class="prof-trend-bar-track">
              <div
                class="prof-trend-bar"
                :class="`prof-band-${bandKey(m.percentage)}`"
                :style="{ height: `${Math.max(m.percentage, 3)}%` }"
              ></div>
            </div>
            <span class="prof-trend-pct">{{ m.percentage }}%</span>
            <span class="prof-trend-label">{{ shortMonth(m.month) }}</span>
          </div>
        </div>

        <!-- Day-by-day calendar: the part parents read fastest -->
        <div v-if="attendance.school_days || attendance.holidays.length" class="prof-calendars">
          <div v-for="month in calendarMonths" :key="month.key" class="prof-calendar">
            <h4>{{ month.label }}</h4>
            <div class="prof-cal-grid">
              <span v-for="d in WEEKDAYS" :key="d" class="prof-cal-head">{{ d }}</span>
              <span
                v-for="(cell, ci) in month.cells"
                :key="ci"
                class="prof-cal-day"
                :data-status="cell ? cell.status : 'blank'"
                :title="cell ? cellTitle(cell) : ''"
              >{{ cell ? cell.day : '' }}</span>
            </div>
          </div>
        </div>

        <div v-if="attendance.school_days || attendance.holidays.length" class="prof-legend">
          <span v-for="l in CALENDAR_LEGEND" :key="l.status">
            <i class="prof-legend-dot" :data-status="l.status"></i>{{ l.label }}
          </span>
        </div>
      </section>

      <!-- ===== Performance ===== -->
      <section class="prof-card">
        <h3 class="prof-card-title"><i class="fa fa-star"></i> Performance</h3>

        <p v-if="!performance.total_entries" class="prof-muted">
          Nothing was recorded for Study, Test, Maths Test or Behaviour in this period.
        </p>

        <div v-else class="prof-perf-grid">
          <div
            v-for="cat in recordedCategories"
            :key="cat.name"
            class="prof-perf-card"
          >
            <div class="prof-perf-head">
              <span class="prof-perf-name">{{ cat.name }}</span>
              <span class="prof-perf-count">{{ cat.entries }} record(s)</span>
            </div>

            <div v-if="cat.uses_marks && cat.percentage !== null" class="prof-perf-score">
              <span class="prof-perf-pct" :class="`prof-band-${bandKey(cat.percentage)}`">
                {{ cat.percentage }}%
              </span>
              <span class="prof-perf-score-sub">
                {{ formatNumber(cat.marks_obtained) }} of {{ formatNumber(cat.total_marks) }} marks
              </span>
            </div>

            <!-- One bar split by grade, widest slice first in the legend below -->
            <div class="prof-perf-bar">
              <div
                v-for="slot in cat.results"
                :key="slot.result"
                v-show="slot.count"
                class="prof-perf-bar-slice"
                :class="`prof-tone-${resultTone(slot.result)}`"
                :style="{ width: `${(slot.count / cat.entries) * 100}%` }"
                :title="`${slot.result}: ${slot.count}`"
              ></div>
            </div>

            <ul class="prof-perf-legend">
              <li v-for="slot in cat.results" :key="slot.result">
                <i class="prof-legend-dot" :data-tone="resultTone(slot.result)"></i>
                <span>{{ slot.result }}</span>
                <b>{{ slot.count }}</b>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ===== Behaviour detail ===== -->
      <section v-if="behaviour.incidents.length" class="prof-card">
        <h3 class="prof-card-title prof-tone-bad">
          <i class="fa fa-exclamation-triangle"></i> Behaviour Concerns
        </h3>

        <div class="prof-reason-tally">
          <span v-for="r in behaviour.reason_counts" :key="r.reason" class="prof-reason-chip">
            {{ r.reason }} <b>{{ r.count }}</b>
          </span>
        </div>

        <table class="prof-table">
          <thead>
            <tr><th>Date</th><th>Rating</th><th>What Happened</th></tr>
          </thead>
          <tbody>
            <tr v-for="(inc, i) in behaviour.incidents" :key="i">
              <td class="prof-nowrap">{{ prettyDate(inc.date) }}</td>
              <td>
                <span class="prof-pill" :data-result="inc.result">{{ inc.result }}</span>
              </td>
              <td>
                {{ inc.reasons.join(', ') || '—' }}
                <em v-if="inc.remarks"> — {{ inc.remarks }}</em>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ===== Recent activity ===== -->
      <section v-if="profile.timeline.length" class="prof-card">
        <h3 class="prof-card-title"><i class="fa fa-history"></i> Recent Activity</h3>
        <ul class="prof-timeline">
          <li v-for="(e, i) in profile.timeline" :key="i" :class="{ 'is-concern': e.is_concern }">
            <span class="prof-timeline-date">{{ prettyDate(e.date) }}</span>
            <span class="prof-timeline-title">{{ e.title }}</span>
            <span class="prof-timeline-value" :class="{ 'is-concern': e.is_concern }">{{ e.value }}</span>
            <span class="prof-timeline-detail">{{ e.detail }}</span>
          </li>
        </ul>
      </section>

      <p class="prof-footnote">
        Generated {{ prettyDate(serverToday) }} · Attendance counts Late and Early Out days as attended.
      </p>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday, formatDate } from '@/data/serverDate'

const WEEKDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const RING_CIRCUMFERENCE = 2 * Math.PI * 52

const PERIODS = [
  { key: 'this_month', label: 'This Month' },
  { key: 'last_month', label: 'Last Month' },
  { key: 'last_3', label: 'Last 3 Months' },
  { key: 'last_6', label: 'Last 6 Months' },
]

const CALENDAR_LEGEND = [
  { status: 'Present', label: 'Present' },
  { status: 'Absent', label: 'Absent' },
  { status: 'Late', label: 'Late' },
  { status: 'Early Outs', label: 'Early Out' },
  { status: 'Holiday', label: 'Holiday' },
  { status: '', label: 'No class / not marked' },
]

// Which grade of each category reads as good, middling or bad. Mirrors the
// tones the Performance Manager paints its buttons with.
const RESULT_TONES = {
  Excellent: 'good',
  Completed: 'mid',
  Incomplete: 'bad',
  'Full Mark': 'good',
  'Pass Mark': 'mid',
  Fail: 'bad',
  Good: 'good',
  Bad: 'mid',
  Worst: 'bad',
}

const route = useRoute()
const router = useRouter()

const standards = ref([])
const batches = ref([])
const standard = ref('')
const batch = ref('')
const query = ref('')
const matches = ref([])
const searching = ref(false)
const pickerOpen = ref(false)

const selectedStudent = ref('')
const period = ref('this_month')
const fromDate = ref('')
const toDate = ref('')

const profile = ref(null)
const loading = ref(false)
const error = ref('')

const standardsResource = createResource({ url: 'frappe.client.get_list' })
const batchesResource = createResource({ url: 'frappe.client.get_list' })
const searchResource = createResource({
  url: 'bb_tution_management.bb_academy.student_profile.search_students',
})
const profileResource = createResource({
  url: 'bb_tution_management.bb_academy.student_profile.get_student_profile',
})

const student = computed(() => profile.value?.student || {})
const range = computed(() => profile.value?.range || {})
const attendance = computed(() => profile.value?.attendance || {})
const performance = computed(() => profile.value?.performance || { categories: [], total_entries: 0 })
const behaviour = computed(() => profile.value?.behaviour || { incidents: [], reason_counts: [] })

const recordedCategories = computed(() =>
  performance.value.categories.filter((c) => c.entries > 0)
)

const ringDash = computed(
  () => (Math.min(attendance.value.percentage || 0, 100) / 100) * RING_CIRCUMFERENCE
)

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function prettyDate(value) {
  if (!value) return ''
  const d = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

function shortMonth(monthKey) {
  const d = new Date(`${monthKey}-01T00:00:00`)
  return Number.isNaN(d.getTime()) ? monthKey : d.toLocaleDateString(undefined, { month: 'short' })
}

function formatNumber(value) {
  const n = Number(value || 0)
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function resultTone(result) {
  return RESULT_TONES[result] || 'mid'
}

// Same thresholds the server uses for its attendance band, reused for the
// per-month bars and the test percentages so one colour means one thing.
function bandKey(pct) {
  if (pct >= 95) return 'excellent'
  if (pct >= 85) return 'good'
  if (pct >= 75) return 'fair'
  return 'poor'
}

function cellTitle(cell) {
  if (!cell.status || cell.status === 'out') return cell.date
  return `${cell.date} — ${cell.status}${cell.remarks ? ` (${cell.remarks})` : ''}`
}

const calendarMonths = computed(() => {
  if (!profile.value) return []
  const from = String(range.value.from_date).slice(0, 10)
  const to = String(range.value.to_date).slice(0, 10)

  const dayMap = {}
  for (const day of attendance.value.days || []) {
    const key = String(day.date).slice(0, 10)
    // A holiday row and an attendance row can land on the same date; the
    // attendance status is the more specific of the two, so it wins.
    if (!dayMap[key] || day.status !== 'Holiday') dayMap[key] = day
  }

  const months = []
  const end = new Date(`${to}T00:00:00`)
  let cursor = new Date(`${from}T00:00:00`)
  cursor.setDate(1)

  while (cursor <= end && months.length < 14) {
    const year = cursor.getFullYear()
    const month = cursor.getMonth()
    const first = new Date(year, month, 1)
    const daysInMonth = new Date(year, month + 1, 0).getDate()

    const cells = []
    // Monday-first grid, matching how the school week is read locally.
    const offset = (first.getDay() + 6) % 7
    for (let i = 0; i < offset; i++) cells.push(null)

    for (let d = 1; d <= daysInMonth; d++) {
      const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      const inRange = iso >= from && iso <= to
      const record = inRange ? dayMap[iso] : null
      cells.push({
        day: d,
        date: iso,
        status: inRange ? record?.status || '' : 'out',
        remarks: record?.remarks || '',
      })
    }
    while (cells.length % 7) cells.push(null)

    months.push({
      key: `${year}-${month}`,
      label: first.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
      cells,
    })
    cursor = new Date(year, month + 1, 1)
  }
  return months
})

function setPeriod(key) {
  period.value = key
  const today = new Date(`${serverToday.value}T00:00:00`)
  const y = today.getFullYear()
  const m = today.getMonth()

  const firstOf = (yy, mm) => formatDate(new Date(yy, mm, 1))
  const lastOf = (yy, mm) => formatDate(new Date(yy, mm + 1, 0))

  if (key === 'this_month') {
    fromDate.value = firstOf(y, m)
    toDate.value = serverToday.value
  } else if (key === 'last_month') {
    fromDate.value = firstOf(y, m - 1)
    toDate.value = lastOf(y, m - 1)
  } else if (key === 'last_3') {
    fromDate.value = firstOf(y, m - 2)
    toDate.value = serverToday.value
  } else if (key === 'last_6') {
    fromDate.value = firstOf(y, m - 5)
    toDate.value = serverToday.value
  }
}

let searchTimer = null
function scheduleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(runSearch, 250)
}

async function runSearch() {
  searching.value = true
  try {
    matches.value =
      (await searchResource.submit({
        query: query.value || undefined,
        standard: standard.value || undefined,
        batch: batch.value || undefined,
        limit: 25,
      })) || []
  } catch (e) {
    matches.value = []
  } finally {
    searching.value = false
  }
}

function selectStudent(name) {
  selectedStudent.value = name
  pickerOpen.value = false
  const chosen = matches.value.find((m) => m.name === name)
  if (chosen) query.value = chosen.student_name
  // Keep the URL shareable: a colleague can be sent straight to this profile.
  router.replace({ name: 'StudentProfile', query: { ...route.query, student: name } })
  loadProfile()
}

async function loadProfile() {
  if (!selectedStudent.value) return
  loading.value = true
  error.value = ''
  try {
    profile.value = await profileResource.submit({
      student: selectedStudent.value,
      from_date: fromDate.value,
      to_date: toDate.value,
    })
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Failed to load the profile'
    profile.value = null
  } finally {
    loading.value = false
  }
}

function printProfile() {
  window.print()
}

onMounted(async () => {
  await loadServerToday()
  setPeriod('this_month')

  const [standardRows, batchRows] = await Promise.all([
    standardsResource.submit({ doctype: 'Standard', fields: ['name'], limit_page_length: 0 }),
    batchesResource.submit({ doctype: 'Batch', fields: ['name'], limit_page_length: 0 }),
  ])
  standards.value = standardRows || []
  batches.value = batchRows || []

  runSearch()

  // Deep link support: /performance and the manager pages can hand off here.
  if (route.query.student) {
    selectedStudent.value = String(route.query.student)
    loadProfile()
  }
})

// Arriving from a student-name link, or stepping back through profiles with the
// browser's back button, only changes the query — the component is not
// remounted, so onMounted would never see the new student.
watch(
  () => route.query.student,
  (name) => {
    if (!name || name === selectedStudent.value) return
    selectedStudent.value = String(name)
    loadProfile()
  }
)

watch(query, scheduleSearch)
watch([standard, batch], () => {
  pickerOpen.value = true
  runSearch()
})
watch([fromDate, toDate], () => {
  if (selectedStudent.value) loadProfile()
})
</script>

<style>
/* ==========================================================================
   The Student Profile is the one screen in this app meant to be read by
   someone outside it — a parent, across a desk or on paper. So it favours
   large type, one idea per band, and colour that means the same thing
   everywhere (green good / amber watch / red concern), and it prints.
   ========================================================================== */

.student-profile {
  --prof-radius: var(--border-radius-md, 8px);
  --prof-radius-sm: var(--border-radius, 6px);
  --prof-gap: 14px;
  --prof-good: var(--green-600, #16a34a);
  --prof-warn: var(--orange-500, #f97316);
  --prof-bad: var(--red-600, #dc2626);
  --prof-info: var(--blue-600, #2563eb);
  color: var(--text-color);
  padding: 14px;
}

.student-profile * { box-sizing: border-box; }
.student-profile button { font-family: inherit; }

.student-profile .prof-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--prof-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 18px;
  margin-bottom: var(--prof-gap);
}

.student-profile .prof-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.student-profile .prof-card-title i { color: var(--gray-500); }
.student-profile .prof-muted { color: var(--text-muted); font-size: 13px; margin: 0; }

/* ---- picker ---- */
.student-profile .prof-picker {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--prof-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 14px 16px;
  margin-bottom: var(--prof-gap);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.student-profile .prof-picker-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
}

.student-profile .prof-field { min-width: 140px; flex: 0 1 160px; position: relative; }
.student-profile .prof-field-search { flex: 1 1 260px; }
.student-profile .prof-field-date { flex: 0 0 auto; min-width: 140px; }

.student-profile .prof-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.student-profile .prof-field label i { width: 14px; margin-right: 4px; color: var(--gray-600); }

.student-profile .prof-suggest {
  position: absolute;
  z-index: 20;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  max-height: 280px;
  overflow-y: auto;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--prof-radius-sm);
  box-shadow: var(--shadow-md);
}

.student-profile .prof-suggest-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
}

.student-profile .prof-suggest-item:last-child { border-bottom: none; }
.student-profile .prof-suggest-item:hover { background: var(--fg-hover-color, var(--gray-100)); }
.student-profile .prof-suggest-name { font-size: 13px; font-weight: 600; color: var(--heading-color); }
.student-profile .prof-suggest-meta { font-size: 11px; color: var(--text-muted); }
.student-profile .prof-suggest-empty { margin: 6px 0 0; font-size: 12px; color: var(--text-muted); }

.student-profile .prof-period-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-right: auto; }

.student-profile .prof-chip {
  border: 1px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-muted);
  border-radius: var(--border-radius-full, 999px);
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.student-profile .prof-chip:hover { border-color: var(--gray-400); }
.student-profile .prof-chip.is-active {
  background: var(--blue-600);
  border-color: var(--blue-600);
  color: #fff;
}

.student-profile .prof-print-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 18px;
  border: 1px solid var(--blue-600);
  border-radius: var(--prof-radius-sm);
  background: var(--blue-600);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.student-profile .prof-print-btn:hover { background: var(--blue-700, var(--blue-600)); }

.student-profile .prof-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-red);
  border: 1px solid var(--red-200);
  color: var(--text-on-red);
  border-radius: var(--prof-radius);
  padding: 10px 14px;
  font-size: 12.5px;
  margin-bottom: var(--prof-gap);
}

/* ---- empty / skeleton ---- */
.student-profile .prof-empty { text-align: center; padding: 56px 20px; }
.student-profile .prof-empty-icon { font-size: 40px; color: var(--gray-400); margin-bottom: 12px; }
.student-profile .prof-empty h3 { margin: 0 0 8px; font-size: 18px; color: var(--heading-color); }
.student-profile .prof-empty p { margin: 0 auto; max-width: 440px; font-size: 13px; color: var(--text-muted); }

.student-profile .prof-skeleton { display: flex; flex-direction: column; gap: 12px; }

.student-profile .prof-skeleton-bar {
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: prof-shine 1.4s ease infinite;
}

@keyframes prof-shine {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* ---- identity ---- */
.student-profile .prof-identity {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.student-profile .prof-identity-photo { flex: 0 0 auto; }

.student-profile .prof-identity-photo img,
.student-profile .prof-photo-fallback {
  width: 88px;
  height: 88px;
  object-fit: cover;
  border-radius: var(--prof-radius);
  border: 1px solid var(--border-color);
}

.student-profile .prof-photo-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-200);
  color: var(--gray-600);
  font-size: 28px;
  font-weight: 700;
}

.student-profile .prof-identity-main { flex: 1 1 260px; min-width: 0; }

.student-profile .prof-identity-main h2 {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--heading-color);
}

.student-profile .prof-status-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 3px 10px;
  border-radius: var(--border-radius-full, 999px);
  background: var(--bg-gray);
  color: var(--text-on-gray);
}

.student-profile .prof-status-badge[data-status='Active'] { background: var(--bg-green); color: var(--text-on-green); }
.student-profile .prof-status-badge[data-status='Suspended'] { background: var(--bg-orange); color: var(--text-on-orange); }
.student-profile .prof-status-badge[data-status='Discontinued'] { background: var(--bg-red); color: var(--text-on-red); }

.student-profile .prof-identity-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  font-size: 12.5px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.student-profile .prof-identity-line i { width: 14px; margin-right: 4px; color: var(--gray-500); }
.student-profile .prof-identity-parents b { color: var(--text-color); margin-left: 4px; font-variant-numeric: tabular-nums; }

.student-profile .prof-identity-period {
  flex: 0 0 auto;
  margin-left: auto;
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.student-profile .prof-period-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.student-profile .prof-identity-period strong { font-size: 13px; color: var(--heading-color); }
.student-profile .prof-period-sub { font-size: 11.5px; color: var(--text-muted); }

/* ---- highlights ---- */
.student-profile .prof-highlights ul { list-style: none; margin: 0; padding: 0; }

.student-profile .prof-highlights li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--prof-radius-sm);
  font-size: 14px;
  line-height: 1.45;
  margin-bottom: 8px;
  background: var(--gray-50);
  border-left: 3px solid var(--gray-400);
}

.student-profile .prof-highlights li:last-child { margin-bottom: 0; }
.student-profile .prof-highlights li i { margin-top: 3px; }

.student-profile .prof-highlights li.prof-tone-good { background: var(--bg-green); border-left-color: var(--prof-good); color: var(--text-on-green); }
.student-profile .prof-highlights li.prof-tone-warn { background: var(--bg-orange); border-left-color: var(--prof-warn); color: var(--text-on-orange); }
.student-profile .prof-highlights li.prof-tone-bad { background: var(--bg-red); border-left-color: var(--prof-bad); color: var(--text-on-red); }
.student-profile .prof-highlights li.prof-tone-info { background: var(--bg-blue); border-left-color: var(--prof-info); color: var(--text-on-blue); }

/* ---- attendance ring ---- */
.student-profile .prof-attendance-top {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.student-profile .prof-ring-wrap { position: relative; width: 150px; height: 150px; flex: 0 0 auto; }
.student-profile .prof-ring { width: 100%; height: 100%; }

.student-profile .prof-ring-track {
  fill: none;
  stroke: var(--gray-200);
  stroke-width: 12;
}

.student-profile .prof-ring-value {
  fill: none;
  stroke-width: 12;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.student-profile .prof-band-excellent .prof-ring-value { stroke: var(--prof-good); }
.student-profile .prof-band-good .prof-ring-value { stroke: var(--prof-good); }
.student-profile .prof-band-fair .prof-ring-value { stroke: var(--prof-warn); }
.student-profile .prof-band-poor .prof-ring-value { stroke: var(--prof-bad); }

.student-profile .prof-ring-centre {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.student-profile .prof-ring-pct {
  font-size: 30px;
  font-weight: 800;
  line-height: 1;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.student-profile .prof-ring-sub {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

.student-profile .prof-attendance-facts { flex: 1 1 300px; min-width: 0; }

.student-profile .prof-band-label {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 700;
}

.student-profile p.prof-band-excellent,
.student-profile p.prof-band-good { color: var(--prof-good); }
.student-profile p.prof-band-fair { color: var(--prof-warn); }
.student-profile p.prof-band-poor { color: var(--prof-bad); }

.student-profile .prof-attendance-sentence {
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--text-color);
}

.student-profile .prof-stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));
  gap: 10px;
}

.student-profile .prof-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 6px;
  border-radius: var(--prof-radius-sm);
  background: var(--gray-50);
  border: 1px solid var(--border-color);
}

.student-profile .prof-stat-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.student-profile .prof-stat-label {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.student-profile .prof-stat.prof-tone-good .prof-stat-value { color: var(--prof-good); }
.student-profile .prof-stat.prof-tone-warn .prof-stat-value { color: var(--prof-warn); }
.student-profile .prof-stat.prof-tone-bad .prof-stat-value { color: var(--prof-bad); }
.student-profile .prof-stat.prof-tone-info .prof-stat-value { color: var(--prof-info); }

/* ---- monthly trend ---- */
.student-profile .prof-trend {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--border-color);
}

.student-profile .prof-trend-col {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.student-profile .prof-trend-bar-track {
  width: 100%;
  max-width: 46px;
  height: 90px;
  display: flex;
  align-items: flex-end;
  background: var(--gray-100);
  border-radius: 4px;
  overflow: hidden;
}

.student-profile .prof-trend-bar { width: 100%; border-radius: 4px 4px 0 0; }
.student-profile .prof-trend-bar.prof-band-excellent,
.student-profile .prof-trend-bar.prof-band-good { background: var(--prof-good); }
.student-profile .prof-trend-bar.prof-band-fair { background: var(--prof-warn); }
.student-profile .prof-trend-bar.prof-band-poor { background: var(--prof-bad); }

.student-profile .prof-trend-pct {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.student-profile .prof-trend-label { font-size: 11px; color: var(--text-muted); }

/* ---- calendars ---- */
.student-profile .prof-calendars {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 18px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--border-color);
}

.student-profile .prof-calendar h4 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--heading-color);
}

.student-profile .prof-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.student-profile .prof-cal-head {
  text-align: center;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  padding-bottom: 2px;
}

.student-profile .prof-cal-day {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  background: var(--gray-100);
  color: var(--text-muted);
}

.student-profile .prof-cal-day[data-status='blank'],
.student-profile .prof-cal-day[data-status='out'] { background: transparent; color: transparent; }
.student-profile .prof-cal-day[data-status='Present'] { background: var(--prof-good); color: #fff; }
.student-profile .prof-cal-day[data-status='Absent'] { background: var(--prof-bad); color: #fff; }
.student-profile .prof-cal-day[data-status='Late'] { background: var(--prof-warn); color: #fff; }
.student-profile .prof-cal-day[data-status='Early Outs'] { background: var(--prof-info); color: #fff; }
.student-profile .prof-cal-day[data-status='Holiday'] { background: var(--gray-300); color: var(--gray-700, #374151); }

.student-profile .prof-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin-top: 14px;
  font-size: 11.5px;
  color: var(--text-muted);
}

.student-profile .prof-legend span { display: inline-flex; align-items: center; gap: 6px; }

.student-profile .prof-legend-dot {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  background: var(--gray-100);
  border: 1px solid var(--border-color);
  display: inline-block;
}

.student-profile .prof-legend-dot[data-status='Present'] { background: var(--prof-good); border-color: var(--prof-good); }
.student-profile .prof-legend-dot[data-status='Absent'] { background: var(--prof-bad); border-color: var(--prof-bad); }
.student-profile .prof-legend-dot[data-status='Late'] { background: var(--prof-warn); border-color: var(--prof-warn); }
.student-profile .prof-legend-dot[data-status='Early Outs'] { background: var(--prof-info); border-color: var(--prof-info); }
.student-profile .prof-legend-dot[data-status='Holiday'] { background: var(--gray-300); border-color: var(--gray-300); }
.student-profile .prof-legend-dot[data-tone='good'] { background: var(--prof-good); border-color: var(--prof-good); }
.student-profile .prof-legend-dot[data-tone='mid'] { background: var(--prof-warn); border-color: var(--prof-warn); }
.student-profile .prof-legend-dot[data-tone='bad'] { background: var(--prof-bad); border-color: var(--prof-bad); }

/* ---- performance ---- */
.student-profile .prof-perf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.student-profile .prof-perf-card {
  border: 1px solid var(--border-color);
  border-radius: var(--prof-radius-sm);
  padding: 14px;
  background: var(--gray-50);
}

.student-profile .prof-perf-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.student-profile .prof-perf-name { font-size: 15px; font-weight: 700; color: var(--heading-color); }
.student-profile .prof-perf-count { font-size: 11px; color: var(--text-muted); }

.student-profile .prof-perf-score {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}

.student-profile .prof-perf-pct { font-size: 28px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.student-profile .prof-perf-pct.prof-band-excellent,
.student-profile .prof-perf-pct.prof-band-good { color: var(--prof-good); }
.student-profile .prof-perf-pct.prof-band-fair { color: var(--prof-warn); }
.student-profile .prof-perf-pct.prof-band-poor { color: var(--prof-bad); }
.student-profile .prof-perf-score-sub { font-size: 11.5px; color: var(--text-muted); }

.student-profile .prof-perf-bar {
  display: flex;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--gray-200);
  margin-bottom: 10px;
}

.student-profile .prof-perf-bar-slice.prof-tone-good { background: var(--prof-good); }
.student-profile .prof-perf-bar-slice.prof-tone-mid { background: var(--prof-warn); }
.student-profile .prof-perf-bar-slice.prof-tone-bad { background: var(--prof-bad); }

.student-profile .prof-perf-legend { list-style: none; margin: 0; padding: 0; }

.student-profile .prof-perf-legend li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  padding: 3px 0;
  color: var(--text-color);
}

.student-profile .prof-perf-legend li b { margin-left: auto; font-variant-numeric: tabular-nums; }

/* ---- behaviour ---- */
.student-profile .prof-reason-tally { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }

.student-profile .prof-reason-chip {
  font-size: 12px;
  background: var(--bg-red);
  color: var(--text-on-red);
  border-radius: var(--border-radius-full, 999px);
  padding: 4px 12px;
}

.student-profile .prof-reason-chip b { margin-left: 4px; }

.student-profile .prof-table { width: 100%; border-collapse: collapse; }

.student-profile .prof-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-color);
}

.student-profile .prof-table td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  vertical-align: top;
}

.student-profile .prof-table tr:last-child td { border-bottom: none; }
.student-profile .prof-table em { color: var(--text-muted); font-style: italic; }
.student-profile .prof-nowrap { white-space: nowrap; }

.student-profile .prof-pill {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: var(--border-radius-full, 999px);
  background: var(--bg-orange);
  color: var(--text-on-orange);
}

.student-profile .prof-pill[data-result='Worst'] { background: var(--bg-red); color: var(--text-on-red); }

/* ---- timeline ---- */
.student-profile .prof-timeline { list-style: none; margin: 0; padding: 0; }

.student-profile .prof-timeline li {
  display: grid;
  grid-template-columns: 110px 110px 110px 1fr;
  gap: 10px;
  align-items: baseline;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  border-left: 3px solid transparent;
}

.student-profile .prof-timeline li:last-child { border-bottom: none; }
.student-profile .prof-timeline li.is-concern { border-left-color: var(--prof-bad); background: var(--bg-red); }

.student-profile .prof-timeline-date { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.student-profile .prof-timeline-title { font-weight: 600; color: var(--heading-color); }
.student-profile .prof-timeline-value { font-weight: 700; color: var(--prof-good); }
.student-profile .prof-timeline-value.is-concern { color: var(--prof-bad); }
.student-profile .prof-timeline-detail { color: var(--text-muted); font-size: 12px; }

.student-profile .prof-footnote {
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
  margin: 0 0 8px;
}

/* ---- mobile ---- */
@media (max-width: 767px) {
  .student-profile { padding: 10px; }
  .student-profile .prof-field,
  .student-profile .prof-field-date { flex: 1 1 100%; min-width: 0; }
  .student-profile .prof-print-btn { width: 100%; justify-content: center; }
  .student-profile .prof-period-chips { width: 100%; }
  .student-profile .prof-chip { flex: 1 1 auto; }

  .student-profile .prof-identity { flex-direction: column; align-items: flex-start; text-align: left; }
  .student-profile .prof-identity-period { margin-left: 0; text-align: left; }
  .student-profile .prof-identity-main h2 { font-size: 19px; }

  .student-profile .prof-attendance-top { justify-content: center; }
  .student-profile .prof-ring-wrap { width: 130px; height: 130px; }

  .student-profile .prof-timeline li {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      'title  value'
      'date   date'
      'detail detail';
    row-gap: 2px;
  }
  .student-profile .prof-timeline-title { grid-area: title; }
  .student-profile .prof-timeline-value { grid-area: value; }
  .student-profile .prof-timeline-date { grid-area: date; }
  .student-profile .prof-timeline-detail { grid-area: detail; }
}

/* ==========================================================================
   Print. The whole point of the screen is that it can be handed over, so the
   app chrome and the picker come off and the cards are kept whole across page
   breaks. Hiding the shell affects every page's print output, which is what
   you want everywhere in this app.
   ========================================================================== */
@media print {
  .att-shell-header,
  .att-bottom-nav,
  .student-profile .no-print { display: none !important; }

  .att-shell-main { padding-bottom: 0 !important; }

  .student-profile { padding: 0; }

  .student-profile .prof-card {
    box-shadow: none;
    border: 1px solid #ddd;
    break-inside: avoid;
    page-break-inside: avoid;
    margin-bottom: 10px;
  }

  .student-profile .prof-cal-day,
  .student-profile .prof-perf-bar-slice,
  .student-profile .prof-trend-bar,
  .student-profile .prof-ring-value,
  .student-profile .prof-highlights li,
  .student-profile .prof-legend-dot,
  .student-profile .prof-reason-chip,
  .student-profile .prof-pill {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
</style>
