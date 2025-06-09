/**
 * 本地存储服务
 * 提供统一的本地数据存储和管理功能
 */

// 存储键名常量
export const STORAGE_KEYS = {
  // 认证相关
  AUTH_TOKEN: 'auth_token',
  USER_INFO: 'user_info',
  REFRESH_TOKEN: 'refresh_token',
  
  // 用户偏好
  THEME: 'theme',
  LANGUAGE: 'language',
  SELECTED_MODEL: 'selected_model_id',
  RAG_ENABLED: 'rag_enabled',
  
  // 聊天相关
  DRAFT_MESSAGES: 'draft_messages',
  CHAT_SETTINGS: 'chat_settings',
  CONVERSATION_FILTERS: 'conversation_filters',
  
  // UI状态
  SIDEBAR_COLLAPSED: 'sidebar_collapsed',
  WINDOW_SIZE: 'window_size',
  LAYOUT_CONFIG: 'layout_config',
  
  // 缓存
  MODEL_CACHE: 'model_cache',
  USER_CACHE: 'user_cache',
  CONVERSATION_CACHE: 'conversation_cache'
} as const

// 存储类型
export enum StorageType {
  LOCAL = 'localStorage',
  SESSION = 'sessionStorage'
}

// 缓存配置
interface CacheConfig {
  ttl?: number // 生存时间（毫秒）
  maxSize?: number // 最大缓存大小
}

// 缓存项
interface CacheItem<T> {
  data: T
  timestamp: number
  ttl?: number
}

export class StorageService {
  private storage: Storage
  private caches: Map<string, Map<string, CacheItem<any>>> = new Map()

  constructor(type: StorageType = StorageType.LOCAL) {
    this.storage = type === StorageType.LOCAL ? window.localStorage : window.sessionStorage
  }

  /**
   * 设置存储项
   */
  set<T>(key: string, value: T): void {
    try {
      const serializedValue = JSON.stringify(value)
      this.storage.setItem(key, serializedValue)
    } catch (error) {
      console.error(`Failed to set storage item ${key}:`, error)
    }
  }

  /**
   * 直接设置字符串值（不进行JSON序列化）
   */
  setString(key: string, value: string): void {
    try {
      this.storage.setItem(key, value)
    } catch (error) {
      console.error(`Failed to set string storage item ${key}:`, error)
    }
  }

  /**
   * 直接获取字符串值（不进行JSON解析）
   */
  getString(key: string, defaultValue?: string): string | null {
    try {
      const item = this.storage.getItem(key)
      return item ?? defaultValue ?? null
    } catch (error) {
      console.error(`Failed to get string storage item ${key}:`, error)
      return defaultValue ?? null
    }
  }

  /**
   * 获取存储项
   */
  get<T>(key: string, defaultValue?: T): T | null {
    try {
      const item = this.storage.getItem(key)
      if (item === null) {
        return defaultValue ?? null
      }
      return JSON.parse(item) as T
    } catch (error) {
      console.error(`Failed to get storage item ${key}:`, error)
      return defaultValue ?? null
    }
  }

  /**
   * 移除存储项
   */
  remove(key: string): void {
    try {
      this.storage.removeItem(key)
    } catch (error) {
      console.error(`Failed to remove storage item ${key}:`, error)
    }
  }

  /**
   * 清空所有存储
   */
  clear(): void {
    try {
      this.storage.clear()
    } catch (error) {
      console.error('Failed to clear storage:', error)
    }
  }

  /**
   * 检查存储项是否存在
   */
  has(key: string): boolean {
    return this.storage.getItem(key) !== null
  }

  /**
   * 获取所有键名
   */
  keys(): string[] {
    const keys: string[] = []
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i)
      if (key) {
        keys.push(key)
      }
    }
    return keys
  }

  /**
   * 获取存储大小（字节）
   */
  getSize(): number {
    let size = 0
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i)
      if (key) {
        const value = this.storage.getItem(key)
        if (value) {
          size += key.length + value.length
        }
      }
    }
    return size
  }

  /**
   * 设置缓存项
   */
  setCache<T>(
    cacheKey: string,
    itemKey: string,
    value: T,
    config?: CacheConfig
  ): void {
    if (!this.caches.has(cacheKey)) {
      this.caches.set(cacheKey, new Map())
    }

    const cache = this.caches.get(cacheKey)!
    const cacheItem: CacheItem<T> = {
      data: value,
      timestamp: Date.now(),
      ttl: config?.ttl
    }

    cache.set(itemKey, cacheItem)

    // 检查缓存大小限制
    if (config?.maxSize && cache.size > config.maxSize) {
      this.evictOldestCacheItem(cache)
    }
  }

  /**
   * 获取缓存项
   */
  getCache<T>(cacheKey: string, itemKey: string): T | null {
    const cache = this.caches.get(cacheKey)
    if (!cache) {
      return null
    }

    const cacheItem = cache.get(itemKey)
    if (!cacheItem) {
      return null
    }

    // 检查是否过期
    if (cacheItem.ttl && Date.now() - cacheItem.timestamp > cacheItem.ttl) {
      cache.delete(itemKey)
      return null
    }

    return cacheItem.data
  }

  /**
   * 移除缓存项
   */
  removeCache(cacheKey: string, itemKey?: string): void {
    if (itemKey) {
      const cache = this.caches.get(cacheKey)
      if (cache) {
        cache.delete(itemKey)
      }
    } else {
      this.caches.delete(cacheKey)
    }
  }

  /**
   * 清空所有缓存
   */
  clearCache(): void {
    this.caches.clear()
  }

  /**
   * 清理过期缓存
   */
  cleanExpiredCache(): void {
    for (const [cacheKey, cache] of this.caches) {
      for (const [itemKey, cacheItem] of cache) {
        if (cacheItem.ttl && Date.now() - cacheItem.timestamp > cacheItem.ttl) {
          cache.delete(itemKey)
        }
      }
      
      // 如果缓存为空，删除整个缓存
      if (cache.size === 0) {
        this.caches.delete(cacheKey)
      }
    }
  }

  /**
   * 驱逐最旧的缓存项
   */
  private evictOldestCacheItem(cache: Map<string, CacheItem<any>>): void {
    let oldestKey: string | null = null
    let oldestTimestamp = Date.now()

    for (const [key, item] of cache) {
      if (item.timestamp < oldestTimestamp) {
        oldestTimestamp = item.timestamp
        oldestKey = key
      }
    }

    if (oldestKey) {
      cache.delete(oldestKey)
    }
  }

  /**
   * 导出存储数据
   */
  export(): Record<string, any> {
    const data: Record<string, any> = {}
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i)
      if (key) {
        const value = this.storage.getItem(key)
        if (value) {
          try {
            data[key] = JSON.parse(value)
          } catch {
            data[key] = value
          }
        }
      }
    }
    return data
  }

  /**
   * 导入存储数据
   */
  import(data: Record<string, any>): void {
    for (const [key, value] of Object.entries(data)) {
      this.set(key, value)
    }
  }

  /**
   * 备份存储数据到文件
   */
  backup(filename = 'storage_backup.json'): void {
    const data = this.export()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
  }

  /**
   * 从文件恢复存储数据
   */
  async restore(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target?.result as string)
          this.import(data)
          resolve()
        } catch (error) {
          reject(new Error('Invalid backup file format'))
        }
      }
      
      reader.onerror = () => {
        reject(new Error('Failed to read backup file'))
      }
      
      reader.readAsText(file)
    })
  }
}

// 创建存储服务实例
export const localStorage = new StorageService(StorageType.LOCAL)
export const sessionStorage = new StorageService(StorageType.SESSION)

// 便捷方法
export const storage = {
  // 认证相关
  setAuthToken: (token: string) => localStorage.setString(STORAGE_KEYS.AUTH_TOKEN, token),
  getAuthToken: () => localStorage.getString(STORAGE_KEYS.AUTH_TOKEN),
  removeAuthToken: () => localStorage.remove(STORAGE_KEYS.AUTH_TOKEN),
  
  setUserInfo: (userInfo: any) => localStorage.set(STORAGE_KEYS.USER_INFO, userInfo),
  getUserInfo: () => localStorage.get(STORAGE_KEYS.USER_INFO),
  removeUserInfo: () => localStorage.remove(STORAGE_KEYS.USER_INFO),
  
  // 用户偏好
  setTheme: (theme: string) => localStorage.set(STORAGE_KEYS.THEME, theme),
  getTheme: () => localStorage.get<string>(STORAGE_KEYS.THEME, 'light'),
  
  setLanguage: (language: string) => localStorage.set(STORAGE_KEYS.LANGUAGE, language),
  getLanguage: () => localStorage.get<string>(STORAGE_KEYS.LANGUAGE, 'zh-CN'),
  
  setSelectedModel: (modelId: string) => localStorage.set(STORAGE_KEYS.SELECTED_MODEL, modelId),
  getSelectedModel: () => localStorage.get<string>(STORAGE_KEYS.SELECTED_MODEL),
  
  setRagEnabled: (enabled: boolean) => localStorage.set(STORAGE_KEYS.RAG_ENABLED, enabled),
  getRagEnabled: () => localStorage.get<boolean>(STORAGE_KEYS.RAG_ENABLED, false),
  
  // 聊天相关
  setDraftMessage: (conversationId: string, message: string) => {
    const drafts = localStorage.get<Record<string, string>>(STORAGE_KEYS.DRAFT_MESSAGES, {}) || {}
    drafts[conversationId] = message
    localStorage.set(STORAGE_KEYS.DRAFT_MESSAGES, drafts)
  },

  getDraftMessage: (conversationId: string) => {
    const drafts = localStorage.get<Record<string, string>>(STORAGE_KEYS.DRAFT_MESSAGES, {}) || {}
    return drafts[conversationId] || ''
  },

  removeDraftMessage: (conversationId: string) => {
    const drafts = localStorage.get<Record<string, string>>(STORAGE_KEYS.DRAFT_MESSAGES, {}) || {}
    delete drafts[conversationId]
    localStorage.set(STORAGE_KEYS.DRAFT_MESSAGES, drafts)
  },
  
  // UI状态
  setSidebarCollapsed: (collapsed: boolean) => localStorage.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, collapsed),
  getSidebarCollapsed: () => localStorage.get<boolean>(STORAGE_KEYS.SIDEBAR_COLLAPSED, false),
  
  // 清理方法
  clearAuth: () => {
    localStorage.remove(STORAGE_KEYS.AUTH_TOKEN)
    localStorage.remove(STORAGE_KEYS.USER_INFO)
    localStorage.remove(STORAGE_KEYS.REFRESH_TOKEN)
  },
  
  clearAll: () => {
    localStorage.clear()
    sessionStorage.clear()
  }
}

// 定期清理过期缓存
setInterval(() => {
  localStorage.cleanExpiredCache()
  sessionStorage.cleanExpiredCache()
}, 5 * 60 * 1000) // 每5分钟清理一次
