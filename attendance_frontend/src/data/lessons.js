import { reactive } from 'vue'

// Lesson docname -> bare title, shared by every picker on the Performance
// Manager. Lesson names carry their subject and standard so they stay unique;
// the screen shows only the title. A lesson the cache has not seen yet still
// has to read as something, and the docname carries the title, so it is the
// honest fallback.
const titles = reactive({})

export function rememberLessons(rows) {
  ;(rows || []).forEach((l) => {
    titles[l.name] = l.lesson_name
  })
}

export function rememberLessonTitles(map) {
  Object.assign(titles, map || {})
}

export function lessonTitle(name) {
  return titles[name] || name
}
