<template>
  <div class="lp-manager">
    <!-- Control panel -->
    <div class="lp-panel">
      <div class="lp-panel-filters">
        <div class="lp-field lp-field-type">
          <label><i class="fa fa-tag"></i> Type</label>
          <select class="form-control" v-model="type">
            <option value="Late Permission">Late Permission</option>
            <option value="Early Out">Early Out</option>
          </select>
        </div>
        <div class="lp-field lp-field-standard">
          <label><i class="fa fa-graduation-cap"></i> Standard</label>
          <select class="form-control" v-model="standard">
            <option value="">Select Standard</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="lp-field lp-field-batch">
          <label><i class="fa fa-users"></i> Batch</label>
          <select class="form-control" v-model="batch" :disabled="!standard">
            <option value="">Select Batch</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
        <div class="lp-field lp-field-gender">
          <label><i class="fa fa-venus-mars"></i> Gender</label>
          <select class="form-control" v-model="gender">
            <option value="">All</option>
            <option value="Boys">Boys</option>
            <option value="Girls">Girls</option>
          </select>
        </div>
      </div>

      <div class="lp-panel-date">
        <span class="lp-date-label"><i class="fa fa-calendar"></i> Date</span>
        <div class="lp-date-stepper">
          <button type="button" class="lp-date-nav-btn" title="Previous Day" @click="stepDate(-1)">
            <i class="fa fa-arrow-left"></i>
          </button>
          <input type="date" class="lp-date-input" v-model="date" />
          <button type="button" class="lp-date-nav-btn" title="Next Day" @click="stepDate(1)">
            <i class="fa fa-arrow-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="lp-toolbar">
      <div class="lp-search-wrap">
        <i class="fa fa-search"></i>
        <input
          type="text"
          class="lp-search-input"
          placeholder="Search student name or ID"
          v-model="search"
        />
      </div>
    </div>

    <!-- Table -->
    <div class="lp-table-card">
      <div class="lp-table-scroll">
        <table class="lp-table">
          <thead>
            <tr>
              <th class="lp-col-id">Student ID</th>
              <th class="lp-col-name">Student Name</th>
              <th class="lp-col-att-status">Attendance</th>
              <th class="lp-col-status">Status</th>
              <th class="lp-col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="i in 3" :key="`sk${i}`" class="lp-skeleton-row">
                <td colspan="5">
                  <div class="lp-skeleton-bar" style="width: 40%; margin-bottom: 8px"></div>
                  <div class="lp-skeleton-bar" style="width: 70%"></div>
                </td>
              </tr>
            </template>

            <tr v-else-if="emptyState" class="lp-placeholder-row">
              <td colspan="5">
                <div class="lp-empty-state">
                  <div class="lp-empty-icon"><i class="fa" :class="emptyState.icon"></i></div>
                  <h4>{{ emptyState.title }}</h4>
                  <p>{{ emptyState.text }}</p>
                </div>
              </td>
            </tr>

            <tr
              v-for="s in (loading || emptyState ? [] : filteredStudents)"
              :key="s.name"
              class="lp-student-row"
              :data-current-status="s.attendance_status || ''"
            >
              <td class="lp-td-id">
                <div class="lp-student-id">{{ s.name }}</div>
              </td>
              <td class="lp-td-name">
                <div class="lp-student-profile">
                  <div class="lp-student-name-wrap">
                    <span class="lp-student-name">{{ s.student_name }}</span>
                    <i
                      v-if="s.gender"
                      class="fa lp-gender-icon"
                      :class="[
                        s.gender === 'Girls' ? 'fa-female' : 'fa-male',
                        s.gender === 'Girls' ? 'lp-gender-icon-female' : 'lp-gender-icon-male',
                      ]"
                      :title="s.gender"
                    ></i>
                  </div>
                </div>
              </td>
              <td class="lp-td-att-status">
                <span class="lp-badge" :class="attendanceBadgeClass(s.attendance_status)">
                  {{ s.attendance_status || '—' }}
                </span>
              </td>
              <td class="lp-td-status">
                <template v-if="type === 'Early Out'">
                  <span v-if="s.has_permission" class="lp-badge lp-badge-info">
                    Early Out Granted{{ earlyOutInfo(s) }}
                  </span>
                  <span v-else class="lp-badge lp-badge-secondary">None</span>
                </template>
                <template v-else>
                  <span v-if="s.has_permission" class="lp-badge lp-badge-success">
                    Permission Granted ({{ s.late_reason }})
                  </span>
                  <span v-if="s.has_permission && s.time" class="lp-time-chip">
                    <i class="fa fa-clock-o"></i> {{ s.time }}
                  </span>
                  <span v-if="!s.has_permission" class="lp-badge lp-badge-secondary">None</span>
                  <label v-if="s.has_permission" class="lp-parents-toggle">
                    <input
                      type="checkbox"
                      :checked="!!s.parents_informed"
                      :disabled="savingParents === s.name"
                      @change="toggleParentsInformed(s, $event.target.checked)"
                    />
                    <span>Parents informed</span>
                    <span v-if="savingParents === s.name" class="lp-saving">saving…</span>
                  </label>
                </template>
              </td>
              <td class="lp-td-actions">
                <button
                  v-if="!s.has_permission"
                  class="lp-btn lp-btn-primary"
                  :disabled="!canAct(s)"
                  :title="canAct(s) ? '' : 'Attendance must be marked first'"
                  @click="openGrantModal(s)"
                >
                  {{ type === 'Early Out' ? 'Grant Early Out' : 'Grant Permission' }}
                </button>
                <template v-else>
                  <button class="lp-btn lp-btn-default" @click="openGrantModal(s)">Edit</button>
                  <button class="lp-btn lp-btn-danger" @click="revoke(s)">Revoke</button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Grant / edit modal -->
    <div v-if="modal.open" class="lp-modal-backdrop" @click.self="modal.open = false">
      <div class="lp-modal">
        <h3>
          {{ modal.student?.has_permission ? 'Update' : 'Grant' }} {{ type }} —
          {{ modal.student?.student_name }}
        </h3>

        <template v-if="type === 'Late Permission'">
          <label class="lp-modal-label">Late Reason <span class="lp-req">*</span></label>
          <select class="form-control" v-model="modal.reason">
            <option value="">Select a reason</option>
            <option v-for="r in lateEntryReasons" :key="r.name" :value="r.name">{{ r.name }}</option>
          </select>
          <p v-if="!lateEntryReasons.length" class="lp-modal-warn">
            No "Late Entry Reason" records exist yet — create them in the desk first.
          </p>

          <label class="lp-modal-label">
            Time <span class="lp-optional">(optional)</span>
          </label>
          <div class="lp-time-row">
            <input type="time" class="form-control" v-model="modal.time" />
            <button type="button" class="lp-now-btn" title="Use current time" @click="setTimeNow">
              Now
            </button>
            <button
              v-if="modal.time"
              type="button"
              class="lp-now-btn lp-clear-btn"
              title="Clear time"
              @click="modal.time = ''"
            >
              Clear
            </button>
          </div>

          <label class="lp-checkbox">
            <input type="checkbox" v-model="modal.parentsInformed" />
            <span>Parents informed</span>
          </label>
        </template>
        <template v-else>
          <label class="lp-modal-label">Early Out Time <span class="lp-req">*</span></label>
          <input type="time" class="form-control" v-model="modal.time" />
          <label class="lp-modal-label">Early Out Reason <span class="lp-req">*</span></label>
          <select class="form-control" v-model="modal.reason">
            <option value="">Select a reason</option>
            <option v-for="r in earlyExitReasons" :key="r.name" :value="r.name">{{ r.name }}</option>
          </select>
          <p v-if="!earlyExitReasons.length" class="lp-modal-warn">
            No "Early Exit Reason" records exist yet — create them in the desk first.
          </p>
        </template>

        <p v-if="modal.error" class="lp-modal-error">{{ modal.error }}</p>

        <div class="lp-modal-actions">
          <button class="lp-btn-lg lp-btn-secondary" @click="modal.open = false">Cancel</button>
          <button
            class="lp-btn-lg lp-btn-primary-lg"
            :disabled="!canGrant || modal.saving"
            @click="confirmGrant"
          >
            {{ modal.saving ? 'Saving…' : modal.student?.has_permission ? 'Update' : 'Grant' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday, formatDate, addDays } from '@/data/serverDate'


const standards = ref([])
const batches = ref([])
const standard = ref('')
const batch = ref('')
const date = ref(serverToday.value)
const type = ref('Late Permission')
const gender = ref('')
const search = ref('')
const students = ref([])
const loading = ref(false)
const lateEntryReasons = ref([])
const earlyExitReasons = ref([])
const savingParents = ref(null)

const modal = reactive({
  open: false,
  student: null,
  reason: '',
  time: '',
  // Late Permission doctype defaults parents_informed to 1
  parentsInformed: true,
  saving: false,
  error: '',
})

const filteredStudents = computed(() => {
  if (!search.value.trim()) return students.value
  const q = search.value.trim().toLowerCase()
  return students.value.filter(
    (s) => (s.student_name || '').toLowerCase().includes(q) || (s.name || '').toLowerCase().includes(q)
  )
})

const canGrant = computed(() => {
  if (type.value === 'Late Permission') return !!modal.reason
  return !!modal.time && !!modal.reason
})

const emptyState = computed(() => {
  if (!standard.value || !batch.value) {
    return {
      icon: 'fa-graduation-cap',
      title: 'Select Standard & Batch',
      text: 'Choose a Standard and Batch above to load students.',
    }
  }
  if (filteredStudents.value.length === 0) {
    return {
      icon: 'fa-info-circle',
      title: 'No students found',
      text:
        type.value === 'Early Out'
          ? 'No present or late students found with attendance for this Standard and Batch.'
          : 'No active students found for this Standard and Batch.',
    }
  }
  return null
})

const standardsResource = createResource({ url: 'frappe.client.get_list' })
const batchesResource = createResource({ url: 'frappe.client.get_list' })
const lateEntryReasonsResource = createResource({ url: 'frappe.client.get_list' })
const earlyExitReasonsResource = createResource({ url: 'frappe.client.get_list' })
const listResource = createResource({
  url: 'bb_tution_management.bb_academy.late_permission.get_students_for_late_permission',
})
const grantLateResource = createResource({
  url: 'bb_tution_management.bb_academy.late_permission.grant_late_permission',
})
const revokeLateResource = createResource({
  url: 'bb_tution_management.bb_academy.late_permission.revoke_late_permission',
})
const grantEarlyOutResource = createResource({
  url: 'bb_tution_management.bb_academy.late_permission.grant_early_out',
})
const revokeEarlyOutResource = createResource({
  url: 'bb_tution_management.bb_academy.late_permission.revoke_early_out',
})
const setParentsInformedResource = createResource({
  url: 'bb_tution_management.bb_academy.late_permission.set_parents_informed',
})

function nowTime() {
  return new Date().toTimeString().slice(0, 5)
}

function setTimeNow() {
  modal.time = nowTime()
}

function attendanceBadgeClass(status) {
  if (status === 'Present') return 'lp-badge-success'
  if (status === 'Late') return 'lp-badge-warning'
  if (status === 'Absent') return 'lp-badge-danger'
  if (status === 'Early Outs') return 'lp-badge-info'
  return 'lp-badge-secondary'
}

function earlyOutInfo(s) {
  const parts = []
  if (s.early_out_time) parts.push(s.early_out_time)
  if (s.early_out_reason) parts.push(s.early_out_reason)
  return parts.length ? ` (${parts.join(' - ')})` : ''
}

// Late Permission can be granted before attendance is marked; Early Out edits
// an existing attendance record, so it needs one to exist.
function canAct(s) {
  return type.value === 'Late Permission' ? true : !!s.attendance_status
}

function stepDate(delta) {
  date.value = addDays(date.value, delta)
}

async function loadFilters() {
  standards.value =
    (await standardsResource.submit({ doctype: 'Standard', fields: ['name'], limit_page_length: 0 })) || []
  batches.value =
    (await batchesResource.submit({ doctype: 'Batch', fields: ['name'], limit_page_length: 0 })) || []
  lateEntryReasons.value =
    (await lateEntryReasonsResource.submit({
      doctype: 'Late Entry Reason',
      fields: ['name'],
      limit_page_length: 0,
    })) || []
  earlyExitReasons.value =
    (await earlyExitReasonsResource.submit({
      doctype: 'Early Exit Reason',
      fields: ['name'],
      limit_page_length: 0,
    })) || []
}

async function loadStudents() {
  if (!standard.value || !batch.value) {
    students.value = []
    return
  }
  loading.value = true
  try {
    const res = await listResource.submit({
      standard: standard.value,
      batch: batch.value,
      date: date.value,
      gender: gender.value || undefined,
      permission_type: type.value,
    })
    students.value = res?.students || []
  } finally {
    loading.value = false
  }
}

function openGrantModal(student) {
  modal.open = true
  modal.student = student
  modal.reason = student.has_permission
    ? student.late_reason || student.early_out_reason || ''
    : ''
  modal.time =
    type.value === 'Early Out'
      ? student.early_out_time || nowTime()
      // Late Permission time is optional: prefill only what was already stored
      : student.time || ''
  modal.parentsInformed = student.has_permission ? !!student.parents_informed : true
  modal.error = ''
  modal.saving = false
}

async function confirmGrant() {
  const s = modal.student
  modal.error = ''
  modal.saving = true
  try {
    if (type.value === 'Late Permission') {
      await grantLateResource.submit({
        student: s.name,
        date: date.value,
        late_reason: modal.reason,
        parents_informed: modal.parentsInformed ? 1 : 0,
        // empty string clears a previously recorded time
        time: modal.time || '',
      })
    } else {
      await grantEarlyOutResource.submit({
        student: s.name,
        date: date.value,
        early_out_time: modal.time,
        early_out_reason: modal.reason,
      })
    }
    modal.open = false
    await loadStudents()
  } catch (e) {
    modal.error = e?.messages?.[0] || e?.message || 'Failed to grant'
  } finally {
    modal.saving = false
  }
}

async function revoke(s) {
  if (type.value === 'Late Permission') {
    await revokeLateResource.submit({ student: s.name, date: date.value })
  } else {
    await revokeEarlyOutResource.submit({ student: s.name, date: date.value })
  }
  await loadStudents()
}

async function toggleParentsInformed(s, checked) {
  const previous = s.parents_informed
  s.parents_informed = checked ? 1 : 0
  savingParents.value = s.name
  try {
    await setParentsInformedResource.submit({
      student: s.name,
      date: date.value,
      parents_informed: checked ? 1 : 0,
    })
  } catch (e) {
    s.parents_informed = previous
  } finally {
    savingParents.value = null
  }
}

onMounted(async () => {
  const t = await loadServerToday()
  if (date.value === formatDate(new Date())) date.value = t
  loadFilters()
})
watch(standard, () => {
  if (!standard.value) batch.value = ''
})
watch([standard, batch, date, type, gender], loadStudents)
</script>

<style>
/* Ported from bb_academy/page/late_permission/late_permission.css. Badges and
   action buttons are re-expressed here because the desk builds them as
   Bootstrap strings in JS (badge-success / btn-xs btn-primary etc.). */

.lp-manager {
  --lp-radius: var(--border-radius-md, 8px);
  --lp-radius-sm: var(--border-radius, 6px);
  --lp-gap: 14px;
  color: var(--text-color);
  padding: 14px;
}

.lp-manager * { box-sizing: border-box; }
.lp-manager button { font-family: inherit; }

/* ---- panel ---- */
.lp-manager .lp-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 18px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--lp-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 16px 18px;
  margin-bottom: var(--lp-gap);
}

.lp-manager .lp-panel-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  flex: 1 1 320px;
}

.lp-manager .lp-field { min-width: 150px; flex: 1 1 150px; }

.lp-manager .lp-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.lp-manager .lp-field label i { width: 14px; margin-right: 4px; color: var(--gray-600); }

.lp-manager .lp-panel-date {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 0 0 auto;
}

.lp-manager .lp-date-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
}

.lp-manager .lp-date-label i { width: 14px; margin-right: 4px; color: var(--gray-600); }

.lp-manager .lp-date-stepper {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--border-color);
  border-radius: var(--lp-radius-sm);
  background: var(--control-bg, var(--gray-100));
  overflow: hidden;
}

.lp-manager .lp-date-nav-btn {
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

.lp-manager .lp-date-nav-btn:hover { background: var(--gray-200); }
.lp-manager .lp-date-nav-btn:active { background: var(--gray-300); }

.lp-manager .lp-date-input {
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

.lp-manager .lp-date-input:focus { outline: none; box-shadow: var(--highlight-shadow); }

/* ---- toolbar ---- */
.lp-manager .lp-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: var(--lp-gap);
}

.lp-manager .lp-search-wrap { position: relative; flex: 1 1 280px; max-width: 360px; }

.lp-manager .lp-search-wrap i {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 13px;
}

.lp-manager .lp-search-input {
  width: 100%;
  height: 38px;
  border: 1px solid var(--border-color);
  border-radius: var(--lp-radius-sm);
  background: var(--card-bg);
  padding: 0 12px 0 34px;
  font-size: 13px;
  color: var(--text-color);
}

.lp-manager .lp-search-input:focus {
  outline: none;
  border-color: var(--blue-400, var(--blue-500));
  box-shadow: var(--highlight-shadow);
}

/* ---- table ---- */
.lp-manager .lp-table-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--lp-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  overflow: hidden;
}

.lp-manager .lp-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0;
}

.lp-manager .lp-table thead th {
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

.lp-manager .lp-col-att-status { width: 120px; }
.lp-manager .lp-col-actions { width: 320px; }

.lp-manager .lp-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.lp-manager .lp-table tbody tr.lp-student-row {
  border-left: 3px solid var(--gray-300);
  transition: background-color 0.12s ease, border-left-color 0.12s ease;
}

.lp-manager .lp-table tbody tr.lp-student-row:hover { background: var(--fg-hover-color, var(--gray-50)); }
.lp-manager .lp-table tbody tr.lp-student-row:last-child td { border-bottom: none; }

.lp-manager .lp-table tbody tr.lp-student-row[data-current-status='Present'] { border-left-color: var(--green-500); }
.lp-manager .lp-table tbody tr.lp-student-row[data-current-status='Absent'] { border-left-color: var(--red-500); }
.lp-manager .lp-table tbody tr.lp-student-row[data-current-status='Late'] { border-left-color: var(--orange-500); }
.lp-manager .lp-table tbody tr.lp-student-row[data-current-status='Early Outs'] { border-left-color: var(--blue-500); }

.lp-manager .lp-student-id {
  font-weight: 700;
  font-size: 14px;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.lp-manager .lp-student-profile { display: flex; align-items: center; gap: 10px; }
.lp-manager .lp-student-name-wrap { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; }
.lp-manager .lp-student-name { font-size: 13.5px; color: var(--text-color); }

.lp-manager .lp-gender-icon { margin-left: 6px; font-size: 12px; color: var(--gray-500); }
.lp-manager .lp-gender-icon-female { color: #ff69b4; }
.lp-manager .lp-gender-icon-male { color: #2196f3; }

/* ---- badges (Bootstrap equivalents the desk emits from JS) ---- */
.lp-manager .lp-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--border-radius-full, 999px);
}

.lp-manager .lp-badge-success { background: var(--bg-green); color: var(--text-on-green); }
.lp-manager .lp-badge-warning { background: var(--bg-orange); color: var(--text-on-orange); }
.lp-manager .lp-badge-danger { background: var(--bg-red); color: var(--text-on-red); }
.lp-manager .lp-badge-info { background: var(--bg-blue); color: var(--text-on-blue); }
.lp-manager .lp-badge-secondary { background: var(--bg-gray); color: var(--text-on-gray); }

.lp-manager .lp-parents-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 6px 0 0;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
}

.lp-manager .lp-parents-toggle input { accent-color: var(--blue-500); cursor: pointer; }
.lp-manager .lp-saving { color: var(--gray-500); }

/* ---- action buttons (btn-xs equivalents) ---- */
.lp-manager .lp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--lp-radius-sm);
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  margin-right: 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.lp-manager .lp-btn:last-child { margin-right: 0; }
.lp-manager .lp-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.lp-manager .lp-btn-primary { background: var(--blue-600); border-color: var(--blue-600); color: #fff; }
.lp-manager .lp-btn-primary:hover:not(:disabled) { background: var(--blue-700, var(--blue-600)); }
.lp-manager .lp-btn-danger { background: var(--red-600); border-color: var(--red-600); color: #fff; }
.lp-manager .lp-btn-default { background: var(--card-bg); border-color: var(--border-color); color: var(--text-color); }
.lp-manager .lp-btn-default:hover { background: var(--gray-100); }

/* ---- empty / skeleton ---- */
.lp-manager .lp-empty-state { text-align: center; padding: 48px 20px; color: var(--text-muted); }
.lp-manager .lp-empty-icon { font-size: 34px; color: var(--gray-400); margin-bottom: 12px; }
.lp-manager .lp-empty-state h4 { color: var(--heading-color); font-size: 16px; margin-bottom: 6px; }
.lp-manager .lp-empty-state p { margin: 0 auto; max-width: 360px; font-size: 13px; }

.lp-manager .lp-skeleton-row td { padding: 16px !important; }

.lp-manager .lp-skeleton-bar {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: lp-skeleton-shine 1.4s ease infinite;
}

@keyframes lp-skeleton-shine {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* ---- modal ---- */
.lp-manager .lp-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.lp-manager .lp-modal {
  background: var(--card-bg);
  border-radius: var(--lp-radius);
  box-shadow: var(--shadow-md);
  padding: 20px;
  width: 100%;
  max-width: 380px;
  max-height: 85vh;
  overflow-y: auto;
}

.lp-manager .lp-modal h3 {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: var(--heading-color);
}

.lp-manager .lp-modal-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin: 12px 0 4px;
}

.lp-manager .lp-req { color: var(--red-600); }
.lp-manager .lp-textarea { height: auto; padding: 8px 10px; resize: vertical; }
.lp-manager .lp-modal-warn { font-size: 11px; color: var(--text-on-yellow); margin-top: 6px; }
.lp-manager .lp-modal-error { font-size: 12px; color: var(--red-600); margin-top: 8px; }

.lp-manager .lp-optional { font-weight: 400; color: var(--gray-500); }

.lp-manager .lp-time-row { display: flex; gap: 8px; align-items: center; }
.lp-manager .lp-time-row .form-control { flex: 1 1 auto; min-width: 0; }

.lp-manager .lp-now-btn {
  flex: 0 0 auto;
  border: 1px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-muted);
  border-radius: var(--lp-radius-sm);
  padding: 0 12px;
  height: 36px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.lp-manager .lp-now-btn:hover { background: var(--bg-blue); color: var(--text-on-blue); border-color: var(--blue-200); }
.lp-manager .lp-clear-btn:hover { background: var(--bg-red); color: var(--text-on-red); border-color: var(--red-200); }

.lp-manager .lp-time-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 6px;
  font-size: 11.5px;
  font-weight: 600;
  background: var(--bg-blue);
  color: var(--text-on-blue);
  border-radius: var(--border-radius-full, 999px);
  padding: 2px 9px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.lp-manager .lp-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-color);
  cursor: pointer;
}

.lp-manager .lp-checkbox input { accent-color: var(--blue-500); cursor: pointer; }

.lp-manager .lp-modal-actions { display: flex; gap: 8px; margin-top: 18px; }

.lp-manager .lp-btn-lg,
.lp-manager .lp-btn-primary-lg {
  flex: 1;
  padding: 9px 14px;
  border-radius: var(--lp-radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.lp-manager .lp-btn-secondary { background: var(--card-bg); border-color: var(--border-color); color: var(--text-muted); }
.lp-manager .lp-btn-primary-lg { background: var(--blue-600); border-color: var(--blue-600); color: #fff; }
.lp-manager .lp-btn-primary-lg:disabled { opacity: 0.5; cursor: not-allowed; }

/* ---- responsive ---- */
@media (min-width: 768px) {
  .lp-manager .lp-table-scroll { max-height: 68vh; overflow-y: auto; }
  .lp-manager .lp-table thead th { position: sticky; top: 0; z-index: 2; }
}

@media (max-width: 767px) {
  .lp-manager { padding: 10px; }

  .lp-manager .lp-panel { flex-direction: column; align-items: stretch; padding: 14px; }

  .lp-manager .lp-panel-filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    flex: none;
  }

  .lp-manager .lp-field { min-width: 0; flex: none; }
  .lp-manager .lp-field-gender { grid-column: 1 / -1; }
  .lp-manager .lp-panel-date { width: 100%; }
  .lp-manager .lp-date-stepper { width: 100%; }
  .lp-manager .lp-date-input { flex: 1; min-width: 0; }

  .lp-manager .lp-toolbar { flex-direction: column; align-items: stretch; }
  .lp-manager .lp-search-wrap { max-width: none; flex: none; }

  .lp-manager .lp-table-card {
    background: transparent;
    border: none;
    box-shadow: none;
    overflow: visible;
  }

  .lp-manager .lp-table-scroll { overflow-x: visible; }
  .lp-manager .lp-table thead { display: none; }
  .lp-manager .lp-table,
  .lp-manager .lp-table tbody { display: block; width: 100%; }

  .lp-manager .lp-table tbody tr.lp-placeholder-row,
  .lp-manager .lp-table tbody tr.lp-skeleton-row {
    display: block;
    background: var(--card-bg);
    border-radius: var(--lp-radius);
    margin-bottom: 12px;
  }

  .lp-manager .lp-table tbody tr.lp-student-row {
    display: grid;
    grid-template-columns: 1fr;
    grid-template-areas:
      'id'
      'name'
      'att-status'
      'status'
      'actions';
    row-gap: 10px;
    column-gap: 10px;
    border-left: 4px solid var(--gray-300);
    border-bottom: none;
    border-radius: var(--lp-radius);
    padding: 14px;
    margin: 0 0 12px;
    background: var(--card-bg);
    box-shadow: var(--card-shadow, var(--shadow-sm));
  }

  .lp-manager .lp-table tbody tr.lp-student-row td {
    display: block;
    width: auto;
    padding: 0;
    border-bottom: none;
  }

  .lp-manager .lp-td-id { grid-area: id; }
  .lp-manager .lp-td-name {
    grid-area: name;
    padding-top: 10px !important;
    border-top: 1px solid var(--border-color);
  }
  .lp-manager .lp-td-att-status { grid-area: att-status; }
  .lp-manager .lp-td-status { grid-area: status; }
  .lp-manager .lp-td-actions { grid-area: actions; display: flex; gap: 8px; }
  .lp-manager .lp-td-actions .lp-btn { flex: 1; margin-right: 0; padding: 9px 12px; }
}

@media (max-width: 480px) {
  .lp-manager .lp-student-id { font-size: 13px; }
}
</style>
