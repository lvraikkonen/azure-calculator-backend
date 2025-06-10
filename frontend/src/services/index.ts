/**
 * 服务层统一导出
 */

// HTTP客户端
export { httpClient, HttpClient } from './http'
export type { AxiosRequestConfig, AxiosResponse } from './http'

// API服务
export { authAPI, AuthAPI } from './api/auth'
export { chatAPI, ChatAPI } from './api/chat'
export { modelsAPI, ModelsAPI } from './api/models'
export { billingAPI, BillingAPI } from './api/billing'

// 为stores提供的简化服务接口
export const authService = authAPI
export const chatService = chatAPI
export const modelService = modelsAPI
export const billingService = billingAPI

// WebSocket服务
export {
  webSocketService,
  WebSocketService,
  WebSocketStatus
} from './websocket'
export type { EventListener } from './websocket'

// 重新导出WebSocketEventType
export { WebSocketEventType } from './websocket'

// 存储服务
export { 
  localStorage, 
  sessionStorage, 
  storage, 
  StorageService, 
  StorageType,
  STORAGE_KEYS 
} from './storage'

// 服务工厂类（用于依赖注入和服务管理）
export class ServiceFactory {
  private static instance: ServiceFactory
  private services: Map<string, any> = new Map()

  private constructor() {}

  static getInstance(): ServiceFactory {
    if (!ServiceFactory.instance) {
      ServiceFactory.instance = new ServiceFactory()
    }
    return ServiceFactory.instance
  }

  /**
   * 注册服务
   */
  register<T>(name: string, service: T): void {
    this.services.set(name, service)
  }

  /**
   * 获取服务
   */
  get<T>(name: string): T {
    const service = this.services.get(name)
    if (!service) {
      throw new Error(`Service ${name} not found`)
    }
    return service
  }

  /**
   * 检查服务是否存在
   */
  has(name: string): boolean {
    return this.services.has(name)
  }

  /**
   * 移除服务
   */
  remove(name: string): void {
    this.services.delete(name)
  }

  /**
   * 清空所有服务
   */
  clear(): void {
    this.services.clear()
  }
}

// 创建服务工厂实例
export const serviceFactory = ServiceFactory.getInstance()

// 注册默认服务
import { httpClient } from './http'
import { authAPI } from './api/auth'
import { chatAPI } from './api/chat'
import { modelsAPI } from './api/models'
import { webSocketService } from './websocket'
import { storage } from './storage'

import { billingAPI } from './api/billing'

serviceFactory.register('http', httpClient)
serviceFactory.register('auth', authAPI)
serviceFactory.register('chat', chatAPI)
serviceFactory.register('models', modelsAPI)
serviceFactory.register('billing', billingAPI)
serviceFactory.register('websocket', webSocketService)
serviceFactory.register('storage', storage)

// 服务初始化函数
export async function initializeServices(): Promise<void> {
  try {
    console.log('Initializing services...')

    // 清理过期缓存
    storage.cleanExpiredCache()

    // 检查认证状态
    const token = storage.getAuthToken()
    if (token) {
      try {
        await authAPI.validateToken()
        console.log('Auth token validated')
      } catch (error) {
        console.warn('Auth token validation failed, clearing auth data')
        storage.clearAuth()
      }
    }

    console.log('Services initialized successfully')
  } catch (error) {
    console.error('Failed to initialize services:', error)
    throw error
  }
}

// 服务清理函数
export function cleanupServices(): void {
  try {
    console.log('Cleaning up services...')

    // 断开WebSocket连接
    webSocketService.disconnect()

    // 清理缓存
    storage.clearCache()

    console.log('Services cleaned up successfully')
  } catch (error) {
    console.error('Failed to cleanup services:', error)
  }
}

// 错误处理工具
export class ServiceError extends Error {
  public code: string | number
  public details?: any

  constructor(message: string, code: string | number = 'UNKNOWN', details?: any) {
    super(message)
    this.name = 'ServiceError'
    this.code = code
    this.details = details
  }
}

// 重试工具
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
  delay = 1000
): Promise<T> {
  let lastError: Error | null = null

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error

      if (attempt === maxAttempts) {
        break
      }

      console.warn(`Attempt ${attempt} failed, retrying in ${delay}ms...`, error)
      await new Promise(resolve => setTimeout(resolve, delay))
      delay *= 2 // 指数退避
    }
  }

  throw new ServiceError(
    `Operation failed after ${maxAttempts} attempts: ${lastError?.message || 'Unknown error'}`,
    'RETRY_EXHAUSTED',
    { originalError: lastError, attempts: maxAttempts }
  )
}

// 超时工具
export function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  timeoutMessage = 'Operation timed out'
): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) => {
      setTimeout(() => {
        reject(new ServiceError(timeoutMessage, 'TIMEOUT', { timeoutMs }))
      }, timeoutMs)
    })
  ])
}

// 批处理工具
export async function batchProcess<T, R>(
  items: T[],
  processor: (item: T) => Promise<R>,
  batchSize = 10,
  delay = 100
): Promise<R[]> {
  const results: R[] = []
  
  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize)
    const batchResults = await Promise.all(batch.map(processor))
    results.push(...batchResults)
    
    // 批次间延迟
    if (i + batchSize < items.length && delay > 0) {
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  
  return results
}

// 缓存装饰器
export function cached<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  cacheKey: string,
  ttl = 5 * 60 * 1000 // 5分钟
): T {
  return (async (...args: Parameters<T>) => {
    const key = `${cacheKey}_${JSON.stringify(args)}`

    // 尝试从缓存获取
    const cached = storage.getCache ? storage.getCache(cacheKey, key) : null
    if (cached !== null) {
      return cached
    }

    // 执行函数并缓存结果
    const result = await fn(...args)
    if (storage.setCache) {
      storage.setCache(cacheKey, key, result, { ttl })
    }

    return result
  }) as T
}

// 防抖装饰器
export function debounced<T extends (...args: any[]) => any>(
  fn: T,
  delay = 300
): T {
  let timeoutId: number | null = null
  
  return ((...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    
    return new Promise<ReturnType<T>>((resolve, reject) => {
      timeoutId = window.setTimeout(async () => {
        try {
          const result = await fn(...args)
          resolve(result)
        } catch (error) {
          reject(error)
        }
      }, delay)
    })
  }) as T
}

// 节流装饰器
export function throttled<T extends (...args: any[]) => any>(
  fn: T,
  delay = 300
): T {
  let lastCall = 0
  
  return ((...args: Parameters<T>) => {
    const now = Date.now()
    
    if (now - lastCall >= delay) {
      lastCall = now
      return fn(...args)
    }
    
    return Promise.resolve() as ReturnType<T>
  }) as T
}
