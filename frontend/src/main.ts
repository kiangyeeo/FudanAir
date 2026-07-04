import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import en from 'element-plus/es/locale/lang/en'
import { MotionPlugin } from '@vueuse/motion'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './styles/global.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(ElementPlus, { locale: en })
app.use(MotionPlugin)

const auth = useAuthStore(pinia)

auth.init().finally(() => {
  app.use(router)
  app.mount('#app')
})
