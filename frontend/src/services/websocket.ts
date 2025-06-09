/**
 * WebSocket服务
 * 提供实时通信功能，支持聊天消息推送、状态更新等
 */

import { ElMessage, ElNotification } from 'element-plus'

// WebSocket连接状态
export enum WebSocketStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTING = 'disconnecting',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}

// 事件类型
export enum WebSocketEventType {
  MESSAGE = 'message',
  TYPING = 'typing',
  ERROR = 'error',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  TOKEN_UPDATE = 'token_update',
  CONVERSATION_UPDATE = 'conversation_update',
  USER_STATUS = 'user_status'
}

// 事件监听器类型
type EventListener = (data: any) => void

export class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private heartbeatInterval = 30000 // 30秒
  private listeners: Map<string, EventListener[]> = new Map()
  private status: WebSocketStatus = WebSocketStatus.DISCONNECTED
  private authToken: string | null = null

  constructor(url?: string) {
    this.url = url || import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    this.authToken = localStorage.getItem('auth_token')
  }

  /**
   * 连接WebSocket
   */
  async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('WebSocket is already connected')
      return
    }

    this.setStatus(WebSocketStatus.CONNECTING)

    return new Promise((resolve, reject) => {
      try {
        // 构建WebSocket URL，包含认证token
        const wsUrl = this.buildWebSocketUrl()
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.setStatus(WebSocketStatus.CONNECTED)
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.emit(WebSocketEventType.CONNECTED, {})
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event)
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          this.setStatus(WebSocketStatus.DISCONNECTED)
          this.stopHeartbeat()
          this.emit(WebSocketEventType.DISCONNECTED, { code: event.code, reason: event.reason })
          
          // 如果不是主动关闭，尝试重连
          if (event.code !== 1000) {
            this.handleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.setStatus(WebSocketStatus.ERROR)
          this.emit(WebSocketEventType.ERROR, { error })
          reject(error)
        }
      } catch (error) {
        this.setStatus(WebSocketStatus.ERROR)
        reject(error)
      }
    })
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this.stopHeartbeat()

    if (this.ws) {
      this.setStatus(WebSocketStatus.DISCONNECTING)
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }

    this.setStatus(WebSocketStatus.DISCONNECTED)
  }

  /**
   * 发送消息
   */
  send(type: string, data: any): void {
    if (!this.isConnected) {
      console.warn('WebSocket is not connected, message not sent:', { type, data })
      return
    }

    const message = {
      type,
      data,
      timestamp: new Date().toISOString()
    }

    try {
      this.ws!.send(JSON.stringify(message))
      
      // 开发环境下打印发送的消息
      if (import.meta.env.VITE_APP_ENV === 'development') {
        console.log('📤 WebSocket sent:', message)
      }
    } catch (error) {
      console.error('Failed to send WebSocket message:', error)
      ElMessage.error('消息发送失败')
    }
  }

  /**
   * 添加事件监听器
   */
  on(event: string, listener: EventListener): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(listener)
  }

  /**
   * 移除事件监听器
   */
  off(event: string, listener: EventListener): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      const index = eventListeners.indexOf(listener)
      if (index > -1) {
        eventListeners.splice(index, 1)
      }
    }
  }

  /**
   * 移除所有事件监听器
   */
  removeAllListeners(event?: string): void {
    if (event) {
      this.listeners.delete(event)
    } else {
      this.listeners.clear()
    }
  }

  /**
   * 发送打字状态
   */
  sendTypingStatus(conversationId: string, isTyping: boolean): void {
    this.send(WebSocketEventType.TYPING, {
      conversation_id: conversationId,
      is_typing: isTyping
    })
  }

  /**
   * 加入对话房间
   */
  joinConversation(conversationId: string): void {
    this.send('join_conversation', { conversation_id: conversationId })
  }

  /**
   * 离开对话房间
   */
  leaveConversation(conversationId: string): void {
    this.send('leave_conversation', { conversation_id: conversationId })
  }

  /**
   * 更新认证token
   */
  updateAuthToken(token: string): void {
    this.authToken = token
    
    // 如果已连接，需要重新连接以使用新token
    if (this.isConnected) {
      this.disconnect()
      setTimeout(() => {
        this.connect().catch(console.error)
      }, 1000)
    }
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * 获取当前状态
   */
  get currentStatus(): WebSocketStatus {
    return this.status
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data)

      // 开发环境下打印接收的消息
      if (import.meta.env.VITE_APP_ENV === 'development') {
        console.log('📥 WebSocket received:', message)
      }

      // 处理特殊消息类型
      switch (message.type) {
        case 'heartbeat':
          this.handleHeartbeat()
          break
        case 'error':
          this.handleError(message.data)
          break
        case 'notification':
          this.handleNotification(message.data)
          break
        default:
          this.emit(message.type, message.data)
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  /**
   * 处理心跳消息
   */
  private handleHeartbeat(): void {
    // 回复心跳
    this.send('heartbeat', { timestamp: Date.now() })
  }

  /**
   * 处理错误消息
   */
  private handleError(errorData: any): void {
    console.error('WebSocket server error:', errorData)
    ElMessage.error(errorData.message || 'WebSocket连接出现错误')
  }

  /**
   * 处理通知消息
   */
  private handleNotification(notificationData: any): void {
    const { type, title, message, duration } = notificationData
    
    switch (type) {
      case 'success':
        ElNotification.success({ title, message, duration })
        break
      case 'warning':
        ElNotification.warning({ title, message, duration })
        break
      case 'error':
        ElNotification.error({ title, message, duration })
        break
      default:
        ElNotification.info({ title, message, duration })
    }
  }

  /**
   * 触发事件
   */
  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.forEach(listener => {
        try {
          listener(data)
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error)
        }
      })
    }
  }

  /**
   * 设置连接状态
   */
  private setStatus(status: WebSocketStatus): void {
    this.status = status
  }

  /**
   * 处理重连
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket max reconnection attempts reached')
      ElNotification.error({
        title: 'WebSocket连接失败',
        message: '无法连接到服务器，请检查网络连接或刷新页面',
        duration: 0
      })
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) // 指数退避

    console.log(`WebSocket reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    this.reconnectTimer = window.setTimeout(() => {
      this.connect().catch((error) => {
        console.error('WebSocket reconnection failed:', error)
      })
    }, delay)
  }

  /**
   * 开始心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.isConnected) {
        this.send('heartbeat', { timestamp: Date.now() })
      }
    }, this.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 构建WebSocket URL
   */
  private buildWebSocketUrl(): string {
    const url = new URL(this.url)
    
    // 添加认证token作为查询参数
    if (this.authToken) {
      url.searchParams.set('token', this.authToken)
    }
    
    return url.toString()
  }
}

// 创建并导出WebSocket服务实例
export const webSocketService = new WebSocketService()

// 导出类型和枚举
export type { EventListener }
