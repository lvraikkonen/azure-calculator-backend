import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginRequest, LoginResponse } from '@/types'
import { authService } from '@/services'
import { StorageService } from '@/services/storage'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const isLoading = ref(false)
  const lastLoginTime = ref<Date | null>(null)
  const lastError = ref<string | null>(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userRole = computed(() => {
    if (!user.value) return 'user'
    // 根据后端的实际字段判断角色
    if (user.value.is_superuser) return 'admin'
    if (user.value.groups && user.value.groups.includes('admin')) return 'admin'
    return 'user'
  })
  const isAdmin = computed(() => userRole.value === 'admin' || user.value?.is_superuser === true)
  const userName = computed(() => user.value?.username || '')
  const userEmail = computed(() => user.value?.email || '')

  // 权限检查
  const hasPermission = computed(() => (permission: string) => {
    if (!user.value) return false
    return user.value.permissions?.includes(permission) || isAdmin.value
  })

  // 初始化 - 从本地存储恢复状态
  const initializeAuth = () => {
    const storedToken = StorageService.getToken()
    const storedUser = StorageService.getUser()
    const storedRefreshToken = StorageService.getRefreshToken()

    if (storedToken && storedUser) {
      token.value = storedToken
      user.value = storedUser
      refreshToken.value = storedRefreshToken
      lastLoginTime.value = new Date(StorageService.getItem('lastLoginTime') || Date.now())
    }
  }

  // 登录
  const login = async (credentials: LoginRequest): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      const response = await authService.login(credentials)

      if (response.access_token) {
        // 保存token
        token.value = response.access_token
        refreshToken.value = response.refresh_token || null
        lastLoginTime.value = new Date()

        // 持久化token到本地存储
        StorageService.setToken(response.access_token)
        StorageService.setRefreshToken(response.refresh_token || '')
        StorageService.setItem('lastLoginTime', lastLoginTime.value.toISOString())

        // 获取用户信息
        try {
          const userInfo = await authService.getCurrentUser()
          user.value = userInfo
          StorageService.setUser(userInfo)
        } catch (userError) {
          console.error('获取用户信息失败:', userError)
          // 即使获取用户信息失败，登录仍然算成功，因为token有效
        }

        return true
      }
      return false
    } catch (error) {
      console.error('登录失败:', error)
      lastError.value = error instanceof Error ? error.message : '登录失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  const logout = async (): Promise<void> => {
    try {
      isLoading.value = true
      
      // 调用后端登出API
      if (token.value) {
        await authService.logout()
      }
    } catch (error) {
      console.error('登出API调用失败:', error)
    } finally {
      // 清除本地状态
      clearAuthState()
      isLoading.value = false
    }
  }

  // 清除认证状态
  const clearAuthState = () => {
    user.value = null
    token.value = null
    refreshToken.value = null
    lastLoginTime.value = null
    
    // 清除本地存储
    StorageService.clearAuth()
  }

  // 刷新Token
  const refreshAuthToken = async (): Promise<boolean> => {
    try {
      if (!refreshToken.value) return false

      const response = await authService.refreshToken(refreshToken.value)
      
      if (response.access_token) {
        token.value = response.access_token
        if (response.refresh_token) {
          refreshToken.value = response.refresh_token
        }
        
        // 更新本地存储
        StorageService.setToken(response.access_token)
        if (response.refresh_token) {
          StorageService.setRefreshToken(response.refresh_token)
        }
        
        return true
      }
      return false
    } catch (error) {
      console.error('刷新Token失败:', error)
      clearAuthState()
      return false
    }
  }

  // 检查Token是否即将过期
  const checkTokenExpiry = (): boolean => {
    if (!token.value || !lastLoginTime.value) return false
    
    const now = new Date()
    const loginTime = new Date(lastLoginTime.value)
    const timeDiff = now.getTime() - loginTime.getTime()
    const hoursElapsed = timeDiff / (1000 * 60 * 60)
    
    // 如果超过23小时，认为Token即将过期
    return hoursElapsed > 23
  }

  // 验证当前用户状态
  const validateUser = async (): Promise<boolean> => {
    try {
      if (!token.value) return false
      
      const userInfo = await authService.getCurrentUser()
      if (userInfo) {
        user.value = userInfo
        StorageService.setUser(userInfo)
        return true
      }
      return false
    } catch (error) {
      console.error('验证用户状态失败:', error)
      clearAuthState()
      return false
    }
  }

  // 更新用户信息
  const updateUserInfo = (newUserInfo: Partial<User>) => {
    if (user.value) {
      user.value = { ...user.value, ...newUserInfo }
      StorageService.setUser(user.value)
    }
  }

  return {
    // 状态
    user: readonly(user),
    token: readonly(token),
    isLoading: readonly(isLoading),
    lastLoginTime: readonly(lastLoginTime),
    lastError: readonly(lastError),

    // 计算属性
    isAuthenticated,
    userRole,
    isAdmin,
    userName,
    userEmail,
    hasPermission,

    // 方法
    initializeAuth,
    login,
    logout,
    clearAuthState,
    refreshAuthToken,
    checkTokenExpiry,
    validateUser,
    updateUserInfo
  }
}, {
  persist: {
    key: 'auth-store',
    storage: localStorage,
    paths: ['user', 'token', 'refreshToken', 'lastLoginTime']
  }
})
