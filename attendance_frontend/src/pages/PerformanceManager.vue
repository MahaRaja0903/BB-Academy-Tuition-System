<template>
  <div class="perf-manager">
    <!-- Control panel — same shape as the Attendance Manager, plus Category -->
    <div class="perf-panel">
      <div class="perf-panel-filters">
        <div class="perf-field">
          <label for="perf-standard"><i class="fa fa-graduation-cap"></i> Standard</label>
          <select id="perf-standard" class="form-control" v-model="standard">
            <option value="">Select Standard</option>
            <option v-for="s in standards" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="perf-field">
          <label for="perf-batch"><i class="fa fa-users"></i> Batch</label>
          <select id="perf-batch" class="form-control" v-model="batch" :disabled="!standard">
            <option value="">Select Batch</option>
            <option v-for="b in batches" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
        <div class="perf-field">
          <label for="perf-gender"><i class="fa fa-venus-mars"></i> Gender</label>
          <select id="perf-gender" class="form-control" v-model="gender">
            <option value="">All</option>
            <option value="Boys">Boys</option>
            <option value="Girls">Girls</option>
          </select>
        </div>
        <div class="perf-field perf-field-category">
          <label for="perf-category"><i class="fa" :class="config.icon"></i> Category</label>
          <select id="perf-category" class="form-control" v-model="category">
            <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
      </div>

      <div class="perf-panel-date">
        <span class="perf-date-label"><i class="fa fa-calendar"></i> Performance Date</span>
        <div class="perf-date-stepper">
          <button type="button" class="perf-date-nav-btn" title="Previous Day" @click="stepDate(-1)">
            <i class="fa fa-arrow-left"></i>
          </button>
          <input type="date" class="perf-date-input" v-model="date" :max="serverToday" />
          <button
            type="button"
            class="perf-date-nav-btn"
            title="Next Day"
            :disabled="!canStepForward"
            @click="stepDate(1)"
          >
            <i class="fa fa-arrow-right"></i>
          </button>
        </div>
      </div>

      <div v-if="config.usesSkip" class="perf-panel-actions">
        <!-- "No Study" / "No Test" / "No Maths Test" — the day management
             planned nothing for this batch. Reads back as the same button,
             pressed, so one control both sets and undoes it. -->
        <button
          type="button"
          class="perf-noclass-btn"
          :class="{ 'is-active': noSession }"
          :disabled="!standard || !batch || isFutureDate || !!holiday"
          :title="noSession
            ? `${noSessionLabel} is set for this date — click to undo it`
            : `Management planned no ${category} for this batch on this date`"
          @click="noSession ? undoNoSession() : openNoSessionModal()"
        >
          <i class="fa" :class="noSession ? 'fa-check-square-o' : 'fa-ban'"></i>
          <span>{{ noSessionLabel }}</span>
        </button>
      </div>
    </div>

    <!-- Batch setup: entered once, inherited by every student graded after it -->
    <div v-if="config.usesSyllabus && standard && batch && !noSession" class="perf-setup-card">
      <button type="button" class="perf-setup-head" @click="setupOpen = !setupOpen">
        <span class="perf-setup-title">
          <i class="fa fa-sliders"></i> {{ category }} Setup for the whole batch
        </span>
        <span class="perf-setup-summary">{{ setupSummary }}</span>
        <i class="fa" :class="setupOpen ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
      </button>

      <div v-if="setupOpen" class="perf-setup-body">
        <div class="perf-setup-grid">
          <div class="perf-field">
            <label for="perf-subject">Subject</label>
            <select id="perf-subject" class="form-control" v-model="setup.subject">
              <option value="">Select Subject</option>
              <option v-for="s in subjectOptions(setup.subject)" :key="s" :value="s">{{ s }}</option>
            </select>
            <small v-if="!subjects.length" class="perf-field-hint">
              No subject is mapped to {{ standard }} yet — add one in the Subject master.
            </small>
          </div>
          <div class="perf-field perf-field-lesson">
            <label for="perf-lesson-search">Lesson</label>
            <small v-if="!setup.subject" class="perf-field-hint">
              Pick a Subject first — a lesson belongs to one subject of one standard.
            </small>
            <div v-else class="perf-picker">
              <div class="perf-tag-row">
                <span v-for="name in setup.lessons" :key="name" class="perf-tag">
                  {{ lessonTitle(name) }}
                  <button
                    type="button"
                    class="perf-tag-x"
                    :title="`Remove ${lessonTitle(name)}`"
                    @click="removeLesson(setup.lessons, name)"
                  >
                    <i class="fa fa-times"></i>
                  </button>
                </span>
                <small v-if="!setup.lessons.length" class="perf-field-hint">
                  No lesson picked yet — pick as many as the class covered.
                </small>
              </div>
              <div class="perf-inline-add">
                <input
                  id="perf-lesson-search"
                  type="text"
                  class="form-control"
                  placeholder="Search a lesson, or type a new one to add it"
                  v-model="lessonSearch"
                  @keyup.enter="addLesson"
                />
                <button
                  type="button"
                  class="perf-btn perf-btn-secondary perf-btn-compact"
                  :disabled="!lessonSearch.trim() || addingLesson"
                  @click="addLesson"
                >
                  <i class="fa fa-plus"></i> Add
                </button>
              </div>
              <ul class="perf-option-list">
                <li v-for="l in setupLessonPicks" :key="l.name">
                  <button type="button" @click="pickLesson(setup.lessons, l.name)">
                    <i class="fa fa-plus-circle"></i> {{ l.lesson_name }}
                  </button>
                </li>
                <li v-if="!setupLessonPicks.length" class="perf-option-empty">
                  {{ lessonEmptyText(lessons, setup.lessons, lessonSearch) }}
                </li>
              </ul>
            </div>
            <small v-if="lessonError" class="perf-modal-error">{{ lessonError }}</small>
          </div>
          <div class="perf-field perf-field-wide">
            <label>Portion</label>
            <div class="perf-chip-picker">
              <button
                v-for="p in portionOptions"
                :key="p.name"
                type="button"
                class="perf-chip"
                :class="{ active: setup.portions.includes(p.name) }"
                @click="togglePortion(setup.portions, p.name)"
              >
                {{ p.portion_name }}
              </button>
              <small v-if="!portionOptions.length" class="perf-field-hint">
                The Portion master is empty — add 1M, 2M … in the Portion master.
              </small>
            </div>
          </div>
          <div v-if="config.usesQuestions" class="perf-field">
            <label for="perf-questions">Total Number of Questions</label>
            <input
              id="perf-questions"
              type="number"
              min="0"
              class="form-control"
              v-model.number="setup.total_questions"
            />
          </div>
          <div v-if="config.usesMarks" class="perf-field">
            <label for="perf-total-marks">Total Marks</label>
            <input
              id="perf-total-marks"
              type="number"
              min="0"
              class="form-control"
              v-model.number="setup.total_marks"
            />
          </div>
          <div v-if="config.usesMarks" class="perf-field">
            <label for="perf-pass-marks">Pass Marks</label>
            <input
              id="perf-pass-marks"
              type="number"
              min="0"
              class="form-control"
              v-model.number="setup.pass_marks"
            />
          </div>
        </div>

        <p v-if="config.usesMarks" class="perf-setup-hint">
          <i class="fa fa-info-circle"></i>
          Pass Marks fills in at half the total; change it and your value sticks.
          Enter each student's marks below and the grade is set automatically —
          <strong>Full Mark</strong> from {{ fullMarkFrom || 'one mark below the total' }} up (a
          single dropped mark still counts),
          <strong>Pass Mark</strong> from {{ setup.pass_marks || 'the pass mark' }} up, otherwise
          <strong>Fail</strong>. Tapping a grade always overrides it.
        </p>

        <div class="perf-setup-actions">
          <label class="perf-switch">
            <input type="checkbox" v-model="applyToAll" />
            <span>Also update the {{ gradedCount }} student(s) already graded today</span>
          </label>
          <p v-if="setupError" class="perf-modal-error">{{ setupError }}</p>
          <button class="perf-btn perf-btn-primary" :disabled="setupSaving" @click="saveSetup">
            {{ setupSaving ? 'Saving…' : 'Save Setup' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Notices -->
    <div v-if="isFutureDate" class="perf-alert perf-alert-warn">
      <i class="fa fa-exclamation-triangle"></i>
      This date is in the future — performance can only be recorded up to {{ serverToday }}.
    </div>
    <div v-else-if="saveError" class="perf-alert perf-alert-error">
      <i class="fa fa-exclamation-circle"></i> {{ saveError }}
      <button type="button" @click="saveError = ''"><i class="fa fa-times"></i></button>
    </div>
    <div v-if="setupNotice" class="perf-alert perf-alert-ok">
      <i class="fa fa-check-circle"></i> {{ setupNotice }}
      <button type="button" @click="setupNotice = ''"><i class="fa fa-times"></i></button>
    </div>

    <div v-if="specialClass" class="perf-alert perf-alert-ok">
      <i class="fa fa-check-circle"></i>
      This date is a holiday, but class was conducted
      <strong v-if="specialClass.scope !== 'Entire School'">for this {{ specialClass.scope }}</strong>
      — <em>{{ specialClass.reason }}</em>. Grade as usual.
      <button type="button" class="perf-alert-link" @click="undoSpecialClass">Undo</button>
    </div>

    <!-- KPI cards -->
    <div class="perf-kpi-grid">
      <button
        v-for="kpi in kpis"
        :key="kpi.key"
        type="button"
        class="perf-kpi-card"
        :class="[`perf-tone-${kpi.tone}`, { 'is-active': resultFilter === kpi.filter }]"
        :title="kpi.title"
        @click="toggleFilter(kpi.filter)"
      >
        <span class="perf-kpi-icon"><i class="fa" :class="kpi.icon"></i></span>
        <span class="perf-kpi-body">
          <span class="perf-kpi-value">{{ kpi.value }}</span>
          <span class="perf-kpi-label">{{ kpi.label }}</span>
        </span>
      </button>
    </div>

    <!-- Toolbar -->
    <div class="perf-toolbar">
      <div class="perf-search-wrap">
        <i class="fa fa-search"></i>
        <input
          type="text"
          class="perf-search-input"
          placeholder="Search student name or ID"
          v-model="search"
        />
      </div>
      <div class="perf-toolbar-right">
        <span v-if="resultFilter" class="perf-filter-chip">
          <span>Showing <strong>{{ resultFilter }}</strong></span>
          <button type="button" title="Clear filter" @click="resultFilter = null">
            <i class="fa fa-times"></i>
          </button>
        </span>
        <div class="perf-switch">
          <input
            id="perf-select-all"
            type="checkbox"
            :checked="allVisibleSelected"
            :indeterminate.prop="someVisibleSelected"
            @change="toggleSelectAll($event.target.checked)"
          />
          <label for="perf-select-all">Select All</label>
        </div>
        <div class="perf-switch">
          <input id="perf-show-completed" type="checkbox" v-model="showCompleted" />
          <label for="perf-show-completed">Show Completed</label>
        </div>
      </div>
    </div>

    <!-- Bulk selection action bar -->
    <div v-if="selected.size > 0" class="perf-bulk-bar">
      <span class="perf-bulk-count">
        <i class="fa fa-check-square-o"></i> <span>{{ selected.size }}</span> Students Selected
      </span>
      <div class="perf-bulk-actions">
        <button
          v-for="opt in config.results"
          :key="opt.value"
          class="perf-bulk-btn"
          :class="`perf-tone-${opt.tone}`"
          @click="bulkMark(opt.value)"
        >
          <i class="fa" :class="opt.icon"></i> {{ opt.value }}
        </button>
        <button class="perf-bulk-btn perf-bulk-clear" @click="selected.clear()">Clear</button>
      </div>
    </div>

    <!-- Holiday card -->
    <div v-if="holiday" class="perf-holiday-card">
      <div class="perf-holiday-icon"><i class="fa fa-calendar-plus-o"></i></div>
      <div class="perf-holiday-content">
        <h4>Holiday</h4>
        <p><span class="perf-holiday-key">Type</span><span>{{ holiday.holiday_type }}</span></p>
        <p><span class="perf-holiday-key">Reason</span><span>{{ holiday.reason }}</span></p>
        <p class="perf-holiday-note">No performance is recorded for this date.</p>
        <button
          type="button"
          class="perf-btn perf-btn-secondary perf-holiday-action"
          @click="openSpecialModal"
        >
          <i class="fa fa-check-circle"></i> Class was conducted — record anyway
        </button>
      </div>
    </div>

    <!-- No Study / No Test card — nothing was planned, so nothing is graded -->
    <div v-else-if="noSession" class="perf-holiday-card perf-noclass-card">
      <div class="perf-holiday-icon"><i class="fa fa-ban"></i></div>
      <div class="perf-holiday-content">
        <h4>{{ noSessionLabel }}</h4>
        <p>
          <span class="perf-holiday-key">Batch</span>
          <span>{{ standard }} — {{ batch }} on {{ date }}</span>
        </p>
        <p v-if="session?.no_session_reason">
          <span class="perf-holiday-key">Reason</span><span>{{ session.no_session_reason }}</span>
        </p>
        <p class="perf-holiday-note">
          Management planned no {{ category }} for this batch on this date, so no student is
          graded for it. Attendance and the other categories are unaffected.
        </p>
        <button
          type="button"
          class="perf-btn perf-btn-secondary perf-holiday-action"
          :disabled="noSessionModal.saving"
          @click="undoNoSession"
        >
          <i class="fa fa-undo"></i> {{ category }} was held after all — undo
        </button>
      </div>
    </div>

    <!-- Student table / cards -->
    <div v-else class="perf-table-card">
      <div class="perf-table-scroll">
        <table class="perf-table">
          <thead>
            <tr>
              <th class="perf-col-select"></th>
              <th class="perf-col-name">Student Name</th>
              <th class="perf-col-id">Student ID &amp; Stats</th>
              <th v-if="config.usesMarks" class="perf-col-marks">Marks</th>
              <th class="perf-col-actions">{{ category }} Result</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="i in 4" :key="`sk${i}`" class="perf-skeleton-row">
                <td :colspan="columnCount">
                  <div class="perf-skeleton-bar" style="width: 40%; margin-bottom: 8px"></div>
                  <div class="perf-skeleton-bar" style="width: 70%"></div>
                </td>
              </tr>
            </template>

            <tr v-else-if="emptyState" class="perf-placeholder-row">
              <td :colspan="columnCount">
                <div class="perf-empty-state" :class="emptyState.cls">
                  <div class="perf-empty-icon"><i class="fa" :class="emptyState.icon"></i></div>
                  <h4>{{ emptyState.title }}</h4>
                  <p>{{ emptyState.text }}</p>
                  <router-link v-if="emptyState.linkToAttendance" class="perf-empty-link" :to="{ name: 'AttendanceManager' }">
                    <i class="fa fa-check-circle"></i> Go to Attendance Manager
                  </router-link>
                </div>
              </td>
            </tr>

            <tr
              v-for="s in (loading || emptyState ? [] : visibleStudents)"
              :key="s.student_id"
              class="perf-student-row"
              :data-tone="toneOf(s.result)"
            >
              <td class="perf-td-select">
                <input
                  type="checkbox"
                  class="perf-row-select"
                  :checked="selected.has(s.student_id)"
                  @change="toggleSelect(s.student_id)"
                />
              </td>
              <td class="perf-td-name">
                <div class="perf-student-profile">
                  <div class="perf-student-name-wrap">
                    <router-link
                      class="perf-student-name student-link"
                      :to="{ name: 'StudentProfile', query: { student: s.student_id } }"
                      title="Open this student's profile"
                    >{{ s.student_name }}</router-link>
                    <i
                      v-if="s.gender"
                      class="fa perf-gender-icon"
                      :class="[
                        s.gender === 'Girls' ? 'fa-female' : 'fa-male',
                        s.gender === 'Girls' ? 'perf-gender-icon-female' : 'perf-gender-icon-male',
                      ]"
                      :title="s.gender"
                    ></i>
                    <i
                      v-if="s.is_birthday"
                      class="fa fa-birthday-cake perf-birthday-icon"
                      title="Birthday Today!"
                    ></i>
                    <span
                      v-if="s.is_temporary"
                      class="perf-badge-temp"
                      :title="`Temporarily moved from Batch ${s.original_batch}`"
                    >
                      <i class="fa fa-exchange"></i> Actual Batch: {{ s.original_batch }}
                    </span>
                  </div>
                  <img
                    v-if="s.image"
                    class="perf-avatar"
                    :src="s.image"
                    :alt="s.student_name"
                    loading="lazy"
                  />
                  <div v-else class="perf-avatar perf-avatar-fallback">
                    {{ initials(s.student_name) }}
                  </div>
                </div>
              </td>
              <td class="perf-td-id">
                <div class="perf-student-id">{{ s.student_id }}</div>
                <div class="perf-student-stats">
                  <span
                    v-for="chip in monthlyChips(s)"
                    :key="chip.key"
                    class="perf-stat-chip"
                    :class="`perf-tone-${chip.tone}`"
                    :title="`${chip.key} this month`"
                  >{{ chip.key }} Count <b>{{ chip.count }}</b></span>
                  <span v-if="!monthlyChips(s).length" class="perf-stat-chip perf-stat-none">
                    Nothing recorded this month
                  </span>
                </div>
              </td>
              <td v-if="config.usesMarks" class="perf-td-marks">
                <span class="perf-inline-label">Marks</span>
                <div class="perf-marks-wrap">
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    class="perf-marks-input"
                    :max="s.total_marks || undefined"
                    :value="s.skipped ? '' : s.marks_obtained"
                    :disabled="savingStudent === s.student_id || isFutureDate || !!s.skipped"
                    :placeholder="s.skipped ? 'Skipped' : '—'"
                    @change="onMarksChange(s, $event.target.value)"
                  />
                  <span class="perf-marks-total">/ {{ s.total_marks || setup.total_marks || 0 }}</span>
                </div>
              </td>
              <td class="perf-td-actions">
                <div class="perf-status-group">
                  <!-- Handler sits on the radio's change, not the label's click:
                       a label wrapping an input fires click twice and would send
                       two concurrent saves. Same fix as the attendance page. -->
                  <label
                    v-for="opt in config.results"
                    :key="opt.value"
                    class="perf-status-btn"
                    :class="[
                      `perf-tone-${opt.tone}`,
                      { active: s.result === opt.value },
                      { 'is-saving': savingStudent === s.student_id },
                    ]"
                  >
                    <input
                      type="radio"
                      :name="`perf_${s.student_id}`"
                      :value="opt.value"
                      :checked="s.result === opt.value"
                      :disabled="savingStudent === s.student_id"
                      @change="onResultClick(s, opt.value)"
                    />
                    <i class="fa" :class="opt.icon"></i><span>{{ opt.value }}</span>
                  </label>
                </div>

                <div class="perf-row-meta">
                  <label v-if="config.usesSkip" class="perf-skip-toggle" :class="{ active: !!s.skipped }">
                    <input
                      type="checkbox"
                      :checked="!!s.skipped"
                      :disabled="savingStudent === s.student_id || isFutureDate"
                      @change="onSkipToggle(s, $event.target.checked)"
                    />
                    <span>{{ config.skipLabel }}</span>
                  </label>
                  <span v-if="config.usesSyllabus && rowSyllabus(s)" class="perf-row-syllabus">
                    <i class="fa fa-book"></i> {{ rowSyllabus(s) }}
                  </span>
                  <button type="button" class="perf-row-edit" @click="openDetail(s)">
                    <i class="fa fa-pencil"></i> Details
                  </button>
                </div>

                <div v-if="s.skipped && s.remarks" class="perf-skip-msg">
                  <i class="fa fa-info-circle"></i> {{ s.remarks }}
                </div>

                <div v-if="s.behaviour_reasons.length" class="perf-reason-msg">
                  <i class="fa fa-exclamation-circle"></i> {{ s.behaviour_reasons.join(', ') }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Behaviour reason modal (single + bulk) -->
    <div v-if="reasonModal.open" class="perf-modal-backdrop" @click.self="closeReasonModal">
      <div class="perf-modal">
        <h3>
          {{ reasonModal.bulk ? `Mark ${selected.size} students ${reasonModal.result}` : `Mark ${reasonModal.result}` }}
        </h3>
        <p class="perf-modal-sub">
          Pick what the student did from the master list. At least one is required.
        </p>

        <div class="perf-reason-list">
          <label v-for="r in reasonOptions" :key="r.name" class="perf-reason-item">
            <input
              type="checkbox"
              :checked="reasonModal.selected.has(r.name)"
              @change="toggleReason(r.name)"
            />
            <span>{{ r.reason_name }}</span>
            <em v-if="r.severity !== 'Both'">{{ r.severity }}</em>
          </label>
          <p v-if="!reasonOptions.length" class="perf-modal-warn">
            The Behaviour Reason master list is empty — add the first one below.
          </p>
        </div>

        <div class="perf-reason-add">
          <input
            type="text"
            class="form-control"
            placeholder="Add a new reason to the master list"
            v-model="reasonModal.newReason"
            @keyup.enter="addReason"
          />
          <button
            class="perf-btn perf-btn-secondary perf-btn-compact"
            :disabled="!reasonModal.newReason.trim() || reasonModal.adding"
            @click="addReason"
          >
            <i class="fa fa-plus"></i> Add
          </button>
        </div>

        <label class="perf-modal-label">Remarks</label>
        <textarea class="form-control perf-textarea" rows="2" v-model="reasonModal.remarks"></textarea>

        <p v-if="reasonModal.error" class="perf-modal-error">{{ reasonModal.error }}</p>

        <div class="perf-modal-actions">
          <button class="perf-btn perf-btn-secondary" @click="closeReasonModal">Cancel</button>
          <button
            class="perf-btn perf-btn-primary"
            :disabled="reasonModal.selected.size === 0 || reasonModal.saving"
            @click="confirmReasons"
          >
            {{ reasonModal.saving ? 'Saving…' : `Mark ${reasonModal.result}` }}
          </button>
        </div>
      </div>
    </div>

    <!-- No Study / No Test modal -->
    <div v-if="noSessionModal.open" class="perf-modal-backdrop" @click.self="noSessionModal.open = false">
      <div class="perf-modal">
        <h3>{{ noSessionLabel }}</h3>
        <p class="perf-modal-sub">
          Records that management planned no {{ category }} for
          <strong>{{ standard }} — {{ batch }}</strong> on <strong>{{ date }}</strong>.
          The day is left ungraded for this category; attendance and the other categories
          carry on as usual.
        </p>

        <label class="perf-modal-label">Reason</label>
        <textarea
          class="form-control perf-textarea"
          rows="2"
          :placeholder="`Why was no ${category} planned?`"
          v-model="noSessionModal.reason"
        ></textarea>

        <p v-if="gradedCount" class="perf-modal-warn">
          {{ gradedCount }} student(s) already have a {{ category }} result for this date. Clear
          those first — a day with no {{ category }} cannot hold results.
        </p>
        <p v-if="noSessionModal.error" class="perf-modal-error">{{ noSessionModal.error }}</p>

        <div class="perf-modal-actions">
          <button class="perf-btn perf-btn-secondary" @click="noSessionModal.open = false">Cancel</button>
          <button
            class="perf-btn perf-btn-primary"
            :disabled="noSessionModal.saving"
            @click="confirmNoSession"
          >
            {{ noSessionModal.saving ? 'Saving…' : noSessionLabel }}
          </button>
        </div>
      </div>
    </div>

    <!-- "Class was conducted" modal -->
    <div v-if="specialModal.open" class="perf-modal-backdrop" @click.self="specialModal.open = false">
      <div class="perf-modal">
        <h3>Class Conducted on a Holiday</h3>
        <p class="perf-modal-sub">
          {{ date }} is a holiday, but a class was taken. Recording that re-opens the day for
          attendance and performance — for the scope you pick and nobody else. Mark attendance
          first; only students marked Present can be graded.
        </p>

        <label class="perf-modal-label">Who sat the class <span class="perf-required">*</span></label>
        <select class="form-control" v-model="specialModal.scope">
          <option value="Standard + Batch">Only {{ standard }} — Batch {{ batch }}</option>
          <option value="Standard">All batches of {{ standard }}</option>
          <option value="Entire School">The entire school</option>
        </select>

        <label class="perf-modal-label">Reason <span class="perf-required">*</span></label>
        <textarea
          class="form-control perf-textarea"
          rows="2"
          placeholder="Why was class held on a holiday?"
          v-model="specialModal.reason"
        ></textarea>

        <p v-if="specialModal.error" class="perf-modal-error">{{ specialModal.error }}</p>

        <div class="perf-modal-actions">
          <button class="perf-btn perf-btn-secondary" @click="specialModal.open = false">Cancel</button>
          <button
            class="perf-btn perf-btn-primary"
            :disabled="!specialModal.reason.trim() || specialModal.saving"
            @click="confirmSpecialClass"
          >
            {{ specialModal.saving ? 'Saving…' : 'Class Was Conducted' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Skip Test / Study modal — a skip is only ever recorded with a reason,
         and with what this student did instead of the planned session -->
    <div v-if="skipModal.open" class="perf-modal-backdrop" @click.self="closeSkipModal">
      <div class="perf-modal">
        <h3>{{ config.skipLabel }} — {{ skipModal.student?.student_name }}</h3>
        <p class="perf-modal-sub">
          The student is excused from today's {{ category }}. It counts as neither a pass nor a
          fail, and is left out of the monthly percentage.
        </p>

        <template v-if="config.usesSyllabus">
          <p class="perf-modal-sub perf-modal-sub-tight">
            <i class="fa fa-book"></i>
            This starts from what the batch was set up to cover. Change it to what
            <strong>{{ skipModal.student?.student_name }}</strong> actually studied instead — it is
            saved on this student's row only.
          </p>

          <label class="perf-modal-label">Subject</label>
          <select class="form-control" v-model="skipModal.subject">
            <option value="">Select Subject</option>
            <option v-for="sub in subjectOptions(skipModal.subject)" :key="sub" :value="sub">
              {{ sub }}
            </option>
          </select>

          <label class="perf-modal-label">Lesson</label>
          <small v-if="!skipModal.subject" class="perf-field-hint">
            Pick a Subject first — a lesson belongs to one subject of one standard.
          </small>
          <div v-else class="perf-picker">
            <div class="perf-tag-row">
              <span v-for="name in skipModal.lessons" :key="name" class="perf-tag">
                {{ lessonTitle(name, skipLessons) }}
                <button
                  type="button"
                  class="perf-tag-x"
                  :title="`Remove ${lessonTitle(name, skipLessons)}`"
                  @click="removeLesson(skipModal.lessons, name)"
                >
                  <i class="fa fa-times"></i>
                </button>
              </span>
              <small v-if="!skipModal.lessons.length" class="perf-field-hint">
                No lesson picked yet.
              </small>
            </div>
            <input
              type="text"
              class="form-control"
              placeholder="Search a lesson"
              v-model="skipLessonSearch"
            />
            <ul class="perf-option-list">
              <li v-for="l in skipLessonPicks" :key="l.name">
                <button type="button" @click="pickLesson(skipModal.lessons, l.name)">
                  <i class="fa fa-plus-circle"></i> {{ l.lesson_name }}
                </button>
              </li>
              <li v-if="!skipLessonPicks.length" class="perf-option-empty">
                {{ lessonEmptyText(skipLessons, skipModal.lessons, skipLessonSearch) }}
              </li>
            </ul>
          </div>

          <label class="perf-modal-label">Portion</label>
          <div class="perf-chip-picker">
            <button
              v-for="pt in portionOptions"
              :key="pt.name"
              type="button"
              class="perf-chip"
              :class="{ active: skipModal.portions.includes(pt.name) }"
              @click="togglePortion(skipModal.portions, pt.name)"
            >
              {{ pt.portion_name }}
            </button>
          </div>
        </template>

        <label class="perf-modal-label">Remarks <span class="perf-required">*</span></label>
        <textarea
          class="form-control perf-textarea"
          rows="3"
          placeholder="Why was this student excused?"
          v-model="skipModal.remarks"
        ></textarea>

        <p v-if="skipModal.error" class="perf-modal-error">{{ skipModal.error }}</p>

        <div class="perf-modal-actions">
          <button class="perf-btn perf-btn-secondary" @click="closeSkipModal">Cancel</button>
          <button
            class="perf-btn perf-btn-primary"
            :disabled="!skipModal.remarks.trim() || skipModal.saving"
            @click="confirmSkip"
          >
            {{ skipModal.saving ? 'Saving…' : config.skipLabel }}
          </button>
        </div>
      </div>
    </div>

    <!-- Per-student override modal -->
    <div v-if="detailModal.open" class="perf-modal-backdrop" @click.self="detailModal.open = false">
      <div class="perf-modal">
        <h3>{{ detailModal.student?.student_name }}</h3>
        <p class="perf-modal-sub">
          These start from the batch setup. Anything changed here applies to this student only.
        </p>

        <template v-if="config.usesSyllabus">
          <label class="perf-modal-label">Subject</label>
          <select class="form-control" v-model="detailModal.subject">
            <option value="">Select Subject</option>
            <option v-for="s in subjectOptions(detailModal.subject)" :key="s" :value="s">
              {{ s }}
            </option>
          </select>

          <label class="perf-modal-label">Lesson</label>
          <small v-if="!detailModal.subject" class="perf-field-hint">
            Pick a Subject first — a lesson belongs to one subject of one standard.
          </small>
          <div v-else class="perf-picker">
            <div class="perf-tag-row">
              <span v-for="name in detailModal.lessons" :key="name" class="perf-tag">
                {{ lessonTitle(name, detailLessons) }}
                <button
                  type="button"
                  class="perf-tag-x"
                  :title="`Remove ${lessonTitle(name, detailLessons)}`"
                  @click="removeLesson(detailModal.lessons, name)"
                >
                  <i class="fa fa-times"></i>
                </button>
              </span>
              <small v-if="!detailModal.lessons.length" class="perf-field-hint">
                No lesson picked yet.
              </small>
            </div>
            <input
              type="text"
              class="form-control"
              placeholder="Search a lesson"
              v-model="detailLessonSearch"
            />
            <ul class="perf-option-list">
              <li v-for="l in detailLessonPicks" :key="l.name">
                <button type="button" @click="pickLesson(detailModal.lessons, l.name)">
                  <i class="fa fa-plus-circle"></i> {{ l.lesson_name }}
                </button>
              </li>
              <li v-if="!detailLessonPicks.length" class="perf-option-empty">
                {{ lessonEmptyText(detailLessons, detailModal.lessons, detailLessonSearch) }}
              </li>
            </ul>
          </div>

          <label class="perf-modal-label">Portion</label>
          <div class="perf-chip-picker">
            <button
              v-for="p in portionOptions"
              :key="p.name"
              type="button"
              class="perf-chip"
              :class="{ active: detailModal.portions.includes(p.name) }"
              @click="togglePortion(detailModal.portions, p.name)"
            >
              {{ p.portion_name }}
            </button>
          </div>
        </template>

        <template v-if="config.usesQuestions">
          <label class="perf-modal-label">Total Number of Questions</label>
          <input type="number" min="0" class="form-control" v-model.number="detailModal.total_questions" />
        </template>

        <template v-if="config.usesMarks">
          <label class="perf-modal-label">Total Marks</label>
          <input type="number" min="0" class="form-control" v-model.number="detailModal.total_marks" />

          <label class="perf-modal-label">Pass Marks</label>
          <input type="number" min="0" class="form-control" v-model.number="detailModal.pass_marks" />

          <label class="perf-modal-label">Marks Obtained</label>
          <input type="number" min="0" class="form-control" v-model.number="detailModal.marks_obtained" />
        </template>

        <label class="perf-modal-label">
          Remarks
          <span v-if="detailModal.student?.skipped" class="perf-required">*</span>
        </label>
        <textarea class="form-control perf-textarea" rows="2" v-model="detailModal.remarks"></textarea>
        <small v-if="detailModal.student?.skipped" class="perf-field-hint">
          Required — this student is marked {{ config.skipLabel }}.
        </small>

        <p v-if="detailModal.error" class="perf-modal-error">{{ detailModal.error }}</p>
        <p v-if="!detailModal.student?.result" class="perf-modal-warn">
          Pick a {{ category }} result for this student first — the details are saved with it.
        </p>

        <div class="perf-modal-actions">
          <button class="perf-btn perf-btn-secondary" @click="detailModal.open = false">Cancel</button>
          <button
            class="perf-btn perf-btn-primary"
            :disabled="detailModal.saving || !detailModal.student?.result"
            @click="saveDetail"
          >
            {{ detailModal.saving ? 'Saving…' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { serverToday, loadServerToday, formatDate, addDays } from '@/data/serverDate'

// Mirrors bb_academy/performance_config.py — the server validates against its
// own copy, so any change here needs the same change there.
//
// "Maths Test" and "Accounts Test" are the same test under the name the
// standard actually sits it under; `categoryOptions` offers exactly one of them.
const TEST_RESULTS = [
  { value: 'Full Mark', icon: 'fa-trophy', tone: 'good' },
  { value: 'Pass Mark', icon: 'fa-check-circle', tone: 'mid' },
  { value: 'Fail', icon: 'fa-times-circle', tone: 'bad' },
]

const SKIP_RESULT = 'Skipped'
const SKIP_OPTION = { value: SKIP_RESULT, icon: 'fa-ban', tone: 'skip' }

const CATEGORY_CONFIG = {
  Study: {
    icon: 'fa-book',
    usesSyllabus: true,
    usesQuestions: true,
    usesMarks: false,
    usesReasons: false,
    usesSkip: true,
    skipLabel: 'Skip Study',
    results: [
      { value: 'Excellent', icon: 'fa-star', tone: 'good' },
      { value: 'Completed', icon: 'fa-check-circle', tone: 'mid' },
      { value: 'Incomplete', icon: 'fa-times-circle', tone: 'bad' },
    ],
  },
  Test: {
    icon: 'fa-file-text-o',
    usesSyllabus: true,
    usesQuestions: false,
    usesMarks: true,
    usesReasons: false,
    usesSkip: true,
    skipLabel: 'Skip Test',
    results: TEST_RESULTS,
  },
  'Maths Test': {
    icon: 'fa-calculator',
    usesSyllabus: true,
    usesQuestions: false,
    usesMarks: true,
    usesReasons: false,
    usesSkip: true,
    skipLabel: 'Skip Test',
    results: TEST_RESULTS,
  },
  'Accounts Test': {
    icon: 'fa-inr',
    usesSyllabus: true,
    usesQuestions: false,
    usesMarks: true,
    usesReasons: false,
    usesSkip: true,
    skipLabel: 'Skip Test',
    results: TEST_RESULTS,
  },
  Behaviour: {
    icon: 'fa-smile-o',
    usesSyllabus: false,
    usesQuestions: false,
    usesMarks: false,
    usesReasons: true,
    usesSkip: false,
    skipLabel: '',
    results: [
      { value: 'Good', icon: 'fa-smile-o', tone: 'good' },
      { value: 'Bad', icon: 'fa-frown-o', tone: 'mid' },
      { value: 'Worst', icon: 'fa-exclamation-triangle', tone: 'bad' },
    ],
  },
}

// Every standard sits Study, Test and Behaviour; the subject test is whichever
// one the Standard master names (Accounts Test for Commerce).
const SHARED_CATEGORIES = ['Study', 'Test']
const SUBJECT_TESTS = ['Maths Test', 'Accounts Test']
const DEFAULT_SUBJECT_TEST = 'Maths Test'

// Half the paper passes — the same rule bb_academy/performance_config.py applies.
function halfOf(total) {
  return total ? Math.round((total / 2) * 2) / 2 : 0
}

// Grades the teacher must justify against the Behaviour Reason master list.
const REASON_REQUIRED = ['Bad', 'Worst']

const standards = ref([])
const batches = ref([])
// Subject master, narrowed to the picked standard.
const subjects = ref([])
// Lesson master, narrowed to the standard + the subject the setup card holds.
const lessons = ref([])
// The same list for the per-student modal, which can be on another subject.
const detailLessons = ref([])
// And again for the skip modal, where the subject is whatever the student did
// instead of the planned session.
const skipLessons = ref([])
// Portion master — the same 1M / 2M / 5M list for every standard.
const portionOptions = ref([])
// Which subject test this standard sits. Server-decided, so the two never drift.
const subjectTest = ref(DEFAULT_SUBJECT_TEST)
const standard = ref('')
const batch = ref('')
const gender = ref('')
const category = ref('Study')
const date = ref(serverToday.value)

const students = ref([])
const summary = ref({})
// The batch setup row for the loaded date/category. It also carries the
// "No Study / No Test" flag, so the screen reads both off one object.
const session = ref(null)
const holiday = ref(null)
// Set when this date is a holiday a class was taken on anyway. The server then
// treats the day as ordinary, so `holiday` comes back null and this is what
// tells the screen why the students are listed.
const specialClass = ref(null)
const loading = ref(false)
const totalStudents = ref(0)
const attendanceMarked = ref(0)

const saveError = ref('')
const savingStudent = ref(null)
const bulkSaving = ref(false)

const search = ref('')
const resultFilter = ref(null)
// Ships unchecked, like the attendance page: only ungraded students are listed
// until the user opts in to seeing the ones already done.
const showCompleted = ref(false)
const selected = reactive(new Set())

const setupOpen = ref(false)
const setup = reactive({
  subject: '',
  lessons: [],
  portions: [],
  total_questions: 0,
  total_marks: 0,
  pass_marks: 0,
})
// One box does both jobs: it filters the list below, and its text is what the
// Add button pushes into the Lesson master.
const lessonSearch = ref('')
const detailLessonSearch = ref('')
const skipLessonSearch = ref('')
const addingLesson = ref(false)
const lessonError = ref('')

// Raised while a load writes Subject and Lesson in the same tick. Without it the
// "subject changed, so the lessons no longer apply" rule below would fire on
// our own write and drop the lessons we just loaded.
let syncingSyllabus = false

function syncSyllabus(apply) {
  syncingSyllabus = true
  apply()
  nextTick(() => {
    syncingSyllabus = false
  })
}
const applyToAll = ref(false)
const setupSaving = ref(false)
const setupError = ref('')
const setupNotice = ref('')

const behaviourReasons = ref([])
const reasonModal = reactive({
  open: false,
  bulk: false,
  student: null,
  result: '',
  selected: new Set(),
  remarks: '',
  newReason: '',
  adding: false,
  saving: false,
  error: '',
})

const noSessionModal = reactive({
  open: false,
  reason: '',
  saving: false,
  error: '',
})

const specialModal = reactive({
  open: false,
  scope: 'Standard + Batch',
  reason: '',
  saving: false,
  error: '',
})

const skipModal = reactive({
  open: false,
  student: null,
  subject: '',
  lessons: [],
  portions: [],
  remarks: '',
  saving: false,
  error: '',
})

const detailModal = reactive({
  open: false,
  student: null,
  subject: '',
  lessons: [],
  portions: [],
  total_questions: 0,
  total_marks: 0,
  pass_marks: 0,
  marks_obtained: 0,
  remarks: '',
  saving: false,
  error: '',
})

const standardsResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const batchesResource = createResource({ url: 'bb_tution_management.bb_academy.lookups.get_options' })
const studentsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_performance_students',
})
const saveResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.save_student_performance',
})
const saveBulkResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.save_bulk_performance',
})
const saveSessionResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.save_performance_session',
})
const reasonsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_behaviour_reasons',
})
const subjectsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_subjects',
})
const addReasonResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.add_behaviour_reason',
})
const metaResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_performance_meta',
})
const lessonsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_lessons',
})
const detailLessonsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_lessons',
})
const skipLessonsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_lessons',
})
const portionsResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.get_portions',
})
const addLessonResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.add_lesson',
})
const clearResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.clear_student_performance',
})
const noSessionResource = createResource({
  url: 'bb_tution_management.bb_academy.performance.set_no_session',
})
const specialClassResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.assign_special_class_day',
})
const removeSpecialClassResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.remove_special_class_day',
})

const config = computed(() => CATEGORY_CONFIG[category.value] || CATEGORY_CONFIG.Study)

// "No Study" / "No Test" / "No Maths Test" / "No Accounts Test" — the button
// is named after whichever category is on screen.
const noSessionLabel = computed(() => `No ${category.value}`)
const noSession = computed(() => !!session.value?.no_session)
const columnCount = computed(() => (config.value.usesMarks ? 5 : 4))

// The standard sits exactly one subject test, so only that one is offered.
const categoryOptions = computed(() => [...SHARED_CATEGORIES, subjectTest.value, 'Behaviour'])

// The grade buttons stay three wide; Skipped is set by its own checkbox, but it
// still needs a KPI card and a stat chip of its own.
const allResultOptions = computed(() =>
  config.value.usesSkip ? [...config.value.results, SKIP_OPTION] : config.value.results
)

const fullMarkFrom = computed(() => {
  const total = setup.total_marks || 0
  if (!total) return 0
  const threshold = total - 1
  return threshold <= 0 || threshold <= (setup.pass_marks || 0) ? total : threshold
})

const gradedCount = computed(() => students.value.filter((s) => s.result).length)

function lessonTitle(name, pool) {
  // The setup card and the per-student modal each load their own list and can
  // sit on different subjects, so a name is looked up in both before giving up.
  const hit = [pool, lessons.value, detailLessons.value, skipLessons.value]
    .filter(Boolean)
    .map((p) => p.find((l) => l.name === name))
    .find(Boolean)
  // A lesson neither list carries still has to read as something; the docname
  // carries the title, so it is the honest fallback.
  return hit ? hit.lesson_name : name
}

// What the picker offers: the master minus everything already picked, narrowed
// by whatever is typed in the search box.
function lessonPicks(pool, picked, query) {
  const q = (query || '').trim().toLowerCase()
  return pool.filter(
    (l) => !picked.includes(l.name) && (!q || l.lesson_name.toLowerCase().includes(q))
  )
}

function lessonEmptyText(pool, picked, query) {
  if (!pool.length) return 'No lesson is mapped to this subject yet — type one above and add it.'
  if ((query || '').trim()) return 'No lesson matches — type the full title above to add it.'
  if (picked.length >= pool.length) return 'Every lesson for this subject is already picked.'
  return 'No lesson left to pick.'
}

const setupLessonPicks = computed(() =>
  lessonPicks(lessons.value, setup.lessons, lessonSearch.value)
)

const detailLessonPicks = computed(() =>
  lessonPicks(detailLessons.value, detailModal.lessons, detailLessonSearch.value)
)

const skipLessonPicks = computed(() =>
  lessonPicks(skipLessons.value, skipModal.lessons, skipLessonSearch.value)
)

function portionTitle(name) {
  const hit = portionOptions.value.find((p) => p.name === name)
  return hit ? hit.portion_name : name
}

const setupSummary = computed(() => {
  const parts = []
  if (setup.subject) parts.push(setup.subject)
  if (setup.lessons.length) parts.push(setup.lessons.map((n) => lessonTitle(n)).join(' / '))
  if (setup.portions.length) parts.push(setup.portions.map(portionTitle).join(' / '))
  if (config.value.usesQuestions && setup.total_questions) {
    parts.push(`${setup.total_questions} questions`)
  }
  if (config.value.usesMarks && setup.total_marks) {
    parts.push(`${setup.total_marks} marks`)
  }
  return parts.length ? parts.join(' • ') : 'Not set yet'
})

function toneOf(result) {
  const opt = allResultOptions.value.find((r) => r.value === result)
  return opt ? opt.tone : ''
}

const kpis = computed(() => {
  const cards = [
    {
      key: 'total',
      filter: 'Total',
      label: 'Present Students',
      icon: 'fa-users',
      tone: 'neutral',
      value: students.value.length,
      title: 'Show all present students',
    },
  ]
  allResultOptions.value.forEach((opt) => {
    cards.push({
      key: opt.value,
      filter: opt.value,
      label: opt.value,
      icon: opt.icon,
      tone: opt.tone,
      value: summary.value[opt.value] || 0,
      title: `Show ${opt.value} students`,
    })
  })
  cards.push({
    key: 'pending',
    filter: 'Pending',
    label: 'Pending',
    icon: 'fa-hourglass-half',
    tone: 'pending',
    value: summary.value.pending || 0,
    title: 'Show students not graded yet',
  })
  return cards
})

// Same rule as the attendance page: an explicit KPI filter wins, otherwise
// "Show Completed" decides whether graded students stay listed.
function visibleForResult(result) {
  if (resultFilter.value === 'Pending') return !result
  if (resultFilter.value === 'Total') return true
  if (resultFilter.value) return result === resultFilter.value
  return showCompleted.value ? true : !result
}

const resultFiltered = computed(() => students.value.filter((s) => visibleForResult(s.result)))

const visibleStudents = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return resultFiltered.value
  return resultFiltered.value.filter(
    (s) =>
      s.student_id.toLowerCase().includes(q) || (s.student_name || '').toLowerCase().includes(q)
  )
})

const emptyState = computed(() => {
  if (!standard.value || !batch.value) {
    return {
      icon: 'fa-graduation-cap',
      title: 'Select Standard & Batch',
      text: `Choose a Standard and Batch above to load the students present today and start recording ${category.value}.`,
    }
  }
  // Nobody is gradable until the attendance register has been filled in — say
  // so, rather than showing a bare "no students" that looks like a data bug.
  if (totalStudents.value > 0 && attendanceMarked.value === 0) {
    return {
      icon: 'fa-clock-o',
      title: 'Attendance Not Marked Yet',
      text: `None of the ${totalStudents.value} students in this batch have attendance for ${date.value}. Mark attendance first — only Present students can be graded.`,
      linkToAttendance: true,
    }
  }
  if (students.value.length === 0) {
    return {
      icon: 'fa-user-times',
      title: 'No Present Students',
      text: `No student in this Standard and Batch is marked Present on ${date.value}.`,
    }
  }
  if (visibleStudents.value.length === 0) {
    if (resultFilter.value) {
      return {
        icon: 'fa-info-circle',
        title: `No ${resultFilter.value} Students`,
        text: `No students match the "${resultFilter.value}" filter for this selection.`,
      }
    }
    return {
      icon: 'fa-check-circle',
      title: 'All Done!',
      text: `Every present student has a ${category.value} result for this date.`,
      cls: 'is-success',
    }
  }
  return null
})

const allVisibleSelected = computed(
  () =>
    visibleStudents.value.length > 0 &&
    visibleStudents.value.every((s) => selected.has(s.student_id))
)
const someVisibleSelected = computed(
  () => !allVisibleSelected.value && visibleStudents.value.some((s) => selected.has(s.student_id))
)

const reasonOptions = computed(() =>
  behaviourReasons.value.filter(
    (r) => r.severity === 'Both' || r.severity === reasonModal.result
  )
)

function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function rowSyllabus(s) {
  const portions = (s.portions || []).map(portionTitle).join(' / ')
  const lessonNames = (s.lesson_titles?.length ? s.lesson_titles : s.lessons || []).join(' / ')
  return [s.subject, lessonNames, portions].filter(Boolean).join(' • ')
}

// "Full Mark Count 4 · Fail Count 1" — one chip per grade the student actually
// picked up this month. A zero says nothing, so it is left out entirely.
function monthlyChips(s) {
  const counts = s.monthly_counts || {}
  return allResultOptions.value
    .filter((opt) => (counts[opt.value] || 0) > 0)
    .map((opt) => ({ key: opt.value, count: counts[opt.value], tone: opt.tone }))
}

function togglePortion(list, name) {
  const at = list.indexOf(name)
  if (at === -1) list.push(name)
  else list.splice(at, 1)
}

function pickLesson(list, name) {
  // The list below never offers what is already picked, so this cannot double
  // up — but a stale click during a reload could, and the server rejects that.
  if (!list.includes(name)) list.push(name)
}

function removeLesson(list, name) {
  const at = list.indexOf(name)
  if (at !== -1) list.splice(at, 1)
}

function toggleFilter(key) {
  resultFilter.value = resultFilter.value === key ? null : key
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
  if (next > serverToday.value) return
  date.value = next
}

function errorText(e, fallback) {
  return e?.messages?.[0] || e?.message || fallback
}

async function loadStandards() {
  standards.value =
    (await standardsResource.submit({ doctype: 'Standard' })) || []
}

async function loadBatches() {
  batches.value =
    (await batchesResource.submit({ doctype: 'Batch' })) || []
}

async function loadSubjects() {
  if (!standard.value) {
    subjects.value = []
    return
  }
  subjects.value = (await subjectsResource.submit({ standard: standard.value })) || []
}

async function loadMeta() {
  // Which subject test this standard sits is the server's call, so the PWA asks
  // rather than re-deriving it from the standard's name.
  if (!standard.value) {
    subjectTest.value = DEFAULT_SUBJECT_TEST
    return
  }
  try {
    const meta = await metaResource.submit({ standard: standard.value })
    subjectTest.value = meta?.subject_test || DEFAULT_SUBJECT_TEST
  } catch (e) {
    subjectTest.value = DEFAULT_SUBJECT_TEST
  }
  // The standard just switched away from the test the screen was showing.
  if (SUBJECT_TESTS.includes(category.value) && category.value !== subjectTest.value) {
    category.value = subjectTest.value
  }
}

async function loadLessons() {
  if (!standard.value || !setup.subject) {
    lessons.value = []
    return
  }
  lessons.value =
    (await lessonsResource.submit({
      standard: standard.value,
      subject: setup.subject,
      include: setup.lessons.length ? JSON.stringify(setup.lessons) : undefined,
    })) || []
}

async function loadDetailLessons(subject, include) {
  if (!standard.value || !subject) {
    detailLessons.value = []
    return
  }
  detailLessons.value =
    (await detailLessonsResource.submit({
      standard: standard.value,
      subject,
      include: include?.length ? JSON.stringify(include) : undefined,
    })) || []
}

async function loadSkipLessons(subject, include) {
  if (!standard.value || !subject) {
    skipLessons.value = []
    return
  }
  skipLessons.value =
    (await skipLessonsResource.submit({
      standard: standard.value,
      subject,
      include: include?.length ? JSON.stringify(include) : undefined,
    })) || []
}

async function loadPortions() {
  portionOptions.value = (await portionsResource.submit()) || []
}

async function addLesson() {
  const title = lessonSearch.value.trim()
  if (!title || !setup.subject) return
  addingLesson.value = true
  lessonError.value = ''
  try {
    // The server hands back the existing lesson when the title is already in
    // the master, so typing one that exists picks it rather than duplicating it.
    const res = await addLessonResource.submit({
      lesson_name: title,
      subject: setup.subject,
      standard: standard.value,
    })
    if (res?.name) pickLesson(setup.lessons, res.name)
    await loadLessons()
    lessonSearch.value = ''
  } catch (e) {
    lessonError.value = errorText(e, 'Failed to add lesson')
  } finally {
    addingLesson.value = false
  }
}

function subjectOptions(current) {
  // A subject saved before it was mapped to this standard (or before the Subject
  // master existed) must stay visible, or opening the form would blank it.
  if (current && !subjects.value.includes(current)) return [...subjects.value, current]
  return subjects.value
}

async function loadBehaviourReasons() {
  behaviourReasons.value = (await reasonsResource.submit()) || []
}

async function loadStudents() {
  if (!standard.value || !batch.value || !category.value || !date.value) {
    students.value = []
    session.value = null
    holiday.value = null
    specialClass.value = null
    totalStudents.value = 0
    attendanceMarked.value = 0
    return
  }
  loading.value = true
  selected.clear()
  resultFilter.value = null
  try {
    const res = await studentsResource.submit({
      standard: standard.value,
      batch: batch.value,
      category: category.value,
      performance_date: date.value,
      gender: gender.value || undefined,
    })
    holiday.value = res.holiday || null
    session.value = res.session || null
    specialClass.value = res.special_class || null
    students.value = res.students || []
    summary.value = res.summary || {}
    totalStudents.value = res.total_students || 0
    attendanceMarked.value = res.attendance_marked || 0
    applySessionToForm(res.session)
  } catch (e) {
    saveError.value = errorText(e, 'Failed to load students')
    students.value = []
  } finally {
    loading.value = false
  }
}

function applySessionToForm(session) {
  syncSyllabus(() => {
    setup.subject = session?.subject || ''
    setup.lessons = [...(session?.lessons || [])]
  })
  lessonSearch.value = ''

  setup.portions = [...(session?.portions || [])]
  setup.total_questions = session?.total_questions || 0
  setup.total_marks = session?.total_marks || 0
  setup.pass_marks = session?.pass_marks || 0
  // Nudge the teacher into filling the setup in before grading a fresh batch.
  setupOpen.value = config.value.usesSyllabus && !session
  loadLessons()
}

function recomputeSummary() {
  const next = {}
  allResultOptions.value.forEach((opt) => {
    next[opt.value] = 0
  })
  next.pending = 0
  students.value.forEach((s) => {
    if (s.result && next[s.result] !== undefined) next[s.result]++
    else next.pending++
  })
  next.total = students.value.length
  summary.value = next
}

function openNoSessionModal() {
  noSessionModal.open = true
  noSessionModal.reason = session.value?.no_session_reason || ''
  noSessionModal.error = ''
  noSessionModal.saving = false
}

async function setNoSession(flag, reason) {
  noSessionModal.saving = true
  noSessionModal.error = ''
  saveError.value = ''
  try {
    const res = await noSessionResource.submit({
      standard: standard.value,
      batch: batch.value,
      category: category.value,
      performance_date: date.value,
      no_session: flag ? 1 : 0,
      reason: reason || undefined,
    })
    session.value = res?.session || null
    noSessionModal.open = false
    // The roster and the setup card both read differently either side of this,
    // so the day is reloaded rather than patched.
    await loadStudents()
  } catch (e) {
    const message = errorText(e, `Failed to save ${noSessionLabel.value}`)
    if (noSessionModal.open) noSessionModal.error = message
    else saveError.value = message
  } finally {
    noSessionModal.saving = false
  }
}

function confirmNoSession() {
  return setNoSession(true, noSessionModal.reason.trim())
}

function undoNoSession() {
  return setNoSession(false)
}

function openSpecialModal() {
  specialModal.open = true
  // Default to the narrowest scope: one batch working through a holiday must
  // not re-open the day for the whole school by accident.
  specialModal.scope = 'Standard + Batch'
  specialModal.reason = ''
  specialModal.error = ''
  specialModal.saving = false
}

async function confirmSpecialClass() {
  const reason = specialModal.reason.trim()
  if (!reason) return
  specialModal.saving = true
  specialModal.error = ''
  try {
    await specialClassResource.submit({
      date: date.value,
      reason,
      scope: specialModal.scope,
      standard: specialModal.scope !== 'Entire School' ? standard.value : undefined,
      batch: specialModal.scope === 'Standard + Batch' ? batch.value : undefined,
    })
    specialModal.open = false
    await loadStudents()
  } catch (e) {
    specialModal.error = errorText(e, 'Failed to save')
  } finally {
    specialModal.saving = false
  }
}

async function undoSpecialClass() {
  saveError.value = ''
  try {
    await removeSpecialClassResource.submit({
      date: date.value,
      standard: standard.value,
      batch: batch.value,
    })
    await loadStudents()
  } catch (e) {
    // Grades already recorded stay; only the "it was a working day" flag goes.
    saveError.value = errorText(e, 'Failed to undo')
  }
}

async function saveSetup() {
  setupError.value = ''
  setupNotice.value = ''
  if (config.value.usesMarks && (setup.pass_marks || 0) > (setup.total_marks || 0)) {
    setupError.value = 'Pass Marks cannot be greater than Total Marks.'
    return
  }
  setupSaving.value = true
  try {
    const res = await saveSessionResource.submit({
      standard: standard.value,
      batch: batch.value,
      category: category.value,
      performance_date: date.value,
      subject: setup.subject || undefined,
      lessons: JSON.stringify(setup.lessons),
      portions: JSON.stringify(setup.portions),
      total_questions: setup.total_questions || 0,
      total_marks: setup.total_marks || 0,
      pass_marks: setup.pass_marks || 0,
      apply_to_all: applyToAll.value ? 1 : 0,
    })
    setupNotice.value = applyToAll.value
      ? `Setup saved and applied to ${res?.updated_students || 0} student(s).`
      : 'Setup saved. Every student graded from now on picks it up.'
    setupOpen.value = false
    if (applyToAll.value) await loadStudents()
  } catch (e) {
    setupError.value = errorText(e, 'Failed to save setup')
  } finally {
    setupSaving.value = false
  }
}

function onResultClick(student, result) {
  if (savingStudent.value === student.student_id) return
  if (student.result === result && !config.value.usesReasons) return
  // Grading a skipped student un-skips them — the server clears the flag when
  // it sees a real grade come in.
  if (isFutureDate.value) {
    saveError.value = 'Cannot record performance for future dates.'
    return
  }

  if (config.value.usesReasons && REASON_REQUIRED.includes(result)) {
    openReasonModal(result, student)
    return
  }

  applyResult(student, { result }).catch((e) => {
    saveError.value = errorText(e, 'Failed to save performance')
    // force a re-render so the hidden radio snaps back to the stored result
    students.value = [...students.value]
  })
}

async function applyResult(student, payload) {
  saveError.value = ''
  savingStudent.value = student.student_id
  try {
    const res = await saveResource.submit({
      student: student.student_id,
      performance_date: date.value,
      category: category.value,
      standard: standard.value,
      batch: batch.value,
      ...payload,
      behaviour_reasons: payload.behaviour_reasons
        ? JSON.stringify(payload.behaviour_reasons)
        : undefined,
      lessons: payload.lessons ? JSON.stringify(payload.lessons) : undefined,
      portions: payload.portions ? JSON.stringify(payload.portions) : undefined,
    })
    if (res) {
      student.result = res.result
      student.skipped = res.skipped || 0
      student.marks_obtained = res.marks_obtained
      student.remarks = res.remarks || ''
      student.behaviour_reasons = res.behaviour_reasons || []
      student.portions = res.portions || []
      student.lessons = res.lessons || []
      student.lesson_titles = student.lessons.map((n) => lessonTitle(n))
      student.monthly_counts = res.monthly_counts || {}
      student.monthly_low = res.monthly_low
      student.monthly_graded = res.monthly_graded
    }
    if (payload.subject !== undefined) student.subject = payload.subject
    if (payload.total_questions !== undefined) student.total_questions = payload.total_questions
    if (payload.total_marks !== undefined) student.total_marks = payload.total_marks
    if (payload.pass_marks !== undefined) student.pass_marks = payload.pass_marks
    if (payload.remarks !== undefined) student.remarks = payload.remarks
    recomputeSummary()
    return res
  } finally {
    savingStudent.value = null
  }
}

// Marks are the primary input for a test: entering them grades the student
// (Full Mark / Pass Mark / Fail) server-side. Tapping a grade still overrides.
function onMarksChange(student, raw) {
  if (isFutureDate.value) {
    saveError.value = 'Cannot record performance for future dates.'
    return
  }
  const marks = raw === '' ? null : Number(raw)
  if (marks === null || Number.isNaN(marks)) return

  const total = student.total_marks || setup.total_marks || 0
  if (!total) {
    saveError.value = `Set Total Marks in the ${category.value} setup above before entering marks.`
    setupOpen.value = true
    students.value = [...students.value]
    return
  }
  if (marks > total) {
    saveError.value = `Marks (${marks}) cannot exceed the total of ${total}.`
    students.value = [...students.value]
    return
  }

  applyResult(student, { marks_obtained: marks }).catch((e) => {
    saveError.value = errorText(e, 'Failed to save marks')
    students.value = [...students.value]
  })
}

// Ticking "Skip Test / Study" always goes through the modal — a skip without a
// reason is exactly the record nobody can explain a month later.
function onSkipToggle(student, checked) {
  if (isFutureDate.value) {
    saveError.value = 'Cannot record performance for future dates.'
    students.value = [...students.value]
    return
  }

  if (checked) {
    skipModal.open = true
    skipModal.student = student
    // Opens on what the batch was planned to cover, which is what the teacher
    // edits down to whatever this student did instead.
    syncSyllabus(() => {
      skipModal.subject = student.subject || setup.subject || ''
      skipModal.lessons = [...(student.lessons?.length ? student.lessons : setup.lessons)]
    })
    skipModal.portions = [...(student.portions?.length ? student.portions : setup.portions)]
    skipLessonSearch.value = ''
    skipModal.remarks = student.remarks || ''
    skipModal.error = ''
    loadSkipLessons(skipModal.subject, skipModal.lessons)
    return
  }

  // Un-ticking puts the student back to ungraded rather than inventing a grade.
  clearResult(student).catch((e) => {
    saveError.value = errorText(e, 'Failed to clear the skip')
    students.value = [...students.value]
  })
}

function closeSkipModal() {
  skipModal.open = false
  skipModal.student = null
  skipModal.subject = ''
  skipModal.lessons = []
  skipModal.portions = []
  skipModal.remarks = ''
  skipModal.error = ''
  skipLessonSearch.value = ''
  // The checkbox has already flipped; re-render to snap it back to what is saved.
  students.value = [...students.value]
}

async function confirmSkip() {
  const student = skipModal.student
  const remarks = skipModal.remarks.trim()
  if (!student || !remarks) return

  skipModal.saving = true
  skipModal.error = ''
  try {
    // The syllabus goes with the skip: a skipped student still did something,
    // and this row is the only record of what.
    await applyResult(student, {
      result: SKIP_RESULT,
      skipped: 1,
      remarks,
      subject: config.value.usesSyllabus ? skipModal.subject : undefined,
      lessons: config.value.usesSyllabus ? skipModal.lessons : undefined,
      portions: config.value.usesSyllabus ? skipModal.portions : undefined,
    })
    skipModal.open = false
    skipModal.student = null
    skipModal.subject = ''
    skipModal.lessons = []
    skipModal.portions = []
    skipModal.remarks = ''
    skipLessonSearch.value = ''
  } catch (e) {
    skipModal.error = errorText(e, 'Failed to save')
  } finally {
    skipModal.saving = false
  }
}

async function clearResult(student) {
  saveError.value = ''
  savingStudent.value = student.student_id
  try {
    const res = await clearResource.submit({
      student: student.student_id,
      performance_date: date.value,
      category: category.value,
      standard: standard.value,
      batch: batch.value,
    })
    student.result = null
    student.skipped = 0
    student.marks_obtained = null
    student.remarks = ''
    student.behaviour_reasons = []
    if (res) {
      student.monthly_counts = res.monthly_counts || {}
      student.monthly_low = res.monthly_low
      student.monthly_graded = res.monthly_graded
    }
    recomputeSummary()
  } finally {
    savingStudent.value = null
  }
}

function openReasonModal(result, student) {
  reasonModal.open = true
  reasonModal.bulk = !student
  reasonModal.student = student || null
  reasonModal.result = result
  reasonModal.selected = new Set(student?.behaviour_reasons || [])
  reasonModal.remarks = student?.remarks || ''
  reasonModal.newReason = ''
  reasonModal.error = ''
}

function closeReasonModal() {
  reasonModal.open = false
  reasonModal.student = null
  reasonModal.selected = new Set()
  reasonModal.remarks = ''
  reasonModal.error = ''
  // The radio may have moved to the un-saved option; re-render to snap it back.
  students.value = [...students.value]
}

function toggleReason(name) {
  const next = new Set(reasonModal.selected)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  reasonModal.selected = next
}

async function addReason() {
  const name = reasonModal.newReason.trim()
  if (!name) return
  reasonModal.adding = true
  reasonModal.error = ''
  try {
    const res = await addReasonResource.submit({ reason_name: name, severity: 'Both' })
    await loadBehaviourReasons()
    if (res?.name) toggleReason(res.name)
    reasonModal.newReason = ''
  } catch (e) {
    reasonModal.error = errorText(e, 'Failed to add reason')
  } finally {
    reasonModal.adding = false
  }
}

async function confirmReasons() {
  reasonModal.saving = true
  reasonModal.error = ''
  const reasons = Array.from(reasonModal.selected)
  try {
    if (reasonModal.bulk) {
      await saveBulkResource.submit({
        students: JSON.stringify(Array.from(selected)),
        standard: standard.value,
        batch: batch.value,
        performance_date: date.value,
        category: category.value,
        result: reasonModal.result,
        behaviour_reasons: JSON.stringify(reasons),
      })
      students.value.forEach((s) => {
        if (selected.has(s.student_id)) {
          s.result = reasonModal.result
          s.behaviour_reasons = reasons
        }
      })
      selected.clear()
      recomputeSummary()
    } else if (reasonModal.student) {
      await applyResult(reasonModal.student, {
        result: reasonModal.result,
        behaviour_reasons: reasons,
        remarks: reasonModal.remarks || undefined,
      })
    }
    reasonModal.open = false
    reasonModal.student = null
  } catch (e) {
    reasonModal.error = errorText(e, 'Failed to save')
  } finally {
    reasonModal.saving = false
  }
}

async function bulkMark(result) {
  if (selected.size === 0 || bulkSaving.value) return
  saveError.value = ''
  if (isFutureDate.value) {
    saveError.value = 'Cannot record performance for future dates.'
    return
  }
  if (config.value.usesReasons && REASON_REQUIRED.includes(result)) {
    openReasonModal(result, null)
    return
  }

  bulkSaving.value = true
  try {
    const res = await saveBulkResource.submit({
      students: JSON.stringify(Array.from(selected)),
      standard: standard.value,
      batch: batch.value,
      performance_date: date.value,
      category: category.value,
      result,
    })
    const saved = new Set(res?.saved || [])
    students.value.forEach((s) => {
      if (saved.has(s.student_id)) s.result = result
    })
    if (res?.skipped?.length) {
      saveError.value = `${res.skipped.length} student(s) were skipped — they are not marked Present today.`
    }
    selected.clear()
    recomputeSummary()
  } catch (e) {
    saveError.value = errorText(e, 'Failed to save performance')
  } finally {
    bulkSaving.value = false
  }
}

function openDetail(student) {
  detailModal.open = true
  detailModal.student = student
  syncSyllabus(() => {
    detailModal.subject = student.subject || setup.subject || ''
    detailModal.lessons = [...(student.lessons?.length ? student.lessons : setup.lessons)]
  })
  detailLessonSearch.value = ''

  detailModal.portions = [...(student.portions?.length ? student.portions : setup.portions)]
  detailModal.total_questions = student.total_questions || setup.total_questions || 0
  detailModal.total_marks = student.total_marks || setup.total_marks || 0
  detailModal.pass_marks = student.pass_marks || setup.pass_marks || 0
  detailModal.marks_obtained = student.marks_obtained || 0
  detailModal.remarks = student.remarks || ''
  detailModal.error = ''
  loadDetailLessons(detailModal.subject, detailModal.lessons)
}

async function saveDetail() {
  const student = detailModal.student
  if (!student?.result) return
  // The row is only Skipped because someone said why; an edit must not strip it.
  if (student.skipped && !detailModal.remarks.trim()) {
    detailModal.error = `Remarks are required while this student is marked ${config.value.skipLabel}.`
    return
  }
  detailModal.saving = true
  detailModal.error = ''
  try {
    await applyResult(student, {
      // The result is resent unchanged: the server needs it to know which
      // category rules to validate the rest of the payload against.
      result: student.result,
      subject: config.value.usesSyllabus ? detailModal.subject : undefined,
      lessons: config.value.usesSyllabus ? detailModal.lessons : undefined,
      portions: config.value.usesSyllabus ? detailModal.portions : undefined,
      total_questions: config.value.usesQuestions ? detailModal.total_questions : undefined,
      total_marks: config.value.usesMarks ? detailModal.total_marks : undefined,
      pass_marks: config.value.usesMarks ? detailModal.pass_marks : undefined,
      marks_obtained: config.value.usesMarks ? detailModal.marks_obtained : undefined,
      remarks: detailModal.remarks,
      behaviour_reasons: config.value.usesReasons ? student.behaviour_reasons : undefined,
    })
    detailModal.open = false
  } catch (e) {
    detailModal.error = errorText(e, 'Failed to save')
  } finally {
    detailModal.saving = false
  }
}

onMounted(async () => {
  const t = await loadServerToday()
  if (date.value !== t && date.value === formatDate(new Date())) date.value = t
  loadStandards()
  loadBatches()
  loadBehaviourReasons()
  loadPortions()
})

watch([standard, batch, gender, category, date], loadStudents)
watch(standard, async () => {
  await loadMeta()
  await loadSubjects()
  await loadLessons()
})

// A lesson belongs to its subject, so switching subject reloads the list and
// drops picks that no longer apply.
watch(
  () => setup.subject,
  (subject, previous) => {
    if (!syncingSyllabus && previous !== undefined && subject !== previous) {
      setup.lessons = []
      lessonSearch.value = ''
    }
    loadLessons()
  }
)

watch(
  () => detailModal.subject,
  (subject, previous) => {
    if (!detailModal.open) return
    if (!syncingSyllabus && previous !== undefined && subject !== previous) {
      detailModal.lessons = []
      detailLessonSearch.value = ''
    }
    loadDetailLessons(subject, detailModal.lessons)
  }
)

watch(
  () => skipModal.subject,
  (subject, previous) => {
    if (!skipModal.open) return
    if (!syncingSyllabus && previous !== undefined && subject !== previous) {
      skipModal.lessons = []
      skipLessonSearch.value = ''
    }
    loadSkipLessons(subject, skipModal.lessons)
  }
)

// Pass Marks follows the total at 50% until someone types their own value —
// after that their number is left alone.
watch(
  () => setup.total_marks,
  (total, previous) => {
    if (!config.value.usesMarks) return
    if (!setup.pass_marks || setup.pass_marks === halfOf(previous || 0)) {
      setup.pass_marks = halfOf(total || 0)
    }
  }
)

watch(
  () => detailModal.total_marks,
  (total, previous) => {
    if (!detailModal.open || !config.value.usesMarks) return
    if (!detailModal.pass_marks || detailModal.pass_marks === halfOf(previous || 0)) {
      detailModal.pass_marks = halfOf(total || 0)
    }
  }
)

// Selections must not survive a filter change that hides the rows.
watch([resultFilter, showCompleted, search], () => {
  const visible = new Set(visibleStudents.value.map((s) => s.student_id))
  ;[...selected].forEach((id) => {
    if (!visible.has(id)) selected.delete(id)
  })
})
</script>

<style>
/* ==========================================================================
   Deliberately parallel to AttendanceManager.vue's stylesheet — same panel,
   KPI grid, toolbar, bulk bar and table-to-card mobile collapse — so the two
   pages of the PWA feel like one app. The one structural difference is that a
   result's colour comes from a `tone` (good / mid / bad) rather than from the
   status name, because each category names its three grades differently.
   ========================================================================== */

.perf-manager {
  --perf-radius: var(--border-radius-md, 8px);
  --perf-radius-sm: var(--border-radius, 6px);
  --perf-gap: 14px;
  color: var(--text-color);
  padding: 14px;
}

.perf-manager * { box-sizing: border-box; }
.perf-manager button { font-family: inherit; }

/* ---- control panel ---- */
.perf-manager .perf-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 18px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 16px 18px;
  margin-bottom: var(--perf-gap);
}

.perf-manager .perf-panel-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  flex: 1 1 320px;
}

.perf-manager .perf-field {
  min-width: 150px;
  flex: 1 1 150px;
}

.perf-manager .perf-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.perf-manager .perf-field-hint {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.perf-manager .perf-field label i {
  width: 14px;
  margin-right: 4px;
  color: var(--gray-600);
}

.perf-manager .perf-panel-date {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 0 0 auto;
  margin-left: auto;
}

.perf-manager .perf-date-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
}

.perf-manager .perf-date-label i { width: 14px; margin-right: 4px; color: var(--gray-600); }

.perf-manager .perf-date-stepper {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
  background: var(--control-bg, var(--gray-100));
  overflow: hidden;
}

.perf-manager .perf-date-nav-btn {
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

.perf-manager .perf-date-nav-btn:hover:not(:disabled) { background: var(--gray-200); }
.perf-manager .perf-date-nav-btn:active { background: var(--gray-300); }
.perf-manager .perf-date-nav-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.perf-manager .perf-date-input {
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

.perf-manager .perf-date-input:focus { outline: none; box-shadow: var(--highlight-shadow); }

/* ---- batch setup card ---- */
.perf-manager .perf-setup-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  margin-bottom: var(--perf-gap);
  overflow: hidden;
}

.perf-manager .perf-setup-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  background: var(--subtle-accent, var(--gray-50));
  color: var(--heading-color);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}

.perf-manager .perf-setup-title { font-weight: 700; white-space: nowrap; }
.perf-manager .perf-setup-title i { margin-right: 6px; color: var(--gray-600); }

.perf-manager .perf-setup-summary {
  flex: 1;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.perf-manager .perf-setup-body { padding: 16px; }

.perf-manager .perf-setup-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.perf-manager .perf-setup-hint {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-blue);
  color: var(--text-on-blue);
  border-radius: var(--perf-radius-sm);
  padding: 8px 12px;
}

.perf-manager .perf-setup-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

.perf-manager .perf-setup-actions .perf-btn { flex: 0 0 auto; margin-left: auto; }
.perf-manager .perf-setup-actions .perf-modal-error { margin: 0; }

/* ---- alerts ---- */
.perf-manager .perf-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--perf-radius);
  padding: 10px 14px;
  font-size: 12.5px;
  font-weight: 500;
  margin-bottom: var(--perf-gap);
}

.perf-manager .perf-alert-warn {
  background: var(--bg-yellow);
  border: 1px solid var(--yellow-300);
  color: var(--text-on-yellow);
}

.perf-manager .perf-alert-error {
  background: var(--bg-red);
  border: 1px solid var(--red-200);
  color: var(--text-on-red);
}

.perf-manager .perf-alert-ok {
  background: var(--bg-green);
  border: 1px solid var(--green-200);
  color: var(--text-on-green);
}

/* The alert's generic rule pushes a lone button to the right; this one is part
   of the sentence, so it stays inline. */
.perf-manager .perf-alert .perf-alert-link {
  margin-left: 6px;
  padding: 0;
  font-weight: 700;
  text-decoration: underline;
}

.perf-manager .perf-alert button {
  margin-left: auto;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
}

/* ---- KPI cards ---- */
.perf-manager .perf-kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: var(--perf-gap);
}

.perf-manager .perf-kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  padding: 14px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.perf-manager .perf-kpi-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.perf-manager .perf-kpi-card:focus-visible { outline: 2px solid var(--blue-500); outline-offset: 2px; }
.perf-manager .perf-kpi-card.is-active { border-color: currentColor; box-shadow: var(--shadow-md); }

.perf-manager .perf-kpi-icon {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border-radius: var(--perf-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.perf-manager .perf-kpi-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }

.perf-manager .perf-kpi-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.perf-manager .perf-kpi-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.perf-manager .perf-kpi-card.perf-tone-neutral .perf-kpi-icon { background: var(--bg-blue); color: var(--text-on-blue); }
.perf-manager .perf-kpi-card.perf-tone-neutral.is-active { color: var(--blue-600); }
.perf-manager .perf-kpi-card.perf-tone-good .perf-kpi-icon { background: var(--bg-green); color: var(--text-on-green); }
.perf-manager .perf-kpi-card.perf-tone-good.is-active { color: var(--green-600); }
.perf-manager .perf-kpi-card.perf-tone-mid .perf-kpi-icon { background: var(--bg-orange); color: var(--text-on-orange); }
.perf-manager .perf-kpi-card.perf-tone-mid.is-active { color: var(--orange-600, var(--text-on-orange)); }
.perf-manager .perf-kpi-card.perf-tone-bad .perf-kpi-icon { background: var(--bg-red); color: var(--text-on-red); }
.perf-manager .perf-kpi-card.perf-tone-bad.is-active { color: var(--red-600); }
.perf-manager .perf-kpi-card.perf-tone-skip .perf-kpi-icon { background: var(--gray-100); color: var(--gray-700); }
.perf-manager .perf-kpi-card.perf-tone-skip.is-active { color: var(--gray-700); }
.perf-manager .perf-kpi-card.perf-tone-pending .perf-kpi-icon { background: var(--bg-yellow); color: var(--text-on-yellow); }
.perf-manager .perf-kpi-card.perf-tone-pending.is-active { color: var(--yellow-700, var(--text-on-yellow)); }

/* ---- toolbar ---- */
.perf-manager .perf-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: var(--perf-gap);
}

.perf-manager .perf-search-wrap { position: relative; flex: 1 1 280px; max-width: 360px; }

.perf-manager .perf-search-wrap i {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 13px;
}

.perf-manager .perf-search-input {
  width: 100%;
  height: 38px;
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
  background: var(--card-bg);
  padding: 0 12px 0 34px;
  font-size: 13px;
  color: var(--text-color);
}

.perf-manager .perf-search-input:focus {
  outline: none;
  border-color: var(--blue-400, var(--blue-500));
  box-shadow: var(--highlight-shadow);
}

.perf-manager .perf-toolbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-left: auto;
  flex-wrap: wrap;
}

.perf-manager .perf-filter-chip {
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

.perf-manager .perf-filter-chip button {
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

.perf-manager .perf-switch { display: flex; align-items: center; gap: 6px; white-space: nowrap; }

.perf-manager .perf-switch label,
.perf-manager .perf-switch span {
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  margin: 0;
}

.perf-manager .perf-switch input[type='checkbox'] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--blue-500);
}

/* ---- bulk bar ---- */
.perf-manager .perf-bulk-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: var(--bg-blue);
  border: 1px solid var(--blue-200, var(--border-color));
  border-radius: var(--perf-radius);
  padding: 10px 16px;
  margin-bottom: var(--perf-gap);
  animation: perf-bulk-in 0.15s ease;
}

@keyframes perf-bulk-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.perf-manager .perf-bulk-count {
  font-weight: 600;
  color: var(--text-on-blue);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.perf-manager .perf-bulk-actions { display: flex; flex-wrap: wrap; gap: 8px; }

.perf-manager .perf-bulk-btn {
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
  padding: 7px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--card-bg);
  color: var(--text-color);
  transition: background-color 0.15s ease, color 0.15s ease;
}

.perf-manager .perf-bulk-btn.perf-tone-good { color: var(--green-600); border-color: var(--green-200, var(--border-color)); }
.perf-manager .perf-bulk-btn.perf-tone-good:hover { background: var(--green-600); color: #fff; }
.perf-manager .perf-bulk-btn.perf-tone-mid { color: var(--orange-600, var(--text-on-orange)); border-color: var(--orange-200, var(--border-color)); }
.perf-manager .perf-bulk-btn.perf-tone-mid:hover { background: var(--orange-500); color: #fff; }
.perf-manager .perf-bulk-btn.perf-tone-bad { color: var(--red-600); border-color: var(--red-200, var(--border-color)); }
.perf-manager .perf-bulk-btn.perf-tone-bad:hover { background: var(--red-600); color: #fff; }

.perf-manager .perf-bulk-clear { background: transparent; border-color: transparent; color: var(--text-muted); }
.perf-manager .perf-bulk-clear:hover { color: var(--text-color); text-decoration: underline; }

/* ---- holiday card ---- */
.perf-manager .perf-holiday-card {
  display: flex;
  gap: 16px;
  background: var(--alert-bg-info, var(--bg-blue));
  border: 1px solid var(--blue-200, var(--border-color));
  border-radius: var(--perf-radius);
  padding: 20px;
  margin-bottom: var(--perf-gap);
}

.perf-manager .perf-holiday-icon {
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

.perf-manager .perf-holiday-content h4 { margin: 0 0 8px; font-size: 16px; color: var(--heading-color); }
.perf-manager .perf-holiday-content p { margin: 0 0 4px; font-size: 13px; color: var(--text-color); }

.perf-manager .perf-holiday-key {
  display: inline-block;
  min-width: 60px;
  font-weight: 600;
  color: var(--text-muted);
}

.perf-manager .perf-holiday-note {
  margin-top: 8px !important;
  color: var(--text-muted) !important;
  font-style: italic;
}

.perf-manager .perf-holiday-action {
  margin-top: 12px;
  white-space: normal;
  text-align: left;
}

/* ---- panel actions ---- */
.perf-manager .perf-panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.perf-manager .perf-noclass-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
  cursor: pointer;
  white-space: nowrap;
}

.perf-manager .perf-noclass-btn:hover:not(:disabled) { border-color: var(--gray-400); }
.perf-manager .perf-noclass-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Pressed: the day is already marked "no session", and the same button undoes it. */
.perf-manager .perf-noclass-btn.is-active {
  color: var(--red-600);
  border-color: var(--red-300, var(--red-600));
  background: var(--red-50, var(--bg-red, var(--card-bg)));
}

.perf-manager .perf-noclass-card {
  background: var(--alert-bg-warning, var(--bg-orange, var(--card-bg)));
  border-color: var(--orange-200, var(--border-color));
}

.perf-manager .perf-noclass-card .perf-holiday-icon { color: var(--orange-600, var(--red-600)); }

/* The skip modal's "what they did instead" lead-in sits tight under the main
   explanation rather than reading as a second paragraph of it. */
.perf-manager .perf-modal-sub-tight {
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

/* ---- empty / skeleton ---- */
.perf-manager .perf-empty-state { text-align: center; padding: 48px 20px; color: var(--text-muted); }
.perf-manager .perf-empty-icon { font-size: 34px; color: var(--gray-400); margin-bottom: 12px; }
.perf-manager .perf-empty-state h4 { color: var(--heading-color); font-size: 16px; margin-bottom: 6px; }
.perf-manager .perf-empty-state p { margin: 0 auto; max-width: 420px; font-size: 13px; }

.perf-manager .perf-empty-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 8px 16px;
  border-radius: var(--perf-radius-sm);
  background: var(--blue-600);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.perf-manager .perf-empty-state.is-success .perf-empty-icon { color: var(--green-500); }
.perf-manager .perf-empty-state.is-success h4 { color: var(--green-600); }

.perf-manager .perf-skeleton-row td { padding: 16px !important; }

.perf-manager .perf-skeleton-bar {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--gray-100) 25%, var(--gray-200) 37%, var(--gray-100) 63%);
  background-size: 400% 100%;
  animation: perf-skeleton-shine 1.4s ease infinite;
}

@keyframes perf-skeleton-shine {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* ---- table ---- */
.perf-manager .perf-table-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius);
  box-shadow: var(--card-shadow, var(--shadow-sm));
  overflow: hidden;
}

.perf-manager .perf-table-scroll { overflow-x: auto; }

.perf-manager .perf-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0;
}

.perf-manager .perf-table thead th {
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

.perf-manager .perf-col-select { width: 40px; text-align: center !important; }
.perf-manager .perf-col-marks { width: 130px; }
.perf-manager .perf-col-actions { width: 340px; }

.perf-manager .perf-row-select { width: 17px; height: 17px; cursor: pointer; accent-color: var(--blue-500); }

.perf-manager .perf-table tbody tr.perf-student-row {
  border-left: 3px solid var(--gray-300);
  transition: background-color 0.12s ease, border-left-color 0.12s ease;
}

.perf-manager .perf-table tbody tr.perf-student-row:hover { background: var(--fg-hover-color, var(--gray-50)); }
.perf-manager .perf-table tbody tr.perf-student-row[data-tone='good'] { border-left-color: var(--green-500); }
.perf-manager .perf-table tbody tr.perf-student-row[data-tone='mid'] { border-left-color: var(--orange-500); }
.perf-manager .perf-table tbody tr.perf-student-row[data-tone='bad'] { border-left-color: var(--red-500); }

.perf-manager .perf-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.perf-manager .perf-table tbody tr.perf-student-row:last-child td { border-bottom: none; }
.perf-manager .perf-td-select { text-align: center; }

.perf-manager .perf-student-id {
  font-weight: 700;
  font-size: 14px;
  color: var(--heading-color);
  font-variant-numeric: tabular-nums;
}

.perf-manager .perf-student-stats { display: flex; gap: 6px; margin-top: 4px; }

.perf-manager .perf-stat-chip {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--subtle-fg, var(--gray-100));
  border-radius: 4px;
  padding: 1px 6px;
  display: inline-flex;
  gap: 3px;
}

.perf-manager .perf-student-stats { flex-wrap: wrap; }

.perf-manager .perf-stat-chip b { font-weight: 700; }
.perf-manager .perf-stat-low b { color: var(--red-600); }
.perf-manager .perf-stat-none { font-style: italic; }

/* One chip per grade, coloured the same way its button is, so a month of
   Fails reads red at a glance without anyone reading the numbers. */
.perf-manager .perf-stat-chip.perf-tone-good { background: var(--bg-green); color: var(--text-on-green); }
.perf-manager .perf-stat-chip.perf-tone-good b { color: var(--green-600); }
.perf-manager .perf-stat-chip.perf-tone-mid { background: var(--bg-orange); color: var(--text-on-orange); }
.perf-manager .perf-stat-chip.perf-tone-mid b { color: var(--orange-600, var(--text-on-orange)); }
.perf-manager .perf-stat-chip.perf-tone-bad { background: var(--bg-red); color: var(--text-on-red); }
.perf-manager .perf-stat-chip.perf-tone-bad b { color: var(--red-600); }
.perf-manager .perf-stat-chip.perf-tone-skip { background: var(--gray-100); color: var(--gray-700); }
.perf-manager .perf-stat-chip.perf-tone-skip b { color: var(--gray-700); }

.perf-manager .perf-student-profile { display: flex; align-items: center; gap: 10px; }

.perf-manager .perf-student-name-wrap {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
}

.perf-manager .perf-student-name { font-size: 13.5px; color: var(--text-color); }

.perf-manager .perf-gender-icon { margin-left: 6px; font-size: 12px; color: var(--gray-500); }
.perf-manager .perf-gender-icon-female { color: #ff69b4; }
.perf-manager .perf-gender-icon-male { color: #2196f3; }
.perf-manager .perf-birthday-icon { color: #d63384; margin-left: 6px; }

.perf-manager .perf-badge-temp {
  background-color: #9c27b0;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 12px;
  font-weight: bold;
}

.perf-manager .perf-avatar {
  border-radius: 0 !important;
  width: 78px !important;
  height: 78px !important;
  min-width: 78px;
  object-fit: cover;
  margin-left: auto;
}

.perf-manager .perf-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-200);
  color: var(--gray-600);
  font-weight: 700;
  font-size: 20px;
}

/* ---- marks ---- */
.perf-manager .perf-inline-label { display: none; }

.perf-manager .perf-marks-wrap { display: flex; align-items: center; gap: 6px; }

.perf-manager .perf-marks-input {
  width: 72px;
  height: 34px;
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
  background: var(--card-bg);
  padding: 0 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--heading-color);
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.perf-manager .perf-marks-input:focus {
  outline: none;
  border-color: var(--blue-400, var(--blue-500));
  box-shadow: var(--highlight-shadow);
}

.perf-manager .perf-marks-input:disabled { opacity: 0.5; }
.perf-manager .perf-marks-total { font-size: 12px; color: var(--text-muted); white-space: nowrap; }

/* ---- result buttons ---- */
.perf-manager .perf-status-group { display: flex; gap: 6px; }

.perf-manager .perf-status-btn {
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
  border-radius: var(--perf-radius-sm);
  background: var(--card-bg);
  color: var(--text-muted);
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.12s ease, color 0.12s ease, border-color 0.12s ease;
}

.perf-manager .perf-status-btn input { position: absolute; opacity: 0; pointer-events: none; }
.perf-manager .perf-status-btn:hover { border-color: var(--gray-400); }
.perf-manager .perf-status-btn.is-saving { opacity: 0.6; pointer-events: none; }

.perf-manager .perf-status-btn.perf-tone-good { background: var(--bg-green); border-color: var(--green-200); color: var(--text-on-green); }
.perf-manager .perf-status-btn.perf-tone-good:hover { border-color: var(--green-400); }
.perf-manager .perf-status-btn.perf-tone-mid { background: var(--bg-orange); border-color: var(--orange-200); color: var(--text-on-orange); }
.perf-manager .perf-status-btn.perf-tone-mid:hover { border-color: var(--orange-400); }
.perf-manager .perf-status-btn.perf-tone-bad { background: var(--bg-red); border-color: var(--red-200); color: var(--text-on-red); }
.perf-manager .perf-status-btn.perf-tone-bad:hover { border-color: var(--red-400); }

.perf-manager .perf-status-btn.perf-tone-good.active { background: var(--green-600); border-color: var(--green-600); color: #fff; }
.perf-manager .perf-status-btn.perf-tone-mid.active { background: var(--orange-500); border-color: var(--orange-500); color: #fff; }
.perf-manager .perf-status-btn.perf-tone-bad.active { background: var(--red-600); border-color: var(--red-600); color: #fff; }

/* ---- row meta ---- */
.perf-manager .perf-row-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.perf-manager .perf-row-syllabus {
  font-size: 11px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.perf-manager .perf-row-syllabus i { margin-right: 4px; }

.perf-manager .perf-row-edit {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--blue-600);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  white-space: nowrap;
}

.perf-manager .perf-row-edit:hover { text-decoration: underline; }

/* ---- skip toggle ---- */
.perf-manager .perf-skip-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  padding: 2px 8px 2px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
}

.perf-manager .perf-skip-toggle input { margin: 0; cursor: pointer; }
.perf-manager .perf-skip-toggle:hover { border-color: var(--gray-400); }

.perf-manager .perf-skip-toggle.active {
  background: var(--gray-100);
  border-color: var(--gray-400);
  color: var(--gray-800, var(--text-color));
}

.perf-manager .perf-skip-msg {
  margin-top: 6px;
  font-size: 11px;
  color: var(--gray-700);
  background: var(--gray-100);
  border-radius: var(--perf-radius-sm);
  padding: 4px 8px;
}

.perf-manager .perf-skip-msg i { margin-right: 4px; }

/* ---- portion chip picker ---- */
.perf-manager .perf-field-wide { flex: 1 1 100%; min-width: 100%; }

/* The lesson picker stacks chips, a search box and a list, so it takes the
   whole row of the setup grid rather than one 180px cell. `1 / -1` spans the
   explicit columns without creating an implicit one when the grid collapses
   to a single column on a phone. */
.perf-manager .perf-field-lesson { grid-column: 1 / -1; }

.perf-manager .perf-chip-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 2px 0;
}

.perf-manager .perf-chip {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease, border-color 0.12s ease;
}

.perf-manager .perf-chip:hover { border-color: var(--gray-400); }

.perf-manager .perf-chip.active {
  background: var(--blue-600);
  border-color: var(--blue-600);
  color: #fff;
}

/* ---- inline "add to the master" row ---- */
.perf-manager .perf-inline-add {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.perf-manager .perf-inline-add .form-control { flex: 1 1 auto; min-width: 0; }

/* ---- searchable multiselect (Lesson) ----
   A chip row for what is picked, one box that both searches the master and
   names a new lesson to add, then the list of what is left. A lesson already
   picked never appears in the list, so it cannot be added twice. */
.perf-manager .perf-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.perf-manager .perf-tag-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 24px;
}

.perf-manager .perf-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: var(--blue-600);
  border-radius: 999px;
}

.perf-manager .perf-tag-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  font-size: 10px;
  color: inherit;
  background: rgba(255, 255, 255, 0.22);
  border: 0;
  border-radius: 50%;
  cursor: pointer;
}

.perf-manager .perf-tag-x:hover { background: rgba(255, 255, 255, 0.4); }

.perf-manager .perf-option-list {
  list-style: none;
  margin: 0;
  padding: 4px;
  max-height: 152px;
  overflow-y: auto;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
}

.perf-manager .perf-option-list li { margin: 0; }

.perf-manager .perf-option-list button {
  display: block;
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  text-align: left;
  color: var(--text-color);
  background: transparent;
  border: 0;
  border-radius: var(--perf-radius-sm);
  cursor: pointer;
}

.perf-manager .perf-option-list button:hover { background: var(--gray-100); }
.perf-manager .perf-option-list button i { margin-right: 6px; color: var(--blue-600); }

.perf-manager .perf-option-empty {
  padding: 6px 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.perf-manager .perf-required { color: var(--red-600); }

/* Skipped is neither a win nor a loss — it reads grey wherever it appears. */
.perf-manager .perf-status-btn.perf-tone-skip { background: var(--gray-100); border-color: var(--gray-300, var(--border-color)); color: var(--gray-700); }
.perf-manager .perf-status-btn.perf-tone-skip.active { background: var(--gray-700); border-color: var(--gray-700); color: #fff; }
.perf-manager .perf-bulk-btn.perf-tone-skip { color: var(--gray-700); }
.perf-manager .perf-bulk-btn.perf-tone-skip:hover { background: var(--gray-700); color: #fff; }
.perf-manager .perf-student-row[data-tone='skip'] { opacity: 0.92; }

.perf-manager .perf-reason-msg {
  font-size: 11px;
  color: #856404;
  background: #fff3cd;
  padding: 3px 6px;
  border-radius: 3px;
  margin-top: 5px;
}

/* ---- modals ---- */
.perf-manager .perf-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.perf-manager .perf-modal {
  background: var(--card-bg);
  border-radius: var(--perf-radius);
  box-shadow: var(--shadow-md);
  padding: 20px;
  width: 100%;
  max-width: 420px;
  max-height: 85vh;
  overflow-y: auto;
}

.perf-manager .perf-modal h3 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: var(--heading-color);
}

.perf-manager .perf-modal-sub { margin: 0 0 12px; font-size: 12px; color: var(--text-muted); }

.perf-manager .perf-modal-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin: 12px 0 4px;
}

.perf-manager .perf-textarea { height: auto; padding: 8px 10px; resize: vertical; }
.perf-manager .perf-modal-warn { font-size: 11.5px; color: var(--text-on-yellow); margin-top: 6px; }
.perf-manager .perf-modal-error { font-size: 12px; color: var(--red-600); margin-top: 8px; }

.perf-manager .perf-reason-list {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--perf-radius-sm);
  padding: 6px;
}

.perf-manager .perf-reason-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--perf-radius-sm);
  font-size: 13px;
  color: var(--text-color);
  cursor: pointer;
  margin: 0;
}

.perf-manager .perf-reason-item:hover { background: var(--fg-hover-color, var(--gray-100)); }

.perf-manager .perf-reason-item input {
  width: 16px;
  height: 16px;
  accent-color: var(--blue-500);
  cursor: pointer;
}

.perf-manager .perf-reason-item em {
  margin-left: auto;
  font-style: normal;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  background: var(--gray-100);
  border-radius: 4px;
  padding: 1px 5px;
}

.perf-manager .perf-reason-add { display: flex; gap: 8px; margin-top: 10px; }
.perf-manager .perf-reason-add input { flex: 1; }

.perf-manager .perf-modal-actions { display: flex; gap: 8px; margin-top: 18px; }

.perf-manager .perf-btn {
  flex: 1;
  padding: 9px 14px;
  border-radius: var(--perf-radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.perf-manager .perf-btn-compact { flex: 0 0 auto; padding: 9px 12px; }
.perf-manager .perf-btn-primary { background: var(--blue-600); border-color: var(--blue-600); color: #fff; }
.perf-manager .perf-btn-primary:hover { background: var(--blue-700, var(--blue-600)); }
.perf-manager .perf-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.perf-manager .perf-btn-secondary { background: var(--card-bg); border-color: var(--border-color); color: var(--text-muted); }
.perf-manager .perf-btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

/* ---- sticky header on tall lists ---- */
@media (min-width: 768px) {
  .perf-manager .perf-table-scroll { max-height: 68vh; overflow-y: auto; }
  .perf-manager .perf-table thead th { position: sticky; top: 0; z-index: 2; }
}

@media (max-width: 992px) {
  .perf-manager .perf-kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .perf-manager .perf-panel-date { margin-left: 0; }
}

/* ---- mobile: panel stacking + table -> card ---- */
@media (max-width: 767px) {
  .perf-manager { padding: 10px; }

  .perf-manager .perf-panel { flex-direction: column; align-items: stretch; padding: 14px; }

  .perf-manager .perf-panel-filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    flex: none;
  }

  .perf-manager .perf-field { min-width: 0; flex: none; }
  .perf-manager .perf-field-category { grid-column: 1 / -1; }
  .perf-manager .perf-panel-date { width: 100%; margin-left: 0; }
  .perf-manager .perf-date-stepper { width: 100%; }
  .perf-manager .perf-date-input { flex: 1; min-width: 0; }

  .perf-manager .perf-setup-grid { grid-template-columns: 1fr 1fr; }
  .perf-manager .perf-setup-actions .perf-btn { margin-left: 0; width: 100%; flex: 1 1 auto; }

  .perf-manager .perf-kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .perf-manager .perf-kpi-card:first-child { grid-column: span 2; }

  .perf-manager .perf-toolbar { flex-direction: column; align-items: stretch; }
  .perf-manager .perf-search-wrap { max-width: none; flex: none; }
  .perf-manager .perf-toolbar-right { margin-left: 0; justify-content: space-between; }

  .perf-manager .perf-bulk-bar { flex-direction: column; align-items: stretch; }
  .perf-manager .perf-bulk-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .perf-manager .perf-bulk-clear { grid-column: span 2; }

  .perf-manager .perf-holiday-card { flex-direction: column; text-align: left; }

  .perf-manager .perf-table-card {
    background: transparent;
    border: none;
    box-shadow: none;
    overflow: visible;
  }

  .perf-manager .perf-table-scroll { overflow-x: visible; }
  .perf-manager .perf-table thead { display: none; }
  .perf-manager .perf-table,
  .perf-manager .perf-table tbody { display: block; width: 100%; }

  .perf-manager .perf-table tbody tr.perf-placeholder-row,
  .perf-manager .perf-table tbody tr.perf-skeleton-row {
    display: block;
    background: var(--card-bg);
    border-radius: var(--perf-radius);
    margin-bottom: 12px;
  }

  /* Media-object card, matching the attendance screen. The photo owns a fixed
     column of its own spanning the three identity rows, so it can be large
     without taking width from the name or from the result buttons, which keep
     their own full-width row. The select box moves into a leading gutter,
     freeing the top-right corner the photo used to be pinned into.
     The reserved marks-row height is gone with the absolute positioning that
     needed it: the photo now sizes the top block itself, so a Study or
     Behaviour card with no marks cell still matches a Test card. */
  .perf-manager .perf-table tbody tr.perf-student-row {
    position: relative;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) 104px;
    grid-template-areas:
      'select  name    avatar'
      'select  id      avatar'
      'select  marks   avatar'
      'actions actions actions';
    row-gap: 10px;
    column-gap: 10px;
    border-left: 4px solid var(--gray-300);
    border-bottom: none;
    border-radius: var(--perf-radius);
    padding: 14px;
    margin: 0 0 12px;
    background: var(--card-bg);
    box-shadow: var(--card-shadow, var(--shadow-sm));
  }

  .perf-manager .perf-table tbody tr.perf-student-row td {
    display: block;
    width: auto;
    padding: 0;
    border-bottom: none;
  }

  .perf-manager .perf-td-select { grid-area: select; align-self: start; text-align: center; }
  .perf-manager .perf-td-id { grid-area: id; align-self: center; }

  /* The name cell and its flex wrapper dissolve so the name block and the photo
     become grid items of the card itself -- that is what lets the photo span
     rows it is not nested in. !important because the blanket
     `tr.perf-student-row td { display: block }` rule above is more specific. */
  .perf-manager .perf-td-name,
  .perf-manager .perf-student-profile {
    display: contents !important;
  }

  .perf-manager .perf-student-name-wrap {
    grid-area: name;
    min-width: 0;
    align-self: center;
  }

  .perf-manager .perf-student-name { overflow-wrap: anywhere; }

  .perf-manager .perf-td-marks {
    grid-area: marks;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .perf-manager .perf-inline-label {
    display: inline;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .perf-manager .perf-td-actions { grid-area: actions; }
  .perf-manager .perf-status-group { gap: 8px; }

  .perf-manager .perf-status-btn {
    flex-direction: column;
    gap: 4px;
    padding: 10px 4px;
    min-height: 52px;
    font-size: 11.5px;
    white-space: normal;
  }

  .perf-manager .perf-status-btn i { font-size: 15px; }

  /* In the flow now, not pinned over it: the photo is a grid item in its own
     column, so the action cell's variable height (result labels, the
     syllabus/Details meta row, behaviour reason notes) can no longer push
     anything onto it. It fills the three-row span rather than sitting at the
     top of it, leaving no dead space beneath. */
  .perf-manager .perf-avatar {
    grid-area: avatar;
    align-self: stretch;
    justify-self: end;
    position: static !important;
    margin: 0 !important;
    width: 104px !important;
    height: auto !important;
    min-width: 104px;
    min-height: 104px;
    object-fit: cover;
  }

  .perf-manager .perf-avatar-fallback { font-size: 28px; }
}

/* Narrowest phones: give the name column back some room. */
@media (max-width: 380px) {
  .perf-manager .perf-table tbody tr.perf-student-row {
    grid-template-columns: auto minmax(0, 1fr) 84px;
    column-gap: 8px;
  }

  .perf-manager .perf-avatar {
    width: 84px !important;
    min-width: 84px;
    min-height: 84px;
  }

  .perf-manager .perf-avatar-fallback { font-size: 24px; }
}

@media (max-width: 480px) {
  .perf-manager .perf-kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .perf-manager .perf-kpi-value { font-size: 19px; }
  .perf-manager .perf-row-select { width: 22px; height: 22px; }
  .perf-manager .perf-setup-grid { grid-template-columns: 1fr; }
}

@media (max-width: 360px) {
  .perf-manager .perf-status-btn span { display: none; }
  .perf-manager .perf-status-btn i { font-size: 17px; }
}

@media (min-width: 1200px) {
  .perf-manager .perf-kpi-value { font-size: 24px; }
}
</style>
