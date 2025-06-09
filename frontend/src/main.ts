import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@unocss/reset/tailwind.css'
import 'uno.css'

import App from './App.vue'
import router from './router'
import pinia from './stores'
import { initializeServices } from './services'

const app = createApp(App)

// 安装插件
app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 初始化服务
initializeServices().catch(console.error)

app.mount('#app')
