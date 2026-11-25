<template>
  <div v-if="open" class="pcw-modal-backdrop" @click.self="$emit('close')">
    <div class="pcw-modal">
      <template v-if="mode === 'not_attended'">
        <h3><i class="fa fa-phone-square"></i> Not Attended — {{ record?.student_name }}</h3>
        <p class="pcw-modal-hint">
          Nobody picked up. The attempt is counted on the card and the student stays on the list.
          <template v-if="record?.not_attended">
            Already not attended <b>{{ record.not_attended }}</b>
            {{ record.not_attended === 1 ? 'time' : 'times' }} this month.
          </template>
        </p>

        <label class="pcw-modal-label">Number tried</label>
        <select class="form-control" v-model="form.spoken_to">
          <option value="">—</option>
          <option v-for="o in TRIED" :key="o" :value="o">{{ o }}</option>
        </select>

        <label class="pcw-modal-label">When was the call made?</label>
        <input type="datetime-local" class="form-control" v-model="form.called_on" />

        <label class="pcw-modal-label">Who called from the tuition? <span class="pcw-req">*</span></label>
        <select class="form-control" v-model="form.called_by">
          <option value="">Select staff</option>
          <option v-for="s in staffList" :key="s.name" :value="s.name">{{ s.name }}</option>
        </select>

        <label class="pcw-modal-label">Notes</label>
        <textarea class="form-control" rows="2" v-model="form.call_notes"></textarea>
      </template>

      <template v-else>
        <h3><i class="fa fa-check"></i> Close — {{ record?.student_name }}</h3>
        <p class="pcw-modal-hint">{{ closeHint }}</p>

        <label class="pcw-modal-label">Closure notes</label>
        <textarea class="form-control" rows="3" v-model="form.call_notes"></textarea>
      </template>

      <p v-if="error" class="pcw-modal-error">{{ error }}</p>
      <div class="pcw-modal-actions">
        <button class="pcw-btn-lg" @click="$emit('close')">Cancel</button>
        <button
          class="pcw-btn-lg pcw-btn-primary-lg"
          :disabled="saving || (mode === 'not_attended' && !form.called_by)"
          @click="save"
        >
          <template v-if="saving">Saving…</template>
          <template v-else>{{ mode === 'not_attended' ? 'Save Not Attended' : 'Close' }}</template>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'

const props = defineProps({
  open: Boolean,
  // 'not_attended' | 'close'
  mode: { type: String, default: 'not_attended' },
  record: Object,
  // Which screen: 'Attendance' | 'Pending Calls' | 'Mistakes'
  callFor: { type: String, required: true },
  // Python module behind the screen's Close, e.g. 'attendance_calls'
  closeModule: String,
  closeHint: { type: String, default: 'Takes the student off the list without a call.' },
  staffList: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const TRIED = ['Father', 'Mother', 'Guardian', 'Other']

const form = reactive({ spoken_to: '', called_on: '', called_by: '', call_notes: '' })
const saving = ref(false)
const error = ref('')

const notAttendedResource = createResource({
  url: 'bb_tution_management.bb_academy.pending_calls.log_not_attended',
})
const closeResources = {
  attendance_calls: createResource({
    url: 'bb_tution_management.bb_academy.attendance_calls.close_student',
  }),
  pending_calls: createResource({
    url: 'bb_tution_management.bb_academy.pending_calls.close_student',
  }),
}

function nowForInput() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}`
}

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    Object.assign(form, { spoken_to: '', called_on: nowForInput(), called_by: '', call_notes: '' })
    error.value = ''
    saving.value = false
  }
)

async function save() {
  saving.value = true
  error.value = ''
  try {
    let res
    if (props.mode === 'not_attended') {
      res = await notAttendedResource.submit({
        student: props.record.student,
        call_for: props.callFor,
        spoken_to: form.spoken_to || null,
        called_on: form.called_on ? String(form.called_on).replace('T', ' ') + ':00' : null,
        called_by: form.called_by,
        call_notes: form.call_notes,
      })
    } else {
      res = await closeResources[props.closeModule].submit({
        student: props.record.student,
        call_notes: form.call_notes,
      })
    }
    emit('saved', res)
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || String(e || 'Something went wrong')
  } finally {
    saving.value = false
  }
}
</script>

<style src="../pending-calls.css"></style>
