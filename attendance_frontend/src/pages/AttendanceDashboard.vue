<template>
  <div class="attendance-dashboard" :class="{ 'is-loading': loading }">
    <!-- Control panel -->
    <div class="dash-panel">
      <div class="dash-panel-filters">
        <div class="dash-field">
          <label><i class="fa fa-graduation-cap"></i> Standard</label>
          <select class="form-control form-control-sm" v-model="standard">
            <option value="">All Standards</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="dash-field">
          <label><i class="fa fa-users"></i> Batch</label>
          <select class="form-control form-control-sm" v-model="batch" :disabled="!standard">
            <option value="">All Batches</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
        <div class="dash-field">
          <label><i class="fa fa-calendar"></i> Date</label>
          <input type="date" class="form-control form-control-sm" v-model="date" :max="serverToday" />
        </div>
      </div>

      <div class="dash-panel-actions">
        <router-link :to="{ name: 'AttendanceManager' }" class="dash-btn dash-btn-primary">
          <i class="fa fa-check-circle"></i> Take Attendance
        </router-link>
      </div>
    </div>

    <div class="dash-content-area">
      <div class="dash-loading-overlay" v-show="loading"></div>

      <!-- KPI cards -->
      <div class="dash-kpi-grid">
        <button
          v-for="k in kpiCards"
          :key="k.id"
          type="button"
          class="dash-kpi-card"
          :class="k.color"
          @click="onKpiClick(k)"
        >
          <span class="dash-kpi-icon"><i class="fa" :class="k.icon"></i></span>
          <span class="dash-kpi-body">
            <span class="dash-kpi-value">{{ k.value }}</span>
            <span class="dash-kpi-label">{{ k.label }}</span>
            <span class="dash-kpi-sub">{{ k.sub }}</span>
          </span>
        </button>
      </div>

      <!-- Today's distribution — donut plus an always-readable value legend -->
      <div class="dash-grid dash-grid-split">
        <section class="dash-card">
          <header class="dash-card-header">
            <i class="fa fa-pie-chart"></i>
            <h6>Today&apos;s Attendance</h6>
            <span class="dash-card-meta">{{ todaySummary.total || 0 }} students</span>
          </header>
          <div class="dash-card-body">
            <div v-if="!hasTodayData" class="dash-empty">
              <i class="fa fa-pie-chart"></i>
              <p>No attendance data available</p>
            </div>
            <template v-else>
              <div v-show="!isNarrow" ref="chartTodayEl" class="dash-chart-canvas"></div>
              <!-- Stacked bar stands in for the donut on phones -->
              <div v-if="isNarrow" class="dash-stackbar">
                <span
                  v-for="p in todayParts.filter((x) => x.value > 0)"
                  :key="p.key"
                  :class="`dash-stackbar-seg dash-seg-${p.key}`"
                  :style="{ width: p.pct + '%' }"
                  :title="`${p.label}: ${p.value}`"
                ></span>
              </div>
              <ul class="dash-legend">
                <li v-for="p in todayParts" :key="p.key">
                  <span class="dash-legend-dot" :class="`dash-seg-${p.key}`"></span>
                  <span class="dash-legend-label">{{ p.label }}</span>
                  <span class="dash-legend-value">{{ p.value }}</span>
                  <span class="dash-legend-pct">{{ p.pct }}%</span>
                </li>
              </ul>
            </template>
          </div>
        </section>

        <!-- 30-day trend -->
        <section class="dash-card">
          <header class="dash-card-header">
            <i class="fa fa-line-chart"></i>
            <h6>Last 30 Days Trend</h6>
            <span v-if="hasTrendData" class="dash-card-meta">avg {{ trendStats.avg }}%</span>
          </header>
          <div class="dash-card-body">
            <div v-if="!hasTrendData" class="dash-empty">
              <i class="fa fa-line-chart"></i>
              <p>No attendance data available</p>
            </div>
            <template v-else>
              <div ref="chartTrendEl" class="dash-chart-canvas"></div>
              <!-- The thinned axis hides most points, so state the numbers -->
              <div class="dash-statrow">
                <div><span>Latest</span><strong>{{ trendStats.latest }}%</strong></div>
                <div><span>Average</span><strong>{{ trendStats.avg }}%</strong></div>
                <div><span>Best</span><strong>{{ trendStats.best }}%</strong></div>
                <div><span>Lowest</span><strong>{{ trendStats.worst }}%</strong></div>
              </div>
            </template>
          </div>
        </section>
      </div>

      <!-- Attendance by standard / batch -->
      <section class="dash-card">
        <header class="dash-card-header">
          <i class="fa fa-bar-chart"></i>
          <h6>{{ standard ? 'Attendance by Batch' : 'Attendance by Standard' }}</h6>
          <span v-if="hasSbData" class="dash-card-meta">{{ sb.labels.length }} groups</span>
        </header>
        <div class="dash-card-body">
          <div v-if="!hasSbData" class="dash-empty">
            <i class="fa fa-bar-chart"></i>
            <p>No attendance data available</p>
          </div>
          <template v-else>
            <div v-show="!isNarrow" ref="chartStdEl" class="dash-chart-canvas"></div>
            <!-- Bars get unreadable on a phone: show every group as a row -->
            <ul v-if="isNarrow" class="dash-barlist">
              <li v-for="row in sbRows" :key="row.label">
                <span class="dash-barlist-label">{{ row.label }}</span>
                <span class="dash-barlist-track">
                  <span
                    class="dash-barlist-fill"
                    :class="pctClass(row.value)"
                    :style="{ width: row.value + '%' }"
                  ></span>
                </span>
                <span class="dash-barlist-value">{{ row.value }}%</span>
              </li>
            </ul>
          </template>
        </div>
      </section>

      <!-- Top 10 lists -->
      <div class="dash-grid dash-grid-half">
        <section class="dash-card">
          <header class="dash-card-header">
            <i class="fa fa-user-times"></i>
            <h6>Top Absent <small>(This Month)</small></h6>
          </header>
          <div class="dash-card-body">
            <div v-if="!hasAbsData" class="dash-empty">
              <i class="fa fa-user-times"></i>
              <p>No attendance data available</p>
            </div>
            <template v-else>
              <div v-show="!isNarrow" ref="chartAbsEl" class="dash-chart-canvas"></div>
              <!-- Full names + exact counts; the chart truncates both -->
              <ol v-if="isNarrow" class="dash-ranklist">
                <li v-for="(r, i) in data.top_absent" :key="r.student">
                  <span class="dash-rank">{{ i + 1 }}</span>
                  <span class="dash-rank-name">{{ r.student_name }}</span>
                  <span class="dash-rank-value dash-rank-absent">{{ r.absent_count }}</span>
                </li>
              </ol>
            </template>
          </div>
        </section>

        <section class="dash-card">
          <header class="dash-card-header">
            <i class="fa fa-clock-o"></i>
            <h6>Top Late <small>(This Month)</small></h6>
          </header>
          <div class="dash-card-body">
            <div v-if="!hasLateData" class="dash-empty">
              <i class="fa fa-clock-o"></i>
              <p>No attendance data available</p>
            </div>
            <template v-else>
              <div v-show="!isNarrow" ref="chartLateEl" class="dash-chart-canvas"></div>
              <ol v-if="isNarrow" class="dash-ranklist">
                <li v-for="(r, i) in data.top_late" :key="r.student">
                  <span class="dash-rank">{{ i + 1 }}</span>
                  <span class="dash-rank-name">{{ r.student_name }}</span>
                  <span class="dash-rank-value dash-rank-late">{{ r.late_count }}</span>
                </li>
              </ol>
            </template>
          </div>
        </section>
      </div>

      <!-- Quick reports -->
      <section class="dash-card">
        <header class="dash-card-header">
          <i class="fa fa-list-alt"></i>
          <h6>Quick Reports</h6>
        </header>
        <div class="dash-card-body">
          <div class="dash-reports-grid">
            <router-link
              v-for="r in QUICK_REPORTS"
              :key="r.report"
              class="dash-report-btn"
              :to="{ name: 'AttendanceReports', query: { report: r.report } }"
            >
              <i class="fa" :class="r.icon"></i> <span>{{ r.label }}</span>
            </router-link>
          </div>
        </div>
      </section>
    </div>

    <div class="dash-loading-spinner" v-show="loading">
      <i class="fa fa-spinner fa-spin"></i> Loading&hellip;
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday, formatDate } from '@/data/serverDate'
import { Chart } from 'frappe-charts'

// Same eight shortcuts the desk dashboard offers.
const QUICK_REPORTS = [
  { icon: 'fa-calendar-check-o', label: 'Daily Attendance', report: 'Daily Attendance Report' },
  { icon: 'fa-user', label: 'Student History', report: 'Student Attendance History' },
  { icon: 'fa-calendar', label: 'Monthly Report', report: 'Monthly Attendance Report' },
  { icon: 'fa-users', label: 'Batch Summary', report: 'Standard and Batch Attendance Summary' },
  { icon: 'fa-user-times', label: 'Absent Report', report: 'Absent Student Report' },
  { icon: 'fa-clock-o', label: 'Late Entry Report', report: 'Late Entry Report' },
  { icon: 'fa-exclamation-triangle', label: 'Defaulters', report: 'Attendance Defaulters' },
  { icon: 'fa-list-alt', label: 'Register', report: 'Monthly Attendance Register' },
]

const router = useRouter()

const standards = ref([])
const batches = ref([])
const standard = ref('')
const batch = ref('')
const date = ref(serverToday.value)
const data = ref(null)
const loading = ref(false)

const chartTodayEl = ref(null)
const chartTrendEl = ref(null)
const chartStdEl = ref(null)
const chartAbsEl = ref(null)
const chartLateEl = ref(null)
const charts = reactive({})

// Below this, charts are swapped for lists that show exact values.
const NARROW_BP = 768
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)
const isNarrow = computed(() => viewportWidth.value < NARROW_BP)

const standardsResource = createResource({ url: 'frappe.client.get_list' })
const batchesResource = createResource({ url: 'frappe.client.get_list' })
const dashboardResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.get_attendance_dashboard_data',
})

const todaySummary = computed(
  () => data.value?.today_summary || { present: 0, absent: 0, late: 0, pending: 0, total: 0 }
)

const kpiCards = computed(() => {
  const d = data.value || {}
  return [
    { id: 'new-students', color: 'dash-kpi-blue', icon: 'fa-user-plus', value: d.new_students ?? 0, label: 'New Students', sub: 'Last 7 Days' },
    { id: 'today-absent', color: 'dash-kpi-red', icon: 'fa-times-circle', value: d.today_absent ?? 0, label: "Today's Absent", sub: 'Today' },
    { id: 'absent-5', color: 'dash-kpi-orange', icon: 'fa-exclamation-triangle', value: d.absent_5_plus ?? 0, label: 'Absent > 5', sub: 'This Month' },
    { id: 'late-5', color: 'dash-kpi-amber', icon: 'fa-clock-o', value: d.late_5_plus ?? 0, label: 'Late > 5', sub: 'This Month' },
    { id: 'absent-10', color: 'dash-kpi-red', icon: 'fa-exclamation-triangle', value: d.absent_10_plus ?? 0, label: 'Absent > 10', sub: 'This Month' },
    { id: 'late-10', color: 'dash-kpi-orange', icon: 'fa-clock-o', value: d.late_10_plus ?? 0, label: 'Late > 10', sub: 'This Month' },
  ]
})

const hasTodayData = computed(() => (todaySummary.value.total || 0) > 0)

const todayParts = computed(() => {
  const s = todaySummary.value
  const total = s.total || 0
  const pct = (v) => (total > 0 ? Math.round((v / total) * 100) : 0)
  return [
    { key: 'present', label: 'Present', value: s.present || 0, pct: pct(s.present || 0) },
    { key: 'absent', label: 'Absent', value: s.absent || 0, pct: pct(s.absent || 0) },
    { key: 'late', label: 'Late', value: s.late || 0, pct: pct(s.late || 0) },
    { key: 'pending', label: 'Pending', value: s.pending || 0, pct: pct(s.pending || 0) },
  ]
})

const trend = computed(() => buildTrend(data.value?.trend_raw || []))
const hasTrendData = computed(() => trend.value.labels.length > 0)

const trendStats = computed(() => {
  const v = trend.value.values
  if (!v.length) return { latest: 0, avg: 0, best: 0, worst: 0 }
  return {
    latest: v[v.length - 1],
    avg: Math.round(v.reduce((a, b) => a + b, 0) / v.length),
    best: Math.max(...v),
    worst: Math.min(...v),
  }
})

const sb = computed(() =>
  buildStandardBatch(standard.value ? data.value?.batch_summary : data.value?.standard_summary, !!standard.value)
)
const hasSbData = computed(() => sb.value.labels.length > 0)
const sbRows = computed(() => sb.value.labels.map((l, i) => ({ label: l, value: sb.value.values[i] })))

const hasAbsData = computed(() => (data.value?.top_absent || []).length > 0)
const hasLateData = computed(() => (data.value?.top_late || []).length > 0)

function pctClass(v) {
  if (v >= 75) return 'is-good'
  if (v >= 50) return 'is-warn'
  return 'is-bad'
}

const isMobile = () => viewportWidth.value < 576
const isTablet = () => viewportWidth.value < 992
const chartHeight = (desktop, mobile) => (isMobile() ? mobile : desktop)

function truncateLabel(text, maxLen) {
  if (!text) return text
  return text.length > maxLen ? text.slice(0, maxLen - 1) + '…' : text
}

// Bounds the number of visible tick labels without touching the data points.
function buildThinnedLabels(rawLabels, maxVisible) {
  const map = {}
  const n = rawLabels.length
  if (n <= maxVisible) {
    rawLabels.forEach((l) => (map[l] = l))
    return { labels: rawLabels.slice(), map }
  }
  const step = Math.ceil(n / maxVisible)
  const labels = rawLabels.map((label, i) => {
    if (i % step === 0 || i === n - 1) {
      map[label] = label
      return label
    }
    const placeholder = ' '.repeat(i + 1)
    map[placeholder] = label
    return placeholder
  })
  return { labels, map }
}

function buildTrend(rows) {
  const datesMap = {}
  rows.forEach((r) => {
    if (!datesMap[r.attendance_date]) datesMap[r.attendance_date] = { p: 0, total: 0 }
    if (r.status === 'Present' || r.status === 'Late') datesMap[r.attendance_date].p += r.cnt
    datesMap[r.attendance_date].total += r.cnt
  })
  const labels = []
  const values = []
  Object.keys(datesMap)
    .sort()
    .forEach((dt) => {
      labels.push(dt)
      const v = datesMap[dt]
      values.push(v.total > 0 ? Math.round((v.p / v.total) * 100) : 0)
    })
  return { labels, values }
}

function buildStandardBatch(rows, byBatch) {
  const map = {}
  ;(rows || []).forEach((r) => {
    const key = byBatch ? r.batch : r.standard
    if (!map[key]) map[key] = { p: 0, total: 0 }
    if (r.status === 'Present' || r.status === 'Late') map[key].p += r.cnt
    map[key].total += r.cnt
  })
  const labels = []
  const values = []
  Object.keys(map)
    .sort()
    .forEach((k) => {
      labels.push(k)
      const v = map[k]
      values.push(v.total > 0 ? Math.round((v.p / v.total) * 100) : 0)
    })
  return { labels, values }
}

function destroyChart(key) {
  if (charts[key]) {
    try {
      charts[key].destroy?.()
    } catch (e) {
      /* frappe-charts throws if the node is already gone */
    }
    charts[key] = null
  }
}

function renderCharts() {
  const d = data.value
  if (!d) return
  const narrow = isNarrow.value

  // --- donut: today's distribution (list stands in when narrow) ---
  destroyChart('today')
  if (!narrow && hasTodayData.value && chartTodayEl.value) {
    const s = todaySummary.value
    charts.today = new Chart(chartTodayEl.value, {
      data: {
        labels: ['Present', 'Absent', 'Late', 'Pending'],
        datasets: [{ values: [s.present, s.absent, s.late, s.pending] }],
      },
      type: 'donut',
      colors: ['#30a66d', '#cc2929', '#e86c13', '#c7c7c7'],
      height: chartHeight(280, 240),
      tooltipOptions: { formatTooltipY: (val) => val + ' students' },
    })
  }

  // --- line: 30-day trend (kept on every size; stats row carries the numbers) ---
  destroyChart('trend')
  if (hasTrendData.value && chartTrendEl.value) {
    const maxVisible = isMobile() ? 5 : isTablet() ? 8 : 12
    const thinned = buildThinnedLabels(trend.value.labels, maxVisible)
    charts.trend = new Chart(chartTrendEl.value, {
      data: {
        labels: thinned.labels,
        datasets: [{ name: 'Attendance %', values: trend.value.values }],
      },
      type: 'line',
      colors: ['#007be0'],
      height: chartHeight(260, 200),
      tooltipOptions: {
        formatTooltipX: (label) => thinned.map[label] || label,
        formatTooltipY: (val) => val + '%',
      },
    })
  }

  // --- bar: by standard / batch ---
  destroyChart('standard')
  if (!narrow && hasSbData.value && chartStdEl.value) {
    const maxVisible = isTablet() ? 10 : 20
    const thinned = buildThinnedLabels(sb.value.labels, maxVisible)
    charts.standard = new Chart(chartStdEl.value, {
      data: {
        labels: thinned.labels,
        datasets: [{ name: 'Attendance %', values: sb.value.values }],
      },
      type: 'bar',
      colors: ['#007be0'],
      height: chartHeight(300, 260),
      tooltipOptions: {
        formatTooltipX: (label) => thinned.map[label] || label,
        formatTooltipY: (val) => val + '%',
      },
    })
  }

  // --- bar: top 10 absent ---
  destroyChart('topAbsent')
  if (!narrow && hasAbsData.value && chartAbsEl.value) {
    const nameMap = {}
    const labels = (d.top_absent || []).map((r) => {
      const short = truncateLabel(r.student_name, 16)
      nameMap[short] = r.student_name
      return short
    })
    charts.topAbsent = new Chart(chartAbsEl.value, {
      data: { labels, datasets: [{ name: 'Days', values: (d.top_absent || []).map((r) => r.absent_count) }] },
      type: 'bar',
      colors: ['#cc2929'],
      height: 300,
      tooltipOptions: { formatTooltipX: (label) => nameMap[label] || label },
    })
  }

  // --- bar: top 10 late ---
  destroyChart('topLate')
  if (!narrow && hasLateData.value && chartLateEl.value) {
    const nameMap = {}
    const labels = (d.top_late || []).map((r) => {
      const short = truncateLabel(r.student_name, 16)
      nameMap[short] = r.student_name
      return short
    })
    charts.topLate = new Chart(chartLateEl.value, {
      data: { labels, datasets: [{ name: 'Days', values: (d.top_late || []).map((r) => r.late_count) }] },
      type: 'bar',
      colors: ['#e86c13'],
      height: 300,
      tooltipOptions: { formatTooltipX: (label) => nameMap[label] || label },
    })
  }
}

function onKpiClick(k) {
  const map = {
    'absent-5': 'Absent Student Report',
    'absent-10': 'Absent Student Report',
    'late-5': 'Late Entry Report',
    'late-10': 'Late Entry Report',
    'today-absent': 'Daily Attendance Report',
  }
  const report = map[k.id]
  if (report) router.push({ name: 'AttendanceReports', query: { report } })
}

async function loadFilters() {
  standards.value =
    (await standardsResource.submit({ doctype: 'Standard', fields: ['name'], limit_page_length: 0 })) || []
  batches.value =
    (await batchesResource.submit({ doctype: 'Batch', fields: ['name'], limit_page_length: 0 })) || []
}

async function loadData() {
  loading.value = true
  try {
    data.value = await dashboardResource.submit({
      standard: standard.value || undefined,
      batch: batch.value || undefined,
      date: date.value,
    })
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

let resizeTimer = null
function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    viewportWidth.value = window.innerWidth
  }, 150)
}

onMounted(async () => {
  const t = await loadServerToday()
  if (date.value === formatDate(new Date())) date.value = t
  loadFilters()
  loadData()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(resizeTimer)
  Object.keys(charts).forEach(destroyChart)
})

// Crossing the breakpoint swaps charts and lists, so re-create what's visible.
watch(isNarrow, async () => {
  await nextTick()
  renderCharts()
})

watch(standard, () => {
  if (!standard.value) batch.value = ''
})
watch([standard, batch, date], loadData)
</script>

<style>
.attendance-dashboard {
  --dash-radius: var(--border-radius-md, 8px);
  --dash-radius-sm: var(--border-radius, 6px);
  --dash-gap: 14px;
  position: relative;
  color: var(--text-color);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: var(--dash-gap);
}

.attendance-dashboard * { box-sizing: border-box; }

/* ---- control panel ---- */
.attendance-dashboard .dash-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--dash-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 14px 16px;
}

.attendance-dashboard .dash-panel-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  flex: 1 1 320px;
}

.attendance-dashboard .dash-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.attendance-dashboard .dash-field label i { width: 14px; margin-right: 4px; color: var(--gray-600); }

.attendance-dashboard .dash-panel-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.attendance-dashboard .dash-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: var(--dash-radius-sm);
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.attendance-dashboard .dash-btn-primary { background: var(--blue-600); border-color: var(--blue-600); color: #fff; }
.attendance-dashboard .dash-btn-primary:hover { background: var(--blue-700, var(--blue-600)); color: #fff; }

/* ---- loading ---- */
.attendance-dashboard .dash-content-area {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--dash-gap);
}

.attendance-dashboard .dash-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  background: var(--card-bg);
  opacity: 0.6;
  border-radius: var(--dash-radius);
}

.attendance-dashboard .dash-loading-spinner {
  position: fixed;
  top: 90px;
  right: 24px;
  z-index: 21;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-full, 999px);
  box-shadow: var(--shadow-md);
  padding: 8px 16px;
  font-size: 12px;
  color: var(--text-muted);
}

.attendance-dashboard .dash-loading-spinner i { color: var(--blue-500); }

/* ---- KPI grid ---- */
.attendance-dashboard .dash-kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.attendance-dashboard .dash-kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--dash-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 14px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.attendance-dashboard .dash-kpi-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.attendance-dashboard .dash-kpi-card:active { transform: translateY(-1px); }

.attendance-dashboard .dash-kpi-icon {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border-radius: var(--dash-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
}

.attendance-dashboard .dash-kpi-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }

.attendance-dashboard .dash-kpi-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.attendance-dashboard .dash-kpi-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.attendance-dashboard .dash-kpi-sub { font-size: 11px; color: var(--text-muted); }

.attendance-dashboard .dash-kpi-blue .dash-kpi-icon { background: var(--bg-blue); color: var(--text-on-blue); }
.attendance-dashboard .dash-kpi-red .dash-kpi-icon { background: var(--bg-red); color: var(--text-on-red); }
.attendance-dashboard .dash-kpi-orange .dash-kpi-icon { background: var(--bg-orange); color: var(--text-on-orange); }
.attendance-dashboard .dash-kpi-amber .dash-kpi-icon { background: var(--bg-yellow); color: var(--text-on-yellow); }

/* ---- cards + grid ---- */
.attendance-dashboard .dash-grid { display: grid; gap: var(--dash-gap); }
.attendance-dashboard .dash-grid-split { grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); }
.attendance-dashboard .dash-grid-half { grid-template-columns: repeat(2, minmax(0, 1fr)); }

.attendance-dashboard .dash-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--dash-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  overflow: hidden;
}

.attendance-dashboard .dash-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--border-color);
  background: var(--subtle-accent, var(--gray-50));
}

.attendance-dashboard .dash-card-header i { color: var(--gray-600); font-size: 13px; }

.attendance-dashboard .dash-card-header h6 {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--heading-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attendance-dashboard .dash-card-header h6 small {
  font-weight: 400;
  color: var(--text-muted);
  font-size: 11.5px;
}

.attendance-dashboard .dash-card-meta {
  margin-left: auto;
  flex: 0 0 auto;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-100));
  border-radius: var(--border-radius-full, 999px);
  padding: 2px 9px;
}

.attendance-dashboard .dash-card-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
}

.attendance-dashboard .dash-chart-canvas { width: 100%; min-width: 0; overflow: hidden; }
.attendance-dashboard .dash-chart-canvas svg { max-width: 100%; }

.attendance-dashboard .dash-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 28px 10px;
  color: var(--text-muted);
}

.attendance-dashboard .dash-empty i { font-size: 26px; color: var(--gray-300); }
.attendance-dashboard .dash-empty p { margin: 0; font-size: 12.5px; }

/* ---- today's distribution ---- */
.attendance-dashboard .dash-stackbar {
  display: flex;
  width: 100%;
  height: 14px;
  border-radius: var(--border-radius-full, 999px);
  overflow: hidden;
  background: var(--gray-200);
  margin-bottom: 12px;
}

.attendance-dashboard .dash-stackbar-seg { display: block; height: 100%; }

.attendance-dashboard .dash-seg-present { background: var(--green-600); }
.attendance-dashboard .dash-seg-absent { background: var(--red-600); }
.attendance-dashboard .dash-seg-late { background: var(--orange-500); }
.attendance-dashboard .dash-seg-pending { background: var(--gray-400); }

.attendance-dashboard .dash-legend { list-style: none; margin: 10px 0 0; padding: 0; }

.attendance-dashboard .dash-legend li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}

.attendance-dashboard .dash-legend li:last-child { border-bottom: none; }

.attendance-dashboard .dash-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.attendance-dashboard .dash-legend-label { color: var(--text-color); }

.attendance-dashboard .dash-legend-value {
  margin-left: auto;
  font-weight: 700;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.attendance-dashboard .dash-legend-pct {
  min-width: 42px;
  text-align: right;
  font-size: 11.5px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

/* ---- trend stats ---- */
.attendance-dashboard .dash-statrow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.attendance-dashboard .dash-statrow div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: center;
}

.attendance-dashboard .dash-statrow span { font-size: 11px; color: var(--text-muted); }

.attendance-dashboard .dash-statrow strong {
  font-size: 15px;
  font-weight: 700;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

/* ---- bar list (by standard / batch on narrow screens) ---- */
.attendance-dashboard .dash-barlist { list-style: none; margin: 0; padding: 0; }

.attendance-dashboard .dash-barlist li {
  display: grid;
  grid-template-columns: minmax(56px, auto) 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.attendance-dashboard .dash-barlist li:last-child { border-bottom: none; }

.attendance-dashboard .dash-barlist-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attendance-dashboard .dash-barlist-track {
  height: 8px;
  border-radius: var(--border-radius-full, 999px);
  background: var(--gray-200);
  overflow: hidden;
}

.attendance-dashboard .dash-barlist-fill { display: block; height: 100%; border-radius: inherit; }
.attendance-dashboard .dash-barlist-fill.is-good { background: var(--green-600); }
.attendance-dashboard .dash-barlist-fill.is-warn { background: var(--orange-500); }
.attendance-dashboard .dash-barlist-fill.is-bad { background: var(--red-600); }

.attendance-dashboard .dash-barlist-value {
  min-width: 40px;
  text-align: right;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

/* ---- rank list (top absent / late on narrow screens) ---- */
.attendance-dashboard .dash-ranklist { list-style: none; margin: 0; padding: 0; counter-reset: rank; }

.attendance-dashboard .dash-ranklist li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.attendance-dashboard .dash-ranklist li:last-child { border-bottom: none; }

.attendance-dashboard .dash-rank {
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--subtle-fg, var(--gray-100));
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.attendance-dashboard .dash-rank-name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 13px;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attendance-dashboard .dash-rank-value {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
  border-radius: var(--border-radius-full, 999px);
  padding: 2px 10px;
  font-variant-numeric: tabular-nums;
}

.attendance-dashboard .dash-rank-absent { background: var(--bg-red); color: var(--text-on-red); }
.attendance-dashboard .dash-rank-late { background: var(--bg-orange); color: var(--text-on-orange); }

/* ---- quick reports ---- */
.attendance-dashboard .dash-reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.attendance-dashboard .dash-report-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--dash-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
  padding: 11px 12px;
  font-size: 12.5px;
  font-weight: 500;
  text-decoration: none;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.attendance-dashboard .dash-report-btn i {
  flex: 0 0 auto;
  width: 14px;
  text-align: center;
  color: var(--gray-600);
}

.attendance-dashboard .dash-report-btn span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attendance-dashboard .dash-report-btn:hover {
  background: var(--bg-blue);
  color: var(--text-on-blue);
  border-color: var(--blue-200, var(--border-color));
}

.attendance-dashboard .dash-report-btn:hover i { color: inherit; }

/* ======================= responsive ======================= */

/* tablet: 3-up KPIs, charts stack full width */
@media (max-width: 991px) {
  .attendance-dashboard .dash-kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .attendance-dashboard .dash-kpi-value { font-size: 21px; }
  .attendance-dashboard .dash-grid-split { grid-template-columns: minmax(0, 1fr); }
}

/* phone / small tablet */
@media (max-width: 767px) {
  .attendance-dashboard { padding: 10px; gap: 12px; }

  .attendance-dashboard .dash-panel { padding: 12px; gap: 12px; }

  .attendance-dashboard .dash-panel-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    flex: none;
    width: 100%;
  }

  /* date gets its own full-width row so the value is never clipped */
  .attendance-dashboard .dash-field:nth-child(3) { grid-column: 1 / -1; }

  .attendance-dashboard .dash-panel-actions { width: 100%; }
  .attendance-dashboard .dash-btn { width: 100%; }

  .attendance-dashboard .dash-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }

  /* stack the two Top-10 lists rather than squeezing them side by side */
  .attendance-dashboard .dash-grid-half { grid-template-columns: minmax(0, 1fr); }

  .attendance-dashboard .dash-card-body { padding: 12px; }

  .attendance-dashboard .dash-reports-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  /* keep the spinner clear of the bottom nav */
  .attendance-dashboard .dash-loading-spinner {
    top: auto;
    bottom: 84px;
    right: 12px;
    left: 12px;
    justify-content: center;
  }
}

/* small phones: KPI cards go vertical so long labels stay readable */
@media (max-width: 480px) {
  .attendance-dashboard .dash-kpi-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
  }

  .attendance-dashboard .dash-kpi-icon { width: 32px; height: 32px; font-size: 14px; }
  .attendance-dashboard .dash-kpi-value { font-size: 20px; }
  .attendance-dashboard .dash-kpi-label { font-size: 12px; white-space: normal; }
  .attendance-dashboard .dash-kpi-sub { font-size: 10.5px; }

  .attendance-dashboard .dash-statrow { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .attendance-dashboard .dash-legend li { font-size: 12.5px; }
}

/* very narrow: single-column reports so labels never truncate */
@media (max-width: 360px) {
  .attendance-dashboard .dash-reports-grid { grid-template-columns: minmax(0, 1fr); }
  .attendance-dashboard .dash-panel-filters { grid-template-columns: minmax(0, 1fr); }
  .attendance-dashboard .dash-field:nth-child(3) { grid-column: auto; }
}
</style>
