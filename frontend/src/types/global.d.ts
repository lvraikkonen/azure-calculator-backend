/**
 * 全局类型声明
 */

// 环境变量类型声明
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_ENV: 'development' | 'production' | 'test'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// 全局常量
declare const __APP_VERSION__: string
declare const __BUILD_TIME__: string

// Window对象扩展
declare interface Window {
  // 可能的第三方库
  gtag?: (...args: any[]) => void
  dataLayer?: any[]
  
  // 应用特定的全局变量
  __APP_CONFIG__?: AppConfig
  __USER_CONFIG__?: UserConfig
}

// 应用配置
interface AppConfig {
  apiBaseUrl: string
  wsUrl: string
  version: string
  buildTime: string
  features: FeatureFlags
}

// 用户配置
interface UserConfig {
  theme: 'light' | 'dark' | 'auto'
  language: string
  timezone: string
  preferences: UserPreferences
}

// 功能开关
interface FeatureFlags {
  enableRAG: boolean
  enableVoiceInput: boolean
  enableFileUpload: boolean
  enableAdvancedAnalytics: boolean
  enableMultiTenant: boolean
  enableSSO: boolean
}

// 用户偏好设置
interface UserPreferences {
  defaultModel?: string
  autoSave: boolean
  showTypingIndicator: boolean
  enableNotifications: boolean
  compactMode: boolean
  showTimestamps: boolean
  messageGrouping: boolean
}

// 通用工具类型
type Nullable<T> = T | null
type Optional<T> = T | undefined
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

// 分页参数
interface PaginationParams {
  page?: number
  limit?: number
  offset?: number
}

// 排序参数
interface SortParams {
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// 过滤参数
interface FilterParams {
  search?: string
  filters?: Record<string, any>
}

// 查询参数（组合类型）
type QueryParams = PaginationParams & SortParams & FilterParams

// 表单验证规则
interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  pattern?: RegExp
  validator?: (value: any) => boolean | string
  message?: string
}

// 表单字段配置
interface FormFieldConfig {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'textarea' | 'checkbox' | 'radio'
  placeholder?: string
  defaultValue?: any
  options?: Array<{ label: string; value: any }>
  rules?: ValidationRule[]
  disabled?: boolean
  hidden?: boolean
}

// 表格列配置
interface TableColumn {
  key: string
  title: string
  dataIndex?: string
  width?: number | string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  filterable?: boolean
  render?: (value: any, record: any, index: number) => any
  fixed?: 'left' | 'right'
}

// 菜单项配置
interface MenuItem {
  key: string
  label: string
  icon?: string
  path?: string
  children?: MenuItem[]
  disabled?: boolean
  hidden?: boolean
  permission?: string
}

// 通知配置
interface NotificationConfig {
  type: 'success' | 'info' | 'warning' | 'error'
  title: string
  message?: string
  duration?: number
  showClose?: boolean
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
}

// 模态框配置
interface ModalConfig {
  title: string
  content?: string
  width?: number | string
  height?: number | string
  closable?: boolean
  maskClosable?: boolean
  keyboard?: boolean
  centered?: boolean
  destroyOnClose?: boolean
}

// 主题配置
interface ThemeConfig {
  primaryColor: string
  successColor: string
  warningColor: string
  errorColor: string
  infoColor: string
  textColor: string
  backgroundColor: string
  borderColor: string
  borderRadius: string
  fontSize: string
  fontFamily: string
}

// 路由元信息
interface RouteMeta {
  title?: string
  icon?: string
  permission?: string
  roles?: string[]
  hidden?: boolean
  keepAlive?: boolean
  breadcrumb?: boolean
  affix?: boolean
}

// 错误信息
interface ErrorInfo {
  code: string | number
  message: string
  details?: any
  timestamp: string
  requestId?: string
  stack?: string
}

// 加载状态
interface LoadingState {
  loading: boolean
  error?: ErrorInfo
  lastUpdated?: string
}

// 异步操作状态
type AsyncState<T> = {
  data?: T
  loading: boolean
  error?: ErrorInfo
  lastUpdated?: string
}

// 事件处理器类型
type EventHandler<T = Event> = (event: T) => void
type AsyncEventHandler<T = Event> = (event: T) => Promise<void>

// 组件Props基础类型
interface BaseComponentProps {
  class?: string
  style?: string | Record<string, any>
  id?: string
}

// 可选的组件Props
type ComponentProps<T = {}> = BaseComponentProps & T

// 插件配置
interface PluginConfig {
  name: string
  version: string
  enabled: boolean
  config?: Record<string, any>
}

// 系统信息
interface SystemInfo {
  version: string
  buildTime: string
  environment: string
  features: FeatureFlags
  plugins: PluginConfig[]
}

// 导出常用类型
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
}
