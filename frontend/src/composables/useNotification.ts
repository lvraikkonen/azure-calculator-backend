import { computed, ref } from 'vue'
import { useUIStore } from '@/stores/ui'

export type NotificationType = 'success' | 'warning' | 'error' | 'info'

export interface NotificationOptions {
  type: NotificationType
  title: string
  message: string
  duration?: number
  persistent?: boolean
  actions?: Array<{
    label: string
    action: () => void
    style?: 'primary' | 'secondary' | 'danger'
  }>
}

/**
 * 通知管理相关的组合式函数
 * 基于 UIStore 提供高级通知管理逻辑
 */
export function useNotification() {
  const uiStore = useUIStore()

  // 本地状态
  const notificationQueue = ref<NotificationOptions[]>([])
  const maxNotifications = ref(5)
  const defaultDuration = ref(3000)

  // 响应式状态
  const notifications = computed(() => uiStore.notifications)
  const unreadNotifications = computed(() => uiStore.unreadNotifications)
  const showNotifications = computed(() => uiStore.showNotifications)

  // 通知统计
  const notificationCount = computed(() => notifications.value.length)
  const unreadCount = computed(() => unreadNotifications.value.length)
  const hasUnread = computed(() => unreadCount.value > 0)

  // 按类型分组的通知
  const notificationsByType = computed(() => {
    const grouped: Record<NotificationType, Array<typeof notifications.value[0]>> = {
      success: [],
      warning: [],
      error: [],
      info: []
    }

    notifications.value.forEach(notification => {
      grouped[notification.type] = [...grouped[notification.type], notification]
    })

    return grouped
  })

  // 添加通知
  const addNotification = (options: NotificationOptions): string => {
    const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const notification = {
      id,
      ...options,
      duration: options.duration ?? getDefaultDuration(options.type)
    }

    uiStore.addNotification(notification)

    // 如果通知过多，移除最旧的
    if (notifications.value.length > maxNotifications.value) {
      const oldestId = notifications.value[notifications.value.length - 1].id
      removeNotification(oldestId)
    }

    return id
  }

  // 成功通知
  const success = (title: string, message: string, duration?: number): string => {
    return addNotification({
      type: 'success',
      title,
      message,
      duration
    })
  }

  // 警告通知
  const warning = (title: string, message: string, duration?: number): string => {
    return addNotification({
      type: 'warning',
      title,
      message,
      duration: duration ?? 4000
    })
  }

  // 错误通知
  const error = (title: string, message: string, duration?: number): string => {
    return addNotification({
      type: 'error',
      title,
      message,
      duration: duration ?? 5000
    })
  }

  // 信息通知
  const info = (title: string, message: string, duration?: number): string => {
    return addNotification({
      type: 'info',
      title,
      message,
      duration
    })
  }

  // 持久化通知（不会自动消失）
  const persistent = (
    type: NotificationType,
    title: string,
    message: string,
    actions?: NotificationOptions['actions']
  ): string => {
    return addNotification({
      type,
      title,
      message,
      persistent: true,
      duration: 0,
      actions
    })
  }

  // 确认通知（带确认和取消按钮）
  const confirm = (
    title: string,
    message: string,
    onConfirm: () => void,
    onCancel?: () => void
  ): string => {
    return persistent('warning', title, message, [
      {
        label: '确认',
        action: () => {
          onConfirm()
        },
        style: 'primary'
      },
      {
        label: '取消',
        action: () => {
          onCancel?.()
        },
        style: 'secondary'
      }
    ])
  }

  // 移除通知
  const removeNotification = (id: string): void => {
    uiStore.removeNotification(id)
  }

  // 清除所有通知
  const clearAll = (): void => {
    uiStore.clearAllNotifications()
  }

  // 清除指定类型的通知
  const clearByType = (type: NotificationType): void => {
    const toRemove = notifications.value
      .filter(n => n.type === type)
      .map(n => n.id)

    toRemove.forEach(id => removeNotification(id))
  }

  // 获取默认持续时间
  const getDefaultDuration = (type: NotificationType): number => {
    switch (type) {
      case 'success': return 3000
      case 'info': return 3000
      case 'warning': return 4000
      case 'error': return 5000
      default: return defaultDuration.value
    }
  }

  // 获取通知图标
  const getNotificationIcon = (type: NotificationType): string => {
    switch (type) {
      case 'success': return '✓'
      case 'warning': return '⚠'
      case 'error': return '✗'
      case 'info': return 'ℹ'
      default: return 'ℹ'
    }
  }

  // 获取通知颜色
  const getNotificationColor = (type: NotificationType): string => {
    switch (type) {
      case 'success': return '#10b981'
      case 'warning': return '#f59e0b'
      case 'error': return '#ef4444'
      case 'info': return '#3b82f6'
      default: return '#6b7280'
    }
  }

  // 批量操作
  const batch = (operations: Array<() => string>): string[] => {
    return operations.map(op => op())
  }

  // 延迟通知
  const delayed = (
    options: NotificationOptions,
    delay: number
  ): Promise<string> => {
    return new Promise(resolve => {
      setTimeout(() => {
        const id = addNotification(options)
        resolve(id)
      }, delay)
    })
  }

  // 条件通知
  const conditional = (
    condition: boolean | (() => boolean),
    options: NotificationOptions
  ): string | null => {
    const shouldShow = typeof condition === 'function' ? condition() : condition
    return shouldShow ? addNotification(options) : null
  }

  // 进度通知
  const progress = (
    title: string,
    initialMessage: string = '处理中...'
  ) => {
    const id = persistent('info', title, initialMessage)
    
    return {
      update: (message: string, progress?: number) => {
        // 这里需要扩展通知系统来支持进度更新
        // 暂时通过移除旧通知并添加新通知来实现
        removeNotification(id)
        return persistent('info', title, `${message}${progress ? ` (${progress}%)` : ''}`)
      },
      complete: (message: string = '完成') => {
        removeNotification(id)
        return success(title, message)
      },
      error: (message: string = '失败') => {
        removeNotification(id)
        return error(title, message)
      }
    }
  }

  // 网络状态通知
  const networkStatus = {
    offline: () => warning('网络连接', '网络连接已断开'),
    online: () => success('网络连接', '网络连接已恢复'),
    slow: () => warning('网络连接', '网络连接较慢')
  }

  // 权限相关通知
  const permission = {
    denied: (feature: string) => 
      error('权限不足', `您没有访问${feature}的权限`),
    granted: (feature: string) => 
      success('权限已获得', `已获得${feature}的访问权限`),
    required: (feature: string, action: () => void) =>
      confirm(
        '需要权限',
        `访问${feature}需要相应权限，是否继续？`,
        action
      )
  }

  // 数据操作通知
  const dataOperation = {
    saving: () => info('保存中', '正在保存数据...'),
    saved: () => success('保存成功', '数据已保存'),
    loading: () => info('加载中', '正在加载数据...'),
    loaded: () => success('加载完成', '数据加载完成'),
    deleting: () => warning('删除中', '正在删除数据...'),
    deleted: () => success('删除成功', '数据已删除'),
    failed: (operation: string, reason?: string) =>
      error(`${operation}失败`, reason || '操作失败，请重试')
  }

  // 表单验证通知
  const validation = {
    required: (field: string) => 
      warning('必填字段', `${field}为必填字段`),
    invalid: (field: string, reason?: string) =>
      error('格式错误', `${field}格式不正确${reason ? `：${reason}` : ''}`),
    success: () => success('验证通过', '所有字段验证通过')
  }

  return {
    // 状态
    notifications,
    unreadNotifications,
    showNotifications,
    notificationCount,
    unreadCount,
    hasUnread,
    notificationsByType,
    
    // 配置
    maxNotifications,
    defaultDuration,
    
    // 基础方法
    addNotification,
    removeNotification,
    clearAll,
    clearByType,
    
    // 快捷方法
    success,
    warning,
    error,
    info,
    persistent,
    confirm,
    
    // 高级方法
    batch,
    delayed,
    conditional,
    progress,
    
    // 预设通知
    networkStatus,
    permission,
    dataOperation,
    validation,
    
    // 工具方法
    getNotificationIcon,
    getNotificationColor,
    getDefaultDuration
  }
}
