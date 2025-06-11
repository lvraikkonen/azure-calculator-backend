import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  Conversation, 
  Message, 
  CreateConversationRequest,
  SendMessageRequest,
  MessageStatus 
} from '@/types'
import { chatService } from '@/services'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<string | null>(null)
  const messages = ref<Record<string, Message[]>>({})
  const isLoading = ref(false)
  const isSending = ref(false)
  const isTyping = ref(false)
  const connectionStatus = ref<'connected' | 'disconnected' | 'connecting'>('disconnected')
  const lastError = ref<string | null>(null)

  // 计算属性
  const currentConversation = computed(() => 
    conversations.value.find(conv => conv.id === currentConversationId.value) || null
  )

  const currentMessages = computed(() => 
    currentConversationId.value ? messages.value[currentConversationId.value] || [] : []
  )

  const conversationCount = computed(() => conversations.value.length)

  const hasActiveConversation = computed(() => !!currentConversationId.value)

  const sortedConversations = computed(() => 
    [...conversations.value].sort((a, b) => 
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )
  )

  // 获取对话列表
  const fetchConversations = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null

      const response = await chatService.getConversations()
      // 转换ConversationSummary到Conversation类型
      conversations.value = response.map(summary => ({
        ...summary,
        user_id: 'current-user', // 临时填充
        created_at: summary.updated_at, // 使用updated_at作为created_at
        last_message: summary.last_message,
        metadata: undefined
      }))
    } catch (error) {
      console.error('获取对话列表失败:', error)
      lastError.value = '获取对话列表失败'
    } finally {
      isLoading.value = false
    }
  }

  // 创建新对话（通过发送第一条消息）
  const createConversation = async (request: CreateConversationRequest): Promise<string | null> => {
    try {
      isLoading.value = true
      lastError.value = null

      // 后端通过发送消息自动创建对话，所以我们直接发送消息
      const messageRequest: SendMessageRequest = {
        content: request.initial_message || request.title || '你好',
        conversation_id: undefined, // 不指定conversation_id，让后端自动创建
        model_id: request.model_id // 传递模型ID
      }

      const response = await chatService.sendMessage(messageRequest)

      if (response && response.conversation_id) {
        // 初始化消息数组并添加响应消息
        messages.value[response.conversation_id] = [response]

        // 刷新对话列表以获取新创建的对话
        await fetchConversations()

        // 设置当前对话（在对话列表刷新完成后）
        currentConversationId.value = response.conversation_id

        return response.conversation_id
      }

      return null
    } catch (error) {
      console.error('创建对话失败:', error)
      lastError.value = '创建对话失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  // 设置当前对话
  const setCurrentConversation = async (conversationId: string): Promise<void> => {
    currentConversationId.value = conversationId
    
    // 如果还没有加载过这个对话的消息，则加载
    if (!messages.value[conversationId]) {
      await fetchMessages(conversationId)
    }
  }

  // 获取对话消息
  const fetchMessages = async (conversationId: string): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null

      // 使用getConversation API获取对话及其消息
      const response = await chatService.getConversation(conversationId)

      // 提取消息数组
      if (response && response.messages) {
        messages.value[conversationId] = response.messages
      } else {
        messages.value[conversationId] = []
      }
    } catch (error) {
      console.error('获取消息失败:', error)
      lastError.value = '获取消息失败'
      // 确保即使失败也初始化空数组
      messages.value[conversationId] = []
    } finally {
      isLoading.value = false
    }
  }

  // 发送消息
  const sendMessage = async (request: SendMessageRequest): Promise<Message | null> => {
    let tempMessage: Message | null = null
    let conversationId: string | null = null

    try {
      isSending.value = true
      lastError.value = null

      // 如果没有当前对话ID，使用request中的conversation_id
      conversationId = request.conversation_id || currentConversationId.value

      // 创建临时消息显示在界面上（只有在有对话ID时才显示）
      if (conversationId) {
        tempMessage = {
          id: `temp-${Date.now()}`,
          conversation_id: conversationId,
          content: request.content,
          role: 'user' as any, // 临时使用any，因为MessageRole枚举值不匹配
          status: 'sending' as MessageStatus,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }

        // 添加到消息列表
        if (!messages.value[conversationId]) {
          messages.value[conversationId] = []
        }
        messages.value[conversationId].push(tempMessage)
      }

      // 发送消息到后端
      const response = await chatService.sendMessage(request)

      // 处理响应
      if (response) {
        const responseConversationId = response.conversation_id

        // 如果是新对话，更新当前对话ID
        if (!currentConversationId.value && responseConversationId) {
          currentConversationId.value = responseConversationId
          // 刷新对话列表
          await fetchConversations()
        }

        // 替换临时消息或添加新消息
        if (tempMessage && conversationId) {
          const messageList = messages.value[conversationId]
          if (messageList && tempMessage) {
            const tempIndex = messageList.findIndex((msg: any) => msg.id === tempMessage!.id)
            if (tempIndex !== -1) {
              messageList.splice(tempIndex, 1, response)
            } else {
              messageList.push(response)
            }
          }
        } else if (responseConversationId) {
          // 新对话的情况，初始化消息列表
          if (!messages.value[responseConversationId]) {
            messages.value[responseConversationId] = []
          }
          messages.value[responseConversationId].push(response)
        }

        // 更新对话的最后更新时间
        const conversation = conversations.value.find(conv => conv.id === responseConversationId)
        if (conversation) {
          conversation.updated_at = new Date().toISOString()
        }
      }

      return response
    } catch (error) {
      console.error('发送消息失败:', error)
      lastError.value = '发送消息失败'

      // 移除临时消息
      if (tempMessage && conversationId && messages.value[conversationId]) {
        const messageList = messages.value[conversationId]
        const tempIndex = messageList.findIndex((msg: any) => msg.id === tempMessage!.id)
        if (tempIndex !== -1) {
          messageList.splice(tempIndex, 1)
        }
      }

      return null
    } finally {
      isSending.value = false
    }
  }

  // 删除对话
  const deleteConversation = async (conversationId: string): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      await chatService.deleteConversation(conversationId)
      
      // 从本地状态中移除
      conversations.value = conversations.value.filter(conv => conv.id !== conversationId)
      delete messages.value[conversationId]
      
      // 如果删除的是当前对话，清除当前对话ID
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = null
      }
      
      return true
    } catch (error) {
      console.error('删除对话失败:', error)
      lastError.value = '删除对话失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 更新对话标题
  const updateConversationTitle = async (conversationId: string, title: string): Promise<boolean> => {
    try {
      const updatedConversation = await chatService.updateConversation(conversationId, { title })
      
      // 更新本地状态
      const index = conversations.value.findIndex(conv => conv.id === conversationId)
      if (index !== -1) {
        conversations.value[index] = updatedConversation
      }
      
      return true
    } catch (error) {
      console.error('更新对话标题失败:', error)
      lastError.value = '更新对话标题失败'
      return false
    }
  }

  // 添加接收到的消息（用于WebSocket）
  const addReceivedMessage = (message: Message) => {
    if (!messages.value[message.conversation_id]) {
      messages.value[message.conversation_id] = []
    }
    messages.value[message.conversation_id].push(message)
    
    // 更新对话的最后更新时间
    const conversation = conversations.value.find(conv => conv.id === message.conversation_id)
    if (conversation) {
      conversation.updated_at = message.created_at
    }
  }

  // 更新消息状态
  const updateMessageStatus = (messageId: string, status: MessageStatus) => {
    for (const conversationId in messages.value) {
      const messageList = messages.value[conversationId]
      const message = messageList.find(msg => msg.id === messageId)
      if (message) {
        message.status = status
        break
      }
    }
  }

  // 设置连接状态
  const setConnectionStatus = (status: 'connected' | 'disconnected' | 'connecting') => {
    connectionStatus.value = status
  }

  // 设置打字状态
  const setTypingStatus = (typing: boolean) => {
    isTyping.value = typing
  }

  // 清除错误
  const clearError = () => {
    lastError.value = null
  }

  // 清除所有数据
  const clearAllData = () => {
    conversations.value = []
    currentConversationId.value = null
    messages.value = {}
    lastError.value = null
  }

  return {
    // 状态
    conversations: readonly(conversations),
    currentConversationId: readonly(currentConversationId),
    messages: readonly(messages),
    isLoading: readonly(isLoading),
    isSending: readonly(isSending),
    isTyping: readonly(isTyping),
    connectionStatus: readonly(connectionStatus),
    lastError: readonly(lastError),
    
    // 计算属性
    currentConversation,
    currentMessages,
    conversationCount,
    hasActiveConversation,
    sortedConversations,
    
    // 方法
    fetchConversations,
    createConversation,
    setCurrentConversation,
    fetchMessages,
    sendMessage,
    deleteConversation,
    updateConversationTitle,
    addReceivedMessage,
    updateMessageStatus,
    setConnectionStatus,
    setTypingStatus,
    clearError,
    clearAllData
  }
})
