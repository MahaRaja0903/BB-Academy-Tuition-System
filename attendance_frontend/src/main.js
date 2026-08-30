import './index.css'

import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import { createPinia } from 'pinia'

import { FeatherIcon, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

let app = createApp(App)
let pinia = createPinia()

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)
app.use(pinia)

app.component('FeatherIcon', FeatherIcon)

app.mount('#app')

if ('serviceWorker' in navigator) {
  navigator.serviceWorker
    .register('/api/method/bb_tution_management.api.sw_attendance', {
      scope: '/attendance_manager/',
    })
    .catch(() => {})
}
