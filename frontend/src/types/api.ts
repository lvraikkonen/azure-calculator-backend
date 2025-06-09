/**
 * API响应基础类型定义
 */

// 基础API响应结构
export interface ApiResponse<T = any> {
  code?: number
  message?: string
  data: T
  detail?: string // FastAPI错误格式
}

// 分页响应结构
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  has_next: boolean
  has_prev: boolean
}

// API错误类型
export interface ApiError {
  code: number
  message: string
  detail?: string
  errors?: Record<string, string[]>
}

// HTTP状态码枚举
export enum HttpStatus {
  OK = 200,
  CREATED = 201,
  NO_CONTENT = 204,
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  CONFLICT = 409,
  UNPROCESSABLE_ENTITY = 422,
  INTERNAL_SERVER_ERROR = 500
}

// 请求方法枚举
export enum HttpMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  PATCH = 'PATCH',
  DELETE = 'DELETE'
}

// 认证相关类型
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in?: number
  refresh_token?: string
  user?: UserInfo
}

export interface UserInfo {
  id: string
  username: string
  full_name: string
  email: string
  is_active: boolean
  is_superuser: boolean
  groups?: string
  auth_source: 'local' | 'ldap'
  created_at: string
  updated_at: string
  last_login?: string
}

// 注册相关类型
export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
}

// Token相关类型
export interface TokenPayload {
  sub: string // subject (user id)
  exp: number // expiration time
  iat: number // issued at
  type: string // token type
}

// 健康检查响应
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy'
  database_connected?: boolean
  active_plugins?: number
  total_plugins?: number
  checked_at: string
  error?: string
}
