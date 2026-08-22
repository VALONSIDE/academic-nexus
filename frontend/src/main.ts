import { createApp, watch } from 'vue'

import App from './App.vue'
import { i18n } from './i18n'
import router from './router'
import './assets/main.css'

watch(
  () => i18n.global.locale.value,
  locale => {
    document.documentElement.lang = locale
    document.title = i18n.global.t('appTitle')
  },
  { immediate: true },
)

createApp(App).use(i18n).use(router).mount('#app')
