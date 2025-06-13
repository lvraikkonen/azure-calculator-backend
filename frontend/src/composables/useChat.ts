import { computed, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useModelsStore } from '@/stores/models'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import type { 
  CreateConversationRequest, 
  SendMessageRequest, 
  Message,
  Conversation 
} from '@/types'

/**
 * 聊天相关的组合式函数
 * 基于 ChatStore 和 ModelsStore 提供高级聊天逻辑
 */
export function useChat() {
  const chatStore = useChatStore()
  const modelsStore = useModelsStore()
  const authStore = useAuthStore()
  const uiStore = useUIStore()

  // 本地状态
  const messageInput = ref('')
  const isComposing = ref(false)

  // 响应式状态
  const conversations = computed(() => chatStore.conversations)
  const currentConversation = computed(() => chatStore.currentConversation)
  const currentMessages = computed(() => chatStore.currentMessages)
  const isLoading = computed(() => chatStore.isLoading)
  const isSending = computed(() => chatStore.isSending)
  const isTyping = computed(() => chatStore.isTyping)
  const lastError = computed(() => chatStore.lastError)
  const hasActiveConversation = computed(() => chatStore.hasActiveConversation)
  const sortedConversations = computed(() => chatStore.sortedConversations)

  // 模型相关状态
  const selectedModel = computed(() => modelsStore.selectedModel)
  const selectedModelId = computed(() => modelsStore.selectedModelId)

  // 聊天连接状态（基于模型选择和认证状态）
  const connectionStatus = computed(() => {
    if (!selectedModelId.value) return 'disconnected'
    if (isLoading.value || isSending.value) return 'connecting'
    return 'connected'
  })

  // 确保选择了模型
  const ensureModelSelected = (): boolean => {
    if (!selectedModelId.value) {
      uiStore.addNotification({
        type: 'warning',
        title: '请选择模型',
        message: '开始对话前请先选择一个AI模型'
      })
      return false
    }
    return true
  }

  // 创建新对话
  const createConversation = async (
    title?: string,
    initialMessage?: string
  ): Promise<string | null> => {
    if (!ensureModelSelected()) return null

    try {
      uiStore.showLoading('正在创建对话...')

      const request: CreateConversationRequest = {
        title: title || '新对话',
        model_id: selectedModelId.value!,
        initial_message: initialMessage
      }

      const conversationId = await chatStore.createConversation(request)

      if (conversationId) {
        uiStore.addNotification({
          type: 'success',
          title: '对话已创建',
          message: '新对话创建成功'
        })
        return conversationId
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '创建失败',
          message: chatStore.lastError || '创建对话失败'
        })
        return null
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '创建失败',
        message: error instanceof Error ? error.message : '创建对话时发生错误'
      })
      return null
    } finally {
      uiStore.hideLoading()
    }
  }

  // 发送消息
  const sendMessage = async (
    content: string,
    conversationId?: string
  ): Promise<Message | null> => {
    if (!content.trim()) {
      uiStore.addNotification({
        type: 'warning',
        title: '消息不能为空',
        message: '请输入消息内容'
      })
      return null
    }

    if (!ensureModelSelected()) return null

    try {
      const request: SendMessageRequest = {
        content: content.trim(),
        conversation_id: conversationId,
        model_id: selectedModelId.value!
      }

      const message = await chatStore.sendMessage(request)

      if (message) {
        // 清空输入框
        messageInput.value = ''
        return message
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '发送失败',
          message: chatStore.lastError || '消息发送失败'
        })
        return null
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '发送失败',
        message: error instanceof Error ? error.message : '发送消息时发生错误'
      })
      return null
    }
  }

  // 发送流式消息
  const sendStreamMessage = async (
    content: string,
    conversationId?: string,
    onChunk?: (chunk: any) => void
  ): Promise<Message | null> => {
    if (!content.trim()) {
      uiStore.addNotification({
        type: 'warning',
        title: '消息不能为空',
        message: '请输入消息内容'
      })
      return null
    }

    if (!ensureModelSelected()) return null

    // 设置发送状态
    chatStore.setIsSending(true)

    try {
      const request: SendMessageRequest = {
        content: content.trim(),
        conversation_id: conversationId,
        model_id: selectedModelId.value!
      }

      // 调用流式API
      const response = await fetch('/api/v1/chat/messages/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法获取响应流')
      }

      let fullContent = ''
      let thinkingContent = ''
      let messageId = ''
      let newConversationId = conversationId
      let isThinking = false
      let finalMessage: Message | null = null

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = new TextDecoder().decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                // 处理不同类型的数据块
                if (data.error) {
                  throw new Error(data.error)
                }

                if (data.id && !messageId) {
                  messageId = data.id
                }

                if (data.conversation_id && !newConversationId) {
                  newConversationId = data.conversation_id
                }

                // 处理thinking模式
                if (data.thinking_mode !== undefined) {
                  isThinking = data.thinking_mode
                  if (onChunk) {
                    onChunk({
                      type: 'thinking_mode',
                      isThinking,
                      content: isThinking ? '🤔 AI正在思考...' : ''
                    })
                  }
                }

                // 处理thinking内容块
                if (data.thinking_chunk) {
                  thinkingContent += data.thinking_chunk
                  if (onChunk) {
                    onChunk({
                      type: 'thinking_chunk',
                      content: data.thinking_chunk,
                      fullThinking: thinkingContent
                    })
                  }
                }

                // 处理完整thinking内容
                if (data.thinking) {
                  thinkingContent = data.thinking
                  if (onChunk) {
                    onChunk({
                      type: 'thinking_complete',
                      content: thinkingContent
                    })
                  }
                }

                // 处理内容块
                if (data.content) {
                  fullContent += data.content
                  if (onChunk) {
                    onChunk({
                      type: 'content',
                      content: data.content,
                      fullContent
                    })
                  }
                }

                // 处理完成消息
                if (data.done) {
                  finalMessage = {
                    id: messageId,
                    conversation_id: newConversationId || '',
                    content: data.content || fullContent,
                    role: 'assistant',
                    status: 'completed',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    thinking: data.thinking || thinkingContent,
                    suggestions: data.suggestions,
                    recommendation: data.recommendation
                  } as Message

                  if (onChunk) {
                    onChunk({
                      type: 'complete',
                      message: finalMessage
                    })
                  }
                }

              } catch (parseError) {
                console.warn('解析SSE数据失败:', parseError, line)
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }

      // 清空输入框
      messageInput.value = ''

      // 刷新对话列表（如果是新对话）
      if (newConversationId && newConversationId !== conversationId) {
        await refreshConversations()
        await chatStore.setCurrentConversation(newConversationId)
      }

      return finalMessage

    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '发送失败',
        message: error instanceof Error ? error.message : '发送流式消息时发生错误'
      })
      return null
    } finally {
      // 重置发送状态
      chatStore.setIsSending(false)
    }
  }

  // 快速发送（使用输入框内容）
  const quickSend = async (conversationId?: string): Promise<Message | null> => {
    return await sendMessage(messageInput.value, conversationId)
  }

  // 切换对话
  const switchConversation = async (conversationId: string): Promise<void> => {
    try {
      uiStore.showLoading('正在加载对话...')
      await chatStore.setCurrentConversation(conversationId)
      
      uiStore.addNotification({
        type: 'info',
        title: '对话已切换',
        message: '已切换到选定的对话'
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '切换失败',
        message: error instanceof Error ? error.message : '切换对话失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 删除对话
  const deleteConversation = async (conversationId: string): Promise<boolean> => {
    try {
      uiStore.showLoading('正在删除对话...')
      
      const success = await chatStore.deleteConversation(conversationId)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '对话已删除',
          message: '对话删除成功'
        })
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '删除失败',
          message: chatStore.lastError || '删除对话失败'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '删除失败',
        message: error instanceof Error ? error.message : '删除对话时发生错误'
      })
      return false
    } finally {
      uiStore.hideLoading()
    }
  }

  // 更新对话标题
  const updateConversationTitle = async (
    conversationId: string, 
    title: string
  ): Promise<boolean> => {
    try {
      const success = await chatStore.updateConversationTitle(conversationId, title)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '标题已更新',
          message: '对话标题更新成功'
        })
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '更新失败',
          message: chatStore.lastError || '更新标题失败'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '更新失败',
        message: error instanceof Error ? error.message : '更新标题时发生错误'
      })
      return false
    }
  }

  // 刷新对话列表
  const refreshConversations = async (): Promise<void> => {
    try {
      await chatStore.fetchConversations()
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '刷新失败',
        message: error instanceof Error ? error.message : '刷新对话列表失败'
      })
    }
  }

  // 清除错误
  const clearError = (): void => {
    chatStore.clearError()
  }

  // 添加本地消息到当前对话
  const addLocalMessages = (messages: any[]): void => {
    const currentConvId = chatStore.currentConversationId
    if (currentConvId && messages.length > 0) {
      chatStore.addLocalMessages(currentConvId, messages)
    }
  }

  // 截断消息列表（删除从指定索引开始的所有消息）
  const truncateMessages = async (conversationId: string, fromIndex: number): Promise<void> => {
    try {
      await chatStore.truncateMessages(conversationId, fromIndex)

      uiStore.addNotification({
        type: 'success',
        title: '消息已删除',
        message: '已删除指定位置之后的所有消息'
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '删除失败',
        message: error instanceof Error ? error.message : '删除消息时发生错误'
      })
      throw error
    }
  }

  // 输入框辅助函数
  const handleKeyPress = (event: KeyboardEvent): void => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!isSending.value && messageInput.value.trim()) {
        quickSend()
      }
    }
  }

  const handleCompositionStart = (): void => {
    isComposing.value = true
  }

  const handleCompositionEnd = (): void => {
    isComposing.value = false
  }

  // 监听模型变化
  watch(selectedModelId, (newModelId, oldModelId) => {
    if (newModelId && newModelId !== oldModelId) {
      console.log('聊天模型已切换:', newModelId)
    }
  })

  // 监听连接状态
  watch(connectionStatus, (status) => {
    if (status === 'disconnected') {
      uiStore.addNotification({
        type: 'warning',
        title: '连接断开',
        message: '与服务器的连接已断开，正在尝试重连...'
      })
    } else if (status === 'connected') {
      uiStore.addNotification({
        type: 'success',
        title: '连接已恢复',
        message: '与服务器的连接已恢复'
      })
    }
  })

  return {
    // 状态
    conversations,
    currentConversation,
    currentMessages,
    isLoading,
    isSending,
    isTyping,
    connectionStatus,
    lastError,
    hasActiveConversation,
    sortedConversations,
    selectedModel,
    selectedModelId,
    
    // 本地状态
    messageInput,
    isComposing,
    
    // 对话操作
    createConversation,
    sendMessage,
    sendStreamMessage,
    quickSend,
    switchConversation,
    deleteConversation,
    updateConversationTitle,
    refreshConversations,
    fetchMessages: chatStore.fetchMessages,
    addLocalMessages,
    truncateMessages,
    clearError,
    
    // 输入辅助
    handleKeyPress,
    handleCompositionStart,
    handleCompositionEnd,
    
    // 工具函数
    ensureModelSelected
  }
}
