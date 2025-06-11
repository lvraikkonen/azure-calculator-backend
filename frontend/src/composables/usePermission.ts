import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { useRouter } from 'vue-router'

export interface PermissionRule {
  permission: string
  fallback?: string | (() => void)
  message?: string
}

export interface RolePermissions {
  [role: string]: string[]
}

/**
 * 权限控制相关的组合式函数
 * 基于 AuthStore 提供高级权限管理逻辑
 */
export function usePermission() {
  const authStore = useAuthStore()
  const uiStore = useUIStore()
  const router = useRouter()

  // 本地状态
  const permissionCache = ref<Map<string, boolean>>(new Map())
  const cacheExpiry = ref(5 * 60 * 1000) // 5分钟缓存

  // 响应式状态
  const user = computed(() => authStore.user)
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const userRole = computed(() => authStore.userRole)
  const isAdmin = computed(() => authStore.isAdmin)

  // 预定义权限
  const PERMISSIONS = {
    // 用户管理
    USER_VIEW: 'user:view',
    USER_CREATE: 'user:create',
    USER_UPDATE: 'user:update',
    USER_DELETE: 'user:delete',
    
    // 模型管理
    MODEL_VIEW: 'model:view',
    MODEL_CREATE: 'model:create',
    MODEL_UPDATE: 'model:update',
    MODEL_DELETE: 'model:delete',
    MODEL_TEST: 'model:test',
    MODEL_MANAGE: 'model:manage',
    
    // 对话管理
    CHAT_VIEW: 'chat:view',
    CHAT_CREATE: 'chat:create',
    CHAT_UPDATE: 'chat:update',
    CHAT_DELETE: 'chat:delete',
    
    // 计费管理
    BILLING_VIEW: 'billing:view',
    BILLING_MANAGE: 'billing:manage',
    BILLING_REPORT: 'billing:report',
    
    // 系统管理
    SYSTEM_CONFIG: 'system:config',
    SYSTEM_MONITOR: 'system:monitor',
    SYSTEM_LOG: 'system:log',
    
    // 高级功能
    ADMIN_PANEL: 'admin:panel',
    SUPER_ADMIN: 'super:admin'
  } as const

  // 基础用户权限
  const userPermissions = [
    PERMISSIONS.CHAT_VIEW,
    PERMISSIONS.CHAT_CREATE,
    PERMISSIONS.CHAT_UPDATE,
    PERMISSIONS.CHAT_DELETE,
    PERMISSIONS.MODEL_VIEW,
    PERMISSIONS.BILLING_VIEW
  ]

  // 角色权限映射
  const rolePermissions: RolePermissions = {
    user: userPermissions,
    admin: [
      // 包含所有用户权限
      ...userPermissions,
      PERMISSIONS.USER_VIEW,
      PERMISSIONS.USER_CREATE,
      PERMISSIONS.USER_UPDATE,
      PERMISSIONS.MODEL_CREATE,
      PERMISSIONS.MODEL_UPDATE,
      PERMISSIONS.MODEL_DELETE,
      PERMISSIONS.MODEL_TEST,
      PERMISSIONS.BILLING_MANAGE,
      PERMISSIONS.BILLING_REPORT,
      PERMISSIONS.SYSTEM_CONFIG,
      PERMISSIONS.SYSTEM_MONITOR,
      PERMISSIONS.ADMIN_PANEL
    ],
    superuser: [
      // 包含所有权限
      ...Object.values(PERMISSIONS)
    ]
  }

  // 基础权限检查
  const hasPermission = (permission: string): boolean => {
    if (!isAuthenticated.value) return false
    
    // 检查缓存
    const cacheKey = `${user.value?.id}-${permission}`
    const cached = permissionCache.value.get(cacheKey)
    if (cached !== undefined) return cached
    
    // 超级管理员拥有所有权限
    if (isAdmin.value && user.value?.is_superuser) {
      permissionCache.value.set(cacheKey, true)
      return true
    }
    
    // 检查用户直接权限
    const userPermissions = user.value?.permissions || []
    if (userPermissions.includes(permission)) {
      permissionCache.value.set(cacheKey, true)
      return true
    }
    
    // 检查角色权限
    const rolePerms = rolePermissions[userRole.value] || []
    const hasRolePermission = rolePerms.includes(permission)
    
    // 缓存结果
    permissionCache.value.set(cacheKey, hasRolePermission)
    
    // 设置缓存过期
    setTimeout(() => {
      permissionCache.value.delete(cacheKey)
    }, cacheExpiry.value)
    
    return hasRolePermission
  }

  // 检查多个权限（任一满足）
  const hasAnyPermission = (permissions: string[]): boolean => {
    return permissions.some(permission => hasPermission(permission))
  }

  // 检查多个权限（全部满足）
  const hasAllPermissions = (permissions: string[]): boolean => {
    return permissions.every(permission => hasPermission(permission))
  }

  // 检查角色
  const hasRole = (role: string): boolean => {
    return userRole.value === role || isAdmin.value
  }

  // 检查多个角色（任一满足）
  const hasAnyRole = (roles: string[]): boolean => {
    return roles.some(role => hasRole(role))
  }

  // 权限守卫
  const requirePermission = (
    permission: string,
    options?: {
      fallback?: string
      message?: string
      silent?: boolean
    }
  ): boolean => {
    if (!isAuthenticated.value) {
      if (!options?.silent) {
        uiStore.addNotification({
          type: 'warning',
          title: '需要登录',
          message: '请先登录后再访问此功能'
        })
      }
      
      router.push({
        path: '/auth/login',
        query: { redirect: router.currentRoute.value.fullPath }
      })
      return false
    }

    if (!hasPermission(permission)) {
      if (!options?.silent) {
        uiStore.addNotification({
          type: 'error',
          title: '权限不足',
          message: options?.message || '您没有访问此功能的权限'
        })
      }
      
      if (options?.fallback) {
        router.push(options.fallback)
      }
      return false
    }

    return true
  }

  // 角色守卫
  const requireRole = (
    role: string,
    options?: {
      fallback?: string
      message?: string
      silent?: boolean
    }
  ): boolean => {
    if (!isAuthenticated.value) {
      if (!options?.silent) {
        uiStore.addNotification({
          type: 'warning',
          title: '需要登录',
          message: '请先登录后再访问此功能'
        })
      }
      
      router.push({
        path: '/auth/login',
        query: { redirect: router.currentRoute.value.fullPath }
      })
      return false
    }

    if (!hasRole(role)) {
      if (!options?.silent) {
        uiStore.addNotification({
          type: 'error',
          title: '权限不足',
          message: options?.message || `此功能需要${role}角色权限`
        })
      }
      
      if (options?.fallback) {
        router.push(options.fallback)
      }
      return false
    }

    return true
  }

  // 管理员守卫
  const requireAdmin = (options?: {
    fallback?: string
    message?: string
    silent?: boolean
  }): boolean => {
    return requireRole('admin', {
      ...options,
      message: options?.message || '此功能仅限管理员访问'
    })
  }

  // 权限装饰器（用于组件方法）
  const withPermission = <T extends (...args: any[]) => any>(
    permission: string,
    fn: T,
    options?: {
      fallback?: () => void
      message?: string
    }
  ): T => {
    return ((...args: any[]) => {
      if (requirePermission(permission, { 
        message: options?.message,
        silent: true 
      })) {
        return fn(...args)
      } else {
        options?.fallback?.()
      }
    }) as T
  }

  // 角色装饰器
  const withRole = <T extends (...args: any[]) => any>(
    role: string,
    fn: T,
    options?: {
      fallback?: () => void
      message?: string
    }
  ): T => {
    return ((...args: any[]) => {
      if (requireRole(role, { 
        message: options?.message,
        silent: true 
      })) {
        return fn(...args)
      } else {
        options?.fallback?.()
      }
    }) as T
  }

  // 获取用户所有权限
  const getUserPermissions = (): string[] => {
    if (!isAuthenticated.value) return []
    
    const userPerms = user.value?.permissions || []
    const rolePerms = rolePermissions[userRole.value] || []
    
    return [...new Set([...userPerms, ...rolePerms])]
  }

  // 获取权限描述
  const getPermissionDescription = (permission: string): string => {
    const descriptions: Record<string, string> = {
      [PERMISSIONS.USER_VIEW]: '查看用户信息',
      [PERMISSIONS.USER_CREATE]: '创建用户',
      [PERMISSIONS.USER_UPDATE]: '更新用户信息',
      [PERMISSIONS.USER_DELETE]: '删除用户',
      [PERMISSIONS.MODEL_VIEW]: '查看模型',
      [PERMISSIONS.MODEL_CREATE]: '创建模型',
      [PERMISSIONS.MODEL_UPDATE]: '更新模型',
      [PERMISSIONS.MODEL_DELETE]: '删除模型',
      [PERMISSIONS.MODEL_TEST]: '测试模型',
      [PERMISSIONS.CHAT_VIEW]: '查看对话',
      [PERMISSIONS.CHAT_CREATE]: '创建对话',
      [PERMISSIONS.CHAT_UPDATE]: '更新对话',
      [PERMISSIONS.CHAT_DELETE]: '删除对话',
      [PERMISSIONS.BILLING_VIEW]: '查看计费信息',
      [PERMISSIONS.BILLING_MANAGE]: '管理计费',
      [PERMISSIONS.BILLING_REPORT]: '生成计费报告',
      [PERMISSIONS.SYSTEM_CONFIG]: '系统配置',
      [PERMISSIONS.SYSTEM_MONITOR]: '系统监控',
      [PERMISSIONS.SYSTEM_LOG]: '查看系统日志',
      [PERMISSIONS.ADMIN_PANEL]: '访问管理面板',
      [PERMISSIONS.SUPER_ADMIN]: '超级管理员权限'
    }
    
    return descriptions[permission] || permission
  }

  // 清除权限缓存
  const clearPermissionCache = (): void => {
    permissionCache.value.clear()
  }

  // 权限变更检测
  const checkPermissionChanges = async (): Promise<void> => {
    // 清除缓存，强制重新检查权限
    clearPermissionCache()
    
    // 可以在这里添加权限变更的通知逻辑
    uiStore.addNotification({
      type: 'info',
      title: '权限已更新',
      message: '用户权限已更新，请刷新页面以获得最新权限'
    })
  }

  return {
    // 常量
    PERMISSIONS,
    
    // 状态
    user,
    isAuthenticated,
    userRole,
    isAdmin,
    
    // 基础权限检查
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
    
    // 权限守卫
    requirePermission,
    requireRole,
    requireAdmin,
    
    // 装饰器
    withPermission,
    withRole,
    
    // 工具方法
    getUserPermissions,
    getPermissionDescription,
    clearPermissionCache,
    checkPermissionChanges
  }
}
