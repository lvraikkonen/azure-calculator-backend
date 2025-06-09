import { createPinia } from 'pinia'
import { createPersistedState } from 'pinia-plugin-persistedstate'

// 创建Pinia实例
const pinia = createPinia()

// 配置持久化插件
pinia.use(createPersistedState({
  storage: localStorage,
  key: id => `ai-chat-${id}`,
  auto: true
}))

export default pinia

// 导出所有store
export { useAuthStore } from './auth'
export { useChatStore } from './chat'
export { useModelsStore } from './models'
export { useBillingStore } from './billing'
export { useUIStore } from './ui'
