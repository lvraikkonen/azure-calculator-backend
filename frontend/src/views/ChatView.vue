<template>
  <div class="chat-view">
    <!-- 顶部导航栏 -->
    <div class="chat-header">
      <div class="header-left">
        <h1 class="chat-title">AI智能对话</h1>
        <div class="connection-status" :class="chat.connectionStatus?.value">
          <span class="status-indicator"></span>
          <span class="status-text">{{ getConnectionStatusText() }}</span>
        </div>
      </div>
      
      <div class="header-right">
        <div class="model-info" v-if="selectedModel">
          <span class="model-name">{{ selectedModel.display_name || selectedModel.name }}</span>
          <span class="model-description" v-if="selectedModel.description">
            {{ selectedModel.description }}
          </span>
        </div>

        <!-- 当前用户信息 -->
        <div class="user-info" v-if="currentUser">
          <div class="user-avatar">
            <span class="avatar-text">{{ getUserInitials(currentUser.username || currentUser.email) }}</span>
          </div>
          <div class="user-details">
            <span class="user-name">{{ currentUser.username || currentUser.email }}</span>
            <span class="user-role">{{ currentUser.role || '用户' }}</span>
          </div>
        </div>

        <el-button @click="showConversationList = !showConversationList" size="small">
          {{ showConversationList ? '隐藏对话列表' : '显示对话列表' }}
        </el-button>
      </div>
    </div>

    <div class="chat-container">
      <!-- 左侧对话列表 -->
      <div class="conversation-sidebar" v-show="showConversationList">
        <div class="sidebar-header">
          <!-- 模型选择区域 -->
          <div class="model-selection-area">
            <div class="current-model" v-if="selectedModel">
              <div class="model-display">
                <span class="model-icon">🤖</span>
                <div class="model-details">
                  <span class="model-name">{{ selectedModel.display_name || selectedModel.name }}</span>
                  <span class="model-status">{{ getConnectionStatusText() }}</span>
                </div>
              </div>
            </div>

            <div class="model-actions">
              <el-button
                @click="showModelSelector = true"
                type="primary"
                size="small"
                :icon="selectedModel ? 'Edit' : 'Plus'"
              >
                {{ selectedModel ? '切换模型' : '选择模型' }}
              </el-button>
            </div>
          </div>

          <!-- 对话历史标题和新对话按钮 -->
          <div class="conversation-header">
            <h3>对话历史</h3>
            <el-button @click="createNewConversation" type="success" size="small">
              新对话
            </el-button>
          </div>
        </div>
        
        <div class="conversation-list">
          <div v-if="conversationsLength === 0" class="empty-state">
            <p>暂无对话记录</p>
            <p class="text-secondary">创建第一个对话开始聊天吧！</p>
          </div>

          <div v-else class="conversation-items">
            <div
              v-for="conversation in sortedConversationsValue"
              :key="conversation.id"
              class="conversation-item"
              :class="{
                'active': conversation.id === chat.currentConversation?.value?.id,
                'archived': conversation.is_archived
              }"
              @click="switchToConversation(conversation.id)"
            >
              <div class="conversation-item-header">
                <h5 class="conversation-title">{{ conversation.title || '未命名对话' }}</h5>
                <span class="conversation-time">{{ formatMessageTime(conversation.updated_at) }}</span>
              </div>

              <div class="conversation-item-content">
                <div class="conversation-meta">
                  <span class="message-count">{{ conversation.message_count || 0 }} 条消息</span>
                  <span v-if="conversation.model_name" class="model-name">{{ conversation.model_name }}</span>
                </div>
              </div>

              <div class="conversation-actions">
                <el-button @click.stop="deleteConversationFromList(conversation.id)" 
                          type="danger" 
                          size="small" 
                          text>
                  删除
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 主聊天区域 -->
      <div class="chat-main">
        <!-- 消息显示区域 -->
        <div class="messages-container" ref="messagesContainer">
          <!-- 历史消息 -->
          <div
            v-for="(message, index) in conversationMessages"
            :key="message.id || index"
            class="message-wrapper"
            :class="message.role"
          >
            <!-- AI消息布局 -->
            <div v-if="message.role === 'assistant'" class="message-item assistant">
              <div class="message-avatar">
                <span class="ai-icon">🤖</span>
              </div>

              <div class="message-content-wrapper">
                <div class="message-header">
                  <span class="sender-name">{{ selectedModel?.display_name || selectedModel?.name || 'AI助手' }}</span>
                  <span class="message-time">{{ formatMessageTime(message.created_at) }}</span>
                </div>

                <!-- Thinking内容（可折叠） -->
                <div v-if="message.thinking" class="thinking-section">
                  <div
                    class="thinking-toggle"
                    @click="toggleThinking(message.id || index)"
                    :class="{ 'expanded': expandedThinking.has(message.id || index) }"
                  >
                    <span class="thinking-icon">🤔</span>
                    <span class="thinking-label">思考过程</span>
                    <span class="toggle-arrow">{{ expandedThinking.has(message.id || index) ? '▼' : '▶' }}</span>
                  </div>

                  <div
                    v-show="expandedThinking.has(message.id || index)"
                    class="thinking-content"
                  >
                    {{ message.thinking }}
                  </div>
                </div>

                <!-- AI回复内容 -->
                <div class="message-content ai-content">{{ message.content }}</div>
              </div>
            </div>

            <!-- 用户消息布局 -->
            <div v-else class="message-item user">
              <div class="message-content-wrapper">
                <div class="message-header">
                  <span class="sender-name">{{ currentUser?.username || currentUser?.email || '用户' }}</span>
                  <span class="message-time">{{ formatMessageTime(message.created_at) }}</span>

                  <!-- 消息操作按钮 -->
                  <div class="message-actions">
                    <el-button
                      size="small"
                      text
                      type="primary"
                      @click="startEditMessage(message, index)"
                      :icon="'Edit'"
                    >
                      编辑
                    </el-button>
                    <el-button
                      size="small"
                      text
                      type="warning"
                      @click="restartFromMessage(index)"
                      :icon="'Refresh'"
                    >
                      从此重新开始
                    </el-button>
                  </div>
                </div>

                <!-- 用户消息内容 -->
                <div v-if="editingMessageIndex !== index" class="message-content user-content">
                  {{ message.content }}
                </div>

                <!-- 编辑模式 -->
                <div v-else class="message-edit-mode">
                  <el-input
                    v-model="editingMessageContent"
                    type="textarea"
                    placeholder="编辑消息内容..."
                    :autosize="{ minRows: 2, maxRows: 6 }"
                    @keydown="handleEditKeydown"
                  />
                  <div class="edit-actions">
                    <el-button size="small" @click="cancelEditMessage">取消</el-button>
                    <el-button size="small" type="primary" @click="confirmEditMessage(message, index)">
                      确认并重新发送
                    </el-button>
                  </div>
                </div>
              </div>

              <div class="message-avatar">
                <span class="user-icon">{{ getUserInitials(currentUser?.username || currentUser?.email || '用户') }}</span>
              </div>
            </div>
          </div>

          <!-- 当前流式消息（如果正在发送） -->
          <!-- 用户消息 -->
          <div v-if="streamingMessage" class="message-wrapper user">
            <div class="message-item user">
              <div class="message-content-wrapper">
                <div class="message-header">
                  <span class="sender-name">{{ currentUser?.username || currentUser?.email || '用户' }}</span>
                  <span class="message-time">刚刚</span>
                </div>
                <div class="message-content user-content">{{ streamingMessage.userMessage }}</div>
              </div>

              <div class="message-avatar">
                <span class="user-icon">{{ getUserInitials(currentUser?.username || currentUser?.email || '用户') }}</span>
              </div>
            </div>
          </div>

          <!-- AI流式回复 -->
          <div v-if="streamingMessage" class="message-wrapper assistant">
            <div class="message-item assistant streaming">
              <div class="message-avatar">
                <span class="ai-icon">🤖</span>
              </div>

              <div class="message-content-wrapper">
                <div class="message-header">
                  <span class="sender-name">{{ selectedModel?.display_name || selectedModel?.name || 'AI助手' }}</span>
                  <span class="message-time">
                    {{ streamingMessage.isComplete ? '刚刚' : '正在回复...' }}
                  </span>
                </div>

                <!-- 当前thinking内容（可折叠） -->
                <div v-if="streamingMessage.thinking || streamingMessage.isThinking" class="thinking-section">
                  <div
                    class="thinking-toggle"
                    @click="toggleStreamingThinking()"
                    :class="{ 'expanded': showStreamingThinking }"
                  >
                    <span class="thinking-icon">🤔</span>
                    <span class="thinking-label">
                      {{ streamingMessage.isThinking ? '正在思考...' : '思考过程' }}
                    </span>
                    <span class="toggle-arrow">{{ showStreamingThinking ? '▼' : '▶' }}</span>
                  </div>

                  <div v-show="showStreamingThinking" class="thinking-content">
                    {{ streamingMessage.thinking }}
                    <span v-if="streamingMessage.isThinking" class="thinking-cursor">|</span>
                  </div>
                </div>

                <!-- 当前AI回复内容 -->
                <div class="message-content ai-content">
                  {{ streamingMessage.content }}
                  <span v-if="!streamingMessage.isComplete && streamingMessage.content" class="typing-cursor">|</span>
                </div>

                <!-- 状态指示器 -->
                <div class="message-status">
                  <span v-if="streamingMessage.isComplete" class="complete-indicator">✅ 回复完成</span>
                  <span v-else-if="streamingMessage.content" class="streaming-indicator">⏳ 正在生成...</span>
                  <span v-else-if="streamingMessage.isThinking" class="thinking-indicator">🤔 正在思考...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 消息输入区域 -->
        <div class="message-input-container">
          <div class="input-area">
            <el-input
              v-model="chatMessageInput"
              type="textarea"
              placeholder="输入消息..."
              :disabled="!selectedModel || chat.isSending.value"
              @keydown="handleKeydown"
              :autosize="{ minRows: 1, maxRows: 4 }"
              resize="none"
            />
            <el-button
              type="primary"
              :disabled="!canSendMessage"
              :loading="chat.isSending.value"
              @click="sendMessage"
              class="send-button"
            >
              发送
            </el-button>
          </div>
          
          <div class="input-status" v-if="!selectedModel">
            <span class="warning-text">请先选择一个AI模型开始对话</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 模型选择弹窗 -->
    <el-dialog v-model="showModelSelector" title="选择AI模型" width="600px">
      <div class="model-selector">
        <div class="model-grid">
          <div
            v-for="model in activeModelsValue"
            :key="model.id"
            class="model-card"
            :class="{ 'selected': model.id === models.selectedModelId?.value }"
            @click="selectModel(model.id)"
          >
            <div class="model-header">
              <h4>{{ model.display_name || model.name }}</h4>
              <span class="model-provider">{{ model.provider || '未知' }}</span>
            </div>
            <div class="model-description">
              {{ model.description || '暂无描述' }}
            </div>
            <div class="model-capabilities" v-if="model.capabilities">
              <span v-for="capability in model.capabilities" :key="capability" class="capability-tag">
                {{ capability }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showModelSelector = false">取消</el-button>
        <el-button type="primary" @click="confirmModelSelection">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useChat, useModels } from '@/composables'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

// 初始化composables
const chat = useChat()
const models = useModels()
const authStore = useAuthStore()

// 本地状态
const showConversationList = ref(true)
const showModelSelector = ref(false)
const messagesContainer = ref<HTMLElement>()

// thinking展开状态管理
const expandedThinking = ref(new Set<string>())
const showStreamingThinking = ref(false)

// 消息编辑状态
const editingMessageIndex = ref<number | null>(null)
const editingMessageContent = ref('')

// 当前用户信息
const currentUser = computed(() => authStore.user)

// 流式消息状态
const streamingMessage = ref<{
  userMessage: string
  content: string
  thinking: string
  isThinking: boolean
  isComplete: boolean
} | null>(null)

// 计算属性
const conversationsLength = computed(() => chat.conversations?.value?.length || 0)
const selectedModel = computed(() => models.selectedModel?.value)
const activeModelsValue = computed(() => models.activeModels?.value || [])
const conversationMessages = computed(() => {
  const messages = chat.currentMessages?.value || []
  // 调试：打印消息数据
  console.log('🎭 当前对话消息:', messages)
  console.log('🎭 消息角色检查:', messages.map(msg => ({
    id: msg.id,
    role: msg.role,
    content: msg.content?.substring(0, 50) + '...',
    sender: (msg as any).sender // 检查是否有sender字段
  })))
  return messages
})
const sortedConversationsValue = computed(() => chat.sortedConversations?.value || [])

// 直接使用useChat中的messageInput
const chatMessageInput = computed({
  get: () => chat.messageInput.value || '',
  set: (value: string) => {
    chat.messageInput.value = value
  }
})

const canSendMessage = computed(() => {
  const messageText = chatMessageInput.value
  return selectedModel.value &&
         messageText &&
         typeof messageText === 'string' &&
         messageText.trim() &&
         !chat.isSending.value
})

// 获取连接状态文本
const getConnectionStatusText = (): string => {
  switch (chat.connectionStatus?.value) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中'
    case 'disconnected': return '未连接'
    default: return '未知状态'
  }
}

// 格式化消息时间
const formatMessageTime = (dateString: string): string => {
  if (!dateString) return '未知时间'

  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`

    return date.toLocaleDateString()
  } catch (error) {
    return '时间格式错误'
  }
}

// 获取用户名首字母
const getUserInitials = (name: string): string => {
  if (!name) return 'U'

  const words = name.split(/[\s@.]+/).filter(word => word.length > 0)
  if (words.length === 0) return 'U'

  if (words.length === 1) {
    return words[0].charAt(0).toUpperCase()
  }

  return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase()
}

// 切换thinking内容显示
const toggleThinking = (messageId: string): void => {
  if (expandedThinking.value.has(messageId)) {
    expandedThinking.value.delete(messageId)
  } else {
    expandedThinking.value.add(messageId)
  }
}

// 切换流式thinking内容显示
const toggleStreamingThinking = (): void => {
  showStreamingThinking.value = !showStreamingThinking.value
}

// 开始编辑消息
const startEditMessage = (message: any, index: number): void => {
  editingMessageIndex.value = index
  editingMessageContent.value = message.content
}

// 取消编辑消息
const cancelEditMessage = (): void => {
  editingMessageIndex.value = null
  editingMessageContent.value = ''
}

// 确认编辑消息并重新发送
const confirmEditMessage = async (message: any, index: number): Promise<void> => {
  if (!editingMessageContent.value.trim()) {
    ElMessage.warning('消息内容不能为空')
    return
  }

  try {
    // 1. 删除从当前消息开始的所有后续消息
    await truncateMessagesFromIndex(index)

    // 2. 发送编辑后的消息
    chatMessageInput.value = editingMessageContent.value.trim()

    // 3. 清除编辑状态
    cancelEditMessage()

    // 4. 发送新消息
    await sendMessage()

    ElMessage.success('消息已编辑并重新发送')
  } catch (error) {
    ElMessage.error(`编辑消息失败: ${error}`)
  }
}

// 从指定消息开始重新对话
const restartFromMessage = async (index: number): Promise<void> => {
  try {
    // 确认操作
    const confirmed = await ElMessageBox.confirm(
      '这将删除此消息之后的所有对话内容，是否继续？',
      '确认重新开始',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    if (confirmed) {
      // 删除从下一个消息开始的所有后续消息
      await truncateMessagesFromIndex(index + 1)
      ElMessage.success('已从此处重新开始对话')
    }
  } catch (error) {
    // 用户取消操作
    if (error !== 'cancel') {
      ElMessage.error(`操作失败: ${error}`)
    }
  }
}

// 截断消息列表（删除从指定索引开始的所有消息）
const truncateMessagesFromIndex = async (fromIndex: number): Promise<void> => {
  const messages = conversationMessages.value
  if (!messages || fromIndex >= messages.length) {
    return
  }

  // 获取要删除的消息
  const messagesToDelete = messages.slice(fromIndex)

  // 从本地状态中删除这些消息
  if (chat.currentConversation?.value?.id) {
    await chat.truncateMessages(chat.currentConversation.value.id, fromIndex)
  }
}

// 处理编辑模式的键盘事件
const handleEditKeydown = (event: KeyboardEvent): void => {
  if (event.key === 'Enter' && event.ctrlKey) {
    event.preventDefault()
    const currentIndex = editingMessageIndex.value
    if (currentIndex !== null) {
      const message = conversationMessages.value[currentIndex]
      confirmEditMessage(message, currentIndex)
    }
  } else if (event.key === 'Escape') {
    event.preventDefault()
    cancelEditMessage()
  }
}

// 选择模型
const selectModel = (modelId: string): void => {
  const success = models.selectModel(modelId)
  if (success) {
    const model = activeModelsValue.value.find(m => m.id === modelId)
    ElMessage.success(`已选择模型：${model?.display_name || model?.name || modelId}`)
  } else {
    ElMessage.error('选择模型失败')
  }
}

// 确认模型选择
const confirmModelSelection = (): void => {
  showModelSelector.value = false
  if (selectedModel.value) {
    ElMessage.success(`当前模型：${selectedModel.value.display_name || selectedModel.value.name}`)
  }
}

// 创建新对话
const createNewConversation = async (): Promise<void> => {
  try {
    if (!chat.ensureModelSelected()) {
      ElMessage.warning('请先选择一个AI模型')
      showModelSelector.value = true
      return
    }

    const id = await chat.createConversation('新对话')
    if (id) {
      ElMessage.success('创建对话成功')
      await chat.refreshConversations()
    }
  } catch (error) {
    ElMessage.error(`创建对话失败: ${error}`)
  }
}

// 切换到指定对话
const switchToConversation = async (conversationId: string): Promise<void> => {
  try {
    await chat.switchConversation(conversationId)
    ElMessage.success('切换对话成功')
    scrollToBottom()
  } catch (error) {
    ElMessage.error(`切换对话失败: ${error}`)
  }
}

// 删除对话
const deleteConversationFromList = async (conversationId: string): Promise<void> => {
  try {
    const conversation = chat.conversations?.value?.find(c => c.id === conversationId)
    const title = conversation?.title || '未命名对话'

    const success = await chat.deleteConversation(conversationId)
    if (success) {
      ElMessage.success(`对话 "${title}" 已删除`)
      await chat.refreshConversations()
    } else {
      ElMessage.error(`删除对话 "${title}" 失败`)
    }
  } catch (error) {
    ElMessage.error(`删除对话失败: ${error}`)
  }
}

// 发送消息
const sendMessage = async (): Promise<void> => {
  if (!canSendMessage.value) return

  try {
    if (!chat.ensureModelSelected()) {
      ElMessage.warning('请先选择一个AI模型')
      showModelSelector.value = true
      return
    }

    const messageText = chatMessageInput.value
    if (!messageText || typeof messageText !== 'string') return

    const messageContent = messageText.trim()
    if (!messageContent) return

    // 初始化流式消息状态
    streamingMessage.value = {
      userMessage: messageContent,
      content: '',
      thinking: '',
      isThinking: false,
      isComplete: false
    }

    // 清空输入框
    chatMessageInput.value = ''

    // 调用流式消息API
    const message = await chat.sendStreamMessage(
      messageContent,
      chat.currentConversation?.value?.id,
      (chunk) => {
        // 处理流式数据块
        if (!streamingMessage.value) return

        switch (chunk.type) {
          case 'thinking_mode':
            streamingMessage.value.isThinking = chunk.isThinking
            break

          case 'thinking_chunk':
            streamingMessage.value.thinking += chunk.content
            break

          case 'thinking_complete':
            streamingMessage.value.thinking = chunk.content
            streamingMessage.value.isThinking = false
            break

          case 'content':
            streamingMessage.value.content += chunk.content
            scrollToBottom()
            break

          case 'complete':
            streamingMessage.value.isComplete = true
            streamingMessage.value.content = chunk.message.content
            if (chunk.message.thinking) {
              streamingMessage.value.thinking = chunk.message.thinking
            }

            // 延迟清除流式消息状态，将消息添加到本地列表
            setTimeout(async () => {
              // 将AI回复添加到本地消息列表
              if (streamingMessage.value && chunk.message) {
                // 检查当前消息列表，避免重复添加用户消息
                const currentMessages = chat.currentMessages?.value || []
                const userMessageExists = currentMessages.some(msg =>
                  msg.role === 'user' && msg.content === streamingMessage.value?.userMessage
                )

                const messagesToAdd = []

                // 如果用户消息不存在，添加用户消息
                if (!userMessageExists) {
                  const userMessage = {
                    id: `user-${Date.now()}`,
                    conversation_id: chunk.message.conversation_id,
                    content: streamingMessage.value.userMessage,
                    role: 'user',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                  }
                  messagesToAdd.push(userMessage)
                }

                // 添加AI回复消息
                const aiMessage = {
                  ...chunk.message,
                  role: 'assistant'
                }
                messagesToAdd.push(aiMessage)

                // 将消息添加到本地存储
                if (messagesToAdd.length > 0) {
                  chat.addLocalMessages(messagesToAdd)
                }
              }

              streamingMessage.value = null
              // 只刷新对话列表（更新最后消息时间等），不重新获取消息
              await chat.refreshConversations()
              scrollToBottom()
            }, 500)
            break
        }
      }
    )

    if (!message) {
      streamingMessage.value = null
      ElMessage.error('发送消息失败')
    }

  } catch (error) {
    streamingMessage.value = null
    ElMessage.error(`发送消息失败: ${error}`)
  }
}

// 处理键盘事件
const handleKeydown = (event: KeyboardEvent): void => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

// 滚动到底部
const scrollToBottom = (): void => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 初始化
onMounted(async () => {
  try {
    // 获取模型列表
    await models.fetchModels()

    // 如果没有选中模型且有可用模型，提示用户选择
    if (!models.selectedModelId?.value && models.activeModels?.value && models.activeModels.value.length > 0) {
      ElMessage.info('请选择一个AI模型开始对话')
      showModelSelector.value = true
    }

    // 获取对话列表
    await chat.refreshConversations()

    // 滚动到底部
    scrollToBottom()
  } catch (error) {
    ElMessage.error(`初始化失败: ${error}`)
  }
})
</script>

<style scoped>
.chat-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #ffffff);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.connection-status.connected {
  background: #dcfce7;
  color: #166534;
}

.connection-status.connecting {
  background: #fef3c7;
  color: #92400e;
}

.connection-status.disconnected {
  background: #fee2e2;
  color: #991b1b;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.model-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 200px;
}

.model-name {
  font-weight: 500;
  color: var(--text-primary, #1f2937);
  font-size: 14px;
}

.model-description {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  text-align: right;
  line-height: 1.3;
}

/* 用户信息样式 */
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-tertiary, #f8fafc);
  border-radius: 8px;
  border: 1px solid var(--border-color, #e5e7eb);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-color, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-text {
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
  line-height: 1.2;
}

.user-role {
  font-size: 11px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.2;
}

.chat-container {
  display: flex;
  flex: 1;
  min-height: 0;
}

.conversation-sidebar {
  width: 300px;
  border-right: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-tertiary, #f9fafb);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-secondary, #ffffff);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-selection-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary, #f8fafc);
  border-radius: 8px;
  border: 1px solid var(--border-color, #e5e7eb);
}

.current-model {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-display {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.model-icon {
  font-size: 18px;
}

.model-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
  line-height: 1.2;
}

.model-status {
  font-size: 11px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.2;
}

.model-actions {
  display: flex;
  justify-content: center;
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversation-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary, #6b7280);
}

.conversation-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conversation-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  background: var(--bg-secondary, #ffffff);
}

.conversation-item:hover {
  background: var(--bg-hover, #f3f4f6);
  border-color: var(--border-hover, #d1d5db);
}

.conversation-item.active {
  background: var(--primary-light, #dbeafe);
  border-color: var(--primary-color, #3b82f6);
}

.conversation-item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.conversation-title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
  line-height: 1.3;
  flex: 1;
}

.conversation-time {
  font-size: 11px;
  color: var(--text-secondary, #6b7280);
  white-space: nowrap;
  margin-left: 8px;
}

.conversation-item-content {
  margin-bottom: 8px;
}

.last-message {
  margin: 0 0 6px 0;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.conversation-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-tertiary, #9ca3af);
}

.conversation-actions {
  display: flex;
  justify-content: flex-end;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 消息包装器 */
.message-wrapper {
  width: 100%;
  display: flex;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.assistant {
  justify-content: flex-start;
}

/* 消息项 */
.message-item {
  display: flex;
  gap: 12px;
  max-width: 75%;
  align-items: flex-start;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-item.assistant {
  flex-direction: row;
}

/* 头像样式 */
.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;
  font-weight: 600;
}

.ai-icon {
  background: var(--ai-bg, #f0f9ff);
  color: var(--ai-color, #0369a1);
  border: 2px solid var(--ai-border, #bae6fd);
}

.user-icon {
  background: var(--primary-color, #3b82f6);
  color: white;
  font-size: 14px;
}

/* 消息内容包装器 */
.message-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 消息头部 */
.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  position: relative;
}

.sender-name {
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}

.message-time {
  color: var(--text-secondary, #6b7280);
  font-size: 11px;
}

/* 消息操作按钮 */
.message-actions {
  display: flex;
  gap: 4px;
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s;
}

.message-item:hover .message-actions {
  opacity: 1;
}

.message-actions .el-button {
  padding: 2px 6px;
  font-size: 11px;
  height: auto;
  min-height: auto;
}

/* 消息编辑模式 */
.message-edit-mode {
  margin-top: 8px;
}

.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
}

.edit-actions .el-button {
  padding: 4px 12px;
  font-size: 12px;
}

/* Thinking区域样式 */
.thinking-section {
  margin-bottom: 8px;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.thinking-toggle:hover {
  background: #fde68a;
}

.thinking-toggle.expanded {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.thinking-icon {
  font-size: 14px;
}

.thinking-label {
  font-size: 12px;
  font-weight: 500;
  color: #92400e;
  flex: 1;
}

.toggle-arrow {
  font-size: 10px;
  color: #92400e;
  transition: transform 0.2s;
}

.thinking-content {
  background: #fffbeb;
  border: 1px solid #f59e0b;
  border-top: none;
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.4;
  color: #78350f;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.thinking-cursor {
  animation: blink 1s infinite;
  color: #f59e0b;
}

/* 消息内容样式 */
.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  position: relative;
}

.ai-content {
  background: var(--ai-message-bg, #f8fafc);
  color: var(--text-primary, #1f2937);
  border: 1px solid var(--border-color, #e5e7eb);
}

.user-content {
  background: var(--primary-color, #3b82f6);
  color: white;
}

.message-item.streaming .ai-content {
  border-bottom: 2px solid var(--primary-color, #3b82f6);
}

.typing-cursor {
  animation: blink 1s infinite;
  color: var(--primary-color, #3b82f6);
  font-weight: bold;
}

/* 消息状态指示器 */
.message-status {
  font-size: 11px;
  color: var(--text-secondary, #6b7280);
  margin-top: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary, #f8fafc);
  display: inline-block;
}

.complete-indicator {
  color: #059669;
  background: #dcfce7;
}

.streaming-indicator {
  color: #f59e0b;
  background: #fef3c7;
  animation: pulse 1.5s ease-in-out infinite;
}

.thinking-indicator {
  color: #8b5cf6;
  background: #f3e8ff;
}

/* 动画效果 */
@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.message-input-container {
  padding: 16px;
  border-top: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
  flex-shrink: 0;
}

.input-area {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-area :deep(.el-textarea) {
  flex: 1;
}

.send-button {
  flex-shrink: 0;
}

.input-status {
  margin-top: 8px;
  text-align: center;
}

.warning-text {
  color: #f59e0b;
  font-size: 13px;
}

.model-selector {
  max-height: 400px;
  overflow-y: auto;
}

.model-grid {
  display: grid;
  gap: 12px;
}

.model-card {
  padding: 16px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-secondary, #ffffff);
}

.model-card:hover {
  border-color: var(--primary-color, #3b82f6);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.model-card.selected {
  border-color: var(--primary-color, #3b82f6);
  background: var(--primary-light, #dbeafe);
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.model-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}

.model-provider {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-tertiary, #f3f4f6);
  padding: 2px 6px;
  border-radius: 4px;
}

.model-description {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.4;
  margin-bottom: 8px;
}

.model-capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.capability-tag {
  font-size: 11px;
  background: var(--primary-light, #dbeafe);
  color: var(--primary-color, #3b82f6);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .conversation-sidebar {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    z-index: 10;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .conversation-sidebar.show {
    transform: translateX(0);
  }

  .model-info {
    display: none;
  }

  .user-info {
    padding: 6px 8px;
  }

  .user-details {
    display: none;
  }

  .message-item {
    max-width: 85%;
  }

  .message-avatar {
    width: 32px;
    height: 32px;
    font-size: 14px;
  }

  .user-icon {
    font-size: 12px;
  }

  .message-content {
    padding: 10px 12px;
    font-size: 13px;
  }

  .thinking-toggle {
    padding: 6px 10px;
  }

  .thinking-content {
    padding: 10px;
    font-size: 12px;
  }
}
</style>
