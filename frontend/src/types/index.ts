/**
 * 类型定义统一导出
 */

// 导入需要在接口定义中使用的类型
import type { RouteMeta } from './global'

// API相关类型
export type {
  ApiResponse,
  PaginatedResponse,
  ApiError,
  LoginRequest,
  LoginResponse,
  UserInfo,
  RegisterRequest,
  TokenPayload,
  HealthCheckResponse
} from './api'

export { HttpStatus, HttpMethod } from './api'

// 用户相关类型
export type {
  User,
  UserCreate,
  UserUpdate,
  UserPasswordUpdate,
  UserListResponse,
  UserDetailResponse,
  Role as UserRole,
  RoleCreate,
  RoleUpdate,
  LDAPUserCreate,
  LDAPUserSearchRequest,
  LDAPUserSearchResponse,
  LDAPUser,
  LDAPTestRequest,
  LDAPTestResponse
} from './user'

export { UserPermission, UserStatus, AuthSource } from './user'

// 聊天相关类型
export type {
  ChatMessage,
  MessageMetadata,
  Citation,
  RAGSource,
  TokenUsage,
  Conversation,
  ConversationMetadata,
  ModelSwitch,
  ConversationSummary,
  MessageCreate,
  ConversationCreate,
  ConversationUpdate,
  MessageFeedback,
  FeedbackCreate,
  ChatStatistics,
  ModelUsageStats,
  DailyUsageStats,
  WebSocketMessage,
  TypingStatus,
  Recommendation,
  MessageSearchRequest,
  MessageSearchResponse,
  SearchHighlight
} from './chat'

export { MessageRole, MessageStatus } from './chat'

// 模型相关类型
export type {
  ModelInfo,
  ModelMetadata,
  ModelParameters,
  RateLimit,
  ModelCreate,
  ModelUpdate,
  ModelResponse,
  ModelSummary,
  ModelListResponse,
  ModelSelection,
  ModelPerformance,
  DailyPerformanceStats,
  ModelRecommendationRequest,
  PerformanceRequirements,
  BudgetConstraints,
  UserPreferences as ModelUserPreferences,
  ModelRecommendationResponse,
  AlternativeModel,
  EstimatedPerformance,
  ModelTestRequest,
  ModelTestResponse,
  TestResult,
  TestSummary
} from './model'

export { ModelType, ModelCapability, ModelStatus } from './model'

// 计费相关类型
export type {
  TokenUsageRecord,
  UsageMetadata,
  UserBilling,
  PaymentMethod,
  BillingAddress,
  UsageStatistics,
  ModelUsageBreakdown,
  DailyUsage,
  CostTrend,
  Invoice,
  InvoiceLineItem,
  BudgetConfiguration,
  AlertThreshold,
  CostAnalysis,
  CostBreakdown,
  ModelCostBreakdown,
  FeatureCostBreakdown,
  TimeCostBreakdown,
  CostPrediction,
  CostRecommendation,
  EfficiencyMetrics,
  BillingConfiguration,
  PaymentRecord,
  RefundRecord,
  UsageQueryRequest,
  UsageQueryResponse,
  UsageSummary
} from './billing'

export { 
  BillingStatus, 
  UsageStatus, 
  BillingPeriod, 
  Currency, 
  NotificationMethod 
} from './billing'

// 全局类型
export type {
  Nullable,
  Optional,
  DeepPartial,
  QueryParams,
  PaginationParams,
  SortParams,
  FilterParams,
  ValidationRule,
  FormFieldConfig,
  TableColumn,
  MenuItem,
  NotificationConfig,
  ModalConfig,
  ThemeConfig,
  RouteMeta,
  ErrorInfo,
  LoadingState,
  AsyncState,
  EventHandler,
  AsyncEventHandler,
  ComponentProps,
  PluginConfig,
  SystemInfo,
  AppConfig,
  UserConfig,
  FeatureFlags,
  UserPreferences
} from './global'

// 常用类型别名
export type ID = string
export type Timestamp = string
export type JSONValue = string | number | boolean | null | JSONObject | JSONArray
export type JSONObject = { [key: string]: JSONValue }
export type JSONArray = JSONValue[]

// 常用泛型类型
export type KeyValuePair<K = string, V = any> = {
  key: K
  value: V
}

export type SelectOption<T = any> = {
  label: string
  value: T
  disabled?: boolean
  children?: SelectOption<T>[]
}

export type TreeNode<T = any> = {
  id: ID
  label: string
  children?: TreeNode<T>[]
  data?: T
  disabled?: boolean
  expanded?: boolean
  selected?: boolean
}

// 表单相关类型
export type FormData = Record<string, any>
export type FormErrors = Record<string, string | string[]>
export type FormTouched = Record<string, boolean>

export interface FormState<T = FormData> {
  values: T
  errors: FormErrors
  touched: FormTouched
  isValid: boolean
  isSubmitting: boolean
  isDirty: boolean
}

// 表格相关类型
export interface TableState<T = any> {
  data: T[]
  loading: boolean
  pagination: {
    current: number
    pageSize: number
    total: number
  }
  sorter: {
    field?: string
    order?: 'ascend' | 'descend'
  }
  filters: Record<string, any>
  selectedRowKeys: (string | number)[]
}

// 路由相关类型
export interface RouteConfig {
  path: string
  name?: string
  component?: any
  redirect?: string
  meta?: RouteMeta
  children?: RouteConfig[]
  beforeEnter?: (to: any, from: any, next: any) => void
}

// 主题相关类型
export type ThemeMode = 'light' | 'dark' | 'auto'
export type ColorScheme = 'blue' | 'green' | 'purple' | 'orange' | 'red'

// 语言相关类型
export type Locale = 'zh-CN' | 'en-US' | 'ja-JP' | 'ko-KR'

// 设备类型
export type DeviceType = 'desktop' | 'tablet' | 'mobile'

// 网络状态
export type NetworkStatus = 'online' | 'offline' | 'slow'

// 权限相关类型
export type Permission = string
export type RoleString = string

// 文件相关类型
export interface FileInfo {
  name: string
  size: number
  type: string
  lastModified: number
  url?: string
}

export interface UploadFile extends FileInfo {
  uid: string
  status: 'uploading' | 'done' | 'error' | 'removed'
  percent?: number
  response?: any
  error?: any
}

// 导出所有枚举
export * from './api'
export * from './user'
export * from './chat'
export * from './model'
export * from './billing'
