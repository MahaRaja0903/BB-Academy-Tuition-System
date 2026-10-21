<template>
  <div class="perf-syllabus">
    <div
      v-for="(block, i) in blocks"
      :key="ui(block).key"
      class="perf-syllabus-block"
      :class="{ 'perf-syllabus-block-multi': blocks.length > 1 }"
    >
      <div v-if="blocks.length > 1" class="perf-syllabus-head">
        <span class="perf-syllabus-title">
          <i class="fa fa-book"></i> Subject {{ i + 1 }}{{ block.subject ? ` — ${block.subject}` : '' }}
        </span>
        <button
          type="button"
          class="perf-syllabus-remove"
          :title="`Remove ${block.subject || `Subject ${i + 1}`}`"
          @click="removeBlock(i)"
        >
          <i class="fa fa-trash"></i> Remove
        </button>
      </div>

      <div class="perf-setup-grid">
        <div class="perf-field">
          <label :for="`${idPrefix}-subject-${i}`">Subject</label>
          <select
            :id="`${idPrefix}-subject-${i}`"
            class="form-control"
            v-model="block.subject"
            @change="onSubjectChange(block)"
          >
            <option value="">Select Subject</option>
            <option v-for="s in subjectChoices(block)" :key="s" :value="s">{{ s }}</option>
          </select>
          <small v-if="!subjects.length" class="perf-field-hint">
            No subject is mapped to {{ standard }} yet<template v-if="allowAdd"> — type one below to add it</template>.
          </small>
          <div v-if="allowAdd" class="perf-inline-add">
            <input
              type="text"
              class="form-control"
              placeholder="New subject? Type it to add"
              v-model="ui(block).newSubject"
              @keyup.enter="addSubject(block)"
            />
            <button
              type="button"
              class="perf-btn perf-btn-secondary perf-btn-compact"
              :disabled="!ui(block).newSubject.trim() || !!ui(block).busy"
              @click="addSubject(block)"
            >
              <i class="fa fa-plus"></i> Add
            </button>
          </div>
        </div>

        <div class="perf-field perf-field-lesson">
          <label :for="`${idPrefix}-lesson-${i}`">Lesson</label>
          <small v-if="!block.subject" class="perf-field-hint">
            Pick a Subject first — a lesson belongs to one subject of one standard.
          </small>
          <div v-else class="perf-picker">
            <div class="perf-tag-row">
              <span v-for="name in block.lessons" :key="name" class="perf-tag">
                {{ lessonTitle(name) }}
                <button
                  type="button"
                  class="perf-tag-x"
                  :title="`Remove ${lessonTitle(name)}`"
                  @click="removeFrom(block.lessons, name)"
                >
                  <i class="fa fa-times"></i>
                </button>
              </span>
              <small v-if="!block.lessons.length" class="perf-field-hint">
                No lesson picked yet — pick as many as the class covered.
              </small>
            </div>
            <div :class="{ 'perf-inline-add': allowAdd }">
              <input
                :id="`${idPrefix}-lesson-${i}`"
                type="text"
                class="form-control"
                :placeholder="allowAdd ? 'Search a lesson, or type a new one to add it' : 'Search a lesson'"
                v-model="ui(block).search"
                @keyup.enter="allowAdd && addLesson(block)"
              />
              <button
                v-if="allowAdd"
                type="button"
                class="perf-btn perf-btn-secondary perf-btn-compact"
                :disabled="!ui(block).search.trim() || !!ui(block).busy"
                @click="addLesson(block)"
              >
                <i class="fa fa-plus"></i> Add
              </button>
            </div>
            <ul class="perf-option-list">
              <li v-for="l in lessonPicks(block)" :key="l.name">
                <button type="button" @click="pickLesson(block, l.name)">
                  <i class="fa fa-plus-circle"></i> {{ l.lesson_name }}
                </button>
              </li>
              <li v-if="!lessonPicks(block).length" class="perf-option-empty">
                {{ lessonEmptyText(block) }}
              </li>
            </ul>
          </div>
        </div>

        <div class="perf-field perf-field-lesson">
          <label>Portion</label>
          <div class="perf-chip-picker">
            <button
              v-for="p in portionOptions"
              :key="p.name"
              type="button"
              class="perf-chip"
              :class="{ active: block.portions.includes(p.name) }"
              @click="togglePortion(block, p.name)"
            >
              {{ p.portion_name }}
            </button>
            <small v-if="!portionOptions.length" class="perf-field-hint">
              The Portion master is empty<template v-if="allowAdd"> — type 1M, 2M … below to add them</template>.
            </small>
          </div>
          <div v-if="allowAdd" class="perf-inline-add">
            <input
              type="text"
              class="form-control"
              placeholder="New portion? Type it to add"
              v-model="ui(block).newPortion"
              @keyup.enter="addPortion(block)"
            />
            <button
              type="button"
              class="perf-btn perf-btn-secondary perf-btn-compact"
              :disabled="!ui(block).newPortion.trim() || !!ui(block).busy"
              @click="addPortion(block)"
            >
              <i class="fa fa-plus"></i> Add
            </button>
          </div>
        </div>
      </div>

      <small v-if="ui(block).error" class="perf-modal-error">{{ ui(block).error }}</small>
    </div>

    <!-- A class can cover more than one subject (Maths, then Science): each gets
         its own Subject / Lesson / Portion block. A Test is one subject only. -->
    <button
      v-if="!single"
      type="button"
      class="perf-btn perf-btn-secondary perf-syllabus-add"
      :disabled="!canAddBlock"
      :title="canAddBlock ? '' : 'Pick a subject in every block first'"
      @click="addBlock"
    >
      <i class="fa fa-plus"></i> Add another subject
    </button>
  </div>
</template>

<script setup>
import { computed, reactive, toRaw, watch } from 'vue'
import { call } from 'frappe-ui'
import { lessonTitle, rememberLessons } from '@/data/lessons'

// `blocks` is the caller's reactive list of { subject, lessons, portions } and
// is edited in place, so the caller's form state is always what is on screen.
const props = defineProps({
  blocks: { type: Array, required: true },
  standard: { type: String, default: '' },
  subjects: { type: Array, default: () => [] },
  portionOptions: { type: Array, default: () => [] },
  // Whether the Subject / Lesson / Portion masters can be added to from here.
  allowAdd: { type: Boolean, default: false },
  // One Subject block only — a Test is one Subject + Lesson + Portion combination.
  single: { type: Boolean, default: false },
  reloadSubjects: { type: Function, default: null },
  reloadPortions: { type: Function, default: null },
  idPrefix: { type: String, default: 'perf-syllabus' },
})

const API = 'bb_tution_management.bb_academy.performance'

// Lesson master per subject, for the current standard.
const pools = reactive({})

// Per-block screen state (search box, inline-add text, errors). Kept off the
// block itself so it never travels to the server with the syllabus.
let nextKey = 1
const uiState = new WeakMap()
function ui(block) {
  const raw = toRaw(block)
  if (!uiState.has(raw)) {
    uiState.set(
      raw,
      reactive({ key: nextKey++, search: '', newSubject: '', newPortion: '', busy: '', error: '' })
    )
  }
  return uiState.get(raw)
}

function errorText(e, fallback) {
  return e?.messages?.[0] || e?.message || fallback
}

async function loadPool(subject, force = false) {
  if (!props.standard || !subject) return
  if (pools[subject] && !force) return
  // Lessons already picked come back even if since disabled, so their chips
  // keep a title.
  const include = props.blocks.filter((b) => b.subject === subject).flatMap((b) => b.lessons)
  try {
    const rows =
      (await call(`${API}.get_lessons`, {
        standard: props.standard,
        subject,
        include: include.length ? JSON.stringify(include) : undefined,
      })) || []
    rememberLessons(rows)
    pools[subject] = rows
  } catch (e) {
    pools[subject] = []
    props.blocks
      .filter((b) => b.subject === subject)
      .forEach((b) => {
        ui(b).error = errorText(e, `Failed to load lessons for ${subject}`)
      })
  }
}

watch(
  () => props.standard,
  () => {
    Object.keys(pools).forEach((k) => delete pools[k])
  }
)

watch(
  () => [props.standard, ...props.blocks.map((b) => b.subject)].join('\u0001'),
  () => {
    if (!props.blocks.length) addBlock()
    props.blocks.forEach((b) => loadPool(b.subject))
  },
  { immediate: true }
)

// A subject is offered in one block only; the block's own pick always stays
// listed, even one no longer mapped to the standard.
function subjectChoices(block) {
  const taken = new Set(props.blocks.filter((b) => b !== block).map((b) => b.subject))
  const list = props.subjects.filter((s) => s === block.subject || !taken.has(s))
  if (block.subject && !list.includes(block.subject)) list.push(block.subject)
  return list
}

function onSubjectChange(block) {
  // A lesson belongs to its subject, so a switch drops the old picks.
  block.lessons.splice(0)
  ui(block).search = ''
  ui(block).error = ''
}

function lessonPicks(block) {
  const pool = pools[block.subject] || []
  const q = ui(block).search.trim().toLowerCase()
  return pool.filter(
    (l) => !block.lessons.includes(l.name) && (!q || l.lesson_name.toLowerCase().includes(q))
  )
}

function lessonEmptyText(block) {
  const pool = pools[block.subject] || []
  const hint = props.allowAdd ? ' — type one above and add it.' : '.'
  if (!pool.length) return `No lesson is mapped to this subject yet${hint}`
  if (ui(block).search.trim()) {
    return props.allowAdd
      ? 'No lesson matches — type the full title above to add it.'
      : 'No lesson matches.'
  }
  if (block.lessons.length >= pool.length) return 'Every lesson for this subject is already picked.'
  return 'No lesson left to pick.'
}

function pickLesson(block, name) {
  if (!block.lessons.includes(name)) block.lessons.push(name)
}

function removeFrom(list, name) {
  const at = list.indexOf(name)
  if (at !== -1) list.splice(at, 1)
}

function togglePortion(block, name) {
  if (block.portions.includes(name)) removeFrom(block.portions, name)
  else block.portions.push(name)
}

const canAddBlock = computed(() => props.blocks.every((b) => b.subject))

function addBlock() {
  props.blocks.push({ subject: '', lessons: [], portions: [] })
}

function removeBlock(i) {
  props.blocks.splice(i, 1)
}

async function runAdd(block, kind, work) {
  const state = ui(block)
  state.busy = kind
  state.error = ''
  try {
    await work(state)
  } catch (e) {
    state.error = errorText(e, `Failed to add ${kind}`)
  } finally {
    state.busy = ''
  }
}

function addSubject(block) {
  const title = ui(block).newSubject.trim()
  if (!title || !props.standard) return
  return runAdd(block, 'subject', async (state) => {
    // An existing subject comes back as-is (mapped to this standard if it was
    // not yet), so typing one that exists just selects it.
    const name = await call(`${API}.add_subject`, { subject_name: title, standard: props.standard })
    if (props.reloadSubjects) await props.reloadSubjects()
    if (props.blocks.some((b) => b !== block && b.subject === name)) {
      state.error = `${name} is already added above.`
      return
    }
    if (name && block.subject !== name) {
      block.subject = name
      onSubjectChange(block)
    }
    state.newSubject = ''
  })
}

function addLesson(block) {
  const title = ui(block).search.trim()
  if (!title || !block.subject) return
  return runAdd(block, 'lesson', async (state) => {
    // The server hands back the existing lesson when the title is already in
    // the master, so typing one that exists picks it rather than duplicating it.
    const res = await call(`${API}.add_lesson`, {
      lesson_name: title,
      subject: block.subject,
      standard: props.standard,
    })
    if (res?.name) {
      rememberLessons([res])
      pickLesson(block, res.name)
    }
    await loadPool(block.subject, true)
    state.search = ''
  })
}

function addPortion(block) {
  const title = ui(block).newPortion.trim()
  if (!title) return
  return runAdd(block, 'portion', async (state) => {
    const res = await call(`${API}.add_portion`, { portion_name: title })
    if (props.reloadPortions) await props.reloadPortions()
    if (res?.name && !block.portions.includes(res.name)) block.portions.push(res.name)
    state.newPortion = ''
  })
}
</script>

<style>
.perf-manager .perf-syllabus {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* With one subject the block is just the fields; from two on, each subject
   gets a card of its own so it is clear which lessons belong to which. */
.perf-manager .perf-syllabus-block-multi {
  border: 1px solid var(--border-color, var(--gray-300));
  border-radius: var(--perf-radius-sm);
  padding: 12px;
}

.perf-manager .perf-syllabus-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.perf-manager .perf-syllabus-title {
  font-size: 13px;
  font-weight: 600;
}

.perf-manager .perf-syllabus-title i { margin-right: 4px; color: var(--gray-600); }

.perf-manager .perf-syllabus-remove {
  border: none;
  background: none;
  color: var(--red-600, #c0392b);
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
}

.perf-manager .perf-syllabus-add {
  align-self: flex-start;
}
</style>
