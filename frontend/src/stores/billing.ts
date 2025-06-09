import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  TokenUsageStats,
  BillingInfo,
  UsageReport,
  CostProjection,
  MonitoringAlert 
} from '@/types'
import { billingService } from '@/services'

export const useBillingStore = defineStore('billing', () => {
  // 状态
  const currentUsage = ref<TokenUsageStats | null>(null)
  const billingInfo = ref<BillingInfo | null>(null)
  const usageHistory = ref<TokenUsageStats[]>([])
  const reports = ref<UsageReport[]>([])
  const projections = ref<CostProjection[]>([])
  const alerts = ref<MonitoringAlert[]>([])
  const isLoading = ref(false)
  const isGeneratingReport = ref(false)
  const lastError = ref<string | null>(null)
  const lastUpdated = ref<Date | null>(null)
  const autoRefreshInterval = ref<NodeJS.Timeout | null>(null)

  // 计算属性
  const totalTokensUsed = computed(() => currentUsage.value?.total_tokens || 0)
  const totalCost = computed(() => currentUsage.value?.total_cost || 0)
  const remainingBalance = computed(() => billingInfo.value?.remaining_balance || 0)
  const usagePercentage = computed(() => {
    if (!billingInfo.value || !currentUsage.value) return 0
    const limit = billingInfo.value.monthly_limit
    const used = currentUsage.value.total_cost
    return limit && limit > 0 ? Math.min((used / limit) * 100, 100) : 0
  })

  const isNearLimit = computed(() => usagePercentage.value > 80)
  const isOverLimit = computed(() => usagePercentage.value >= 100)

  const todayUsage = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    return usageHistory.value.find(usage => usage.date === today) || null
  })

  const weeklyUsage = computed(() => {
    const oneWeekAgo = new Date()
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)

    return usageHistory.value.filter(usage =>
      usage.date && new Date(usage.date) >= oneWeekAgo
    )
  })

  const monthlyUsage = computed(() => {
    const oneMonthAgo = new Date()
    oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)

    return usageHistory.value.filter(usage =>
      usage.date && new Date(usage.date) >= oneMonthAgo
    )
  })

  const activeAlerts = computed(() => 
    alerts.value.filter(alert => alert.status === 'active')
  )

  const criticalAlerts = computed(() => 
    activeAlerts.value.filter(alert => alert.severity === 'critical')
  )

  // 获取当前使用统计
  const fetchCurrentUsage = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const usage = await billingService.getCurrentUsage()
      currentUsage.value = usage
      lastUpdated.value = new Date()
    } catch (error) {
      console.error('获取使用统计失败:', error)
      lastError.value = '获取使用统计失败'
    } finally {
      isLoading.value = false
    }
  }

  // 获取计费信息
  const fetchBillingInfo = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const billing = await billingService.getBillingInfo()
      billingInfo.value = billing
    } catch (error) {
      console.error('获取计费信息失败:', error)
      lastError.value = '获取计费信息失败'
    } finally {
      isLoading.value = false
    }
  }

  // 获取使用历史
  const fetchUsageHistory = async (days: number = 30): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const history = await billingService.getUsageHistory(days)
      usageHistory.value = history
    } catch (error) {
      console.error('获取使用历史失败:', error)
      lastError.value = '获取使用历史失败'
    } finally {
      isLoading.value = false
    }
  }

  // 生成使用报告
  const generateReport = async (
    startDate: string,
    endDate: string,
    reportType: string = 'detailed'
  ): Promise<UsageReport | null> => {
    try {
      isGeneratingReport.value = true
      lastError.value = null
      
      const report = await billingService.generateReport({
        start_date: startDate,
        end_date: endDate,
        report_type: reportType
      })
      
      reports.value.unshift(report)
      
      // 限制保存的报告数量
      if (reports.value.length > 20) {
        reports.value = reports.value.slice(0, 20)
      }
      
      return report
    } catch (error) {
      console.error('生成报告失败:', error)
      lastError.value = '生成报告失败'
      return null
    } finally {
      isGeneratingReport.value = false
    }
  }

  // 获取成本预测
  const fetchCostProjections = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const projectionData = await billingService.getCostProjections()
      projections.value = projectionData
    } catch (error) {
      console.error('获取成本预测失败:', error)
      lastError.value = '获取成本预测失败'
    } finally {
      isLoading.value = false
    }
  }

  // 获取监控告警
  const fetchAlerts = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const alertData = await billingService.getAlerts()
      alerts.value = alertData
    } catch (error) {
      console.error('获取告警信息失败:', error)
      lastError.value = '获取告警信息失败'
    } finally {
      isLoading.value = false
    }
  }

  // 运行监控检查
  const runMonitoringCheck = async (): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const result = await billingService.runMonitoringCheck()
      
      // 刷新告警数据
      await fetchAlerts()
      
      return result.alerts_found > 0
    } catch (error) {
      console.error('运行监控检查失败:', error)
      lastError.value = '运行监控检查失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 标记告警为已读
  const markAlertAsRead = async (alertId: string): Promise<boolean> => {
    try {
      await billingService.markAlertAsRead(alertId)
      
      // 更新本地状态
      const alert = alerts.value.find(a => a.id === alertId)
      if (alert) {
        alert.status = 'read'
      }
      
      return true
    } catch (error) {
      console.error('标记告警失败:', error)
      lastError.value = '标记告警失败'
      return false
    }
  }

  // 设置使用限制
  const setUsageLimit = async (limit: number): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const updatedBilling = await billingService.setUsageLimit(limit)
      billingInfo.value = updatedBilling
      
      return true
    } catch (error) {
      console.error('设置使用限制失败:', error)
      lastError.value = '设置使用限制失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 开始自动刷新
  const startAutoRefresh = (intervalMs: number = 60000) => {
    if (autoRefreshInterval.value) {
      clearInterval(autoRefreshInterval.value)
    }
    
    autoRefreshInterval.value = setInterval(async () => {
      await fetchCurrentUsage()
    }, intervalMs)
  }

  // 停止自动刷新
  const stopAutoRefresh = () => {
    if (autoRefreshInterval.value) {
      clearInterval(autoRefreshInterval.value)
      autoRefreshInterval.value = null
    }
  }

  // 清除错误
  const clearError = () => {
    lastError.value = null
  }

  // 刷新所有数据
  const refreshAllData = async (): Promise<void> => {
    await Promise.all([
      fetchCurrentUsage(),
      fetchBillingInfo(),
      fetchUsageHistory(),
      fetchAlerts()
    ])
  }

  // 清除所有数据
  const clearAllData = () => {
    currentUsage.value = null
    billingInfo.value = null
    usageHistory.value = []
    reports.value = []
    projections.value = []
    alerts.value = []
    lastError.value = null
    lastUpdated.value = null
    stopAutoRefresh()
  }

  return {
    // 状态
    currentUsage: readonly(currentUsage),
    billingInfo: readonly(billingInfo),
    usageHistory: readonly(usageHistory),
    reports: readonly(reports),
    projections: readonly(projections),
    alerts: readonly(alerts),
    isLoading: readonly(isLoading),
    isGeneratingReport: readonly(isGeneratingReport),
    lastError: readonly(lastError),
    lastUpdated: readonly(lastUpdated),
    
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
    
    // 方法
    fetchCurrentUsage,
    fetchBillingInfo,
    fetchUsageHistory,
    generateReport,
    fetchCostProjections,
    fetchAlerts,
    runMonitoringCheck,
    markAlertAsRead,
    setUsageLimit,
    startAutoRefresh,
    stopAutoRefresh,
    clearError,
    refreshAllData,
    clearAllData
  }
})
