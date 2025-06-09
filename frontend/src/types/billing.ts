/**
 * 计费相关类型定义
 */

// 计费状态枚举
export enum BillingStatus {
  ACTIVE = 'active',
  SUSPENDED = 'suspended',
  OVERDUE = 'overdue',
  CANCELLED = 'cancelled'
}

// 使用记录状态枚举
export enum UsageStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded'
}

// 计费周期枚举
export enum BillingPeriod {
  HOURLY = 'hourly',
  DAILY = 'daily',
  WEEKLY = 'weekly',
  MONTHLY = 'monthly',
  YEARLY = 'yearly'
}

// 货币枚举
export enum Currency {
  USD = 'USD',
  CNY = 'CNY',
  EUR = 'EUR',
  GBP = 'GBP'
}

// Token使用记录
export interface TokenUsageRecord {
  id: string
  user_id: string
  model_id: string
  conversation_id?: string
  message_id?: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  input_cost: number
  output_cost: number
  total_cost: number
  currency: Currency
  created_at: string
  status: UsageStatus
  metadata?: UsageMetadata
}

// 使用元数据
export interface UsageMetadata {
  model_name?: string
  model_type?: string
  response_time?: number
  request_id?: string
  session_id?: string
  user_agent?: string
  ip_address?: string
  rag_enabled?: boolean
  reasoning_enabled?: boolean
}

// 用户计费信息
export interface UserBilling {
  user_id: string
  username: string
  status: BillingStatus
  current_balance: number
  credit_limit: number
  currency: Currency
  billing_period: BillingPeriod
  next_billing_date: string
  created_at: string
  updated_at: string
  payment_method?: PaymentMethod
  billing_address?: BillingAddress
}

// 支付方式
export interface PaymentMethod {
  id: string
  type: 'credit_card' | 'debit_card' | 'bank_transfer' | 'digital_wallet'
  last_four?: string
  expiry_month?: number
  expiry_year?: number
  brand?: string
  is_default: boolean
  created_at: string
}

// 账单地址
export interface BillingAddress {
  street: string
  city: string
  state?: string
  postal_code: string
  country: string
  company?: string
}

// 使用统计
export interface UsageStatistics {
  user_id: string
  period_start: string
  period_end: string
  total_requests: number
  total_tokens: number
  total_cost: number
  currency: Currency
  model_breakdown: ModelUsageBreakdown[]
  daily_usage: DailyUsage[]
  cost_trend: CostTrend[]
}

// 模型使用分解
export interface ModelUsageBreakdown {
  model_id: string
  model_name: string
  request_count: number
  token_count: number
  cost: number
  percentage: number
}

// 每日使用
export interface DailyUsage {
  date: string
  requests: number
  tokens: number
  cost: number
}

// 成本趋势
export interface CostTrend {
  period: string
  cost: number
  change_percentage: number
}

// 账单
export interface Invoice {
  id: string
  user_id: string
  invoice_number: string
  billing_period_start: string
  billing_period_end: string
  subtotal: number
  tax_amount: number
  discount_amount: number
  total_amount: number
  currency: Currency
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
  due_date: string
  paid_date?: string
  created_at: string
  line_items: InvoiceLineItem[]
}

// 账单行项目
export interface InvoiceLineItem {
  id: string
  description: string
  quantity: number
  unit_price: number
  total_price: number
  model_id?: string
  usage_period_start: string
  usage_period_end: string
}

// 预算配置
export interface BudgetConfiguration {
  user_id: string
  daily_limit?: number
  weekly_limit?: number
  monthly_limit?: number
  yearly_limit?: number
  currency: Currency
  alert_thresholds: AlertThreshold[]
  auto_disable_on_limit: boolean
  created_at: string
  updated_at: string
}

// 告警阈值
export interface AlertThreshold {
  percentage: number // 预算百分比
  notification_methods: NotificationMethod[]
  is_active: boolean
}

// 通知方式
export enum NotificationMethod {
  EMAIL = 'email',
  SMS = 'sms',
  WEBHOOK = 'webhook',
  IN_APP = 'in_app'
}

// 成本分析
export interface CostAnalysis {
  user_id: string
  analysis_period: string
  total_cost: number
  cost_breakdown: CostBreakdown
  predictions: CostPrediction[]
  recommendations: CostRecommendation[]
  efficiency_metrics: EfficiencyMetrics
}

// 成本分解
export interface CostBreakdown {
  by_model: ModelCostBreakdown[]
  by_feature: FeatureCostBreakdown[]
  by_time: TimeCostBreakdown[]
}

// 模型成本分解
export interface ModelCostBreakdown {
  model_id: string
  model_name: string
  cost: number
  percentage: number
  efficiency_score: number
}

// 功能成本分解
export interface FeatureCostBreakdown {
  feature: string
  cost: number
  percentage: number
  usage_count: number
}

// 时间成本分解
export interface TimeCostBreakdown {
  period: string
  cost: number
  usage_count: number
  avg_cost_per_request: number
}

// 成本预测
export interface CostPrediction {
  period: string
  predicted_cost: number
  confidence_interval: [number, number]
  factors: string[]
}

// 成本建议
export interface CostRecommendation {
  type: 'model_switch' | 'usage_optimization' | 'budget_adjustment'
  title: string
  description: string
  potential_savings: number
  implementation_effort: 'low' | 'medium' | 'high'
  priority: 'low' | 'medium' | 'high'
}

// 效率指标
export interface EfficiencyMetrics {
  cost_per_request: number
  cost_per_token: number
  cost_per_conversation: number
  utilization_rate: number
  waste_percentage: number
}

// 计费配置
export interface BillingConfiguration {
  default_currency: Currency
  tax_rate: number
  billing_cycle: BillingPeriod
  payment_terms_days: number
  late_fee_percentage: number
  credit_limit_default: number
  auto_billing_enabled: boolean
  invoice_template: string
}

// 支付记录
export interface PaymentRecord {
  id: string
  user_id: string
  invoice_id?: string
  amount: number
  currency: Currency
  payment_method_id: string
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  transaction_id?: string
  gateway_response?: Record<string, any>
  created_at: string
  processed_at?: string
}

// 退款记录
export interface RefundRecord {
  id: string
  payment_id: string
  amount: number
  currency: Currency
  reason: string
  status: 'pending' | 'completed' | 'failed'
  processed_at?: string
  created_at: string
}

// 使用查询请求
export interface UsageQueryRequest {
  user_id?: string
  model_id?: string
  date_from?: string
  date_to?: string
  status?: UsageStatus
  limit?: number
  offset?: number
  group_by?: 'model' | 'date' | 'user'
}

// 使用查询响应
export interface UsageQueryResponse {
  records: TokenUsageRecord[]
  total: number
  summary: UsageSummary
  aggregations?: Record<string, any>
}

// 使用摘要
export interface UsageSummary {
  total_requests: number
  total_tokens: number
  total_cost: number
  unique_users: number
  unique_models: number
  date_range: [string, string]
}
