import { computed, watch } from 'vue'
import { useUIStore, type Theme, type UIPreferences } from '@/stores/ui'

/**
 * 主题和UI配置相关的组合式函数
 * 基于 UIStore 提供高级主题管理逻辑
 */
export function useTheme() {
  const uiStore = useUIStore()

  // 响应式状态
  const theme = computed(() => uiStore.theme)
  const currentTheme = computed(() => uiStore.currentTheme)
  const language = computed(() => uiStore.language)
  const layoutMode = computed(() => uiStore.layoutMode)
  const sidebarCollapsed = computed(() => uiStore.sidebarCollapsed)
  const fontSize = computed(() => uiStore.fontSize)
  const animationsEnabled = computed(() => uiStore.animationsEnabled)
  const preferences = computed(() => uiStore.preferences)

  // 设备检测
  const isMobile = computed(() => uiStore.isMobile)
  const isTablet = computed(() => uiStore.isTablet)
  const isDesktop = computed(() => uiStore.isDesktop)
  const windowSize = computed(() => uiStore.windowSize)

  // 布局计算
  const sidebarWidth = computed(() => uiStore.sidebarWidth)
  const contentWidth = computed(() => uiStore.contentWidth)

  // 主题切换
  const setTheme = (newTheme: Theme): void => {
    uiStore.setTheme(newTheme)
    
    // 添加切换反馈
    uiStore.addNotification({
      type: 'info',
      title: '主题已切换',
      message: `已切换到${getThemeDisplayName(newTheme)}主题`,
      duration: 2000
    })
  }

  const toggleTheme = (): void => {
    uiStore.toggleTheme()
    
    // 添加切换反馈
    uiStore.addNotification({
      type: 'info',
      title: '主题已切换',
      message: `已切换到${getThemeDisplayName(currentTheme.value)}主题`,
      duration: 2000
    })
  }

  // 获取主题显示名称
  const getThemeDisplayName = (themeValue: Theme): string => {
    switch (themeValue) {
      case 'light': return '浅色'
      case 'dark': return '深色'
      case 'auto': return '自动'
      default: return '未知'
    }
  }

  // 语言设置
  const setLanguage = (newLanguage: 'zh-CN' | 'en-US'): void => {
    uiStore.setLanguage(newLanguage)
    
    uiStore.addNotification({
      type: 'info',
      title: '语言已切换',
      message: newLanguage === 'zh-CN' ? '已切换到中文' : 'Switched to English',
      duration: 2000
    })
  }

  // 布局模式设置
  const setLayoutMode = (mode: 'sidebar' | 'fullscreen' | 'compact'): void => {
    uiStore.setLayoutMode(mode)
    
    const modeNames = {
      sidebar: '侧边栏',
      fullscreen: '全屏',
      compact: '紧凑'
    }
    
    uiStore.addNotification({
      type: 'info',
      title: '布局已切换',
      message: `已切换到${modeNames[mode]}布局`,
      duration: 2000
    })
  }

  // 侧边栏控制
  const toggleSidebar = (): void => {
    uiStore.toggleSidebar()
  }

  const collapseSidebar = (): void => {
    uiStore.collapseSidebar()
  }

  const expandSidebar = (): void => {
    uiStore.expandSidebar()
  }

  // 字体大小控制
  const setFontSize = (size: number): void => {
    uiStore.setFontSize(size)
    
    uiStore.addNotification({
      type: 'info',
      title: '字体大小已调整',
      message: `字体大小设置为 ${size}px`,
      duration: 2000
    })
  }

  const increaseFontSize = (): void => {
    uiStore.increaseFontSize()
    
    uiStore.addNotification({
      type: 'info',
      title: '字体已放大',
      message: `当前字体大小：${fontSize.value}px`,
      duration: 2000
    })
  }

  const decreaseFontSize = (): void => {
    uiStore.decreaseFontSize()
    
    uiStore.addNotification({
      type: 'info',
      title: '字体已缩小',
      message: `当前字体大小：${fontSize.value}px`,
      duration: 2000
    })
  }

  const resetFontSize = (): void => {
    uiStore.resetFontSize()
    
    uiStore.addNotification({
      type: 'info',
      title: '字体大小已重置',
      message: '字体大小已重置为默认值',
      duration: 2000
    })
  }

  // 动画控制
  const toggleAnimations = (): void => {
    uiStore.toggleAnimations()
    
    uiStore.addNotification({
      type: 'info',
      title: '动画设置已更新',
      message: animationsEnabled.value ? '动画已启用' : '动画已禁用',
      duration: 2000
    })
  }

  // 应用预设配置
  const applyPreferences = (prefs: Partial<UIPreferences>): void => {
    uiStore.applyPreferences(prefs)
    
    uiStore.addNotification({
      type: 'success',
      title: '配置已应用',
      message: '用户界面配置已更新',
      duration: 2000
    })
  }

  // 重置所有设置
  const resetPreferences = (): void => {
    uiStore.resetPreferences()
    
    uiStore.addNotification({
      type: 'info',
      title: '设置已重置',
      message: '所有界面设置已重置为默认值',
      duration: 3000
    })
  }

  // 获取主题相关的CSS类
  const getThemeClasses = computed(() => {
    const classes = [
      `theme-${currentTheme.value}`,
      `layout-${layoutMode.value}`,
      `lang-${language.value}`,
      sidebarCollapsed.value ? 'sidebar-collapsed' : 'sidebar-expanded'
    ]

    if (!animationsEnabled.value) {
      classes.push('no-animations')
    }

    if (isMobile.value) {
      classes.push('is-mobile')
    } else if (isTablet.value) {
      classes.push('is-tablet')
    } else {
      classes.push('is-desktop')
    }

    return classes
  })

  // 获取主题相关的CSS变量
  const getThemeVariables = computed(() => {
    return {
      '--sidebar-width': `${sidebarWidth.value}px`,
      '--content-width': `${contentWidth.value}px`,
      '--font-size': `${fontSize.value}px`,
      '--window-width': `${windowSize.value.width}px`,
      '--window-height': `${windowSize.value.height}px`
    }
  })

  // 检查是否为深色主题
  const isDarkTheme = computed(() => currentTheme.value === 'dark')

  // 检查是否为浅色主题
  const isLightTheme = computed(() => currentTheme.value === 'light')

  // 检查是否为自动主题
  const isAutoTheme = computed(() => theme.value === 'auto')

  // 响应式布局检查
  const isCompactLayout = computed(() => layoutMode.value === 'compact' || isMobile.value)

  // 监听系统主题变化
  const watchSystemTheme = (): (() => void) | void => {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

      const handleChange = () => {
        if (theme.value === 'auto') {
          // 系统主题变化时，如果当前是自动模式，则重新应用主题
          // 直接调用内部方法
          const html = document.documentElement
          const actualTheme = currentTheme.value
          html.classList.remove('light', 'dark')
          html.classList.add(actualTheme)
        }
      }

      mediaQuery.addEventListener('change', handleChange)

      // 返回清理函数
      return () => {
        mediaQuery.removeEventListener('change', handleChange)
      }
    }
  }

  // 监听窗口大小变化
  const watchWindowSize = (): (() => void) | void => {
    const handleResize = () => {
      uiStore.updateWindowSize()
    }

    window.addEventListener('resize', handleResize)

    // 返回清理函数
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }

  // 初始化主题系统
  const initialize = (): void => {
    uiStore.initialize()
    watchSystemTheme()
    watchWindowSize()
  }

  // 监听主题变化，更新文档类名
  watch(getThemeClasses, (newClasses) => {
    const html = document.documentElement
    
    // 移除所有主题相关的类
    html.className = html.className
      .split(' ')
      .filter(cls => !cls.startsWith('theme-') && 
                    !cls.startsWith('layout-') && 
                    !cls.startsWith('lang-') &&
                    !cls.includes('sidebar-') &&
                    !cls.includes('is-') &&
                    cls !== 'no-animations')
      .join(' ')
    
    // 添加新的类
    html.classList.add(...newClasses)
  }, { immediate: true })

  // 监听CSS变量变化
  watch(getThemeVariables, (newVars) => {
    const html = document.documentElement
    
    Object.entries(newVars).forEach(([key, value]) => {
      html.style.setProperty(key, value)
    })
  }, { immediate: true })

  return {
    // 状态
    theme,
    currentTheme,
    language,
    layoutMode,
    sidebarCollapsed,
    fontSize,
    animationsEnabled,
    preferences,
    
    // 设备检测
    isMobile,
    isTablet,
    isDesktop,
    windowSize,
    
    // 布局
    sidebarWidth,
    contentWidth,
    
    // 主题操作
    setTheme,
    toggleTheme,
    getThemeDisplayName,
    
    // 语言设置
    setLanguage,
    
    // 布局控制
    setLayoutMode,
    toggleSidebar,
    collapseSidebar,
    expandSidebar,
    
    // 字体控制
    setFontSize,
    increaseFontSize,
    decreaseFontSize,
    resetFontSize,
    
    // 动画控制
    toggleAnimations,
    
    // 配置管理
    applyPreferences,
    resetPreferences,
    
    // 计算属性
    getThemeClasses,
    getThemeVariables,
    isDarkTheme,
    isLightTheme,
    isAutoTheme,
    isCompactLayout,
    
    // 初始化
    initialize
  }
}
