<template>
  <div v-if="open" class="pcw-modal-backdrop" @click.self="$emit('close')">
    <div class="pcw-modal">
      <h3><i class="fa fa-bullhorn"></i> Complaint — {{ record?.student_name }}</h3>
      <p class="pcw-modal-hint">
        Note the parent's complaint. This call will not be closed: the complaint goes to
        <b>Complaint Calls</b>, where staff call the parents back, solve it and close it.
      </p>

      <label class="pcw-modal-label">Who complained? <span class="pcw-req">*</span></label>
      <div class="pcw-choice-row">
        <button
          v-for="o in WHO"
          :key="o"
          type="button"
          class="pcw-choice"
          :class="{ 'is-active': form.complained_by === o }"
          @click="form.complained_by = o"
        >
          {{ o }}
        </button>
      </div>

      <label class="pcw-modal-label">What did they say? <span class="pcw-req">*</span></label>
      <textarea
        class="form-control"
        rows="4"
        v-model="form.complaint"
        placeholder="The parent's complaint, in their words"
      ></textarea>

      <label class="pcw-modal-label">Who took the complaint?</label>
      <select class="form-control" v-model="form.received_by">
        <option value="">Select staff</option>
        <option v-for="s in staffList" :key="s.name" :value="s.name">{{ s.name }}</option>
      </select>

      <label class="pcw-modal-label">When?</label>
      <input type="datetime-local" class="form-control" v-model="form.received_on" />

      <p v-if="error" class="pcw-modal-error">{{ error }}</p>
      <div class="pcw-modal-actions">
        <button class="pcw-btn-lg" @click="$emit('close')">Cancel</button>
        <button
          class="pcw-btn-lg pcw-btn-primary-lg"
          :disabled="saving || !form.complained_by || !form.complaint.trim()"
          @click="save"
        >
          {{ saving ? 'Saving…' : 'Save Complaint' }}
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
  // Needs at least { student, student_name }
  record: Object,
  // 'Attendance' | 'Mistakes'
  complaintFor: { type: String, required: true },
  // The Student Mistake Record the complaint belongs to, when raised there.
  referenceDoctype: String,
  referenceName: String,
  staffList: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const WHO = ['Father', 'Mother', 'Guardian', 'Other']

const form = reactive({ complained_by: '', complaint: '', received_by: '', received_on: '' })
const saving = ref(false)
const error = ref('')

const raiseResource = createResource({
  url: 'bb_tution_management.bb_academy.complaints.raise_complaint',
})

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
    Object.assign(form, { complained_by: '', complaint: '', received_by: '', received_on: nowForInput() })
    error.value = ''
    saving.value = false
  }
)

async function save() {
  saving.value = true
  error.value = ''
  try {
    const res = await raiseResource.submit({
      student: props.record.student,
      complaint_for: props.complaintFor,
      complained_by: form.complained_by,
      complaint: form.complaint,
      received_by: form.received_by || null,
      received_on: form.received_on ? String(form.received_on).replace('T', ' ') + ':00' : null,
      reference_doctype: props.referenceName ? props.referenceDoctype : null,
      reference_name: props.referenceName || null,
    })
    emit('saved', res)
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || String(e || 'Something went wrong')
  } finally {
    saving.value = false
  }
}
</script>

<style src="../pending-calls.css"></style>
