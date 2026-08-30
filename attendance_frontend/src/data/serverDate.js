import { ref } from 'vue'
import { createResource } from 'frappe-ui'

export function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function addDays(dateStr, delta) {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + delta)
  return formatDate(d)
}

// The device date is only a provisional value: a phone in a different timezone
// (or with a skewed clock) would otherwise default the pickers to a date the
// site considers to be in the future, and every save would be rejected with
// "Cannot mark attendance for future dates". Resolved once, app-wide.
export const serverToday = ref(formatDate(new Date()))

let promise = null

const todayResource = createResource({
  url: 'bb_tution_management.bb_academy.attendance.get_server_today',
})

export function loadServerToday() {
  if (!promise) {
    promise = todayResource
      .submit()
      .then((d) => {
        if (d) serverToday.value = d
        return serverToday.value
      })
      .catch(() => serverToday.value)
  }
  return promise
}
