/**
 * 用户相关类型定义
 */

// 用户基础信息
export interface User {
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
  role?: string
  permissions?: string[]
}

// 用户创建请求
export interface UserCreate {
  username: string
  email: string
  password: string
  full_name?: string
  is_active?: boolean
  is_superuser?: boolean
  groups?: string
}

// 用户更新请求
export interface UserUpdate {
  full_name?: string
  email?: string
  is_active?: boolean
  is_superuser?: boolean
  groups?: string
}

// 用户密码更新
export interface UserPasswordUpdate {
  current_password: string
  new_password: string
  confirm_password: string
}

// 用户列表响应
export interface UserListResponse {
  users: User[]
  total: number
  page: number
  limit: number
}

// 用户详情响应
export interface UserDetailResponse extends User {
  roles?: Role[]
  permissions?: string[]
  last_activity?: string
  login_count?: number
}

// 角色相关类型
export interface Role {
  id: string
  name: string
  description?: string
  permissions?: string[]
  created_at: string
  updated_at: string
}

export interface RoleCreate {
  name: string
  description?: string
  permissions?: string[]
}

export interface RoleUpdate {
  name?: string
  description?: string
  permissions?: string[]
}

// LDAP用户相关类型
export interface LDAPUserCreate {
  username: string
  full_name?: string
  email?: string
  groups?: string
}

export interface LDAPUserSearchRequest {
  search_term: string
  search_base?: string
  attributes?: string[]
}

export interface LDAPUserSearchResponse {
  users: LDAPUser[]
  total: number
}

export interface LDAPUser {
  username: string
  full_name?: string
  email?: string
  department?: string
  title?: string
  groups?: string[]
}

export interface LDAPTestRequest {
  server: string
  port: number
  domain: string
  username: string
  password: string
}

export interface LDAPTestResponse {
  success: boolean
  message: string
  user_info?: LDAPUser
}

// 用户权限枚举
export enum UserPermission {
  // 用户管理
  USER_READ = 'user:read',
  USER_CREATE = 'user:create',
  USER_UPDATE = 'user:update',
  USER_DELETE = 'user:delete',
  
  // 角色管理
  ROLE_READ = 'role:read',
  ROLE_CREATE = 'role:create',
  ROLE_UPDATE = 'role:update',
  ROLE_DELETE = 'role:delete',
  
  // 模型管理
  MODEL_READ = 'model:read',
  MODEL_CREATE = 'model:create',
  MODEL_UPDATE = 'model:update',
  MODEL_DELETE = 'model:delete',
  
  // 系统管理
  SYSTEM_CONFIG = 'system:config',
  SYSTEM_MONITOR = 'system:monitor',
  
  // 聊天功能
  CHAT_USE = 'chat:use',
  CHAT_HISTORY = 'chat:history',
  
  // 计费管理
  BILLING_READ = 'billing:read',
  BILLING_MANAGE = 'billing:manage'
}

// 用户状态枚举
export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}

// 认证来源枚举
export enum AuthSource {
  LOCAL = 'local',
  LDAP = 'ldap',
  SSO = 'sso'
}
