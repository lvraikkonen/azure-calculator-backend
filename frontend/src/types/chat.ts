/**
 * 聊天相关类型定义
 */

// 消息角色枚举
export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system'
}

// 消息状态枚举
export enum MessageStatus {
  PENDING = 'pending',
  SENDING = 'sending',
  SENT = 'sent',
  DELIVERED = 'delivered',
  FAILED = 'failed'
}

// 聊天消息
export interface ChatMessage {
  id: string
  conversation_id: string
  content: string
  role: MessageRole
  model_id?: string
  model_name?: string
  created_at: string
  updated_at: string
  metadata?: MessageMetadata
  status?: MessageStatus
  error_message?: string
  token_usage?: TokenUsage
}

// 消息元数据
export interface MessageMetadata {
  reasoning_content?: string // 推理过程内容
  citations?: Citation[] // 引用来源
  confidence_score?: number // 置信度分数
  processing_time?: number // 处理时间(ms)
  model_parameters?: Record<string, any> // 模型参数
  rag_enabled?: boolean // 是否启用RAG
  rag_sources?: RAGSource[] // RAG来源
}

// 引用来源
export interface Citation {
  source: string
  title?: string
  url?: string
  excerpt?: string
  relevance_score?: number
}

// RAG来源
export interface RAGSource {
  document_id: string
  document_title: string
  chunk_id: string
  content: string
  similarity_score: number
  metadata?: Record<string, any>
}

// Token使用统计
export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost?: number
}

// 对话
export interface Conversation {
  id: string
  title: string
  user_id: string
  model_id?: string
  created_at: string
  updated_at: string
  last_message?: string
  message_count: number
  is_archived?: boolean
  tags?: string[]
  metadata?: ConversationMetadata
}

// 对话元数据
export interface ConversationMetadata {
  total_tokens?: number
  total_cost?: number
  average_response_time?: number
  rag_enabled?: boolean
  model_switches?: ModelSwitch[]
}

// 模型切换记录
export interface ModelSwitch {
  from_model_id?: string
  to_model_id: string
  switched_at: string
  reason?: string
}

// 对话摘要（用于列表显示）
export interface ConversationSummary {
  id: string
  title: string
  last_message: string
  updated_at: string
  message_count: number
  model_name?: string
  is_archived?: boolean
  tags?: string[]
}

// 消息创建请求
export interface MessageCreate {
  content: string
  conversation_id?: string
  model_id?: string
  use_rag?: boolean
  model_parameters?: Record<string, any>
  context_messages?: string[] // 上下文消息ID
}

// 对话创建请求
export interface ConversationCreate {
  title?: string
  model_id?: string
  initial_message?: string
  use_rag?: boolean
  tags?: string[]
}

// 对话更新请求
export interface ConversationUpdate {
  title?: string
  is_archived?: boolean
  tags?: string[]
}

// 消息反馈
export interface MessageFeedback {
  message_id: string
  feedback_type: 'like' | 'dislike' | 'report'
  comment?: string
  rating?: number // 1-5星评分
  categories?: string[] // 反馈分类
}

// 消息反馈创建请求
export interface FeedbackCreate {
  feedback_type: 'like' | 'dislike' | 'report'
  comment?: string
  rating?: number
  categories?: string[]
}

// 聊天统计
export interface ChatStatistics {
  total_conversations: number
  total_messages: number
  total_tokens: number
  total_cost: number
  average_response_time: number
  most_used_models: ModelUsageStats[]
  daily_usage: DailyUsageStats[]
}

// 模型使用统计
export interface ModelUsageStats {
  model_id: string
  model_name: string
  usage_count: number
  total_tokens: number
  total_cost: number
  average_response_time: number
}

// 每日使用统计
export interface DailyUsageStats {
  date: string
  message_count: number
  token_count: number
  cost: number
  unique_users: number
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: 'message' | 'typing' | 'error' | 'connected' | 'disconnected' | 'token_update'
  data: any
  timestamp: string
  conversation_id?: string
  message_id?: string
}

// 打字状态
export interface TypingStatus {
  conversation_id: string
  user_id: string
  is_typing: boolean
  timestamp: string
}

// 推荐相关类型
export interface Recommendation {
  type: 'model' | 'prompt' | 'feature'
  title: string
  description: string
  confidence: number
  metadata?: Record<string, any>
}

// 搜索请求
export interface MessageSearchRequest {
  query: string
  conversation_id?: string
  date_from?: string
  date_to?: string
  model_id?: string
  limit?: number
  offset?: number
}

// 搜索响应
export interface MessageSearchResponse {
  messages: ChatMessage[]
  total: number
  highlights: SearchHighlight[]
}

// 搜索高亮
export interface SearchHighlight {
  message_id: string
  field: string
  fragments: string[]
}

// Store需要的额外类型
export type Message = ChatMessage
export type CreateConversationRequest = ConversationCreate
export type SendMessageRequest = MessageCreate
