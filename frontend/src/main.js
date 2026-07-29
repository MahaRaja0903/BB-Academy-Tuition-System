import './index.css'

import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import { createPinia } from 'pinia'

import {
  Button,
  Card,
  Input,
  Badge,
  FeatherIcon,
  setConfig,
  frappeRequest,
  resourcesPlugin,
} from 'frappe-ui'

let app = createApp(App)
let pinia = createPinia()

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)
app.use(pinia)

app.component('Button', Button)
app.component('Card', Card)
app.component('Input', Input)
app.component('Badge', Badge)
app.component('FeatherIcon', FeatherIcon)

app.mount('#app')
