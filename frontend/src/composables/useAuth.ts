import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import type { LoginRequest, User } from '@/types'

/**
 * 认证相关的组合式函数
 * 基于 AuthStore 提供高级认证逻辑和用户体验优化
 */
export function useAuth() {
  const authStore = useAuthStore()
  const uiStore = useUIStore()
  const router = useRouter()

  // 响应式状态
  const user = computed(() => authStore.user)
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const isLoading = computed(() => authStore.isLoading)
  const userRole = computed(() => authStore.userRole)
  const isAdmin = computed(() => authStore.isAdmin)
  const userName = computed(() => authStore.userName)
  const userEmail = computed(() => authStore.userEmail)
  const lastError = computed(() => authStore.lastError)

  // 权限检查
  const hasPermission = (permission: string): boolean => {
    const permissionChecker = authStore.hasPermission
    return permissionChecker(permission)
  }

  const hasAnyPermission = (permissions: string[]): boolean => {
    return permissions.some(permission => hasPermission(permission))
  }

  const hasAllPermissions = (permissions: string[]): boolean => {
    return permissions.every(permission => hasPermission(permission))
  }

  // 登录逻辑
  const login = async (credentials: LoginRequest): Promise<boolean> => {
    try {
      uiStore.showLoading('正在登录...')
      
      const success = await authStore.login(credentials)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '登录成功',
          message: `欢迎回来，${authStore.userName}！`
        })
        
        // 登录成功后跳转到首页或之前访问的页面
        const redirect = router.currentRoute.value.query.redirect as string
        await router.push(redirect || '/')
        
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '登录失败',
          message: authStore.lastError || '用户名或密码错误'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '登录失败',
        message: error instanceof Error ? error.message : '登录过程中发生错误'
      })
      return false
    } finally {
      uiStore.hideLoading()
    }
  }

  // 登出逻辑
  const logout = async (): Promise<void> => {
    try {
      uiStore.showLoading('正在登出...')
      
      await authStore.logout()
      
      uiStore.addNotification({
        type: 'info',
        title: '已登出',
        message: '您已安全登出系统'
      })
      
      // 跳转到登录页
      await router.push('/auth/login')
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '登出失败',
        message: error instanceof Error ? error.message : '登出过程中发生错误'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 强制登出（清除本地状态）
  const forceLogout = async (): Promise<void> => {
    authStore.clearAuthState()
    
    uiStore.addNotification({
      type: 'warning',
      title: '会话已过期',
      message: '请重新登录'
    })
    
    await router.push('/auth/login')
  }

  // 刷新用户信息
  const refreshUser = async (): Promise<boolean> => {
    try {
      return await authStore.validateUser()
    } catch (error) {
      console.error('刷新用户信息失败:', error)
      return false
    }
  }

  // 检查并刷新Token
  const checkAndRefreshToken = async (): Promise<boolean> => {
    if (!isAuthenticated.value) return false
    
    try {
      // 检查Token是否即将过期
      if (authStore.checkTokenExpiry()) {
        uiStore.showLoading('正在刷新会话...')
        
        const success = await authStore.refreshAuthToken()
        
        if (success) {
          uiStore.addNotification({
            type: 'info',
            title: '会话已刷新',
            message: '您的登录会话已自动续期'
          })
          return true
        } else {
          await forceLogout()
          return false
        }
      }
      return true
    } catch (error) {
      console.error('刷新Token失败:', error)
      await forceLogout()
      return false
    } finally {
      uiStore.hideLoading()
    }
  }

  // 更新用户信息
  const updateUser = (updates: Partial<User>): void => {
    authStore.updateUserInfo(updates)
    
    uiStore.addNotification({
      type: 'success',
      title: '信息已更新',
      message: '用户信息更新成功'
    })
  }

  // 路由守卫辅助函数
  const requireAuth = (): boolean => {
    if (!isAuthenticated.value) {
      router.push({
        path: '/login',
        query: { redirect: router.currentRoute.value.fullPath }
      })
      return false
    }
    return true
  }

  const requirePermission = (permission: string): boolean => {
    if (!requireAuth()) return false
    
    if (!hasPermission(permission)) {
      uiStore.addNotification({
        type: 'error',
        title: '权限不足',
        message: '您没有访问此功能的权限'
      })
      router.push('/')
      return false
    }
    return true
  }

  const requireAdmin = (): boolean => {
    if (!requireAuth()) return false
    
    if (!isAdmin.value) {
      uiStore.addNotification({
        type: 'error',
        title: '权限不足',
        message: '此功能仅限管理员访问'
      })
      router.push('/')
      return false
    }
    return true
  }

  // 监听认证状态变化
  watch(isAuthenticated, (newValue, oldValue) => {
    if (oldValue && !newValue) {
      // 从已认证变为未认证，可能是Token过期
      console.log('认证状态变化：用户已登出')
    }
  })

  // 初始化认证状态
  const initialize = (): void => {
    authStore.initializeAuth()
  }

  return {
    // 状态
    user,
    isAuthenticated,
    isLoading,
    userRole,
    isAdmin,
    userName,
    userEmail,
    lastError,
    
    // 权限检查
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    
    // 认证操作
    login,
    logout,
    forceLogout,
    refreshUser,
    checkAndRefreshToken,
    updateUser,
    
    // 路由守卫
    requireAuth,
    requirePermission,
    requireAdmin,
    
    // 初始化
    initialize
  }
}
