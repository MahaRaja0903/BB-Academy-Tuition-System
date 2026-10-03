<template>
  <div class="smr-manager">
    <!-- Control panel -->
    <div class="smr-panel">
      <div class="smr-panel-filters">
        <div class="smr-field">
          <label><i class="fa fa-graduation-cap"></i> Standard</label>
          <select class="form-control" v-model="standard">
            <option value="">All Standards</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="smr-field">
          <label><i class="fa fa-users"></i> Batch</label>
          <select class="form-control" v-model="batch">
            <option value="">All Batches</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
        <div class="smr-field">
          <label><i class="fa fa-venus-mars"></i> Gender</label>
          <select class="form-control" v-model="gender">
            <option value="">All</option>
            <option value="Boys">Boys</option>
            <option value="Girls">Girls</option>
          </select>
        </div>
        <div class="smr-field">
          <label><i class="fa fa-calendar"></i> Month</label>
          <input type="month" class="form-control" v-model="month" />
        </div>
      </div>

      <div class="smr-panel-status">
        <button
          type="button"
          class="smr-seg"
          :class="{ 'is-active': status === 'Open' }"
          @click="status = 'Open'"
        >
          <i class="fa fa-folder-open-o"></i> Open
        </button>
        <button
          type="button"
          class="smr-seg"
          :class="{ 'is-active': status === 'Closed' }"
          @click="status = 'Closed'"
        >
          <i class="fa fa-check-circle-o"></i> Closed
        </button>
      </div>
    </div>

    <!-- Level summary — how many students sit in each mistake band, and a tap
         on any of them narrows the list below to exactly those students. -->
    <div class="smr-kpi-grid">
      <button
        v-for="k in kpis"
        :key="k.key"
        type="button"
        class="smr-kpi"
        :class="[k.cls, { 'is-active': levelFilter === k.level }]"
        :title="k.title"
        @click="toggleLevel(k.level)"
      >
        <span class="smr-kpi-label">{{ k.label }}</span>
        <span class="smr-kpi-value">{{ k.value }}</span>
        <span class="smr-kpi-sub">{{ k.sub }}</span>
      </button>
    </div>

    <!-- Toolbar -->
    <div class="smr-toolbar">
      <div class="smr-search-wrap">
        <i class="fa fa-search"></i>
        <input
          type="text"
          class="smr-search-input"
          placeholder="Search student name or ID"
          v-model="search"
        />
      </div>
      <span v-if="levelFilter" class="smr-filter-chip">
        <span>Showing <strong>{{ levelLabel(levelFilter) }}</strong></span>
        <button type="button" title="Clear filter" @click="levelFilter = null">
          <i class="fa fa-times"></i>
        </button>
      </span>
      <button type="button" class="smr-refresh-btn" :disabled="loading" @click="load">
        <i class="fa" :class="loading ? 'fa-spinner fa-spin' : 'fa-refresh'"></i>
        <span>Refresh</span>
      </button>
    </div>

    <!-- Skeletons -->
    <template v-if="loading">
      <div v-for="i in 3" :key="`sk${i}`" class="smr-card smr-skeleton">
        <div class="smr-skeleton-bar" style="width: 45%"></div>
        <div class="smr-skeleton-bar" style="width: 75%"></div>
        <div class="smr-skeleton-bar" style="width: 60%"></div>
      </div>
    </template>

    <!-- Empty -->
    <div v-else-if="!visibleRecords.length" class="smr-empty-state">
      <div class="smr-empty-icon"><i class="fa" :class="emptyState.icon"></i></div>
      <h4>{{ emptyState.title }}</h4>
      <p>{{ emptyState.text }}</p>
    </div>

    <!-- Records -->
    <article
      v-for="r in visibleRecords"
      :key="r.name"
      class="smr-card"
      :data-level="r.action_level"
      :data-status="r.status"
    >
      <header class="smr-card-head">
        <img
          v-if="r.image"
          class="smr-avatar"
          :src="r.image"
          :alt="r.student_name"
          loading="lazy"
        />
        <div v-else class="smr-avatar smr-avatar-fallback">{{ initials(r.student_name) }}</div>

        <div class="smr-ident">
          <div class="smr-name-row">
            <router-link
              class="smr-name"
              :to="{ name: 'StudentProfile', query: { student: r.student } }"
              title="Open this student's profile"
            >
              {{ r.student_name }}
            </router-link>
            <i
              v-if="r.gender"
              class="fa smr-gender-icon"
              :class="[
                r.gender === 'Girls' ? 'fa-female' : 'fa-male',
                r.gender === 'Girls' ? 'smr-gender-female' : 'smr-gender-male',
              ]"
              :title="r.gender"
            ></i>
          </div>

          <div class="smr-meta">
            <span class="smr-meta-id">{{ r.student }}</span>
            <span v-if="r.standard" class="smr-meta-dot">·</span>
            <span v-if="r.standard">{{ r.standard }}</span>
            <span v-if="r.batch" class="smr-meta-dot">·</span>
            <span v-if="r.batch">{{ r.batch }}</span>
          </div>

          <div class="smr-badges">
            <span class="smr-count-badge" :title="countTitle(r)">
              <i class="fa fa-exclamation-triangle"></i> {{ r.mistake_count }} mistakes
            </span>
            <!-- Without this the count reads as a data error: a student everyone
                 remembers having a bad month shows 1. -->
            <span v-if="r.batch_changed_on" class="smr-reset-badge" :title="countTitle(r)">
              <i class="fa fa-exchange"></i> Counting from {{ prettyDate(r.batch_changed_on) }}
            </span>
            <span class="smr-level-badge" :data-level="r.action_level">{{ r.action_level }}</span>
            <span v-if="r.status === 'Closed'" class="smr-closed-badge">
              <i class="fa fa-check"></i> Closed
            </span>
            <span v-if="r.reopened_on && r.status === 'Open'" class="smr-reopened-badge">
              Reopened
            </span>
          </div>
        </div>
      </header>

      <!-- Where the mistakes came from -->
      <div class="smr-tally">
        <span class="smr-tally-chip" :class="{ 'is-zero': !r.test_count }">
          Test <b>{{ r.test_count }}</b>
        </span>
        <span class="smr-tally-chip" :class="{ 'is-zero': !r.study_count }">
          Study <b>{{ r.study_count }}</b>
        </span>
        <span class="smr-tally-chip" :class="{ 'is-zero': !r.behaviour_count }">
          Behaviour <b>{{ r.behaviour_count }}</b>
        </span>
        <button type="button" class="smr-link-btn" @click="toggleDetail(r)">
          <i class="fa" :class="expanded.has(r.name) ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
          {{ expanded.has(r.name) ? 'Hide' : 'View' }} mistakes
        </button>
      </div>

      <!-- The mistakes themselves -->
      <div v-if="expanded.has(r.name)" class="smr-detail">
        <div v-if="detailLoading === r.name" class="smr-detail-loading">Loading…</div>
        <table v-else-if="(details[r.name] || []).length" class="smr-detail-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Category</th>
              <th>Result</th>
              <th>What Happened</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in details[r.name]" :key="m.name">
              <td class="smr-detail-date">{{ formatDate(m.date) }}</td>
              <td>{{ m.category }}</td>
              <td>
                <span class="smr-result-badge" :data-result="m.result">{{ m.result }}</span>
              </td>
              <td class="smr-detail-what">
                <span v-if="m.reasons && m.reasons.length">{{ m.reasons.join(', ') }}</span>
                <span v-else-if="m.total_marks">{{ m.marks_obtained }} / {{ m.total_marks }}</span>
                <span v-else-if="m.subject">{{ m.subject }}</span>
                <em v-if="m.remarks" class="smr-detail-remarks">{{ m.remarks }}</em>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="smr-detail-empty">No mistakes found for this month.</p>
      </div>

      <!-- What is still owed -->
      <div v-if="r.pending && r.pending.length" class="smr-pending">
        <span class="smr-pending-label"><i class="fa fa-clock-o"></i> Still to do</span>
        <span v-for="p in r.pending" :key="p" class="smr-pending-chip">{{ p }}</span>
      </div>
      <div v-else-if="r.status === 'Open'" class="smr-pending smr-pending-clear">
        <i class="fa fa-check-circle"></i> All follow-up actions recorded — ready to close.
      </div>

      <!-- Recorded follow-up -->
      <div v-if="r.call_done || r.meeting_done || r.parents_informed" class="smr-done">
        <div v-if="r.call_done" class="smr-done-row">
          <i class="fa fa-phone"></i>
          <span>
            Called <b>{{ r.spoken_to || 'family' }}</b>
            <template v-if="r.spoken_to_name"> ({{ r.spoken_to_name }})</template>
            on {{ formatDateTime(r.called_on) }}
            <template v-if="r.called_by"> by <b>{{ r.called_by }}</b></template>
          </span>
        </div>
        <div v-if="r.call_notes" class="smr-done-notes">“{{ r.call_notes }}”</div>
        <div v-if="r.parents_informed" class="smr-done-row">
          <i class="fa fa-bullhorn"></i>
          <span>Parents informed on {{ formatDateTime(r.parents_informed_on) }}</span>
        </div>
        <div v-if="r.meeting_done" class="smr-done-row">
          <i class="fa fa-handshake-o"></i>
          <span>
            Parents met <b>{{ r.met_staff || 'staff' }}</b> on {{ formatDateTime(r.meeting_on) }}
          </span>
        </div>
        <div v-if="r.meeting_notes" class="smr-done-notes">“{{ r.meeting_notes }}”</div>
        <a
          v-if="r.meeting_photo"
          class="smr-photo-thumb"
          :href="r.meeting_photo"
          target="_blank"
          rel="noopener"
          title="Open meeting photo"
        >
          <img :src="r.meeting_photo" alt="Meeting photo" loading="lazy" />
        </a>
      </div>

      <!-- Actions -->
      <div class="smr-actions">
        <template v-if="r.status === 'Open'">
          <button
            v-if="r.call_required"
            type="button"
            class="smr-btn"
            :class="r.call_done ? 'smr-btn-done' : 'smr-btn-primary'"
            @click="openCall(r)"
          >
            <i class="fa fa-phone"></i> {{ r.call_done ? 'Edit Call' : 'Log Call' }}
          </button>
          <button
            v-if="r.meeting_required"
            type="button"
            class="smr-btn"
            :class="r.meeting_done && r.meeting_photo ? 'smr-btn-done' : 'smr-btn-primary'"
            @click="openMeeting(r)"
          >
            <i class="fa fa-handshake-o"></i>
            {{ r.meeting_done ? 'Edit Meeting' : 'Parent Meeting' }}
          </button>
          <button
            v-if="r.category_review_required"
            type="button"
            class="smr-btn"
            :class="allReviewed(r) ? 'smr-btn-done' : 'smr-btn-primary'"
            @click="openReview(r)"
          >
            <i class="fa fa-list-ul"></i> Monthly Review
          </button>
          <button
            type="button"
            class="smr-btn smr-btn-close"
            :disabled="(r.pending || []).length > 0"
            :title="
              (r.pending || []).length
                ? 'Finish the pending actions first'
                : 'Close and remove from the list'
            "
            @click="openClose(r)"
          >
            <i class="fa fa-check"></i> Close
          </button>
        </template>
        <template v-else>
          <span class="smr-closed-note">
            Closed on {{ formatDateTime(r.closed_on) }}
            <template v-if="r.closed_by"> by {{ r.closed_by }}</template>
          </span>
          <button type="button" class="smr-btn smr-btn-ghost" @click="reopen(r)">
            <i class="fa fa-undo"></i> Reopen
          </button>
        </template>
      </div>
    </article>

    <!-- Call modal -->
    <div v-if="callModal.open" class="smr-modal-backdrop" @click.self="callModal.open = false">
      <div class="smr-modal">
        <h3><i class="fa fa-phone"></i> Call Home — {{ callModal.record?.student_name }}</h3>
        <p class="smr-modal-hint">
          {{ callModal.record?.mistake_count }} mistakes this month. Record who was spoken to, what
          was said, when, and who spoke from the tuition.
        </p>

        <label class="smr-modal-label">Whom did you speak to? <span class="smr-req">*</span></label>
        <select class="form-control" v-model="callModal.spoken_to">
          <option value="">Select</option>
          <option v-for="o in SPOKEN_TO" :key="o" :value="o">{{ o }}</option>
        </select>

        <label class="smr-modal-label">Name / number spoken to</label>
        <input type="text" class="form-control" v-model="callModal.spoken_to_name" />

        <label class="smr-modal-label">When was the call made?</label>
        <input type="datetime-local" class="form-control" v-model="callModal.called_on" />

        <label class="smr-modal-label">
          Who spoke from the tuition? <span class="smr-req">*</span>
        </label>
        <select class="form-control" v-model="callModal.called_by">
          <option value="">Select staff</option>
          <option v-for="s in staffList" :key="s.name" :value="s.name">{{ s.name }}</option>
        </select>

        <label class="smr-modal-label">What was spoken? <span class="smr-req">*</span></label>
        <textarea class="form-control" rows="3" v-model="callModal.call_notes"></textarea>

        <p v-if="callModal.error" class="smr-modal-error">{{ callModal.error }}</p>
        <div class="smr-modal-actions">
          <button class="smr-btn-lg smr-btn-secondary" @click="callModal.open = false">Cancel</button>
          <button
            class="smr-btn-lg smr-btn-primary-lg"
            :disabled="!canSaveCall || callModal.saving"
            @click="saveCall"
          >
            {{ callModal.saving ? 'Saving…' : 'Save Call' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Meeting modal -->
    <div v-if="meetModal.open" class="smr-modal-backdrop" @click.self="meetModal.open = false">
      <div class="smr-modal">
        <h3><i class="fa fa-handshake-o"></i> Parent Meeting — {{ meetModal.record?.student_name }}</h3>
        <p class="smr-modal-hint">
          {{ meetModal.record?.mistake_count }} mistakes this month. The parents must be informed,
          must meet the staff, and a photo of the meeting must be uploaded.
        </p>

        <label class="smr-check">
          <input type="checkbox" v-model="meetModal.parents_informed" />
          <span>Parents have been informed</span>
        </label>

        <label class="smr-check">
          <input type="checkbox" v-model="meetModal.meeting_done" />
          <span>Parents met the staff</span>
        </label>

        <template v-if="meetModal.meeting_done">
          <label class="smr-modal-label">Which staff did they meet? <span class="smr-req">*</span></label>
          <select class="form-control" v-model="meetModal.met_staff">
            <option value="">Select staff</option>
            <option v-for="s in staffList" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>

          <label class="smr-modal-label">Meeting time</label>
          <input type="datetime-local" class="form-control" v-model="meetModal.meeting_on" />

          <label class="smr-modal-label">What was discussed?</label>
          <textarea class="form-control" rows="3" v-model="meetModal.meeting_notes"></textarea>

          <label class="smr-modal-label">Meeting photo <span class="smr-req">*</span></label>
          <div class="smr-photo-row">
            <img v-if="meetModal.photo" class="smr-photo-preview" :src="meetModal.photo" alt="Meeting photo" />
            <label class="smr-upload-btn">
              <i class="fa" :class="meetModal.uploading ? 'fa-spinner fa-spin' : 'fa-camera'"></i>
              <span>{{ meetModal.photo ? 'Replace photo' : 'Take / upload photo' }}</span>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                :disabled="meetModal.uploading"
                @change="onPhotoPicked"
              />
            </label>
          </div>
        </template>

        <p v-if="meetModal.error" class="smr-modal-error">{{ meetModal.error }}</p>
        <div class="smr-modal-actions">
          <button class="smr-btn-lg smr-btn-secondary" @click="meetModal.open = false">Cancel</button>
          <button
            class="smr-btn-lg smr-btn-primary-lg"
            :disabled="!canSaveMeeting || meetModal.saving"
            @click="saveMeeting"
          >
            {{ meetModal.saving ? 'Saving…' : 'Save Meeting' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Monthly category review modal -->
    <div v-if="reviewModal.open" class="smr-modal-backdrop" @click.self="reviewModal.open = false">
      <div class="smr-modal smr-modal-wide">
        <h3><i class="fa fa-list-ul"></i> Monthly Review — {{ reviewModal.record?.student_name }}</h3>
        <p class="smr-modal-hint">
          {{ reviewModal.record?.mistake_count }} mistakes in
          {{ reviewModal.record?.month_label }}. Test, Study and Behaviour are recorded and reviewed
          separately.
        </p>

        <div v-for="row in reviewModal.rows" :key="row.category" class="smr-review-block">
          <div class="smr-review-head">
            <span class="smr-review-title">{{ row.category }}</span>
            <span class="smr-review-count">{{ row.mistake_count }} mistakes</span>
          </div>
          <label class="smr-modal-label">What happened</label>
          <textarea class="form-control" rows="2" v-model="row.what_happened"></textarea>
          <label class="smr-modal-label">Action taken</label>
          <textarea class="form-control" rows="2" v-model="row.action_taken"></textarea>
          <label class="smr-check">
            <input type="checkbox" v-model="row.reviewed" />
            <span>Reviewed</span>
          </label>
        </div>

        <p v-if="reviewModal.error" class="smr-modal-error">{{ reviewModal.error }}</p>
        <div class="smr-modal-actions">
          <button class="smr-btn-lg smr-btn-secondary" @click="reviewModal.open = false">Cancel</button>
          <button
            class="smr-btn-lg smr-btn-primary-lg"
            :disabled="reviewModal.saving"
            @click="saveReview"
          >
            {{ reviewModal.saving ? 'Saving…' : 'Save Review' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Close modal -->
    <div v-if="closeModal.open" class="smr-modal-backdrop" @click.self="closeModal.open = false">
      <div class="smr-modal">
        <h3><i class="fa fa-check"></i> Close — {{ closeModal.record?.student_name }}</h3>
        <p class="smr-modal-hint">
          Closing takes this student off the follow-up list. A new mistake this month reopens it
          automatically.
        </p>
        <label class="smr-modal-label">Closure notes</label>
        <textarea class="form-control" rows="3" v-model="closeModal.notes"></textarea>

        <p v-if="closeModal.error" class="smr-modal-error">{{ closeModal.error }}</p>
        <div class="smr-modal-actions">
          <button class="smr-btn-lg smr-btn-secondary" @click="closeModal.open = false">Cancel</button>
          <button
            class="smr-btn-lg smr-btn-primary-lg"
            :disabled="closeModal.saving"
            @click="confirmClose"
          >
            {{ closeModal.saving ? 'Closing…' : 'Close Record' }}
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

const SPOKEN_TO = ['Father', 'Mother', 'Guardian', 'Student', 'Other']

// The three thresholds, exactly as bb_academy/mistakes.py applies them. The
// levels are cumulative, so the bands are what a student is *currently* in:
// a student on 6 is one Parent Meeting student, not one of each.
const LEVELS = [
  { level: 'Call', label: '3 Mistakes', sub: 'Call home', band: '3–4', cls: 'smr-kpi-call' },
  {
    level: 'Parent Meeting',
    label: '5 Mistakes',
    sub: 'Parent meeting',
    band: '5–9',
    cls: 'smr-kpi-meeting',
  },
  {
    level: 'Category Review',
    label: '10 Mistakes',
    sub: 'Category review',
    band: '10 or more',
    cls: 'smr-kpi-review',
  },
]

const standards = ref([])
const batches = ref([])
const staffList = ref([])

const standard = ref('')
const batch = ref('')
const gender = ref('')
const month = ref((serverToday.value || '').slice(0, 7))
const status = ref('Open')
const search = ref('')
// Which threshold band the list is narrowed to, or null for all of them.
const levelFilter = ref(null)

const records = ref([])
const loading = ref(false)
const expanded = ref(new Set())
const details = reactive({})
const detailLoading = ref(null)

const callModal = reactive({
  open: false,
  record: null,
  spoken_to: '',
  spoken_to_name: '',
  called_on: '',
  called_by: '',
  call_notes: '',
  saving: false,
  error: '',
})

const meetModal = reactive({
  open: false,
  record: null,
  parents_informed: false,
  meeting_done: false,
  met_staff: '',
  meeting_on: '',
  meeting_notes: '',
  photo: '',
  uploading: false,
  saving: false,
  error: '',
})

const reviewModal = reactive({ open: false, record: null, rows: [], saving: false, error: '' })
const closeModal = reactive({ open: false, record: null, notes: '', saving: false, error: '' })

// Searched but not yet narrowed by band — the KPI counts are taken from this,
// so they keep reading as "how many students are at each threshold" while a
// band is selected, instead of collapsing to the one that is showing.
const searchedRecords = computed(() => {
  if (!search.value.trim()) return records.value
  const q = search.value.trim().toLowerCase()
  return records.value.filter(
    (r) =>
      (r.student_name || '').toLowerCase().includes(q) ||
      (r.student || '').toLowerCase().includes(q)
  )
})

const visibleRecords = computed(() => {
  if (!levelFilter.value) return searchedRecords.value
  return searchedRecords.value.filter((r) => r.action_level === levelFilter.value)
})

const levelCounts = computed(() => {
  const counts = { Call: 0, 'Parent Meeting': 0, 'Category Review': 0 }
  for (const r of searchedRecords.value) {
    if (counts[r.action_level] !== undefined) counts[r.action_level] += 1
  }
  return counts
})

const kpis = computed(() => [
  {
    key: 'total',
    level: null,
    label: 'Students',
    sub: 'On follow-up',
    cls: 'smr-kpi-total',
    value: searchedRecords.value.length,
    title: 'Show every student on the follow-up list',
  },
  ...LEVELS.map((l) => ({
    key: l.level,
    level: l.level,
    label: l.label,
    sub: l.sub,
    cls: l.cls,
    value: levelCounts.value[l.level],
    title: `Show only students with ${l.band} mistakes this month (${l.sub})`,
  })),
])

function levelLabel(level) {
  const hit = LEVELS.find((l) => l.level === level)
  return hit ? `${hit.label} · ${hit.sub}` : level
}

// The Students card clears the filter; any band toggles it.
function toggleLevel(level) {
  levelFilter.value = !level || levelFilter.value === level ? null : level
}

function prettyDate(value) {
  if (!value) return ''
  const d = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
}

// A record whose count restarted mid-month has to say so, or the number looks
// like a bug to whoever remembers the student's actual month.
function countTitle(r) {
  if (!r.batch_changed_on) return `${r.mistake_count} mistakes in ${r.month_label}`
  return (
    `${r.mistake_count} mistakes since the batch changed on ${prettyDate(r.batch_changed_on)}. ` +
    `Anything before that belongs to the old batch.`
  )
}

const emptyState = computed(() => {
  if (levelFilter.value && searchedRecords.value.length) {
    return {
      icon: 'fa-info-circle',
      title: `No student at ${levelLabel(levelFilter.value)}`,
      text: 'No student is in that mistake band this month with these filters.',
    }
  }
  if (status.value === 'Closed') {
    return {
      icon: 'fa-folder-open-o',
      title: 'No closed records',
      text: 'Nothing has been closed for this month with these filters.',
    }
  }
  if (search.value.trim() && records.value.length) {
    return {
      icon: 'fa-search',
      title: 'No match',
      text: 'No student on the follow-up list matches that search.',
    }
  }
  return {
    icon: 'fa-thumbs-o-up',
    title: 'Nothing to follow up',
    text: 'No student has reached 3 mistakes this month with these filters.',
  }
})

const canSaveCall = computed(
  () => !!callModal.spoken_to && !!callModal.called_by && !!(callModal.call_notes || '').trim()
)

const canSaveMeeting = computed(() => {
  if (!meetModal.meeting_done) return true
  return !!meetModal.met_staff && !!meetModal.photo
})

const optionsResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const batchesResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const staffResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const listResource = createResource({
  url: 'bb_tution_management.bb_academy.mistakes.get_mistake_students',
})
const detailResource = createResource({
  url: 'bb_tution_management.bb_academy.mistakes.get_mistake_detail',
})
const callResource = createResource({ url: 'bb_tution_management.bb_academy.mistakes.record_call' })
const meetingResource = createResource({
  url: 'bb_tution_management.bb_academy.mistakes.record_meeting',
})
const attachResource = createResource({
  url: 'bb_tution_management.bb_academy.mistakes.attach_meeting_photo',
})
const reviewResource = createResource({
  url: 'bb_tution_management.bb_academy.mistakes.save_category_review',
})
const closeResource = createResource({ url: 'bb_tution_management.bb_academy.mistakes.close_record' })
const reopenResource = createResource({
  url: 'bb_tution_management.bb_academy.mistakes.reopen_record',
})

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function formatDate(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// `<input type="datetime-local">` speaks "YYYY-MM-DDTHH:MM"; Frappe stores
// "YYYY-MM-DD HH:MM:SS". Convert on the way in and out rather than letting the
// browser silently ignore a value it cannot parse.
function toInputDateTime(value) {
  if (!value) return ''
  return String(value).replace(' ', 'T').slice(0, 16)
}

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

function allReviewed(record) {
  const rows = record.category_breakdown || []
  return rows.length > 0 && rows.every((row) => row.reviewed)
}

function errorText(e) {
  return e?.messages?.[0] || e?.message || String(e || 'Something went wrong')
}

async function load() {
  loading.value = true
  try {
    const res = await listResource.submit({
      standard: standard.value || null,
      batch: batch.value || null,
      gender: gender.value || null,
      month: month.value || null,
      status: status.value,
    })
    records.value = res?.records || []
    // A band selected for the old filter set would silently hide everything.
    levelFilter.value = null
    // A record that is no longer listed should not keep a stale expansion open.
    const live = new Set(records.value.map((r) => r.name))
    expanded.value = new Set([...expanded.value].filter((n) => live.has(n)))
  } catch (e) {
    records.value = []
    console.error('Failed to load mistake records', e)
  } finally {
    loading.value = false
  }
}

async function toggleDetail(record) {
  const next = new Set(expanded.value)
  if (next.has(record.name)) {
    next.delete(record.name)
    expanded.value = next
    return
  }
  next.add(record.name)
  expanded.value = next

  if (details[record.name]) return
  detailLoading.value = record.name
  try {
    const res = await detailResource.submit({ record: record.name })
    details[record.name] = res?.mistakes || []
  } catch (e) {
    details[record.name] = []
    console.error('Failed to load mistake detail', e)
  } finally {
    detailLoading.value = null
  }
}

function openCall(record) {
  Object.assign(callModal, {
    open: true,
    record,
    spoken_to: record.spoken_to || '',
    spoken_to_name: record.spoken_to_name || '',
    called_on: toInputDateTime(record.called_on) || nowForInput(),
    called_by: record.called_by || '',
    call_notes: record.call_notes || '',
    saving: false,
    error: '',
  })
}

async function saveCall() {
  callModal.saving = true
  callModal.error = ''
  try {
    await callResource.submit({
      record: callModal.record.name,
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

function openMeeting(record) {
  Object.assign(meetModal, {
    open: true,
    record,
    parents_informed: !!record.parents_informed,
    meeting_done: !!record.meeting_done,
    met_staff: record.met_staff || '',
    meeting_on: toInputDateTime(record.meeting_on) || nowForInput(),
    meeting_notes: record.meeting_notes || '',
    photo: record.meeting_photo || '',
    uploading: false,
    saving: false,
    error: '',
  })
}

async function onPhotoPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  meetModal.uploading = true
  meetModal.error = ''
  try {
    // The meeting has to exist as a document before a file can hang off it, so
    // the record is saved first and the photo attached to it afterwards.
    await meetingResource.submit({
      record: meetModal.record.name,
      parents_informed: meetModal.parents_informed ? 1 : 0,
      meeting_done: meetModal.meeting_done ? 1 : 0,
      met_staff: meetModal.met_staff || null,
      meeting_on: fromInputDateTime(meetModal.meeting_on),
      meeting_notes: meetModal.meeting_notes,
    })

    const form = new FormData()
    form.append('file', file, file.name)
    form.append('is_private', '1')
    form.append('doctype', 'Student Mistake Record')
    form.append('docname', meetModal.record.name)
    form.append('fieldname', 'meeting_photo')

    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { Accept: 'application/json', 'X-Frappe-CSRF-Token': window.csrf_token },
      body: form,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data?.exception || data?._error_message || 'Upload failed')

    const fileUrl = data?.message?.file_url
    if (!fileUrl) throw new Error('Upload returned no file')

    const attached = await attachResource.submit({
      record: meetModal.record.name,
      file_url: fileUrl,
    })
    meetModal.photo = attached?.meeting_photo || fileUrl
  } catch (e) {
    meetModal.error = errorText(e)
  } finally {
    meetModal.uploading = false
  }
}

async function saveMeeting() {
  meetModal.saving = true
  meetModal.error = ''
  try {
    await meetingResource.submit({
      record: meetModal.record.name,
      parents_informed: meetModal.parents_informed ? 1 : 0,
      meeting_done: meetModal.meeting_done ? 1 : 0,
      met_staff: meetModal.met_staff || null,
      meeting_on: fromInputDateTime(meetModal.meeting_on),
      meeting_notes: meetModal.meeting_notes,
    })
    meetModal.open = false
    await load()
  } catch (e) {
    meetModal.error = errorText(e)
  } finally {
    meetModal.saving = false
  }
}

function openReview(record) {
  Object.assign(reviewModal, {
    open: true,
    record,
    rows: (record.category_breakdown || []).map((row) => ({
      category: row.category,
      mistake_count: row.mistake_count,
      what_happened: row.what_happened || '',
      action_taken: row.action_taken || '',
      reviewed: !!row.reviewed,
    })),
    saving: false,
    error: '',
  })
}

async function saveReview() {
  reviewModal.saving = true
  reviewModal.error = ''
  try {
    await reviewResource.submit({
      record: reviewModal.record.name,
      rows: JSON.stringify(
        reviewModal.rows.map((row) => ({
          category: row.category,
          what_happened: row.what_happened,
          action_taken: row.action_taken,
          reviewed: row.reviewed ? 1 : 0,
        }))
      ),
    })
    reviewModal.open = false
    await load()
  } catch (e) {
    reviewModal.error = errorText(e)
  } finally {
    reviewModal.saving = false
  }
}

function openClose(record) {
  Object.assign(closeModal, {
    open: true,
    record,
    notes: record.closure_notes || '',
    saving: false,
    error: '',
  })
}

async function confirmClose() {
  closeModal.saving = true
  closeModal.error = ''
  try {
    await closeResource.submit({
      record: closeModal.record.name,
      closure_notes: closeModal.notes,
    })
    closeModal.open = false
    await load()
  } catch (e) {
    closeModal.error = errorText(e)
  } finally {
    closeModal.saving = false
  }
}

async function reopen(record) {
  try {
    await reopenResource.submit({ record: record.name })
    await load()
  } catch (e) {
    console.error('Failed to reopen record', e)
  }
}

async function loadStandards() {
  const res = await optionsResource.submit({ doctype: 'Standard' })
  standards.value = res || []
}

async function loadBatches() {
  const res = await batchesResource.submit({ doctype: 'Batch' })
  batches.value = res || []
}

async function loadStaff() {
  const res = await staffResource.submit({ doctype: 'Staff' })
  staffList.value = res || []
}

watch([standard, batch, gender, month, status], load)

onMounted(async () => {
  await loadServerToday()
  if (!month.value) month.value = (serverToday.value || '').slice(0, 7)
  await Promise.all([loadStandards(), loadBatches(), loadStaff()])
  await load()
})
</script>

<style>
/* Student Mistakes — the monthly follow-up list.
   Card-based rather than a table: every row carries a photo, a tally, the
   follow-up already recorded and up to four actions, which a table cannot hold
   at phone width without collapsing into cards anyway. */

.smr-manager {
  --smr-radius: var(--border-radius-md, 8px);
  --smr-radius-sm: var(--border-radius, 6px);
  padding: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ---- control panel ---- */
.smr-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px;
  padding: 16px;
  margin-bottom: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
}

.smr-panel-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  flex: 1;
}

.smr-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 150px;
  flex: 1;
}

.smr-field label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin: 0;
}

.smr-field label i { margin-right: 4px; }

.smr-panel-status {
  display: flex;
  gap: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
  overflow: hidden;
}

.smr-seg {
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
  transition: background-color 0.12s ease, color 0.12s ease;
}

.smr-seg + .smr-seg { border-left: 1px solid var(--border-color); }
.smr-seg.is-active { background: var(--blue-500); color: #fff; }

/* ---- level summary ---- */
.smr-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.smr-kpi {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  gap: 2px;
  padding: 12px 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--gray-400);
  border-radius: var(--smr-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.smr-kpi:hover { border-color: var(--gray-400); }

/* The selected band: the card the list below is currently narrowed to. */
.smr-kpi.is-active {
  border-color: var(--gray-600, var(--text-color));
  box-shadow: 0 0 0 1px var(--gray-600, var(--text-color)) inset;
}

.smr-kpi-sub {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-muted);
  line-height: 1.2;
}

.smr-kpi-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.smr-kpi-value {
  font-size: 21px;
  font-weight: 700;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.smr-kpi-total { border-left-color: var(--gray-500); }
.smr-kpi-call { border-left-color: var(--blue-500); }
.smr-kpi-meeting { border-left-color: var(--orange-500); }
.smr-kpi-review { border-left-color: var(--red-500); }

/* ---- band filter chip ---- */
.smr-filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px 5px 10px;
  font-size: 12px;
  color: var(--text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  white-space: nowrap;
}

.smr-filter-chip button {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.smr-filter-chip button:hover { color: var(--red-600); }

/* Says the count restarted mid-month, so the number is not read as a bug. */
.smr-reset-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-on-blue, var(--blue-600));
  background: var(--bg-blue, var(--blue-50));
  border: 1px solid var(--blue-200, var(--border-color));
}

/* ---- toolbar ---- */
.smr-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.smr-search-wrap {
  position: relative;
  flex: 1;
  max-width: 420px;
}

.smr-search-wrap i {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 13px;
}

.smr-search-input {
  width: 100%;
  padding: 8px 12px 8px 32px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
}

.smr-refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.smr-refresh-btn:disabled { opacity: 0.6; cursor: default; }

/* ---- record card ---- */
.smr-card {
  padding: 16px;
  margin-bottom: 12px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--gray-400);
  border-radius: var(--smr-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
}

.smr-card[data-level='Call'] { border-left-color: var(--blue-500); }
.smr-card[data-level='Parent Meeting'] { border-left-color: var(--orange-500); }
.smr-card[data-level='Category Review'] { border-left-color: var(--red-500); }
.smr-card[data-status='Closed'] { border-left-color: var(--green-500); opacity: 0.85; }

/* The photo owns a column of its own, so it can be large without taking width
   from the name or from the action buttons below. Fixed square rather than the
   image's own aspect ratio: a roster reads far better when every photo is the
   same shape, and object-fit crops instead of distorting. */
.smr-card-head {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.smr-avatar {
  width: 96px;
  min-width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: var(--smr-radius-sm);
  background: var(--gray-200);
}

.smr-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-600);
  font-weight: 700;
  font-size: 26px;
}

.smr-ident {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.smr-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.smr-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.smr-name:hover { text-decoration: underline; }

.smr-gender-icon { font-size: 12px; }
.smr-gender-female { color: #ff69b4; }
.smr-gender-male { color: #2196f3; }

.smr-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 12px;
  color: var(--text-muted);
}

.smr-meta-id { font-weight: 700; font-variant-numeric: tabular-nums; }
.smr-meta-dot { opacity: 0.5; }

.smr-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.smr-count-badge,
.smr-level-badge,
.smr-closed-badge,
.smr-reopened-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: var(--border-radius-full, 999px);
  font-size: 11.5px;
  font-weight: 700;
}

.smr-count-badge {
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

.smr-level-badge[data-level='Call'] {
  background: var(--bg-blue, #dbeafe);
  color: var(--text-on-blue, #1d4ed8);
}

.smr-level-badge[data-level='Parent Meeting'] {
  background: var(--bg-orange, #ffedd5);
  color: var(--text-on-orange, #c2410c);
}

.smr-level-badge[data-level='Category Review'] {
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

.smr-closed-badge {
  background: var(--bg-green, #dcfce7);
  color: var(--text-on-green, #15803d);
}

.smr-reopened-badge {
  background: var(--bg-purple, #f3e8ff);
  color: var(--text-on-purple, #7e22ce);
}

/* ---- tally ---- */
.smr-tally {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.smr-tally-chip {
  font-size: 11.5px;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-100));
  border-radius: 4px;
  padding: 3px 8px;
}

.smr-tally-chip b { font-weight: 700; color: var(--heading-color); }
.smr-tally-chip.is-zero { opacity: 0.5; }

.smr-link-btn {
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

/* ---- mistake detail ---- */
.smr-detail {
  margin-top: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
  overflow-x: auto;
}

.smr-detail-loading,
.smr-detail-empty {
  padding: 12px;
  font-size: 12.5px;
  color: var(--text-muted);
  margin: 0;
}

.smr-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  min-width: 420px;
}

.smr-detail-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-50));
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.smr-detail-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: top;
}

.smr-detail-table tr:last-child td { border-bottom: none; }
.smr-detail-date { white-space: nowrap; font-variant-numeric: tabular-nums; }
.smr-detail-what { color: var(--text-muted); }

.smr-detail-remarks {
  display: block;
  margin-top: 2px;
  font-size: 11.5px;
  opacity: 0.85;
}

.smr-result-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--border-radius-full, 999px);
  font-size: 11px;
  font-weight: 700;
  background: var(--bg-gray, var(--gray-100));
  color: var(--text-on-gray);
}

.smr-result-badge[data-result='Fail'],
.smr-result-badge[data-result='Critical'] {
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

.smr-result-badge[data-result='Discipline'],
.smr-result-badge[data-result='Incomplete'] {
  background: var(--bg-orange, #ffedd5);
  color: var(--text-on-orange, #c2410c);
}

/* ---- pending / done ---- */
.smr-pending {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
}

.smr-pending-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.smr-pending-chip {
  padding: 3px 9px;
  border-radius: var(--border-radius-full, 999px);
  font-size: 11.5px;
  font-weight: 600;
  background: var(--bg-orange, #ffedd5);
  color: var(--text-on-orange, #c2410c);
}

.smr-pending-clear {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--green-600, #16a34a);
}

.smr-done {
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--subtle-fg, var(--gray-50));
  border-radius: var(--smr-radius-sm);
  font-size: 12.5px;
  color: var(--text-color);
}

.smr-done-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 2px 0;
}

.smr-done-row i { color: var(--text-muted); margin-top: 2px; }

.smr-done-notes {
  margin: 2px 0 6px 22px;
  font-size: 12px;
  font-style: italic;
  color: var(--text-muted);
}

.smr-photo-thumb {
  display: inline-block;
  margin-top: 6px;
  border-radius: var(--smr-radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.smr-photo-thumb img {
  display: block;
  width: 84px;
  height: 84px;
  object-fit: cover;
}

/* ---- actions ---- */
.smr-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

.smr-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 14px;
  font-size: 12.5px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}

.smr-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.smr-btn-primary {
  background: var(--blue-500);
  border-color: var(--blue-500);
  color: #fff;
}

.smr-btn-done {
  background: var(--bg-green, #dcfce7);
  border-color: var(--bg-green, #dcfce7);
  color: var(--text-on-green, #15803d);
}

.smr-btn-close {
  margin-left: auto;
  background: var(--green-600, #16a34a);
  border-color: var(--green-600, #16a34a);
  color: #fff;
}

/* Disabled Close still has to read as a button rather than as a blank gap --
   it is the one staff look for, and its being unavailable is the message. */
.smr-btn-close:disabled {
  background: var(--subtle-fg, var(--gray-100));
  border-style: dashed;
  border-color: var(--gray-400);
  color: var(--text-muted);
  opacity: 1;
}

.smr-btn-ghost { margin-left: auto; }

.smr-closed-note { font-size: 12px; color: var(--text-muted); }

/* ---- empty / skeleton ---- */
.smr-empty-state {
  padding: 44px 20px;
  text-align: center;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius);
}

.smr-empty-icon { font-size: 34px; color: var(--text-muted); opacity: 0.6; }
.smr-empty-state h4 { margin: 12px 0 4px; font-size: 15px; color: var(--heading-color); }
.smr-empty-state p { margin: 0; font-size: 13px; color: var(--text-muted); }

.smr-skeleton-bar {
  height: 12px;
  margin-bottom: 10px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: smr-shimmer 1.4s ease infinite;
}

@keyframes smr-shimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* ---- modals ---- */
.smr-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.45);
}

.smr-modal {
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  background: var(--card-bg);
  border-radius: var(--smr-radius);
  box-shadow: var(--shadow-lg, 0 10px 30px rgba(0, 0, 0, 0.2));
}

.smr-modal-wide { max-width: 560px; }

.smr-modal h3 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: var(--heading-color);
}

.smr-modal-hint {
  margin: 0 0 14px;
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.5;
}

.smr-modal-label {
  display: block;
  margin: 12px 0 5px;
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.smr-req { color: var(--red-500); }

.smr-check {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-color);
  cursor: pointer;
}

.smr-check input { width: 17px; height: 17px; accent-color: var(--blue-500); }

.smr-review-block {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
}

.smr-review-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.smr-review-title { font-size: 13.5px; font-weight: 700; color: var(--heading-color); }
.smr-review-count { font-size: 11.5px; font-weight: 600; color: var(--text-muted); }

.smr-photo-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.smr-photo-preview {
  width: 88px;
  height: 88px;
  object-fit: cover;
  border-radius: var(--smr-radius-sm);
  border: 1px solid var(--border-color);
}

.smr-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 12.5px;
  font-weight: 600;
  border: 1px dashed var(--border-color);
  border-radius: var(--smr-radius-sm);
  color: var(--text-color);
  cursor: pointer;
}

.smr-upload-btn input { display: none; }

.smr-modal-error {
  margin: 12px 0 0;
  padding: 9px 11px;
  font-size: 12.5px;
  border-radius: var(--smr-radius-sm);
  background: var(--bg-red, #fee2e2);
  color: var(--text-on-red, #b91c1c);
}

.smr-modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.smr-btn-lg {
  flex: 1;
  padding: 11px 16px;
  font-size: 13.5px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: var(--smr-radius-sm);
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.smr-btn-primary-lg {
  background: var(--blue-500);
  border-color: var(--blue-500);
  color: #fff;
}

.smr-btn-primary-lg:disabled { opacity: 0.55; cursor: not-allowed; }

/* ---- tablet ---- */
@media (max-width: 992px) {
  .smr-kpi-grid { grid-template-columns: repeat(2, 1fr); }
}

/* ---- mobile ---- */
@media (max-width: 767px) {
  .smr-manager { padding: 10px; }

  .smr-panel {
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }

  .smr-panel-filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .smr-field { min-width: 0; }
  .smr-panel-status { width: 100%; }
  .smr-seg { flex: 1; justify-content: center; }

  .smr-toolbar { flex-direction: column; align-items: stretch; }
  .smr-search-wrap { max-width: none; }
  .smr-refresh-btn { justify-content: center; }

  .smr-card-head { grid-template-columns: 88px minmax(0, 1fr); gap: 12px; }
  .smr-avatar { width: 88px; min-width: 88px; height: 88px; }

  .smr-link-btn { margin-left: 0; }

  /* Two to a row where two fit, but a lone action takes the whole row rather
     than sitting in half of a rigid grid. */
  .smr-actions { flex-wrap: wrap; }
  .smr-btn { flex: 1 1 42%; }
  .smr-btn-close,
  .smr-btn-ghost { margin-left: 0; flex: 1 1 100%; }
}

@media (max-width: 400px) {
  .smr-card-head { grid-template-columns: 76px minmax(0, 1fr); gap: 10px; }
  .smr-avatar { width: 76px; min-width: 76px; height: 76px; }
  .smr-avatar-fallback { font-size: 22px; }
  .smr-kpi-value { font-size: 19px; }
}
</style>
