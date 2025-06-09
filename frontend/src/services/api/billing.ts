/**
 * 计费相关API服务
 */

import { httpClient } from '../http'
import type {
  TokenUsageStats,
  BillingInfo,
  UsageReport,
  CostProjection,
  MonitoringAlert
} from '@/types'
import { Currency, BillingStatus, BillingPeriod } from '@/types'

export class BillingAPI {
  private readonly baseURL = '/api/v1/token-billing'

  /**
   * 获取当前使用统计 (模拟数据)
   */
  async getCurrentUsage(): Promise<TokenUsageStats> {
    // 暂时返回模拟数据，因为后端还没有这个端点
    return {
      user_id: 'current-user',
      period_start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      period_end: new Date().toISOString(),
      total_requests: 150,
      total_tokens: 45000,
      total_cost: 12.50,
      currency: Currency.USD,
      model_breakdown: [],
      daily_usage: [],
      cost_trend: [],
      date: new Date().toISOString().split('T')[0]
    }
  }

  /**
   * 获取计费信息 (模拟数据)
   */
  async getBillingInfo(): Promise<BillingInfo> {
    // 暂时返回模拟数据，因为后端还没有这个端点
    return {
      user_id: 'current-user',
      username: 'admin',
      status: BillingStatus.ACTIVE,
      current_balance: 87.50,
      credit_limit: 100.00,
      currency: Currency.USD,
      billing_period: BillingPeriod.MONTHLY,
      next_billing_date: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      remaining_balance: 87.50,
      monthly_limit: 100.00
    }
  }

  /**
   * 获取使用历史 (模拟数据)
   */
  async getUsageHistory(days: number = 30): Promise<TokenUsageStats[]> {
    // 暂时返回模拟数据，因为后端还没有这个端点
    const history: TokenUsageStats[] = []
    for (let i = 0; i < Math.min(days, 7); i++) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000)
      history.push({
        user_id: 'current-user',
        period_start: date.toISOString(),
        period_end: date.toISOString(),
        total_requests: Math.floor(Math.random() * 50) + 10,
        total_tokens: Math.floor(Math.random() * 10000) + 1000,
        total_cost: Math.random() * 5 + 1,
        currency: Currency.USD,
        model_breakdown: [],
        daily_usage: [],
        cost_trend: [],
        date: date.toISOString().split('T')[0]
      })
    }
    return history
  }

  /**
   * 生成使用报告
   */
  async generateReport(request: {
    start_date: string
    end_date: string
    report_type: string
  }): Promise<UsageReport> {
    return await httpClient.post<UsageReport>(`${this.baseURL}/reports/generate`, request)
  }

  /**
   * 获取成本预测
   */
  async getCostProjections(): Promise<CostProjection[]> {
    return await httpClient.get<CostProjection[]>(`${this.baseURL}/projections`)
  }

  /**
   * 获取监控告警
   */
  async getAlerts(): Promise<MonitoringAlert[]> {
    return await httpClient.get<MonitoringAlert[]>(`${this.baseURL}/alerts`)
  }

  /**
   * 运行监控检查
   */
  async runMonitoringCheck(): Promise<{ alerts_found: number }> {
    return await httpClient.post<{ alerts_found: number }>(`${this.baseURL}/monitoring/check`, {
      target_date: new Date().toISOString().split('T')[0]
    })
  }

  /**
   * 标记告警为已读
   */
  async markAlertAsRead(alertId: string): Promise<void> {
    await httpClient.patch(`${this.baseURL}/alerts/${alertId}/read`)
  }

  /**
   * 设置使用限制
   */
  async setUsageLimit(limit: number): Promise<BillingInfo> {
    return await httpClient.patch<BillingInfo>(`${this.baseURL}/billing/limit`, {
      monthly_limit: limit
    })
  }

  /**
   * 获取使用统计
   */
  async getUsageStats(params?: {
    start_date?: string
    end_date?: string
    model_id?: string
    group_by?: string
  }): Promise<any> {
    return await httpClient.get<any>(`${this.baseURL}/stats`, { params })
  }

  /**
   * 获取成本分析
   */
  async getCostAnalysis(params?: {
    start_date?: string
    end_date?: string
    breakdown_by?: string
  }): Promise<any> {
    return await httpClient.get<any>(`${this.baseURL}/cost-analysis`, { params })
  }

  /**
   * 导出使用数据
   */
  async exportUsageData(params: {
    start_date: string
    end_date: string
    format: 'csv' | 'excel' | 'json'
  }): Promise<Blob> {
    return await httpClient.get<Blob>(`${this.baseURL}/export`, {
      params,
      responseType: 'blob'
    })
  }

  /**
   * 获取计费配置
   */
  async getBillingConfig(): Promise<any> {
    return await httpClient.get<any>(`${this.baseURL}/config`)
  }

  /**
   * 更新计费配置
   */
  async updateBillingConfig(config: any): Promise<any> {
    return await httpClient.patch<any>(`${this.baseURL}/config`, config)
  }

  /**
   * 获取健康检查
   */
  async getHealthCheck(): Promise<any> {
    return await httpClient.get<any>(`${this.baseURL}/health`)
  }
}

// 创建实例
export const billingAPI = new BillingAPI()

// 默认导出
export default billingAPI
