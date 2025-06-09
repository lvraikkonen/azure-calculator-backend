/**
 * 模型相关类型定义
 */

// 模型类型枚举
export enum ModelType {
  OPENAI = 'openai',
  DEEPSEEK = 'deepseek',
  ANTHROPIC = 'anthropic',
  AZURE = 'azure',
  CUSTOM = 'custom'
}

// 模型能力枚举
export enum ModelCapability {
  TEXT_GENERATION = 'text_generation',
  CHAT = 'chat',
  REASONING = 'reasoning',
  CODE_GENERATION = 'code_generation',
  FUNCTION_CALLING = 'function_calling',
  VISION = 'vision',
  AUDIO = 'audio',
  EMBEDDING = 'embedding'
}

// 模型状态枚举
export enum ModelStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  MAINTENANCE = 'maintenance',
  DEPRECATED = 'deprecated'
}

// 模型信息
export interface ModelInfo {
  id: string
  name: string
  display_name: string
  description?: string
  model_type: ModelType
  model_name: string
  capabilities: ModelCapability[]
  input_price?: number // 每百万tokens价格
  output_price?: number // 每百万tokens价格
  max_tokens?: number
  context_length?: number
  is_active: boolean
  is_custom: boolean
  is_visible: boolean
  created_at: string
  updated_at: string
  metadata?: ModelMetadata
}

// 模型元数据
export interface ModelMetadata {
  api_key_masked?: string
  base_url?: string
  api_version?: string
  deployment_name?: string
  organization?: string
  default_parameters?: ModelParameters
  rate_limits?: RateLimit
  supported_features?: string[]
  model_family?: string
  training_data_cutoff?: string
}

// 模型参数
export interface ModelParameters {
  temperature?: number
  max_tokens?: number
  top_p?: number
  top_k?: number
  frequency_penalty?: number
  presence_penalty?: number
  stop_sequences?: string[]
  stream?: boolean
  [key: string]: any
}

// 速率限制
export interface RateLimit {
  requests_per_minute?: number
  tokens_per_minute?: number
  requests_per_day?: number
  tokens_per_day?: number
}

// 模型创建请求
export interface ModelCreate {
  name: string
  display_name: string
  description?: string
  model_type: ModelType
  model_name: string
  api_key?: string
  base_url?: string
  api_version?: string
  deployment_name?: string
  organization?: string
  capabilities: ModelCapability[]
  input_price?: number
  output_price?: number
  max_tokens?: number
  context_length?: number
  is_active?: boolean
  is_visible?: boolean
  default_parameters?: ModelParameters
  rate_limits?: RateLimit
}

// 模型更新请求
export interface ModelUpdate {
  display_name?: string
  description?: string
  api_key?: string
  base_url?: string
  api_version?: string
  deployment_name?: string
  organization?: string
  capabilities?: ModelCapability[]
  input_price?: number
  output_price?: number
  max_tokens?: number
  context_length?: number
  is_active?: boolean
  is_visible?: boolean
  default_parameters?: ModelParameters
  rate_limits?: RateLimit
}

// 模型响应
export interface ModelResponse extends ModelInfo {
  total_requests?: number
  avg_response_time?: number
  last_used_at?: string
  success_rate?: number
  error_rate?: number
}

// 模型摘要（用于列表显示）
export interface ModelSummary {
  id: string
  name: string
  display_name: string
  model_type: ModelType
  model_name: string
  is_active: boolean
  is_custom: boolean
  total_requests: number
  input_price: number
  output_price: number
  capabilities: ModelCapability[]
}

// 模型列表响应
export interface ModelListResponse {
  models: ModelSummary[]
  total: number
  active_count: number
  custom_count: number
}

// 模型选择
export interface ModelSelection {
  model_id: string
  parameters?: ModelParameters
  use_rag?: boolean
}

// 模型性能数据
export interface ModelPerformance {
  model_id: string
  model_name: string
  avg_response_time: number
  success_rate: number
  error_rate: number
  total_requests: number
  total_tokens: number
  total_cost: number
  last_updated: string
  daily_stats: DailyPerformanceStats[]
}

// 每日性能统计
export interface DailyPerformanceStats {
  date: string
  request_count: number
  avg_response_time: number
  success_rate: number
  total_tokens: number
  total_cost: number
  error_count: number
}

// 模型推荐请求
export interface ModelRecommendationRequest {
  task_type?: string
  performance_requirements?: PerformanceRequirements
  budget_constraints?: BudgetConstraints
  user_preferences?: UserPreferences
}

// 性能要求
export interface PerformanceRequirements {
  max_response_time?: number // 最大响应时间(ms)
  min_accuracy?: number // 最小准确率
  required_capabilities?: ModelCapability[]
  context_length_needed?: number
}

// 预算约束
export interface BudgetConstraints {
  max_cost_per_request?: number
  monthly_budget?: number
  cost_priority?: 'low' | 'medium' | 'high'
}

// 用户偏好
export interface UserPreferences {
  preferred_model_types?: ModelType[]
  avoid_model_types?: ModelType[]
  language_preference?: string
  quality_vs_speed?: 'quality' | 'balanced' | 'speed'
}

// 模型推荐响应
export interface ModelRecommendationResponse {
  recommended_model_id: string
  model_info: ModelInfo
  recommendation_reason: string
  confidence_score: number
  alternatives: AlternativeModel[]
  estimated_performance: EstimatedPerformance
}

// 备选模型
export interface AlternativeModel {
  model_id: string
  model_info: ModelInfo
  reason: string
  confidence_score: number
}

// 预估性能
export interface EstimatedPerformance {
  response_time: number
  accuracy: number
  cost_per_request: number
  suitability_score: number
}

// 模型测试请求
export interface ModelTestRequest {
  model_id: string
  test_prompts: string[]
  parameters?: ModelParameters
  iterations?: number
}

// 模型测试响应
export interface ModelTestResponse {
  model_id: string
  test_results: TestResult[]
  summary: TestSummary
}

// 测试结果
export interface TestResult {
  prompt: string
  response: string
  response_time: number
  token_usage: TokenUsage
  success: boolean
  error_message?: string
}

// 测试摘要
export interface TestSummary {
  total_tests: number
  successful_tests: number
  failed_tests: number
  avg_response_time: number
  total_tokens: number
  total_cost: number
  success_rate: number
}

// Token使用统计（从chat.ts引用）
interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost?: number
}
