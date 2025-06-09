import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@unocss/reset/tailwind.css'
import 'uno.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 安装插件
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
