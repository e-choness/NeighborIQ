import { PiniaColada } from '@pinia/colada'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './lib/theme'
import './styles/app.css'

createApp(App)
  .use(createPinia())
  .use(PiniaColada, { queryOptions: { staleTime: 60_000 } })
  .use(router)
  .mount('#app')
