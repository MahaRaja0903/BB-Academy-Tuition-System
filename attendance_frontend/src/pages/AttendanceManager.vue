<template>
  <div class="attendance-manager">
    <!-- Control panel -->
    <div class="att-panel">
      <div class="att-panel-filters">
        <div class="att-field att-field-standard">
          <label for="att-standard"><i class="fa fa-graduation-cap"></i> Standard</label>
          <select id="att-standard" class="form-control" v-model="standard">
            <option value="">Select Standard</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="att-field att-field-batch">
          <label for="att-batch"><i class="fa fa-users"></i> Batch</label>
          <select id="att-batch" class="form-control" v-model="batch" :disabled="!standard">
            <option value="">Select Batch</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
        <div class="att-field att-field-gender">
          <label for="att-gender"><i class="fa fa-venus-mars"></i> Gender</label>
          <select id="att-gender" class="form-control" v-model="gender">
            <option value="">All</option>
            <option value="Boys">Boys</option>
            <option value="Girls">Girls</option>
          </select>
        </div>
      </div>

      <div class="att-panel-date">
        <span class="att-date-label"><i class="fa fa-calendar"></i> Attendance Date</span>
        <div class="att-date-stepper">
          <button type="button" class="att-date-nav-btn" title="Previous Day" @click="stepDate(-1)">
            <i class="fa fa-arrow-left"></i>
          </button>
          <input type="date" class="att-date-input" v-model="date" :max="serverToday" />
          <button
            type="button"
            class="att-date-nav-btn"
            title="Next Day"
            :disabled="!canStepForward"
            @click="stepDate(1)"
          >
            <i class="fa fa-arrow-right"></i>
          </button>
        </div>
      </div>

      <div class="att-panel-actions">
        <button class="att-holiday-btn" @click="openHolidayModal">
          <i class="fa fa-calendar-plus-o"></i> <span>Assign Holiday</span>
        </button>
        <div
          v-if="birthdayCount > 0"
          id="birthday-alert"
          title="Click to see who is celebrating!"
          @click="showBirthdays"
        >
          <i class="fa fa-birthday-cake"></i> <span>{{ birthdayCount }}</span> Birthdays Today
        </div>
      </div>
    </div>

    <!-- Future-date notice / save failures -->
    <div v-if="isFutureDate" class="att-alert att-alert-warn">
      <i class="fa fa-exclamation-triangle"></i>
      This date is in the future — attendance can only be marked up to
      {{ serverToday }}.
    </div>
    <div v-else-if="saveError" class="att-alert att-alert-error">
      <i class="fa fa-exclamation-circle"></i> {{ saveError }}
      <button type="button" @click="saveError = ''"><i class="fa fa-times"></i></button>
    </div>

    <!-- KPI cards -->
    <div class="att-kpi-grid">
      <button
        v-for="kpi in kpis"
        :key="kpi.key"
        type="button"
        class="att-kpi-card"
        :class="[`att-kpi-${kpi.key}`, { 'is-active': statusFilter === kpi.filter }]"
        :title="kpi.title"
        @click="toggleFilter(kpi.filter)"
      >
        <span class="att-kpi-icon"><i class="fa" :class="kpi.icon"></i></span>
        <span class="att-kpi-body">
          <span class="att-kpi-value">{{ kpi.value }}</span>
          <span class="att-kpi-label">{{ kpi.label }}</span>
        </span>
      </button>
    </div>

    <!-- Toolbar -->
    <div class="att-toolbar">
      <div class="att-search-wrap">
        <i class="fa fa-search"></i>
        <input
          type="text"
          class="att-search-input"
          placeholder="Search student name or ID"
          v-model="search"
        />
      </div>
      <div class="att-toolbar-right">
        <span v-if="statusFilter" class="att-filter-chip">
          <span>Showing <strong>{{ statusFilter }}</strong></span>
          <button type="button" title="Clear filter" @click="statusFilter = null">
            <i class="fa fa-times"></i>
          </button>
        </span>
        <div class="att-switch att-select-all-switch">
          <input
            id="att-toolbar-select-all"
            type="checkbox"
            :checked="allVisibleSelected"
            :indeterminate.prop="someVisibleSelected"
            @change="toggleSelectAll($event.target.checked)"
          />
          <label for="att-toolbar-select-all">Select All</label>
        </div>
        <div class="att-switch att-show-completed-switch">
          <input id="att-show-completed" type="checkbox" v-model="showCompleted" />
          <label for="att-show-completed">Show Completed</label>
        </div>
      </div>
    </div>

    <!-- Bulk selection action bar -->
    <div v-if="selected.size > 0" class="att-bulk-bar">
      <span class="att-bulk-count">
        <i class="fa fa-check-square-o"></i> <span>{{ selected.size }}</span> Students Selected
      </span>
      <div class="att-bulk-actions">
        <button class="att-bulk-btn att-bulk-present" @click="bulkMark('Present')">
          <i class="fa fa-check"></i> Present
        </button>
        <button class="att-bulk-btn att-bulk-absent" @click="bulkMark('Absent')">
          <i class="fa fa-times"></i> Absent
        </button>
        <button class="att-bulk-btn att-bulk-late" @click="bulkMark('Late')">
          <i class="fa fa-clock-o"></i> Late
        </button>
        <button class="att-bulk-btn att-bulk-clear" @click="selected.clear()">Clear</button>
      </div>
    </div>

    <!-- Holiday card -->
    <div v-if="holiday" class="att-holiday-card">
      <div class="att-holiday-icon"><i class="fa fa-calendar-plus-o"></i></div>
      <div class="att-holiday-content">
        <h4>Holiday</h4>
        <p><span class="att-holiday-key">Type</span><span>{{ holiday.holiday_type }}</span></p>
        <p><span class="att-holiday-key">Reason</span><span>{{ holiday.reason }}</span></p>
        <p class="att-holiday-note">Attendance is not required for this date.</p>
      </div>
    </div>

    <!-- Student table / cards -->
    <div v-else class="att-table-card">
      <div class="att-table-scroll">
        <table class="att-table">
          <thead>
            <tr>
              <th class="att-col-select"></th>
              <th class="att-col-name">Student Name</th>
              <th class="att-col-id">Student ID &amp; Stats</th>
              <th class="att-col-prev">Previous Day</th>
              <th class="att-col-actions">Today's Attendance</th>
            </tr>
          </thead>
          <tbody>
            <!-- skeleton -->
            <template v-if="loading">
              <tr v-for="i in 4" :key="`sk${i}`" class="att-skeleton-row">
                <td colspan="5">
                  <div class="att-skeleton-bar" style="width: 40%; margin-bottom: 8px"></div>
                  <div class="att-skeleton-bar" style="width: 70%"></div>
                </td>
              </tr>
            </template>

            <!-- empty states, mirroring the desk's three distinct cases -->
            <tr v-else-if="emptyState" class="att-placeholder-row">
              <td colspan="5">
                <div class="att-empty-state" :class="emptyState.cls">
                  <div class="att-empty-icon"><i class="fa" :class="emptyState.icon"></i></div>
                  <h4>{{ emptyState.title }}</h4>
                  <p>{{ emptyState.text }}</p>
                </div>
              </td>
            </tr>

            <tr
              v-for="s in (loading || emptyState ? [] : visibleStudents)"
              :key="s.student_id"
              class="att-student-row"
              :data-current-status="s.today_status || ''"
            >
              <td class="att-td-select">
                <input
                  type="checkbox"
                  class="att-row-select"
                  :checked="selected.has(s.student_id)"
                  @change="toggleSelect(s.student_id)"
                />
              </td>
              <td class="att-td-name">
                <div class="att-student-profile">
                  <div class="att-student-name-wrap">
                    <span class="att-student-name" :style="s.is_new_joiner ? newJoinerNameStyle : ''">
                      {{ s.student_name }}
                    </span>
                    <i
                      v-if="s.gender"
                      class="fa att-gender-icon"
                      :class="[
                        s.gender === 'Girls' ? 'fa-female' : 'fa-male',
                        s.gender === 'Girls' ? 'att-gender-icon-female' : 'att-gender-icon-male',
                      ]"
                      :title="s.gender"
                    ></i>
                    <i
                      v-if="s.is_birthday"
                      class="fa fa-birthday-cake att-birthday-icon"
                      title="Birthday Today!"
                    ></i>
                    <span v-if="s.is_new_joiner" class="att-badge-new">
                      <i class="fa fa-star"></i> New Student
                    </span>
                    <span
                      v-if="s.is_temporary"
                      class="att-badge-temp"
                      :title="`Temporarily moved from Batch ${s.original_batch}`"
                    >
                      <i class="fa fa-exchange"></i> Actual Batch: {{ s.original_batch }}
                    </span>
                  </div>
                  <img
                    v-if="s.image"
                    class="att-avatar"
                    :src="s.image"
                    :alt="s.student_name"
                    loading="lazy"
                  />
                  <div v-else class="att-avatar att-avatar-fallback">
                    {{ initials(s.student_name) }}
                  </div>
                </div>
              </td>
              <td class="att-td-id">
                <div class="att-student-id" :class="{ 'att-new-joiner': s.is_new_joiner }">
                  {{ s.student_id }}
                </div>
                <div class="att-student-stats">
                  <span class="att-stat-chip att-stat-absent">Absent <b>{{ s.monthly_absent }}</b></span>
                  <span class="att-stat-chip att-stat-late">Late <b>{{ s.monthly_late }}</b></span>
                </div>
              </td>
              <td class="att-td-prev">
                <span class="att-prev-label">Previous</span>
                <span class="att-prev-badge" :data-status="s.previous_status">
                  {{ s.previous_status }}
                </span>
              </td>
              <td class="att-td-actions">
                <div class="att-status-group">
                  <!-- The handler lives on the radio's change, NOT on the
                       label's click: a label wrapping an input fires click
                       twice (once itself, once for the click it forwards to
                       the input), which sent two concurrent save requests. -->
                  <label
                    v-for="opt in STATUS_OPTIONS"
                    :key="opt.value"
                    class="att-status-btn"
                    :class="[
                      `att-status-${opt.value.toLowerCase()}`,
                      { active: s.today_status === opt.value },
                      // desk locks Present/Absent once a late permission exists
                      s.has_late_permission && opt.value !== 'Late' ? 'disabled' : '',
                      { 'is-saving': savingStudent === s.student_id },
                    ]"
                  >
                    <input
                      type="radio"
                      :name="`att_${s.student_id}`"
                      :value="opt.value"
                      :checked="s.today_status === opt.value"
                      :disabled="
                        (s.has_late_permission && opt.value !== 'Late') ||
                        savingStudent === s.student_id
                      "
                      @change="onStatusClick(s, opt.value)"
                    />
                    <i class="fa" :class="opt.icon"></i><span>{{ opt.value }}</span>
                  </label>
                </div>
                <div v-if="s.has_late_permission" class="att-lp-msg">
                  <i class="fa fa-info-circle"></i> Parents informed for late reason:
                  {{ s.late_reason }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Late reason modal -->
    <div v-if="lateModal.open" class="att-modal-backdrop" @click.self="closeLateModal">
      <div class="att-modal">
        <h3>{{ lateModal.bulk ? `Mark ${selected.size} students Late` : 'Mark Late' }}</h3>
        <label class="att-modal-label">Late Reason <span class="att-req">*</span></label>
        <select class="form-control" v-model="lateModal.reason">
          <option value="">Select a reason</option>
          <option v-for="r in lateEntryReasons" :key="r.name" :value="r.name">{{ r.name }}</option>
        </select>
        <p v-if="!lateEntryReasons.length" class="att-modal-warn">
          No "Late Entry Reason" records exist yet — create them in the desk first.
        </p>
        <p v-if="lateModal.error" class="att-modal-error">{{ lateModal.error }}</p>
        <div class="att-modal-actions">
          <button class="att-btn att-btn-secondary" @click="closeLateModal">Cancel</button>
          <button
            class="att-btn att-btn-primary"
            :disabled="!lateModal.reason || lateModal.saving"
            @click="confirmLate"
          >
            {{ lateModal.saving ? 'Saving…' : 'Mark Late' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Assign holiday modal -->
    <div v-if="holidayModal.open" class="att-modal-backdrop" @click.self="holidayModal.open = false">
      <div class="att-modal">
        <h3>Assign Holiday</h3>

        <label class="att-modal-label">Date <span class="att-req">*</span></label>
        <input type="date" class="form-control" v-model="holidayModal.date" />

        <label class="att-modal-label">Holiday Type <span class="att-req">*</span></label>
        <select class="form-control" v-model="holidayModal.holiday_type">
          <option value="">Select type</option>
          <option v-for="t in HOLIDAY_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>

        <label class="att-modal-label">Reason <span class="att-req">*</span></label>
        <textarea class="form-control att-textarea" rows="2" v-model="holidayModal.reason"></textarea>

        <label class="att-modal-label">Scope <span class="att-req">*</span></label>
        <select class="form-control" v-model="holidayModal.scope">
          <option v-for="s in HOLIDAY_SCOPES" :key="s" :value="s">{{ s }}</option>
        </select>

        <template v-if="holidayModal.scope !== 'Entire School'">
          <label class="att-modal-label">Standard</label>
          <select class="form-control" v-model="holidayModal.standard">
            <option value="">Select Standard</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </template>
        <template v-if="holidayModal.scope === 'Standard + Batch'">
          <label class="att-modal-label">Batch</label>
          <select class="form-control" v-model="holidayModal.batch">
            <option value="">Select Batch</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </template>

        <p v-if="holidayModal.error" class="att-modal-error">{{ holidayModal.error }}</p>

        <div class="att-modal-actions">
          <button class="att-btn att-btn-secondary" @click="holidayModal.open = false">Cancel</button>
          <button class="att-btn att-btn-primary" :disabled="holidayModal.saving" @click="confirmHoliday">
            {{ holidayModal.saving ? 'Saving…' : 'Assign Holiday' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Birthday list modal -->
    <div v-if="birthdayModalOpen" class="att-modal-backdrop" @click.self="birthdayModalOpen = false">
      <div class="att-modal">
        <h3>🎂 Birthdays Today</h3>
        <ul class="att-birthday-list">
          <li v-for="s in birthdayStudents" :key="s.student_id">
            {{ s.student_name }} <span>{{ s.student_id }}</span>
          </li>
        </ul>
        <div class="att-modal-actions">
          <button class="att-btn att-btn-secondary" @click="birthdayModalOpen = false">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday, formatDate, addDays } from '@/data/serverDate'


const STATUS_OPTIONS = [
  { value: 'Present', icon: 'fa-check-circle' },
  { value: 'Absent', icon: 'fa-times-circle' },
  { value: 'Late', icon: 'fa-clock-o' },
]

// Mirrors the Select options on the Attendance Holiday doctype — a value
// outside this list is rejected server-side with a ValidationError.
const HOLIDAY_TYPES = [
  'Rain',
  'Government Holiday',
  'School Holiday',
  'Emergency',
  'Sunday',
  'KPI Meeting',
  'Other',
]
const HOLIDAY_SCOPES = ['Entire School', 'Standard', 'Standard + Batch']

const newJoinerNameStyle = 'color: #ff9800; font-weight: bold;'

const standards = ref([])
const batches = ref([])
const standard = ref('')
const batch = ref('')
const gender = ref('')
const date = ref(serverToday.value)
const saveError = ref('')
const savingStudent = ref(null)
const bulkSaving = ref(false)

const students = ref([])
const summary = reactive({ present: 0, absent: 0, late: 0, pending: 0 })
const holiday = ref(null)
const loading = ref(false)

const search = ref('')
const statusFilter = ref(null)
// Desk ships this checkbox unchecked: only unmarked students are listed until
// the user opts in to seeing completed ones.
const showCompleted = ref(false)
const selected = reactive(new Set())

const lateEntryReasons = ref([])
const lateModal = reactive({ open: false, student: null, reason: '', bulk: false, saving: false, error: '' })
const holidayModal = reactive({
  open: false,
  date: '',
  holiday_type: '',
  reason: '',
  scope: 'Entire School',
  standard: '',
  batch: '',
  saving: false,
  error: '',
})
const birthdayModalOpen = ref(false)

const standardsResource = createResource({ url: 'frappe.client.get_list' })
const batchesResource = createResource({ url: 'frappe.client.get_list' })
const lateEntryReasonsResource = createResource({ url: 'frappe.client.get_list' })
const studentsResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.get_attendance_students',
})
const saveAttendanceResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.save_student_attendance',
})
const saveBulkResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.save_bulk_attendance',
})
const assignHolidayResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.assign_holiday',
})

const birthdayStudents = computed(() => students.value.filter((s) => s.is_birthday))
const birthdayCount = computed(() => birthdayStudents.value.length)

const kpis = computed(() => [
  { key: 'total', filter: 'Total', label: 'Total Students', icon: 'fa-users', value: students.value.length, title: 'Show all students' },
  { key: 'present', filter: 'Present', label: 'Present', icon: 'fa-check-circle', value: summary.present, title: 'Show present students' },
  { key: 'absent', filter: 'Absent', label: 'Absent', icon: 'fa-times-circle', value: summary.absent, title: 'Show absent students' },
  { key: 'late', filter: 'Late', label: 'Late', icon: 'fa-clock-o', value: summary.late, title: 'Show late students' },
  { key: 'pending', filter: 'Pending', label: 'Pending', icon: 'fa-hourglass-half', value: summary.pending, title: 'Show pending students' },
])

// Mirrors the desk's student_visible_for_status(): an explicit KPI filter wins,
// otherwise "Show Completed" decides whether marked students are listed.
function visibleForStatus(status) {
  if (statusFilter.value === 'Pending') return !status
  if (statusFilter.value === 'Total') return true
  if (statusFilter.value) return status === statusFilter.value
  return showCompleted.value ? true : !status
}

const statusFiltered = computed(() => students.value.filter((s) => visibleForStatus(s.today_status)))

const visibleStudents = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return statusFiltered.value
  return statusFiltered.value.filter(
    (s) => s.student_id.toLowerCase().includes(q) || (s.student_name || '').toLowerCase().includes(q)
  )
})

const emptyState = computed(() => {
  if (!standard.value || !batch.value) {
    return {
      icon: 'fa-graduation-cap',
      title: 'Select Standard & Batch',
      text: 'Choose a Standard and Batch above to load students and start marking attendance.',
    }
  }
  if (students.value.length === 0) {
    return {
      icon: 'fa-graduation-cap',
      title: 'No Students Found',
      text: 'No active students found for this Standard and Batch on the selected date.',
    }
  }
  if (visibleStudents.value.length === 0) {
    if (statusFilter.value) {
      return {
        icon: 'fa-info-circle',
        title: `No ${statusFilter.value} Students`,
        text: `No students match the "${statusFilter.value}" filter for this selection.`,
      }
    }
    return {
      icon: 'fa-check-circle',
      title: 'All Done!',
      text: 'Awesome! All attendance has been marked for this date.',
      cls: 'is-success',
    }
  }
  return null
})

const allVisibleSelected = computed(
  () => visibleStudents.value.length > 0 && visibleStudents.value.every((s) => selected.has(s.student_id))
)
const someVisibleSelected = computed(
  () => !allVisibleSelected.value && visibleStudents.value.some((s) => selected.has(s.student_id))
)

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function toggleFilter(key) {
  statusFilter.value = statusFilter.value === key ? null : key
}

function toggleSelect(id) {
  if (selected.has(id)) selected.delete(id)
  else selected.add(id)
}

function toggleSelectAll(checked) {
  visibleStudents.value.forEach((s) => {
    if (checked) selected.add(s.student_id)
    else selected.delete(s.student_id)
  })
}

const isFutureDate = computed(() => date.value > serverToday.value)
const canStepForward = computed(() => date.value < serverToday.value)

function stepDate(delta) {
  const next = addDays(date.value, delta)
  // Attendance cannot be marked ahead of the site's today
  if (next > serverToday.value) return
  date.value = next
}

function showBirthdays() {
  birthdayModalOpen.value = true
}

async function loadStandards() {
  standards.value =
    (await standardsResource.submit({ doctype: 'Standard', fields: ['name'], limit_page_length: 0 })) || []
}
async function loadBatches() {
  batches.value =
    (await batchesResource.submit({ doctype: 'Batch', fields: ['name'], limit_page_length: 0 })) || []
}
async function loadLateEntryReasons() {
  lateEntryReasons.value =
    (await lateEntryReasonsResource.submit({
      doctype: 'Late Entry Reason',
      fields: ['name'],
      limit_page_length: 0,
    })) || []
}

async function loadStudents() {
  if (!standard.value || !batch.value || !date.value) {
    students.value = []
    holiday.value = null
    return
  }
  loading.value = true
  selected.clear()
  statusFilter.value = null
  try {
    const res = await studentsResource.submit({
      standard: standard.value,
      batch: batch.value,
      gender: gender.value || undefined,
      attendance_date: date.value,
    })
    holiday.value = res.holiday || null
    students.value = res.students || []
    Object.assign(summary, res.summary || { present: 0, absent: 0, late: 0, pending: 0 })
  } finally {
    loading.value = false
  }
}

function recomputeSummary() {
  const s = { present: 0, absent: 0, late: 0, pending: 0 }
  students.value.forEach((st) => {
    if (st.today_status === 'Present') s.present++
    else if (st.today_status === 'Absent') s.absent++
    else if (st.today_status === 'Late') s.late++
    else s.pending++
  })
  Object.assign(summary, s)
}

function onStatusClick(student, status) {
  if (student.has_late_permission && status !== 'Late') return
  if (savingStudent.value === student.student_id) return
  if (student.today_status === status) return
  if (isFutureDate.value) {
    saveError.value = 'Cannot mark attendance for future dates.'
    return
  }
  if (status === 'Late') {
    lateModal.open = true
    lateModal.bulk = false
    lateModal.student = student
    lateModal.reason = ''
    lateModal.error = ''
    return
  }
  applyAttendance(student, status).catch((e) => {
    saveError.value = e?.messages?.[0] || e?.message || 'Failed to save attendance'
    // re-render so the hidden radio snaps back to the stored status
    students.value = [...students.value]
  })
}

async function applyAttendance(student, status, lateReason) {
  saveError.value = ''
  savingStudent.value = student.student_id
  try {
    const res = await saveAttendanceResource.submit({
      student: student.student_id,
      attendance_date: date.value,
      status,
      late_reason: lateReason || undefined,
    })
    student.today_status = status
    if (status === 'Late' && lateReason) student.late_reason = lateReason
    if (res) {
      student.monthly_absent = res.monthly_absent
      student.monthly_late = res.monthly_late
    }
    recomputeSummary()
  } finally {
    savingStudent.value = null
  }
}

function closeLateModal() {
  lateModal.open = false
  lateModal.student = null
  lateModal.reason = ''
  lateModal.error = ''
}

async function confirmLate() {
  lateModal.saving = true
  lateModal.error = ''
  try {
    if (lateModal.bulk) {
      await saveBulkResource.submit({
        students: JSON.stringify(Array.from(selected)),
        standard: standard.value,
        batch: batch.value,
        attendance_date: date.value,
        status: 'Late',
        late_reason: lateModal.reason,
      })
      students.value.forEach((s) => {
        if (selected.has(s.student_id)) s.today_status = 'Late'
      })
      selected.clear()
      recomputeSummary()
    } else if (lateModal.student) {
      await applyAttendance(lateModal.student, 'Late', lateModal.reason)
    }
    closeLateModal()
  } catch (e) {
    lateModal.error = e?.messages?.[0] || e?.message || 'Failed to save'
  } finally {
    lateModal.saving = false
  }
}

async function bulkMark(status) {
  if (selected.size === 0) return
  if (bulkSaving.value) return
  saveError.value = ''
  if (isFutureDate.value) {
    saveError.value = 'Cannot mark attendance for future dates.'
    return
  }
  if (status === 'Late') {
    lateModal.open = true
    lateModal.bulk = true
    lateModal.reason = ''
    lateModal.error = ''
    return
  }
  bulkSaving.value = true
  try {
    await saveBulkResource.submit({
      students: JSON.stringify(Array.from(selected)),
      standard: standard.value,
      batch: batch.value,
      attendance_date: date.value,
      status,
    })
    students.value.forEach((s) => {
      if (selected.has(s.student_id)) s.today_status = status
    })
    selected.clear()
    recomputeSummary()
  } catch (e) {
    saveError.value = e?.messages?.[0] || e?.message || 'Failed to save attendance'
  } finally {
    bulkSaving.value = false
  }
}

function openHolidayModal() {
  holidayModal.open = true
  holidayModal.date = date.value
  holidayModal.holiday_type = ''
  holidayModal.reason = ''
  holidayModal.scope = 'Entire School'
  holidayModal.standard = standard.value
  holidayModal.batch = batch.value
  holidayModal.error = ''
  holidayModal.saving = false
}

async function confirmHoliday() {
  holidayModal.error = ''
  if (!holidayModal.date || !holidayModal.holiday_type || !holidayModal.reason) {
    holidayModal.error = 'Date, Holiday Type and Reason are required.'
    return
  }
  if (holidayModal.scope !== 'Entire School' && !holidayModal.standard) {
    holidayModal.error = 'Standard is required for this scope.'
    return
  }
  if (holidayModal.scope === 'Standard + Batch' && !holidayModal.batch) {
    holidayModal.error = 'Batch is required for this scope.'
    return
  }
  holidayModal.saving = true
  try {
    await assignHolidayResource.submit({
      date: holidayModal.date,
      holiday_type: holidayModal.holiday_type,
      reason: holidayModal.reason,
      scope: holidayModal.scope,
      standard: holidayModal.scope !== 'Entire School' ? holidayModal.standard : undefined,
      batch: holidayModal.scope === 'Standard + Batch' ? holidayModal.batch : undefined,
    })
    holidayModal.open = false
    if (holidayModal.date === date.value) loadStudents()
  } catch (e) {
    holidayModal.error = e?.messages?.[0] || e?.message || 'Failed to assign holiday'
  } finally {
    holidayModal.saving = false
  }
}

onMounted(async () => {
  const t = await loadServerToday()
  // only override the provisional device date if the user hasn't moved it
  if (date.value !== t && date.value === formatDate(new Date())) date.value = t
  loadStandards()
  loadBatches()
  loadLateEntryReasons()
})

watch([standard, batch, gender, date], loadStudents)
// Selections must not survive a filter change that hides the rows.
watch([statusFilter, showCompleted, search], () => {
  const visible = new Set(visibleStudents.value.map((s) => s.student_id))
  ;[...selected].forEach((id) => {
    if (!visible.has(id)) selected.delete(id)
  })
})
</script>

<style>
/* ==========================================================================
   Ported from bb_academy/page/attendance_manager/attendance_manager.css so the
   PWA renders identically to the desk page. Kept class-for-class; only the
   Frappe-widget bits (custom-control switches, avatar frame) are re-expressed
   with plain elements, and modal/badge styles are added for markup the desk
   builds through frappe.ui.Dialog instead of static HTML.
   ========================================================================== */

.attendance-manager {
  --att-radius: var(--border-radius-md, 8px);
  --att-radius-sm: var(--border-radius, 6px);
  --att-gap: 14px;
  color: var(--text-color);
  padding: 14px;
}

.attendance-manager * {
  box-sizing: border-box;
}

.attendance-manager button {
  font-family: inherit;
}

/* ---- control panel ---- */
.attendance-manager .att-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 18px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--att-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 16px 18px;
  margin-bottom: var(--att-gap);
}

.attendance-manager .att-panel-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  flex: 1 1 320px;
}

.attendance-manager .att-field {
  min-width: 150px;
  flex: 1 1 150px;
}

.attendance-manager .att-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.attendance-manager .att-field label i {
  width: 14px;
  margin-right: 4px;
  color: var(--gray-600);
}

.attendance-manager .att-panel-date {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 0 0 auto;
}

.attendance-manager .att-date-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
}

.attendance-manager .att-date-label i {
  width: 14px;
  margin-right: 4px;
  color: var(--gray-600);
}

.attendance-manager .att-date-stepper {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--border-color);
  border-radius: var(--att-radius-sm);
  background: var(--control-bg, var(--gray-100));
  overflow: hidden;
}

.attendance-manager .att-date-nav-btn {
  border: none;
  background: transparent;
  color: var(--text-color);
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.attendance-manager .att-date-nav-btn:hover:not(:disabled) {
  background: var(--gray-200);
}

.attendance-manager .att-date-nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.attendance-manager .att-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--att-radius);
  padding: 10px 14px;
  font-size: 12.5px;
  font-weight: 500;
  margin-bottom: var(--att-gap);
}

.attendance-manager .att-alert-warn {
  background: var(--bg-yellow);
  border: 1px solid var(--yellow-300);
  color: var(--text-on-yellow);
}

.attendance-manager .att-alert-error {
  background: var(--bg-red);
  border: 1px solid var(--red-200);
  color: var(--text-on-red);
}

.attendance-manager .att-alert button {
  margin-left: auto;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
}
.attendance-manager .att-date-nav-btn:active {
  background: var(--gray-300);
}

.attendance-manager .att-date-input {
  border: none;
  background: var(--card-bg);
  border-left: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
  padding: 0 10px;
  height: 36px;
  font-weight: 600;
  font-size: 14px;
  color: var(--heading-color);
  min-width: 150px;
  text-align: center;
}

.attendance-manager .att-date-input:focus {
  outline: none;
  box-shadow: var(--highlight-shadow);
}

.attendance-manager .att-panel-actions {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.attendance-manager .att-holiday-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-muted);
  border-radius: var(--att-radius-sm);
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.attendance-manager .att-holiday-btn:hover {
  background: var(--bg-yellow);
  color: var(--text-on-yellow);
  border-color: var(--yellow-300, var(--border-color));
}

.attendance-manager #birthday-alert {
  margin-top: 10px;
  cursor: pointer;
  color: #d63384;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  border: 1px solid #fbcfe8;
  background: #fdf2f8;
  border-radius: 6px;
  padding: 6px 12px;
  transition: all 0.2s;
}

/* ---- KPI cards ---- */
.attendance-manager .att-kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: var(--att-gap);
}

.attendance-manager .att-kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--att-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 14px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.attendance-manager .att-kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.attendance-manager .att-kpi-card:focus-visible {
  outline: 2px solid var(--blue-500);
  outline-offset: 2px;
}

.attendance-manager .att-kpi-card.is-active {
  border-color: currentColor;
  box-shadow: var(--shadow-md);
}

.attendance-manager .att-kpi-icon {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border-radius: var(--att-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.attendance-manager .att-kpi-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.attendance-manager .att-kpi-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.attendance-manager .att-kpi-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.attendance-manager .att-kpi-total .att-kpi-icon { background: var(--bg-blue); color: var(--text-on-blue); }
.attendance-manager .att-kpi-total.is-active { color: var(--blue-600); }
.attendance-manager .att-kpi-present .att-kpi-icon { background: var(--bg-green); color: var(--text-on-green); }
.attendance-manager .att-kpi-present.is-active { color: var(--green-600); }
.attendance-manager .att-kpi-absent .att-kpi-icon { background: var(--bg-red); color: var(--text-on-red); }
.attendance-manager .att-kpi-absent.is-active { color: var(--red-600); }
.attendance-manager .att-kpi-late .att-kpi-icon { background: var(--bg-orange); color: var(--text-on-orange); }
.attendance-manager .att-kpi-late.is-active { color: var(--orange-600, var(--text-on-orange)); }
.attendance-manager .att-kpi-pending .att-kpi-icon { background: var(--bg-yellow); color: var(--text-on-yellow); }
.attendance-manager .att-kpi-pending.is-active { color: var(--yellow-700, var(--text-on-yellow)); }

/* ---- toolbar ---- */
.attendance-manager .att-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: var(--att-gap);
}

.attendance-manager .att-search-wrap {
  position: relative;
  flex: 1 1 280px;
  max-width: 360px;
}

.attendance-manager .att-search-wrap i {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 13px;
}

.attendance-manager .att-search-input {
  width: 100%;
  height: 38px;
  border: 1px solid var(--border-color);
  border-radius: var(--att-radius-sm);
  background: var(--card-bg);
  padding: 0 12px 0 34px;
  font-size: 13px;
  color: var(--text-color);
}

.attendance-manager .att-search-input:focus {
  outline: none;
  border-color: var(--blue-400, var(--blue-500));
  box-shadow: var(--highlight-shadow);
}

.attendance-manager .att-toolbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-left: auto;
  flex-wrap: wrap;
}

.attendance-manager .att-filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-blue);
  color: var(--text-on-blue);
  border-radius: var(--border-radius-full, 999px);
  padding: 5px 6px 5px 12px;
  font-size: 12px;
  font-weight: 500;
}

.attendance-manager .att-filter-chip button {
  border: none;
  background: rgba(0, 0, 0, 0.08);
  color: inherit;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  cursor: pointer;
}

.attendance-manager .att-switch {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.attendance-manager .att-switch label {
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  margin: 0;
}

.attendance-manager .att-switch input[type='checkbox'] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--blue-500);
}

/* ---- bulk bar ---- */
.attendance-manager .att-bulk-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: var(--bg-blue);
  border: 1px solid var(--blue-200, var(--border-color));
  border-radius: var(--att-radius);
  padding: 10px 16px;
  margin-bottom: var(--att-gap);
  animation: att-bulk-in 0.15s ease;
}

@keyframes att-bulk-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.attendance-manager .att-bulk-count {
  font-weight: 600;
  color: var(--text-on-blue);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.attendance-manager .att-bulk-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.attendance-manager .att-bulk-btn {
  border: 1px solid transparent;
  border-radius: var(--att-radius-sm);
  padding: 7px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--card-bg);
  color: var(--text-color);
  border-color: var(--border-color);
  transition: background-color 0.15s ease, color 0.15s ease;
}

.attendance-manager .att-bulk-present { color: var(--green-600); border-color: var(--green-200, var(--border-color)); }
.attendance-manager .att-bulk-present:hover { background: var(--green-600); color: #fff; }
.attendance-manager .att-bulk-absent { color: var(--red-600); border-color: var(--red-200, var(--border-color)); }
.attendance-manager .att-bulk-absent:hover { background: var(--red-600); color: #fff; }
.attendance-manager .att-bulk-late { color: var(--orange-600, var(--text-on-orange)); border-color: var(--orange-200, var(--border-color)); }
.attendance-manager .att-bulk-late:hover { background: var(--orange-500); color: #fff; }

.attendance-manager .att-bulk-clear {
  background: transparent;
  border-color: transparent;
  color: var(--text-muted);
}
.attendance-manager .att-bulk-clear:hover {
  color: var(--text-color);
  text-decoration: underline;
}

/* ---- holiday card ---- */
.attendance-manager .att-holiday-card {
  display: flex;
  gap: 16px;
  background: var(--alert-bg-info, var(--bg-blue));
  border: 1px solid var(--blue-200, var(--border-color));
  border-radius: var(--att-radius);
  padding: 20px;
  margin-bottom: var(--att-gap);
}

.attendance-manager .att-holiday-icon {
  flex: 0 0 auto;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--bg-color);
  color: var(--alert-text-info);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.attendance-manager .att-holiday-content h4 {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--heading-color);
}

.attendance-manager .att-holiday-content p {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--text-color);
}

.attendance-manager .att-holiday-key {
  display: inline-block;
  min-width: 60px;
  font-weight: 600;
  color: var(--text-muted);
}

.attendance-manager .att-holiday-note {
  margin-top: 8px !important;
  color: var(--text-muted) !important;
  font-style: italic;
}

/* ---- empty / skeleton ---- */
.attendance-manager .att-empty-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--text-muted);
}

.attendance-manager .att-empty-icon {
  font-size: 34px;
  color: var(--gray-400);
  margin-bottom: 12px;
}

.attendance-manager .att-empty-state h4 {
  color: var(--heading-color);
  font-size: 16px;
  margin-bottom: 6px;
}

.attendance-manager .att-empty-state p {
  margin: 0 auto;
  max-width: 360px;
  font-size: 13px;
}

.attendance-manager .att-empty-state.is-success .att-empty-icon { color: var(--green-500); }
.attendance-manager .att-empty-state.is-success h4 { color: var(--green-600); }

.attendance-manager .att-skeleton-row td { padding: 16px !important; }

.attendance-manager .att-skeleton-bar {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: att-skeleton-shine 1.4s ease infinite;
}

@keyframes att-skeleton-shine {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* ---- table ---- */
.attendance-manager .att-table-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--att-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  overflow: hidden;
}

.attendance-manager .att-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0;
}

.attendance-manager .att-table thead th {
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

.attendance-manager .att-col-select { width: 40px; text-align: center !important; }
.attendance-manager .att-col-actions { width: 320px; }

.attendance-manager .att-row-select {
  width: 17px;
  height: 17px;
  cursor: pointer;
  accent-color: var(--blue-500);
}

.attendance-manager .att-table tbody tr.att-student-row {
  border-left: 3px solid var(--gray-300);
  transition: background-color 0.12s ease, border-left-color 0.12s ease;
}

.attendance-manager .att-table tbody tr.att-student-row:hover {
  background: var(--fg-hover-color, var(--gray-50));
}

.attendance-manager .att-table tbody tr.att-student-row[data-current-status='Present'] { border-left-color: var(--green-500); }
.attendance-manager .att-table tbody tr.att-student-row[data-current-status='Absent'] { border-left-color: var(--red-500); }
.attendance-manager .att-table tbody tr.att-student-row[data-current-status='Late'] { border-left-color: var(--orange-500); }

.attendance-manager .att-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.attendance-manager .att-table tbody tr.att-student-row:last-child td { border-bottom: none; }

.attendance-manager .att-td-select { text-align: center; }

.attendance-manager .att-student-id {
  font-weight: 700;
  font-size: 14px;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.attendance-manager .att-student-id.att-new-joiner {
  color: var(--purple-600, #9333ea) !important;
}

.attendance-manager .att-student-stats {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.attendance-manager .att-stat-chip {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-100));
  border-radius: 4px;
  padding: 1px 6px;
  display: inline-flex;
  gap: 3px;
}

.attendance-manager .att-stat-chip b { font-weight: 700; }
.attendance-manager .att-stat-absent b { color: var(--red-600); }
.attendance-manager .att-stat-late b { color: var(--orange-600, var(--text-on-orange)); }

.attendance-manager .att-student-profile {
  display: flex;
  align-items: center;
  gap: 10px;
}

.attendance-manager .att-student-name-wrap {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
}

.attendance-manager .att-student-name {
  font-size: 13.5px;
  color: var(--text-color);
}

.attendance-manager .att-gender-icon {
  margin-left: 6px;
  font-size: 12px;
  color: var(--gray-500);
}
.attendance-manager .att-gender-icon-female { color: #ff69b4; }
.attendance-manager .att-gender-icon-male { color: #2196f3; }

.attendance-manager .att-birthday-icon { color: #d63384; margin-left: 6px; }

.attendance-manager .att-badge-new {
  background-color: #ff9800;
  color: white;
  font-size: 10px;
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 12px;
  font-weight: bold;
}

.attendance-manager .att-badge-temp {
  background-color: #9c27b0;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 12px;
  font-weight: bold;
}

/* Desk renders frappe.get_avatar('avatar-large') and squares it off. */
.attendance-manager .att-avatar {
  border-radius: 0 !important;
  width: 78px !important;
  height: 78px !important;
  min-width: 78px;
  object-fit: cover;
  margin-left: auto;
}

.attendance-manager .att-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-200);
  color: var(--gray-600);
  font-weight: 700;
  font-size: 20px;
}

.attendance-manager .att-prev-label { display: none; }

.attendance-manager .att-prev-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--border-radius-full, 999px);
  background: var(--bg-gray);
  color: var(--text-on-gray);
}

.attendance-manager .att-prev-badge[data-status='Present'] { background: var(--bg-green); color: var(--text-on-green); }
.attendance-manager .att-prev-badge[data-status='Absent'] { background: var(--bg-red); color: var(--text-on-red); }
.attendance-manager .att-prev-badge[data-status='Late'] { background: var(--bg-orange); color: var(--text-on-orange); }

.attendance-manager .att-status-group { display: flex; gap: 6px; }

.attendance-manager .att-status-btn {
  position: relative;
  flex: 1 1 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 0;
  padding: 7px 8px;
  font-size: 12.5px;
  font-weight: 600;
  text-align: center;
  border: 1px solid var(--border-color);
  border-radius: var(--att-radius-sm);
  background: var(--card-bg);
  color: var(--text-muted);
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease, border-color 0.12s ease;
}

.attendance-manager .att-status-btn input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.attendance-manager .att-status-btn:hover { border-color: var(--gray-400); }

.attendance-manager .att-status-btn.is-saving {
  opacity: 0.6;
  pointer-events: none;
}

.attendance-manager .att-status-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.attendance-manager .att-status-present { background: var(--bg-green); border-color: var(--green-200); color: var(--text-on-green); }
.attendance-manager .att-status-present:hover { border-color: var(--green-400); }
.attendance-manager .att-status-absent { background: var(--bg-red); border-color: var(--red-200); color: var(--text-on-red); }
.attendance-manager .att-status-absent:hover { border-color: var(--red-400); }
.attendance-manager .att-status-late { background: var(--bg-orange); border-color: var(--orange-200); color: var(--text-on-orange); }
.attendance-manager .att-status-late:hover { border-color: var(--orange-400); }

.attendance-manager .att-status-present.active { background: var(--green-600); border-color: var(--green-600); color: #fff; }
.attendance-manager .att-status-absent.active { background: var(--red-600); border-color: var(--red-600); color: #fff; }
.attendance-manager .att-status-late.active { background: var(--orange-500); border-color: var(--orange-500); color: #fff; }

.attendance-manager .att-lp-msg {
  font-size: 11px;
  color: #856404;
  background: #fff3cd;
  padding: 2px 5px;
  border-radius: 3px;
  margin-top: 5px;
}

/* ---- modals (desk uses frappe.ui.Dialog) ---- */
.attendance-manager .att-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.attendance-manager .att-modal {
  background: var(--card-bg);
  border-radius: var(--att-radius);
  box-shadow: var(--shadow-md);
  padding: 20px;
  width: 100%;
  max-width: 380px;
  max-height: 85vh;
  overflow-y: auto;
}

.attendance-manager .att-modal h3 {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: var(--heading-color);
}

.attendance-manager .att-modal-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin: 12px 0 4px;
}

.attendance-manager .att-req { color: var(--red-600); }

.attendance-manager .att-textarea {
  height: auto;
  padding: 8px 10px;
  resize: vertical;
}

.attendance-manager .att-modal-warn { font-size: 11px; color: var(--text-on-yellow); margin-top: 6px; }
.attendance-manager .att-modal-error { font-size: 12px; color: var(--red-600); margin-top: 8px; }

.attendance-manager .att-modal-actions {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}

.attendance-manager .att-btn {
  flex: 1;
  padding: 9px 14px;
  border-radius: var(--att-radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.attendance-manager .att-btn-primary { background: var(--blue-600); border-color: var(--blue-600); color: #fff; }
.attendance-manager .att-btn-primary:hover { background: var(--blue-700, var(--blue-600)); }
.attendance-manager .att-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.attendance-manager .att-btn-secondary { background: var(--card-bg); border-color: var(--border-color); color: var(--text-muted); }

.attendance-manager .att-birthday-list { list-style: none; margin: 0; padding: 0; }
.attendance-manager .att-birthday-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.attendance-manager .att-birthday-list li span { color: var(--text-muted); font-size: 11px; margin-left: 6px; }

/* ---- sticky header on tall lists (desktop / tablet only) ---- */
@media (min-width: 768px) {
  .attendance-manager .att-table-scroll {
    max-height: 68vh;
    overflow-y: auto;
  }
  .attendance-manager .att-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
  }
}

/* ---- tablet ---- */
@media (max-width: 992px) {
  .attendance-manager .att-kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .attendance-manager .att-panel-actions { margin-left: 0; }
}

/* ---- mobile: panel stacking + table -> card ---- */
@media (max-width: 767px) {
  .attendance-manager { padding: 10px; }

  .attendance-manager .att-panel {
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }

  .attendance-manager .att-panel-filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    flex: none;
  }

  .attendance-manager .att-field { min-width: 0; flex: none; }
  .attendance-manager .att-field-gender { grid-column: 1 / -1; }
  .attendance-manager .att-panel-date { width: 100%; }
  .attendance-manager .att-date-stepper { width: 100%; }
  .attendance-manager .att-date-input { flex: 1; min-width: 0; }
  .attendance-manager .att-panel-actions { width: 100%; margin-left: 0; }
  .attendance-manager .att-holiday-btn { width: 100%; justify-content: center; }
  .attendance-manager #birthday-alert { width: 100%; }

  .attendance-manager .att-kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .attendance-manager .att-kpi-total { grid-column: span 2; }

  .attendance-manager .att-toolbar { flex-direction: column; align-items: stretch; }
  .attendance-manager .att-search-wrap { max-width: none; flex: none; }
  .attendance-manager .att-toolbar-right { margin-left: 0; justify-content: space-between; }

  .attendance-manager .att-bulk-bar { flex-direction: column; align-items: stretch; }
  .attendance-manager .att-bulk-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .attendance-manager .att-bulk-clear { grid-column: span 2; }

  .attendance-manager .att-holiday-card { flex-direction: column; text-align: left; }

  .attendance-manager .att-table-card {
    background: transparent;
    border: none;
    box-shadow: none;
    overflow: visible;
  }

  .attendance-manager .att-table-scroll { overflow-x: visible; }
  .attendance-manager .att-table thead { display: none; }
  .attendance-manager .att-table,
  .attendance-manager .att-table tbody { display: block; width: 100%; }
  .attendance-manager .att-table tbody tr.att-placeholder-row,
  .attendance-manager .att-table tbody tr.att-skeleton-row {
    display: block;
    background: var(--card-bg);
    border-radius: var(--att-radius);
    margin-bottom: 12px;
  }

  .attendance-manager .att-table tbody tr.att-student-row {
    position: relative;
    display: grid;
    grid-template-columns: 1fr auto;
    grid-template-areas:
      'name   select'
      'id     id'
      'prev   prev'
      'actions actions';
    row-gap: 10px;
    column-gap: 10px;
    border-left: 4px solid var(--gray-300);
    border-bottom: none;
    border-radius: var(--att-radius);
    padding: 14px;
    margin: 0 0 12px;
    background: var(--card-bg);
    box-shadow: var(--card-shadow, var(--shadow-sm));
  }

  .attendance-manager .att-table tbody tr.att-student-row td {
    display: block;
    width: auto;
    padding: 0;
    border-bottom: none;
  }

  .attendance-manager .att-td-select { grid-area: select; align-self: start; text-align: right; }
  .attendance-manager .att-td-id { grid-area: id; }

  .attendance-manager .att-td-name {
    grid-area: name;
    padding-top: 10px !important;
    border-top: 1px solid var(--border-color);
  }

  .attendance-manager .att-td-prev {
    grid-area: prev;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .attendance-manager .att-prev-label {
    display: inline;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .attendance-manager .att-td-actions { grid-area: actions; }
  .attendance-manager .att-status-group { gap: 8px; }

  .attendance-manager .att-status-btn {
    flex-direction: column;
    gap: 4px;
    padding: 10px 4px;
    min-height: 52px;
    font-size: 11.5px;
  }

  .attendance-manager .att-status-btn i { font-size: 15px; }

  /* desk pins the avatar to the card's right edge on mobile */
  .attendance-manager .att-avatar {
    position: absolute !important;
    right: 5px !important;
    bottom: 46px !important;
    margin: 0 !important;
    top: auto !important;
    left: auto !important;
    z-index: 2;
  }
}

@media (max-width: 480px) {
  .attendance-manager .att-kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .attendance-manager .att-kpi-value { font-size: 19px; }
  .attendance-manager .att-row-select { width: 22px; height: 22px; }
}

@media (max-width: 360px) {
  .attendance-manager .att-status-btn span { display: none; }
  .attendance-manager .att-status-btn i { font-size: 17px; }
}

@media (min-width: 1200px) {
  .attendance-manager .att-kpi-value { font-size: 24px; }
}
</style>
