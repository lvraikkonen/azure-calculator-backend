/**
 * 认证相关API服务
 */

import { httpClient } from '@/services/http'
import type { 
  LoginRequest, 
  LoginResponse, 
  UserInfo, 
  RegisterRequest,
  UserPasswordUpdate 
} from '@/types'

export class AuthAPI {
  /**
   * 用户登录
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // FastAPI的OAuth2PasswordRequestForm需要FormData格式
    const formData = new FormData()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    // 使用axios实例进行请求，但需要特殊处理FormData
    const response = await httpClient.getInstance().post('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return response.data
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<UserInfo> {
    return httpClient.get<UserInfo>('/auth/me')
  }

  /**
   * 用户注册
   */
  async register(userData: RegisterRequest): Promise<UserInfo> {
    return httpClient.post<UserInfo>('/auth/register', userData)
  }

  /**
   * 刷新Token
   */
  async refreshToken(refreshToken?: string): Promise<LoginResponse> {
    const data = refreshToken ? { refresh_token: refreshToken } : {}
    return httpClient.post<LoginResponse>('/auth/refresh', data)
  }

  /**
   * 用户登出
   */
  async logout(): Promise<void> {
    try {
      await httpClient.post<void>('/auth/logout')
    } catch (error) {
      // 即使后端登出失败，也要清除本地状态
      console.warn('Backend logout failed:', error)
    }
  }

  /**
   * 修改密码
   */
  async changePassword(passwordData: UserPasswordUpdate): Promise<void> {
    return httpClient.post<void>('/auth/change-password', passwordData)
  }

  /**
   * 忘记密码 - 发送重置邮件
   */
  async forgotPassword(email: string): Promise<void> {
    return httpClient.post<void>('/auth/forgot-password', { email })
  }

  /**
   * 重置密码
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    return httpClient.post<void>('/auth/reset-password', {
      token,
      new_password: newPassword
    })
  }

  /**
   * 验证Token是否有效
   */
  async validateToken(): Promise<boolean> {
    try {
      await this.getCurrentUser()
      return true
    } catch {
      return false
    }
  }

  /**
   * 获取用户权限列表
   */
  async getUserPermissions(): Promise<string[]> {
    return httpClient.get<string[]>('/auth/permissions')
  }

  /**
   * 检查用户是否有特定权限
   */
  async hasPermission(permission: string): Promise<boolean> {
    try {
      const permissions = await this.getUserPermissions()
      return permissions.includes(permission)
    } catch {
      return false
    }
  }

  /**
   * 获取用户角色列表
   */
  async getUserRoles(): Promise<string[]> {
    return httpClient.get<string[]>('/auth/roles')
  }

  /**
   * 更新用户资料
   */
  async updateProfile(profileData: {
    full_name?: string
    email?: string
  }): Promise<UserInfo> {
    return httpClient.patch<UserInfo>('/auth/profile', profileData)
  }

  /**
   * 上传用户头像
   */
  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    return httpClient.upload<{ avatar_url: string }>('/auth/avatar', file)
  }

  /**
   * 启用两步验证
   */
  async enableTwoFactor(): Promise<{
    qr_code: string
    secret: string
    backup_codes: string[]
  }> {
    return httpClient.post<{
      qr_code: string
      secret: string
      backup_codes: string[]
    }>('/auth/2fa/enable')
  }

  /**
   * 确认两步验证
   */
  async confirmTwoFactor(code: string): Promise<void> {
    return httpClient.post<void>('/auth/2fa/confirm', { code })
  }

  /**
   * 禁用两步验证
   */
  async disableTwoFactor(password: string): Promise<void> {
    return httpClient.post<void>('/auth/2fa/disable', { password })
  }

  /**
   * 验证两步验证码
   */
  async verifyTwoFactor(code: string): Promise<void> {
    return httpClient.post<void>('/auth/2fa/verify', { code })
  }

  /**
   * 获取登录历史
   */
  async getLoginHistory(limit = 10): Promise<Array<{
    id: string
    ip_address: string
    user_agent: string
    location?: string
    login_time: string
    success: boolean
  }>> {
    return httpClient.get<Array<{
      id: string
      ip_address: string
      user_agent: string
      location?: string
      login_time: string
      success: boolean
    }>>(`/auth/login-history?limit=${limit}`)
  }

  /**
   * 获取活跃会话
   */
  async getActiveSessions(): Promise<Array<{
    id: string
    ip_address: string
    user_agent: string
    location?: string
    created_at: string
    last_activity: string
    is_current: boolean
  }>> {
    return httpClient.get<Array<{
      id: string
      ip_address: string
      user_agent: string
      location?: string
      created_at: string
      last_activity: string
      is_current: boolean
    }>>('/auth/sessions')
  }

  /**
   * 终止指定会话
   */
  async terminateSession(sessionId: string): Promise<void> {
    return httpClient.delete<void>(`/auth/sessions/${sessionId}`)
  }

  /**
   * 终止所有其他会话
   */
  async terminateAllOtherSessions(): Promise<void> {
    return httpClient.post<void>('/auth/sessions/terminate-others')
  }
}

// 创建并导出API实例
export const authAPI = new AuthAPI()
