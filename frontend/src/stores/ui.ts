import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type Theme = 'light' | 'dark' | 'auto'
export type Language = 'zh-CN' | 'en-US'
export type LayoutMode = 'sidebar' | 'fullscreen' | 'compact'

export interface UIPreferences {
  theme: Theme
  language: Language
  layoutMode: LayoutMode
  sidebarCollapsed: boolean
  showNotifications: boolean
  autoSave: boolean
  fontSize: number
  animationsEnabled: boolean
}

export const useUIStore = defineStore('ui', () => {
  // 状态
  const theme = ref<Theme>('auto')
  const language = ref<Language>('zh-CN')
  const layoutMode = ref<LayoutMode>('sidebar')
  const sidebarCollapsed = ref(false)
  const showNotifications = ref(true)
  const autoSave = ref(true)
  const fontSize = ref(14)
  const animationsEnabled = ref(true)
  
  // 临时UI状态
  const isLoading = ref(false)
  const loadingText = ref('')
  const notifications = ref<Array<{
    id: string
    type: 'success' | 'warning' | 'error' | 'info'
    title: string
    message: string
    duration?: number
    timestamp: Date
  }>>([])
  const modals = ref<Record<string, boolean>>({})
  const activeTab = ref<string>('chat')
  const windowSize = ref({ width: 1920, height: 1080 })

  // 计算属性
  const currentTheme = computed(() => {
    if (theme.value === 'auto') {
      // 检测系统主题
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return theme.value
  })

  const isMobile = computed(() => windowSize.value.width < 768)
  const isTablet = computed(() => windowSize.value.width >= 768 && windowSize.value.width < 1024)
  const isDesktop = computed(() => windowSize.value.width >= 1024)

  const sidebarWidth = computed(() => sidebarCollapsed.value ? 64 : 240)
  
  const contentWidth = computed(() => {
    if (layoutMode.value === 'fullscreen') return windowSize.value.width
    return windowSize.value.width - sidebarWidth.value
  })

  const unreadNotifications = computed(() => 
    notifications.value.filter(n => !n.id.includes('read'))
  )

  const preferences = computed((): UIPreferences => ({
    theme: theme.value,
    language: language.value,
    layoutMode: layoutMode.value,
    sidebarCollapsed: sidebarCollapsed.value,
    showNotifications: showNotifications.value,
    autoSave: autoSave.value,
    fontSize: fontSize.value,
    animationsEnabled: animationsEnabled.value
  }))

  // 主题相关方法
  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
    applyTheme()
  }

  const toggleTheme = () => {
    // 基于当前实际显示的主题进行切换，而不是基于设置值
    const actualTheme = currentTheme.value

    if (actualTheme === 'light') {
      setTheme('dark')
    } else if (actualTheme === 'dark') {
      setTheme('light')
    } else {
      // 如果出现其他情况，默认切换到 dark
      setTheme('dark')
    }
  }

  const applyTheme = () => {
    const htmlElement = document.documentElement
    const actualTheme = currentTheme.value
    
    htmlElement.classList.remove('light', 'dark')
    htmlElement.classList.add(actualTheme)
    
    // 更新meta标签
    const metaTheme = document.querySelector('meta[name="theme-color"]')
    if (metaTheme) {
      metaTheme.setAttribute('content', actualTheme === 'dark' ? '#1a1a1a' : '#ffffff')
    }
  }

  // 语言相关方法
  const setLanguage = (newLanguage: Language) => {
    language.value = newLanguage
    // 这里可以集成i18n
    document.documentElement.lang = newLanguage
  }

  // 布局相关方法
  const setLayoutMode = (mode: LayoutMode) => {
    layoutMode.value = mode
    if (mode === 'fullscreen') {
      sidebarCollapsed.value = true
    }
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  const collapseSidebar = () => {
    sidebarCollapsed.value = true
  }

  const expandSidebar = () => {
    sidebarCollapsed.value = false
  }

  // 通知相关方法
  const addNotification = (notification: {
    type: 'success' | 'warning' | 'error' | 'info'
    title: string
    message: string
    duration?: number
  }) => {
    const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newNotification = {
      id,
      ...notification,
      timestamp: new Date()
    }
    
    notifications.value.unshift(newNotification)
    
    // 自动移除通知
    const duration = notification.duration || (notification.type === 'error' ? 5000 : 3000)
    setTimeout(() => {
      removeNotification(id)
    }, duration)
    
    // 限制通知数量
    if (notifications.value.length > 50) {
      notifications.value = notifications.value.slice(0, 50)
    }
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearAllNotifications = () => {
    notifications.value = []
  }

  // 模态框相关方法
  const openModal = (modalId: string) => {
    modals.value[modalId] = true
  }

  const closeModal = (modalId: string) => {
    modals.value[modalId] = false
  }

  const isModalOpen = (modalId: string): boolean => {
    return !!modals.value[modalId]
  }

  // 加载状态方法
  const setLoading = (loading: boolean, text: string = '') => {
    isLoading.value = loading
    loadingText.value = text
  }

  const showLoading = (text: string = '加载中...') => {
    setLoading(true, text)
  }

  const hideLoading = () => {
    setLoading(false, '')
  }

  // 标签页方法
  const setActiveTab = (tabId: string) => {
    activeTab.value = tabId
  }

  // 窗口大小方法
  const updateWindowSize = () => {
    windowSize.value = {
      width: window.innerWidth,
      height: window.innerHeight
    }
  }

  // 字体大小方法
  const setFontSize = (size: number) => {
    fontSize.value = Math.max(12, Math.min(20, size))
    document.documentElement.style.fontSize = `${fontSize.value}px`
  }

  const increaseFontSize = () => {
    setFontSize(fontSize.value + 1)
  }

  const decreaseFontSize = () => {
    setFontSize(fontSize.value - 1)
  }

  const resetFontSize = () => {
    setFontSize(14)
  }

  // 动画控制
  const toggleAnimations = () => {
    animationsEnabled.value = !animationsEnabled.value
    document.documentElement.classList.toggle('no-animations', !animationsEnabled.value)
  }

  // 应用所有设置
  const applyPreferences = (prefs: Partial<UIPreferences>) => {
    if (prefs.theme) setTheme(prefs.theme)
    if (prefs.language) setLanguage(prefs.language)
    if (prefs.layoutMode) setLayoutMode(prefs.layoutMode)
    if (prefs.sidebarCollapsed !== undefined) sidebarCollapsed.value = prefs.sidebarCollapsed
    if (prefs.showNotifications !== undefined) showNotifications.value = prefs.showNotifications
    if (prefs.autoSave !== undefined) autoSave.value = prefs.autoSave
    if (prefs.fontSize) setFontSize(prefs.fontSize)
    if (prefs.animationsEnabled !== undefined) {
      animationsEnabled.value = prefs.animationsEnabled
      document.documentElement.classList.toggle('no-animations', !prefs.animationsEnabled)
    }
  }

  // 重置所有设置
  const resetPreferences = () => {
    setTheme('auto')
    setLanguage('zh-CN')
    setLayoutMode('sidebar')
    sidebarCollapsed.value = false
    showNotifications.value = true
    autoSave.value = true
    setFontSize(14)
    animationsEnabled.value = true
  }

  // 初始化
  const initialize = () => {
    // 应用主题
    applyTheme()
    
    // 监听系统主题变化
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (theme.value === 'auto') {
        applyTheme()
      }
    })
    
    // 监听窗口大小变化
    window.addEventListener('resize', updateWindowSize)
    updateWindowSize()
    
    // 应用字体大小
    setFontSize(fontSize.value)
    
    // 应用动画设置
    document.documentElement.classList.toggle('no-animations', !animationsEnabled.value)
  }

  return {
    // 状态
    theme: readonly(theme),
    language: readonly(language),
    layoutMode: readonly(layoutMode),
    sidebarCollapsed: readonly(sidebarCollapsed),
    showNotifications: readonly(showNotifications),
    autoSave: readonly(autoSave),
    fontSize: readonly(fontSize),
    animationsEnabled: readonly(animationsEnabled),
    isLoading: readonly(isLoading),
    loadingText: readonly(loadingText),
    notifications: readonly(notifications),
    modals: readonly(modals),
    activeTab: readonly(activeTab),
    windowSize: readonly(windowSize),
    
    // 计算属性
    currentTheme,
    isMobile,
    isTablet,
    isDesktop,
    sidebarWidth,
    contentWidth,
    unreadNotifications,
    preferences,
    
    // 方法
    setTheme,
    toggleTheme,
    setLanguage,
    setLayoutMode,
    toggleSidebar,
    collapseSidebar,
    expandSidebar,
    addNotification,
    removeNotification,
    clearAllNotifications,
    openModal,
    closeModal,
    isModalOpen,
    setLoading,
    showLoading,
    hideLoading,
    setActiveTab,
    updateWindowSize,
    setFontSize,
    increaseFontSize,
    decreaseFontSize,
    resetFontSize,
    toggleAnimations,
    applyPreferences,
    resetPreferences,
    initialize
  }
}, {
  persist: {
    key: 'ui-store',
    storage: localStorage,
    paths: [
      'theme', 
      'language', 
      'layoutMode', 
      'sidebarCollapsed', 
      'showNotifications', 
      'autoSave', 
      'fontSize', 
      'animationsEnabled'
    ]
  }
})
