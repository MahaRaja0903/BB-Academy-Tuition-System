<template>
  <div class="rep-manager">
    <!-- Control panel -->
    <div class="rep-panel">
      <div class="rep-field rep-field-wide">
        <label><i class="fa fa-list-alt"></i> Report</label>
        <select class="form-control" v-model="reportName">
          <option v-for="r in REPORTS" :key="r.name" :value="r.name">{{ r.name }}</option>
        </select>
      </div>

      <!-- Only the filters the selected report actually consumes are shown -->
      <template v-if="uses('from_date')">
        <div class="rep-field">
          <label><i class="fa fa-calendar"></i> From Date</label>
          <input type="date" class="form-control" v-model="fromDate" />
        </div>
        <div class="rep-field">
          <label><i class="fa fa-calendar"></i> To Date</label>
          <input type="date" class="form-control" v-model="toDate" />
        </div>
      </template>

      <div v-if="uses('attendance_date')" class="rep-field">
        <label><i class="fa fa-calendar"></i> Attendance Date</label>
        <input type="date" class="form-control" v-model="toDate" />
      </div>

      <div v-if="uses('standard')" class="rep-field">
        <label><i class="fa fa-graduation-cap"></i> Standard</label>
        <select class="form-control" v-model="standard">
          <option value="">All Standards</option>
          <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
        </select>
      </div>

      <div v-if="uses('batch')" class="rep-field">
        <label><i class="fa fa-users"></i> Batch</label>
        <select class="form-control" v-model="batch">
          <option value="">All Batches</option>
          <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
        </select>
      </div>

      <div v-if="uses('gender')" class="rep-field">
        <label><i class="fa fa-venus-mars"></i> Gender</label>
        <select class="form-control" v-model="gender">
          <option value="">All</option>
          <option value="Boys">Boys</option>
          <option value="Girls">Girls</option>
        </select>
      </div>

      <!-- Student Attendance History reads filters["student"] directly: without
           it the report raises KeyError, so it is required, not optional. -->
      <div v-if="uses('student')" class="rep-field rep-field-wide">
        <label><i class="fa fa-user"></i> Student <span class="rep-req">*</span></label>
        <select class="form-control" v-model="student">
          <option value="">Select a student</option>
          <option v-for="s in studentList" :key="s.name" :value="s.name">
            {{ s.student_name }} ({{ s.name }})
          </option>
        </select>
      </div>

      <div v-if="uses('status')" class="rep-field">
        <label><i class="fa fa-check-circle"></i> Status</label>
        <select class="form-control" v-model="status">
          <option value="">Any</option>
          <option value="Present">Present</option>
          <option value="Absent">Absent</option>
          <option value="Late">Late</option>
        </select>
      </div>

      <div v-if="uses('holiday_type')" class="rep-field">
        <label><i class="fa fa-calendar-times-o"></i> Holiday Type</label>
        <select class="form-control" v-model="holidayType">
          <option value="">Any</option>
          <option v-for="t in HOLIDAY_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <div v-if="uses('min_absent')" class="rep-field">
        <label><i class="fa fa-times-circle"></i> Minimum absences</label>
        <input type="number" min="0" class="form-control" v-model.number="minAbsent" />
      </div>

      <div v-if="uses('min_late')" class="rep-field">
        <label><i class="fa fa-clock-o"></i> Minimum late entries</label>
        <input type="number" min="0" class="form-control" v-model.number="minLate" />
      </div>

      <div v-if="uses('absent_days')" class="rep-field">
        <label><i class="fa fa-times-circle"></i> Absent days ≥</label>
        <input type="number" min="0" class="form-control" v-model.number="absentDays" />
      </div>

      <div v-if="uses('late_days')" class="rep-field">
        <label><i class="fa fa-clock-o"></i> Late days ≥</label>
        <input type="number" min="0" class="form-control" v-model.number="lateDays" />
      </div>

      <!-- Defaulters lists students BELOW this attendance % (report default 75) -->
      <div v-if="uses('threshold')" class="rep-field">
        <label><i class="fa fa-exclamation-triangle"></i> Attendance % below</label>
        <input type="number" min="0" max="100" class="form-control" v-model.number="pctThreshold" />
      </div>

      <div class="rep-field rep-field-action">
        <button class="rep-run-btn" :disabled="loading || !canRun" @click="runReport">
          <i class="fa fa-play"></i> {{ loading ? 'Running…' : 'Run Report' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="rep-error"><i class="fa fa-exclamation-circle"></i> {{ error }}</div>

    <div class="rep-table-card">
      <div v-if="loading" class="rep-skeleton">
        <div v-for="i in 4" :key="i" class="rep-skeleton-bar"></div>
      </div>

      <div v-else-if="rows.length" class="rep-table-scroll">
        <table class="rep-table">
          <thead>
            <tr>
              <th v-for="(c, i) in columnLabels" :key="i">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in rows" :key="ri">
              <td v-for="(c, ci) in columnLabels" :key="ci">{{ cellValue(row, ci) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="rep-empty-state">
        <div class="rep-empty-icon">
          <i class="fa" :class="ran ? 'fa-info-circle' : 'fa-list-alt'"></i>
        </div>
        <h4>{{ ran ? 'No rows returned' : 'Choose a report' }}</h4>
        <p>
          {{
            ran
              ? 'No data matched the filters for this report.'
              : 'Pick a report and its filters above, then press Run Report.'
          }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday, formatDate } from '@/data/serverDate'


const HOLIDAY_TYPES = [
  'Rain',
  'Government Holiday',
  'School Holiday',
  'Emergency',
  'Sunday',
  'KPI Meeting',
  'Other',
]

// Filter keys come from each report's own execute(). Sending a key a report
// doesn't read is harmless, but omitting one it reads straight off the filters
// dict (student, from_date, …) raises KeyError server-side.
const REPORTS = [
  { name: 'Daily Attendance Report', filters: ['attendance_date', 'standard', 'batch', 'status'] },
  { name: 'Monthly Attendance Report', filters: ['from_date', 'to_date'] },
  { name: 'Attendance Defaulters', filters: ['from_date', 'to_date', 'threshold'] },
  { name: 'Absent Student Report', filters: ['from_date', 'to_date', 'min_absent'] },
  { name: 'Late Entry Report', filters: ['from_date', 'to_date', 'min_late'] },
  { name: 'Student Attendance History', filters: ['student', 'from_date', 'to_date'] },
  {
    name: 'Attendance Holiday Report',
    filters: ['from_date', 'to_date', 'standard', 'batch', 'holiday_type'],
  },
  { name: 'Standard and Batch Attendance Summary', filters: ['from_date', 'to_date'] },
  {
    name: 'Monthly Attendance Register',
    filters: ['from_date', 'to_date', 'standard', 'batch', 'gender', 'late_days', 'absent_days'],
  },
]

const route = useRoute()

const reportName = ref(REPORTS[0].name)
const fromDate = ref(serverToday.value)
const toDate = ref(serverToday.value)
const standard = ref('')
const batch = ref('')
const gender = ref('')
const student = ref('')
const status = ref('')
const holidayType = ref('')
const minAbsent = ref(5)
const minLate = ref(5)
const absentDays = ref(0)
const lateDays = ref(0)
const pctThreshold = ref(75)
const standards = ref([])
const batches = ref([])
const studentList = ref([])

const columns = ref([])
const rows = ref([])
const loading = ref(false)
const ran = ref(false)
const error = ref('')

const standardsResource = createResource({ url: 'frappe.client.get_list' })
const batchesResource = createResource({ url: 'frappe.client.get_list' })
const studentsResource = createResource({ url: 'frappe.client.get_list' })
const reportResource = createResource({ url: 'frappe.desk.query_report.run' })

const activeReport = computed(() => REPORTS.find((r) => r.name === reportName.value) || REPORTS[0])

function uses(key) {
  return activeReport.value.filters.includes(key)
}

const canRun = computed(() => (uses('student') ? !!student.value : true))

const columnLabels = computed(() =>
  columns.value.map((c) => {
    if (typeof c === 'string') return c.split(':')[0]
    return c.label || c.fieldname || ''
  })
)

function cellValue(row, index) {
  if (Array.isArray(row)) return row[index]
  const col = columns.value[index]
  const fieldname = typeof col === 'string' ? col.split(':')[0] : col.fieldname
  return row[fieldname]
}

function buildFilters() {
  const all = {
    from_date: fromDate.value,
    to_date: toDate.value,
    attendance_date: toDate.value,
    standard: standard.value || undefined,
    batch: batch.value || undefined,
    gender: gender.value || undefined,
    student: student.value || undefined,
    status: status.value || undefined,
    holiday_type: holidayType.value || undefined,
    min_absent: minAbsent.value,
    min_late: minLate.value,
    absent_days: absentDays.value,
    late_days: lateDays.value,
    threshold: pctThreshold.value,
  }
  const out = {}
  for (const key of activeReport.value.filters) {
    if (all[key] !== undefined) out[key] = all[key]
  }
  return out
}

async function loadFilters() {
  standards.value =
    (await standardsResource.submit({ doctype: 'Standard', fields: ['name'], limit_page_length: 0 })) || []
  batches.value =
    (await batchesResource.submit({ doctype: 'Batch', fields: ['name'], limit_page_length: 0 })) || []
  studentList.value =
    (await studentsResource.submit({
      doctype: 'Student',
      fields: ['name', 'student_name'],
      filters: { status: 'Active' },
      order_by: 'student_name asc',
      limit_page_length: 0,
    })) || []
}

async function runReport() {
  loading.value = true
  error.value = ''
  ran.value = true
  try {
    const res = await reportResource.submit({
      report_name: reportName.value,
      filters: buildFilters(),
    })
    columns.value = res?.columns || []
    rows.value = res?.result || []
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Failed to run report'
    columns.value = []
    rows.value = []
  } finally {
    loading.value = false
  }
}

// Deep links from the dashboard's Quick Reports / KPI cards
function applyRouteQuery() {
  const wanted = route.query.report
  if (wanted && REPORTS.some((r) => r.name === wanted)) {
    reportName.value = wanted
  }
}

onMounted(async () => {
  const t = await loadServerToday()
  const deviceToday = formatDate(new Date())
  if (fromDate.value === deviceToday) fromDate.value = t
  if (toDate.value === deviceToday) toDate.value = t
  applyRouteQuery()
  loadFilters()
})

watch(() => route.query.report, applyRouteQuery)

// Switching report invalidates the previous result set
watch(reportName, () => {
  rows.value = []
  columns.value = []
  ran.value = false
  error.value = ''
})
</script>

<style>
.rep-manager {
  --rep-radius: var(--border-radius-md, 8px);
  --rep-radius-sm: var(--border-radius, 6px);
  --rep-gap: 14px;
  color: var(--text-color);
  padding: 14px;
}

.rep-manager * { box-sizing: border-box; }
.rep-manager button { font-family: inherit; }

.rep-manager .rep-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--rep-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 16px 18px;
  margin-bottom: var(--rep-gap);
}

.rep-manager .rep-field { min-width: 150px; flex: 1 1 150px; }
.rep-manager .rep-field-wide { flex: 1 1 260px; }
.rep-manager .rep-field-action { flex: 0 0 auto; }

.rep-manager .rep-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.rep-manager .rep-field label i { width: 14px; margin-right: 4px; color: var(--gray-600); }
.rep-manager .rep-req { color: var(--red-600); }

.rep-manager .rep-run-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 20px;
  border: 1px solid var(--blue-600);
  border-radius: var(--rep-radius-sm);
  background: var(--blue-600);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s ease;
}

.rep-manager .rep-run-btn:hover:not(:disabled) { background: var(--blue-700, var(--blue-600)); }
.rep-manager .rep-run-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.rep-manager .rep-error {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-red);
  border: 1px solid var(--red-200);
  color: var(--text-on-red);
  border-radius: var(--rep-radius);
  padding: 10px 14px;
  font-size: 12.5px;
  margin-bottom: var(--rep-gap);
}

.rep-manager .rep-table-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--rep-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  overflow: hidden;
}

.rep-manager .rep-table-scroll { overflow-x: auto; }

.rep-manager .rep-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0;
}

.rep-manager .rep-table thead th {
  background: var(--subtle-accent, var(--gray-50));
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
  white-space: nowrap;
}

.rep-manager .rep-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  font-size: 12.5px;
  white-space: nowrap;
  color: var(--text-color);
}

.rep-manager .rep-table tbody tr:last-child td { border-bottom: none; }
.rep-manager .rep-table tbody tr:hover { background: var(--fg-hover-color, var(--gray-50)); }

.rep-manager .rep-empty-state { text-align: center; padding: 48px 20px; color: var(--text-muted); }
.rep-manager .rep-empty-icon { font-size: 34px; color: var(--gray-400); margin-bottom: 12px; }
.rep-manager .rep-empty-state h4 { color: var(--heading-color); font-size: 16px; margin-bottom: 6px; }
.rep-manager .rep-empty-state p { margin: 0 auto; max-width: 360px; font-size: 13px; }

.rep-manager .rep-skeleton { padding: 16px; display: flex; flex-direction: column; gap: 10px; }

.rep-manager .rep-skeleton-bar {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: rep-skeleton-shine 1.4s ease infinite;
}

@keyframes rep-skeleton-shine {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

@media (min-width: 768px) {
  .rep-manager .rep-table-scroll { max-height: 68vh; overflow-y: auto; }
  .rep-manager .rep-table thead th { position: sticky; top: 0; z-index: 2; }
}

@media (max-width: 767px) {
  .rep-manager { padding: 10px; }
  .rep-manager .rep-panel {
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: end;
    padding: 14px;
  }
  .rep-manager .rep-field { min-width: 0; flex: none; }
  .rep-manager .rep-field-wide,
  .rep-manager .rep-field-action { grid-column: 1 / -1; }
  .rep-manager .rep-run-btn { width: 100%; }
}
</style>
