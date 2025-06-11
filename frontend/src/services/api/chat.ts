/**
 * 聊天相关API服务
 */

import { httpClient } from '@/services/http'
import type {
  ChatMessage,
  Conversation,
  ConversationSummary,
  MessageCreate,
  ConversationCreate,
  ConversationUpdate,
  FeedbackCreate,
  MessageSearchRequest,
  MessageSearchResponse,
  ChatStatistics,
  QueryParams
} from '@/types'

export class ChatAPI {
  /**
   * 发送消息
   */
  async sendMessage(message: MessageCreate): Promise<ChatMessage> {
    return httpClient.post<ChatMessage>('/chat/messages/', message)
  }

  /**
   * 获取对话列表
   */
  async getConversations(params?: QueryParams): Promise<ConversationSummary[]> {
    return httpClient.get<ConversationSummary[]>('/chat/conversations/', { params })
  }

  /**
   * 获取对话详情（包含消息）
   */
  async getConversation(id: string): Promise<Conversation & { messages: ChatMessage[] }> {
    return httpClient.get<Conversation & { messages: ChatMessage[] }>(`/chat/conversations/${id}`)
  }

  /**
   * 创建新对话
   */
  async createConversation(conversationData: ConversationCreate): Promise<Conversation> {
    return httpClient.post<Conversation>('/chat/conversations/', conversationData)
  }

  /**
   * 更新对话信息
   */
  async updateConversation(id: string, updates: ConversationUpdate): Promise<Conversation> {
    return httpClient.patch<Conversation>(`/chat/conversations/${id}`, updates)
  }

  /**
   * 删除对话
   */
  async deleteConversation(id: string): Promise<void> {
    return httpClient.delete<void>(`/chat/conversations/${id}`)
  }

  /**
   * 归档对话
   */
  async archiveConversation(id: string): Promise<void> {
    return httpClient.post<void>(`/chat/conversations/${id}/archive`)
  }

  /**
   * 取消归档对话
   */
  async unarchiveConversation(id: string): Promise<void> {
    return httpClient.post<void>(`/chat/conversations/${id}/unarchive`)
  }

  /**
   * 获取对话消息
   * 注意：后端实际API是 /chat/conversations/{id}，返回对话及其消息
   * 这个方法为了兼容性，内部调用getConversation并提取messages
   */
  async getMessages(
    conversationId: string,
    params?: {
      limit?: number
      offset?: number
      before_message_id?: string
      after_message_id?: string
    }
  ): Promise<ChatMessage[]> {
    try {
      // 调用getConversation获取完整对话数据
      const conversation = await this.getConversation(conversationId)
      return conversation.messages || []
    } catch (error) {
      console.error('获取对话消息失败:', error)
      throw error
    }
  }

  /**
   * 获取单条消息详情
   */
  async getMessage(messageId: string): Promise<ChatMessage> {
    return httpClient.get<ChatMessage>(`/chat/messages/${messageId}`)
  }

  /**
   * 删除消息
   */
  async deleteMessage(messageId: string): Promise<void> {
    return httpClient.delete<void>(`/chat/messages/${messageId}`)
  }

  /**
   * 重新生成消息
   */
  async regenerateMessage(messageId: string): Promise<ChatMessage> {
    return httpClient.post<ChatMessage>(`/chat/messages/${messageId}/regenerate`)
  }

  /**
   * 添加消息反馈
   */
  async addFeedback(messageId: string, feedback: FeedbackCreate): Promise<void> {
    return httpClient.post<void>('/chat/feedback/', {
      message_id: messageId,
      ...feedback
    })
  }

  /**
   * 获取消息反馈
   */
  async getFeedback(messageId: string): Promise<Array<{
    id: string
    feedback_type: string
    comment?: string
    rating?: number
    created_at: string
  }>> {
    return httpClient.get<Array<{
      id: string
      feedback_type: string
      comment?: string
      rating?: number
      created_at: string
    }>>(`/chat/messages/${messageId}/feedback`)
  }

  /**
   * 搜索消息
   */
  async searchMessages(searchRequest: MessageSearchRequest): Promise<MessageSearchResponse> {
    return httpClient.post<MessageSearchResponse>('/chat/search', searchRequest)
  }

  /**
   * 获取聊天统计
   */
  async getChatStatistics(params?: {
    date_from?: string
    date_to?: string
    user_id?: string
  }): Promise<ChatStatistics> {
    return httpClient.get<ChatStatistics>('/chat/statistics', { params })
  }

  /**
   * 导出对话
   */
  async exportConversation(
    conversationId: string,
    format: 'json' | 'txt' | 'pdf' = 'json'
  ): Promise<void> {
    await httpClient.download(
      `/chat/conversations/${conversationId}/export?format=${format}`,
      `conversation_${conversationId}.${format}`
    )
  }

  /**
   * 批量导出对话
   */
  async exportConversations(
    conversationIds: string[],
    format: 'json' | 'zip' = 'zip'
  ): Promise<void> {
    await httpClient.download(
      `/chat/conversations/export?format=${format}`,
      `conversations.${format}`,
      {
        method: 'POST',
        data: { conversation_ids: conversationIds }
      }
    )
  }

  /**
   * 获取对话标签
   */
  async getConversationTags(): Promise<Array<{
    name: string
    count: number
    color?: string
  }>> {
    return httpClient.get<Array<{
      name: string
      count: number
      color?: string
    }>>('/chat/tags')
  }

  /**
   * 添加对话标签
   */
  async addConversationTag(conversationId: string, tag: string): Promise<void> {
    return httpClient.post<void>(`/chat/conversations/${conversationId}/tags`, { tag })
  }

  /**
   * 移除对话标签
   */
  async removeConversationTag(conversationId: string, tag: string): Promise<void> {
    return httpClient.delete<void>(`/chat/conversations/${conversationId}/tags/${tag}`)
  }

  /**
   * 获取推荐问题
   */
  async getRecommendedQuestions(conversationId?: string): Promise<string[]> {
    const params = conversationId ? { conversation_id: conversationId } : undefined
    return httpClient.get<string[]>('/chat/recommendations/questions', { params })
  }

  /**
   * 获取推荐模型
   */
  async getRecommendedModel(prompt: string): Promise<{
    model_id: string
    model_name: string
    reason: string
    confidence: number
  }> {
    return httpClient.post<{
      model_id: string
      model_name: string
      reason: string
      confidence: number
    }>('/chat/recommendations/model', { prompt })
  }

  /**
   * 获取对话摘要
   */
  async getConversationSummary(conversationId: string): Promise<{
    summary: string
    key_points: string[]
    topics: string[]
    sentiment: 'positive' | 'neutral' | 'negative'
  }> {
    return httpClient.get<{
      summary: string
      key_points: string[]
      topics: string[]
      sentiment: 'positive' | 'neutral' | 'negative'
    }>(`/chat/conversations/${conversationId}/summary`)
  }

  /**
   * 生成对话标题
   */
  async generateConversationTitle(conversationId: string): Promise<{ title: string }> {
    return httpClient.post<{ title: string }>(`/chat/conversations/${conversationId}/generate-title`)
  }

  /**
   * 获取相似对话
   */
  async getSimilarConversations(
    conversationId: string,
    limit = 5
  ): Promise<Array<{
    id: string
    title: string
    similarity_score: number
    last_message: string
    updated_at: string
  }>> {
    return httpClient.get<Array<{
      id: string
      title: string
      similarity_score: number
      last_message: string
      updated_at: string
    }>>(`/chat/conversations/${conversationId}/similar?limit=${limit}`)
  }

  /**
   * 检查消息是否正在生成
   */
  async checkMessageStatus(messageId: string): Promise<{
    status: 'pending' | 'generating' | 'completed' | 'failed'
    progress?: number
    error?: string
  }> {
    return httpClient.get<{
      status: 'pending' | 'generating' | 'completed' | 'failed'
      progress?: number
      error?: string
    }>(`/chat/messages/${messageId}/status`)
  }

  /**
   * 取消消息生成
   */
  async cancelMessageGeneration(messageId: string): Promise<void> {
    return httpClient.post<void>(`/chat/messages/${messageId}/cancel`)
  }
}

// 创建并导出API实例
export const chatAPI = new ChatAPI()
