import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useBillingStore } from '@/stores/billing'
import { useUIStore } from '@/stores/ui'
import type { UsageReport } from '@/types'

/**
 * 计费和使用统计相关的组合式函数
 * 基于 BillingStore 提供高级计费管理逻辑
 */
export function useBilling() {
  const billingStore = useBillingStore()
  const uiStore = useUIStore()

  // 本地状态
  const autoRefreshEnabled = ref(false)
  const refreshInterval = ref(60000) // 1分钟
  const reportDateRange = ref({
    start: '',
    end: ''
  })

  // 响应式状态
  const currentUsage = computed(() => billingStore.currentUsage)
  const billingInfo = computed(() => billingStore.billingInfo)
  const usageHistory = computed(() => billingStore.usageHistory)
  const reports = computed(() => billingStore.reports)
  const projections = computed(() => billingStore.projections)
  const alerts = computed(() => billingStore.alerts)
  const isLoading = computed(() => billingStore.isLoading)
  const isGeneratingReport = computed(() => billingStore.isGeneratingReport)
  const lastError = computed(() => billingStore.lastError)
  const lastUpdated = computed(() => billingStore.lastUpdated)

  // 计算属性
  const totalTokensUsed = computed(() => billingStore.totalTokensUsed)
  const totalCost = computed(() => billingStore.totalCost)
  const remainingBalance = computed(() => billingStore.remainingBalance)
  const usagePercentage = computed(() => billingStore.usagePercentage)
  const isNearLimit = computed(() => billingStore.isNearLimit)
  const isOverLimit = computed(() => billingStore.isOverLimit)
  const todayUsage = computed(() => billingStore.todayUsage)
  const weeklyUsage = computed(() => billingStore.weeklyUsage)
  const monthlyUsage = computed(() => billingStore.monthlyUsage)
  const activeAlerts = computed(() => billingStore.activeAlerts)
  const criticalAlerts = computed(() => billingStore.criticalAlerts)

  // 使用状态指示器
  const usageStatus = computed(() => {
    if (isOverLimit.value) return { type: 'error', text: '已超出限额' }
    if (isNearLimit.value) return { type: 'warning', text: '接近限额' }
    return { type: 'success', text: '正常使用' }
  })

  // 获取当前使用统计
  const fetchUsage = async (): Promise<void> => {
    try {
      await billingStore.fetchCurrentUsage()
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '获取使用统计失败',
        message: error instanceof Error ? error.message : '无法获取使用统计'
      })
    }
  }

  // 获取计费信息
  const fetchBilling = async (): Promise<void> => {
    try {
      await billingStore.fetchBillingInfo()
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '获取计费信息失败',
        message: error instanceof Error ? error.message : '无法获取计费信息'
      })
    }
  }

  // 获取使用历史
  const fetchHistory = async (days: number = 30): Promise<void> => {
    try {
      uiStore.showLoading('正在加载使用历史...')
      await billingStore.fetchUsageHistory(days)
      
      uiStore.addNotification({
        type: 'success',
        title: '历史数据已更新',
        message: `已加载最近 ${days} 天的使用历史`
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '加载历史失败',
        message: error instanceof Error ? error.message : '加载使用历史失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 生成使用报告
  const generateReport = async (
    startDate?: string,
    endDate?: string,
    reportType: string = 'detailed'
  ): Promise<UsageReport | null> => {
    const start = startDate || reportDateRange.value.start
    const end = endDate || reportDateRange.value.end

    if (!start || !end) {
      uiStore.addNotification({
        type: 'warning',
        title: '请选择日期范围',
        message: '请选择报告的开始和结束日期'
      })
      return null
    }

    try {
      uiStore.showLoading('正在生成报告...')
      
      const report = await billingStore.generateReport(start, end, reportType)
      
      if (report) {
        uiStore.addNotification({
          type: 'success',
          title: '报告生成成功',
          message: `已生成 ${start} 至 ${end} 的使用报告`
        })
        return report
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '报告生成失败',
          message: billingStore.lastError || '生成报告失败'
        })
        return null
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '报告生成失败',
        message: error instanceof Error ? error.message : '生成报告时发生错误'
      })
      return null
    } finally {
      uiStore.hideLoading()
    }
  }

  // 获取成本预测
  const fetchProjections = async (): Promise<void> => {
    try {
      await billingStore.fetchCostProjections()
      
      uiStore.addNotification({
        type: 'info',
        title: '预测数据已更新',
        message: '成本预测数据已更新'
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '获取预测失败',
        message: error instanceof Error ? error.message : '获取成本预测失败'
      })
    }
  }

  // 获取告警信息
  const fetchAlerts = async (): Promise<void> => {
    try {
      await billingStore.fetchAlerts()
      
      // 检查是否有新的关键告警
      const criticalCount = criticalAlerts.value.length
      if (criticalCount > 0) {
        uiStore.addNotification({
          type: 'error',
          title: '关键告警',
          message: `您有 ${criticalCount} 个关键告警需要处理`
        })
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '获取告警失败',
        message: error instanceof Error ? error.message : '获取告警信息失败'
      })
    }
  }

  // 运行监控检查
  const runMonitoring = async (): Promise<void> => {
    try {
      uiStore.showLoading('正在运行监控检查...')
      
      const hasAlerts = await billingStore.runMonitoringCheck()
      
      if (hasAlerts) {
        uiStore.addNotification({
          type: 'warning',
          title: '发现新告警',
          message: '监控检查发现新的告警信息'
        })
      } else {
        uiStore.addNotification({
          type: 'success',
          title: '监控检查完成',
          message: '未发现异常情况'
        })
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '监控检查失败',
        message: error instanceof Error ? error.message : '运行监控检查失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 标记告警为已读
  const markAlertRead = async (alertId: string): Promise<void> => {
    try {
      const success = await billingStore.markAlertAsRead(alertId)
      
      if (success) {
        uiStore.addNotification({
          type: 'info',
          title: '告警已标记',
          message: '告警已标记为已读'
        })
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '标记失败',
        message: error instanceof Error ? error.message : '标记告警失败'
      })
    }
  }

  // 设置使用限制
  const setLimit = async (limit: number): Promise<void> => {
    if (limit <= 0) {
      uiStore.addNotification({
        type: 'warning',
        title: '无效限制',
        message: '使用限制必须大于0'
      })
      return
    }

    try {
      uiStore.showLoading('正在设置使用限制...')
      
      const success = await billingStore.setUsageLimit(limit)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '限制已设置',
          message: `使用限制已设置为 ${limit}`
        })
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '设置失败',
          message: billingStore.lastError || '设置使用限制失败'
        })
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '设置失败',
        message: error instanceof Error ? error.message : '设置使用限制时发生错误'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 开始自动刷新
  const startAutoRefresh = (): void => {
    if (autoRefreshEnabled.value) return
    
    autoRefreshEnabled.value = true
    billingStore.startAutoRefresh(refreshInterval.value)
    
    uiStore.addNotification({
      type: 'info',
      title: '自动刷新已启用',
      message: `每 ${refreshInterval.value / 1000} 秒自动更新使用统计`
    })
  }

  // 停止自动刷新
  const stopAutoRefresh = (): void => {
    if (!autoRefreshEnabled.value) return
    
    autoRefreshEnabled.value = false
    billingStore.stopAutoRefresh()
    
    uiStore.addNotification({
      type: 'info',
      title: '自动刷新已停用',
      message: '已停止自动更新使用统计'
    })
  }

  // 刷新所有数据
  const refreshAll = async (): Promise<void> => {
    try {
      uiStore.showLoading('正在刷新所有数据...')
      await billingStore.refreshAllData()
      
      uiStore.addNotification({
        type: 'success',
        title: '数据已刷新',
        message: '所有计费数据已更新'
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '刷新失败',
        message: error instanceof Error ? error.message : '刷新数据失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 清除错误
  const clearError = (): void => {
    billingStore.clearError()
  }

  // 格式化货币
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY'
    }).format(amount)
  }

  // 格式化数字
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('zh-CN').format(num)
  }

  // 生命周期钩子
  onMounted(() => {
    // 初始化时获取基础数据
    fetchUsage()
    fetchBilling()
  })

  onUnmounted(() => {
    // 组件卸载时停止自动刷新
    if (autoRefreshEnabled.value) {
      stopAutoRefresh()
    }
  })

  return {
    // 状态
    currentUsage,
    billingInfo,
    usageHistory,
    reports,
    projections,
    alerts,
    isLoading,
    isGeneratingReport,
    lastError,
    lastUpdated,
    
    // 计算属性
    totalTokensUsed,
    totalCost,
    remainingBalance,
    usagePercentage,
    isNearLimit,
    isOverLimit,
    todayUsage,
    weeklyUsage,
    monthlyUsage,
    activeAlerts,
    criticalAlerts,
    usageStatus,
    
    // 本地状态
    autoRefreshEnabled,
    refreshInterval,
    reportDateRange,
    
    // 数据操作
    fetchUsage,
    fetchBilling,
    fetchHistory,
    generateReport,
    fetchProjections,
    fetchAlerts,
    runMonitoring,
    markAlertRead,
    setLimit,
    
    // 自动刷新
    startAutoRefresh,
    stopAutoRefresh,
    
    // 工具函数
    refreshAll,
    clearError,
    formatCurrency,
    formatNumber
  }
}
