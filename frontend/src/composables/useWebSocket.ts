import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useUIStore } from '@/stores/ui'
import type { Message } from '@/types'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: number
}

export interface WebSocketOptions {
  url?: string
  protocols?: string[]
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
  debug?: boolean
}

/**
 * WebSocket连接管理相关的组合式函数
 * 提供实时通信功能
 */
export function useWebSocket(options: WebSocketOptions = {}) {
  const authStore = useAuthStore()
  const chatStore = useChatStore()
  const uiStore = useUIStore()

  // 配置
  const config = {
    url: options.url || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`,
    protocols: options.protocols || [],
    reconnectInterval: options.reconnectInterval || 3000,
    maxReconnectAttempts: options.maxReconnectAttempts || 10,
    heartbeatInterval: options.heartbeatInterval || 30000,
    debug: options.debug || false
  }

  // 状态
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const reconnectAttempts = ref(0)
  const lastError = ref<string | null>(null)
  const messageQueue = ref<WebSocketMessage[]>([])
  const heartbeatTimer = ref<NodeJS.Timeout | null>(null)
  const reconnectTimer = ref<NodeJS.Timeout | null>(null)

  // 计算属性
  const connectionStatus = computed(() => {
    if (isConnected.value) return 'connected'
    if (isConnecting.value) return 'connecting'
    return 'disconnected'
  })

  const canReconnect = computed(() => {
    return reconnectAttempts.value < config.maxReconnectAttempts
  })

  // 日志函数
  const log = (message: string, ...args: any[]): void => {
    if (config.debug) {
      console.log(`[WebSocket] ${message}`, ...args)
    }
  }

  // 连接WebSocket
  const connect = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (socket.value?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (isConnecting.value) {
        reject(new Error('Already connecting'))
        return
      }

      if (!authStore.isAuthenticated) {
        reject(new Error('Not authenticated'))
        return
      }

      try {
        isConnecting.value = true
        lastError.value = null
        
        // 构建WebSocket URL，包含认证token
        const wsUrl = new URL(config.url)
        if (authStore.token) {
          wsUrl.searchParams.set('token', authStore.token)
        }

        log('Connecting to:', wsUrl.toString())
        
        socket.value = new WebSocket(wsUrl.toString(), config.protocols)

        socket.value.onopen = (event) => {
          log('Connected', event)
          isConnected.value = true
          isConnecting.value = false
          reconnectAttempts.value = 0
          
          // 更新聊天store的连接状态
          chatStore.setConnectionStatus('connected')
          
          // 发送队列中的消息
          flushMessageQueue()
          
          // 启动心跳
          startHeartbeat()
          
          uiStore.addNotification({
            type: 'success',
            title: '连接已建立',
            message: '实时通信连接已建立'
          })
          
          resolve()
        }

        socket.value.onmessage = (event) => {
          handleMessage(event)
        }

        socket.value.onclose = (event) => {
          log('Disconnected', event.code, event.reason)
          handleDisconnect(event)
        }

        socket.value.onerror = (event) => {
          log('Error', event)
          handleError(event)
          reject(new Error('WebSocket connection failed'))
        }

      } catch (error) {
        isConnecting.value = false
        lastError.value = error instanceof Error ? error.message : 'Connection failed'
        reject(error)
      }
    })
  }

  // 断开连接
  const disconnect = (): void => {
    if (socket.value) {
      log('Disconnecting...')
      
      // 停止心跳
      stopHeartbeat()
      
      // 停止重连
      stopReconnect()
      
      socket.value.close(1000, 'Manual disconnect')
      socket.value = null
    }
    
    isConnected.value = false
    isConnecting.value = false
    chatStore.setConnectionStatus('disconnected')
  }

  // 发送消息
  const send = (message: WebSocketMessage): boolean => {
    if (!isConnected.value || !socket.value) {
      log('Not connected, queuing message:', message)
      messageQueue.value.push(message)
      return false
    }

    try {
      const payload = JSON.stringify(message)
      socket.value.send(payload)
      log('Sent message:', message)
      return true
    } catch (error) {
      log('Send error:', error)
      lastError.value = error instanceof Error ? error.message : 'Send failed'
      return false
    }
  }

  // 处理接收到的消息
  const handleMessage = (event: MessageEvent): void => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      log('Received message:', message)

      switch (message.type) {
        case 'chat_message':
          handleChatMessage(message.data)
          break
        case 'typing_indicator':
          handleTypingIndicator(message.data)
          break
        case 'user_status':
          handleUserStatus(message.data)
          break
        case 'system_notification':
          handleSystemNotification(message.data)
          break
        case 'heartbeat':
          handleHeartbeat(message.data)
          break
        default:
          log('Unknown message type:', message.type)
      }
    } catch (error) {
      log('Message parse error:', error)
    }
  }

  // 处理聊天消息
  const handleChatMessage = (data: Message): void => {
    chatStore.addReceivedMessage(data)
  }

  // 处理打字指示器
  const handleTypingIndicator = (data: { userId: string; isTyping: boolean }): void => {
    chatStore.setTypingStatus(data.isTyping)
  }

  // 处理用户状态
  const handleUserStatus = (data: { userId: string; status: string }): void => {
    log('User status update:', data)
  }

  // 处理系统通知
  const handleSystemNotification = (data: { title: string; message: string; type: string }): void => {
    uiStore.addNotification({
      type: data.type as any,
      title: data.title,
      message: data.message
    })
  }

  // 处理心跳
  const handleHeartbeat = (data: any): void => {
    log('Heartbeat received:', data)
  }

  // 处理断开连接
  const handleDisconnect = (event: CloseEvent): void => {
    isConnected.value = false
    isConnecting.value = false
    stopHeartbeat()
    
    chatStore.setConnectionStatus('disconnected')
    
    if (event.code !== 1000) { // 非正常关闭
      lastError.value = `Connection closed: ${event.reason || 'Unknown reason'}`
      
      if (canReconnect.value) {
        scheduleReconnect()
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '连接断开',
          message: '无法重新连接到服务器，请刷新页面'
        })
      }
    }
  }

  // 处理错误
  const handleError = (event: Event): void => {
    isConnecting.value = false
    lastError.value = 'WebSocket error occurred'
    
    uiStore.addNotification({
      type: 'error',
      title: '连接错误',
      message: 'WebSocket连接发生错误'
    })
  }

  // 安排重连
  const scheduleReconnect = (): void => {
    if (!canReconnect.value) return
    
    reconnectAttempts.value++
    chatStore.setConnectionStatus('connecting')
    
    log(`Scheduling reconnect attempt ${reconnectAttempts.value}/${config.maxReconnectAttempts}`)
    
    reconnectTimer.value = setTimeout(() => {
      if (authStore.isAuthenticated) {
        connect().catch(() => {
          // 重连失败，会自动安排下次重连
        })
      }
    }, config.reconnectInterval)
  }

  // 停止重连
  const stopReconnect = (): void => {
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
  }

  // 启动心跳
  const startHeartbeat = (): void => {
    stopHeartbeat()
    
    heartbeatTimer.value = setInterval(() => {
      if (isConnected.value) {
        send({
          type: 'heartbeat',
          data: { timestamp: Date.now() },
          timestamp: Date.now()
        })
      }
    }, config.heartbeatInterval)
  }

  // 停止心跳
  const stopHeartbeat = (): void => {
    if (heartbeatTimer.value) {
      clearInterval(heartbeatTimer.value)
      heartbeatTimer.value = null
    }
  }

  // 清空消息队列
  const flushMessageQueue = (): void => {
    while (messageQueue.value.length > 0) {
      const message = messageQueue.value.shift()
      if (message) {
        send(message)
      }
    }
  }

  // 发送聊天消息
  const sendChatMessage = (content: string, conversationId: string): void => {
    send({
      type: 'chat_message',
      data: {
        content,
        conversation_id: conversationId,
        timestamp: Date.now()
      },
      timestamp: Date.now()
    })
  }

  // 发送打字指示器
  const sendTypingIndicator = (isTyping: boolean, conversationId: string): void => {
    send({
      type: 'typing_indicator',
      data: {
        is_typing: isTyping,
        conversation_id: conversationId
      },
      timestamp: Date.now()
    })
  }

  // 监听认证状态变化
  watch(() => authStore.isAuthenticated, (isAuth) => {
    if (isAuth) {
      // 用户登录后自动连接
      connect().catch(error => {
        log('Auto-connect failed:', error)
      })
    } else {
      // 用户登出后断开连接
      disconnect()
    }
  })

  // 生命周期钩子
  onMounted(() => {
    if (authStore.isAuthenticated) {
      connect().catch(error => {
        log('Initial connect failed:', error)
      })
    }
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    // 状态
    isConnected,
    isConnecting,
    connectionStatus,
    lastError,
    reconnectAttempts,
    canReconnect,
    
    // 方法
    connect,
    disconnect,
    send,
    sendChatMessage,
    sendTypingIndicator,
    
    // 配置
    config
  }
}
