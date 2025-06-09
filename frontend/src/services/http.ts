/**
 * HTTP客户端封装
 * 提供统一的API请求处理、错误处理和响应拦截
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage, ElNotification } from 'element-plus'
import type { ApiResponse, ApiError } from '@/types'

// HTTP客户端类
class HttpClient {
  private instance: AxiosInstance
  private baseURL: string

  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    this.instance = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.setupInterceptors()
  }

  /**
   * 设置请求和响应拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        // 添加认证token
        const token = this.getAuthToken()
        console.log('🔍 获取到的token:', token ? `${token.substring(0, 20)}...` : 'null')

        if (token) {
          config.headers.Authorization = `Bearer ${token}`
          console.log('✅ 已设置Authorization头')
        } else {
          console.log('❌ 没有token，跳过Authorization头设置')
        }

        // 添加请求ID用于追踪
        config.headers['X-Request-ID'] = this.generateRequestId()

        // 开发环境下打印请求信息
        if (import.meta.env.VITE_APP_ENV === 'development') {
          console.log(`🚀 ${config.method?.toUpperCase()} ${config.url}`)
          console.log('📋 请求参数:', config.params)
          console.log('📦 请求数据:', config.data)
          console.log('📨 请求头:', config.headers)
          console.log('🔑 Authorization头:', config.headers.Authorization)
        }

        return config
      },
      (error) => {
        console.error('Request interceptor error:', error)
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        // 开发环境下打印响应信息
        if (import.meta.env.VITE_APP_ENV === 'development') {
          console.log(`✅ ${response.config.method?.toUpperCase()} ${response.config.url}`, {
            status: response.status,
            data: response.data
          })
        }

        return response
      },
      (error: AxiosError) => {
        this.handleResponseError(error)
        return Promise.reject(error)
      }
    )
  }

  /**
   * 处理响应错误
   */
  private handleResponseError(error: AxiosError): void {
    const { response, request, message } = error

    if (response) {
      // 服务器返回错误状态码
      const { status, data } = response
      const errorData = data as ApiError

      switch (status) {
        case 400:
          ElMessage.error(errorData?.detail || '请求参数错误')
          break
        case 401:
          // 开发环境下显示详细的401错误信息
          if (import.meta.env.VITE_APP_ENV === 'development') {
            console.error('🔒 401 Unauthorized详细信息:', {
              url: response.config?.url,
              method: response.config?.method,
              headers: response.config?.headers,
              responseData: errorData,
              responseHeaders: response.headers
            })
          }
          this.handleUnauthorized()
          break
        case 403:
          ElMessage.error('权限不足，无法访问该资源')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 422:
          this.handleValidationError(errorData)
          break
        case 429:
          ElMessage.warning('请求过于频繁，请稍后再试')
          break
        case 500:
          ElNotification.error({
            title: '服务器错误',
            message: '服务器内部错误，请联系管理员',
            duration: 5000
          })
          break
        case 502:
        case 503:
        case 504:
          ElNotification.error({
            title: '服务不可用',
            message: '服务暂时不可用，请稍后重试',
            duration: 5000
          })
          break
        default:
          ElMessage.error(errorData?.detail || `请求失败 (${status})`)
      }

      // 开发环境下打印详细错误信息
      if (import.meta.env.VITE_APP_ENV === 'development') {
        console.error(`❌ ${response.config?.method?.toUpperCase()} ${response.config?.url}`, {
          status,
          data: errorData,
          headers: response.headers
        })
      }
    } else if (request) {
      // 网络错误
      ElNotification.error({
        title: '网络错误',
        message: '网络连接失败，请检查网络设置',
        duration: 5000
      })
      console.error('Network error:', message)
    } else {
      // 其他错误
      ElMessage.error('请求配置错误')
      console.error('Request setup error:', message)
    }
  }

  /**
   * 处理401未授权错误
   */
  private handleUnauthorized(): void {
    ElMessage.error('登录已过期，请重新登录')
    
    // 清除本地存储的认证信息
    this.clearAuthToken()
    
    // 跳转到登录页面
    // 注意：这里不能直接使用router，因为会造成循环依赖
    // 应该通过事件或者store来处理
    window.location.href = '/login'
  }

  /**
   * 处理422验证错误
   */
  private handleValidationError(errorData: ApiError): void {
    if (errorData?.errors) {
      // 显示字段验证错误
      const errorMessages = Object.entries(errorData.errors)
        .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
        .join('\n')
      
      ElNotification.error({
        title: '数据验证失败',
        message: errorMessages,
        duration: 8000
      })
    } else {
      ElMessage.error(errorData?.detail || '数据验证失败')
    }
  }

  /**
   * 获取认证token
   */
  private getAuthToken(): string | null {
    return window.localStorage.getItem('auth_token')
  }

  /**
   * 清除认证token
   */
  private clearAuthToken(): void {
    window.localStorage.removeItem('auth_token')
  }

  /**
   * 生成请求ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`
  }

  /**
   * GET请求
   */
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url, config)
    return this.extractData(response)
  }

  /**
   * POST请求
   */
  async post<T, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config)
    return this.extractData(response)
  }

  /**
   * PUT请求
   */
  async put<T, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config)
    return this.extractData(response)
  }

  /**
   * PATCH请求
   */
  async patch<T, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.instance.patch<ApiResponse<T>>(url, data, config)
    return this.extractData(response)
  }

  /**
   * DELETE请求
   */
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config)
    return this.extractData(response)
  }

  /**
   * 文件上传
   */
  async upload<T>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void,
    additionalData?: Record<string, any>
  ): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)
    
    // 添加额外数据
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value)
      })
    }

    const config: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }

    if (onProgress) {
      config.onUploadProgress = (progressEvent) => {
        const progress = Math.round(
          (progressEvent.loaded * 100) / (progressEvent.total || 1)
        )
        onProgress(progress)
      }
    }

    const response = await this.instance.post<ApiResponse<T>>(url, formData, config)
    return this.extractData(response)
  }

  /**
   * 下载文件
   */
  async download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<void> {
    const response = await this.instance.get(url, {
      ...config,
      responseType: 'blob'
    })

    // 创建下载链接
    const blob = new Blob([response.data])
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename || this.extractFilenameFromResponse(response) || 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  }

  /**
   * 从响应中提取数据
   */
  private extractData<T>(response: AxiosResponse<ApiResponse<T>>): T {
    // 如果响应直接是数据（某些API可能不包装在ApiResponse中）
    if (response.data && typeof response.data === 'object' && 'data' in response.data) {
      return response.data.data
    }
    
    // 否则直接返回响应数据
    return response.data as unknown as T
  }

  /**
   * 从响应头中提取文件名
   */
  private extractFilenameFromResponse(response: AxiosResponse): string | null {
    const contentDisposition = response.headers['content-disposition']
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        return filenameMatch[1].replace(/['"]/g, '')
      }
    }
    return null
  }

  /**
   * 获取基础URL
   */
  getBaseURL(): string {
    return this.baseURL
  }

  /**
   * 获取axios实例（用于特殊需求）
   */
  getInstance(): AxiosInstance {
    return this.instance
  }
}

// 创建并导出HTTP客户端实例
export const httpClient = new HttpClient()

// 导出类型
export type { AxiosRequestConfig, AxiosResponse }
export { HttpClient }
