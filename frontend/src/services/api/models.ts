/**
 * 模型管理相关API服务
 */

import { httpClient } from '@/services/http'
import type {
  ModelInfo,
  ModelCreate,
  ModelUpdate,
  ModelResponse,
  ModelListResponse,
  ModelPerformance,
  ModelRecommendationRequest,
  ModelRecommendationResponse,
  ModelTestRequest,
  ModelTestResponse,
  QueryParams
} from '@/types'

export class ModelsAPI {
  /**
   * 获取可用模型列表（聊天用）
   */
  async getAvailableModels(): Promise<ModelInfo[]> {
    return httpClient.get<ModelInfo[]>('/chat/models/')
  }

  /**
   * 获取模型管理列表（管理用）
   */
  async getModels(params?: {
    skip?: number
    limit?: number
    model_type?: string
    is_active?: boolean
    is_custom?: boolean
  }): Promise<ModelListResponse> {
    return httpClient.get<ModelListResponse>('/models-management/models', { params })
  }

  /**
   * 获取模型详情
   */
  async getModel(modelId: string): Promise<ModelResponse> {
    return httpClient.get<ModelResponse>(`/models-management/models/${modelId}`)
  }

  /**
   * 创建新模型
   */
  async createModel(modelData: ModelCreate): Promise<ModelResponse> {
    return httpClient.post<ModelResponse>('/models-management/models', modelData)
  }

  /**
   * 更新模型
   */
  async updateModel(modelId: string, updates: ModelUpdate): Promise<ModelResponse> {
    return httpClient.put<ModelResponse>(`/models-management/models/${modelId}`, updates)
  }

  /**
   * 删除模型
   */
  async deleteModel(modelId: string): Promise<void> {
    return httpClient.delete<void>(`/models-management/models/${modelId}`)
  }

  /**
   * 激活模型
   */
  async activateModel(modelId: string): Promise<void> {
    return httpClient.post<void>(`/models-management/models/${modelId}/activate`)
  }

  /**
   * 停用模型
   */
  async deactivateModel(modelId: string): Promise<void> {
    return httpClient.post<void>(`/models-management/models/${modelId}/deactivate`)
  }

  /**
   * 测试模型连接
   */
  async testModelConnection(modelId: string): Promise<{
    success: boolean
    response_time: number
    error?: string
  }> {
    return httpClient.post<{
      success: boolean
      response_time: number
      error?: string
    }>(`/models-management/models/${modelId}/test-connection`)
  }

  /**
   * 获取模型推荐
   */
  async recommendOptimalModel(
    request: ModelRecommendationRequest
  ): Promise<ModelRecommendationResponse> {
    return httpClient.post<ModelRecommendationResponse>('/chat/models/recommend', request)
  }

  /**
   * 获取模型性能数据
   */
  async getModelPerformance(
    modelId: string,
    params?: {
      date_from?: string
      date_to?: string
      granularity?: 'hour' | 'day' | 'week' | 'month'
    }
  ): Promise<ModelPerformance> {
    return httpClient.get<ModelPerformance>(`/models-management/models/${modelId}/performance`, { params })
  }

  /**
   * 获取所有模型性能概览
   */
  async getAllModelsPerformance(params?: {
    date_from?: string
    date_to?: string
    limit?: number
  }): Promise<ModelPerformance[]> {
    return httpClient.get<ModelPerformance[]>('/models-management/performance', { params })
  }

  /**
   * 运行模型性能测试
   */
  async runPerformanceTest(testRequest: ModelTestRequest): Promise<ModelTestResponse> {
    return httpClient.post<ModelTestResponse>('/models-management/performance/test', testRequest)
  }

  /**
   * 获取性能测试历史
   */
  async getPerformanceTestHistory(
    modelId?: string,
    params?: QueryParams
  ): Promise<Array<{
    id: string
    model_id: string
    model_name: string
    test_type: string
    status: 'running' | 'completed' | 'failed'
    started_at: string
    completed_at?: string
    results?: ModelTestResponse
  }>> {
    const queryParams = modelId ? { ...params, model_id: modelId } : params
    return httpClient.get<Array<{
      id: string
      model_id: string
      model_name: string
      test_type: string
      status: 'running' | 'completed' | 'failed'
      started_at: string
      completed_at?: string
      results?: ModelTestResponse
    }>>('/models-management/performance/tests', { params: queryParams })
  }

  /**
   * 获取模型使用统计
   */
  async getModelUsageStats(
    modelId: string,
    params?: {
      date_from?: string
      date_to?: string
      group_by?: 'hour' | 'day' | 'week' | 'month'
    }
  ): Promise<{
    total_requests: number
    total_tokens: number
    total_cost: number
    avg_response_time: number
    success_rate: number
    usage_by_period: Array<{
      period: string
      requests: number
      tokens: number
      cost: number
      avg_response_time: number
    }>
  }> {
    return httpClient.get<{
      total_requests: number
      total_tokens: number
      total_cost: number
      avg_response_time: number
      success_rate: number
      usage_by_period: Array<{
        period: string
        requests: number
        tokens: number
        cost: number
        avg_response_time: number
      }>
    }>(`/models-management/models/${modelId}/usage`, { params })
  }

  /**
   * 比较模型性能
   */
  async compareModels(modelIds: string[], params?: {
    date_from?: string
    date_to?: string
    metrics?: string[]
  }): Promise<{
    models: Array<{
      model_id: string
      model_name: string
      metrics: Record<string, number>
    }>
    comparison_summary: {
      best_performance: string
      best_cost_efficiency: string
      best_reliability: string
    }
  }> {
    return httpClient.post<{
      models: Array<{
        model_id: string
        model_name: string
        metrics: Record<string, number>
      }>
      comparison_summary: {
        best_performance: string
        best_cost_efficiency: string
        best_reliability: string
      }
    }>('/models-management/models/compare', {
      model_ids: modelIds,
      ...params
    })
  }

  /**
   * 获取模型配置模板
   */
  async getModelTemplates(): Promise<Array<{
    id: string
    name: string
    description: string
    model_type: string
    default_config: ModelCreate
  }>> {
    return httpClient.get<Array<{
      id: string
      name: string
      description: string
      model_type: string
      default_config: ModelCreate
    }>>('/models-management/templates')
  }

  /**
   * 从模板创建模型
   */
  async createModelFromTemplate(
    templateId: string,
    customConfig?: Partial<ModelCreate>
  ): Promise<ModelResponse> {
    return httpClient.post<ModelResponse>(`/models-management/templates/${templateId}/create`, customConfig)
  }

  /**
   * 导出模型配置
   */
  async exportModelConfig(modelId: string): Promise<void> {
    await httpClient.download(
      `/models-management/models/${modelId}/export`,
      `model_${modelId}_config.json`
    )
  }

  /**
   * 导入模型配置
   */
  async importModelConfig(file: File): Promise<ModelResponse> {
    return httpClient.upload<ModelResponse>('/models-management/models/import', file)
  }

  /**
   * 批量操作模型
   */
  async batchUpdateModels(
    modelIds: string[],
    operation: 'activate' | 'deactivate' | 'delete',
    options?: Record<string, any>
  ): Promise<{
    success_count: number
    failed_count: number
    errors: Array<{
      model_id: string
      error: string
    }>
  }> {
    return httpClient.post<{
      success_count: number
      failed_count: number
      errors: Array<{
        model_id: string
        error: string
      }>
    }>('/models-management/models/batch', {
      model_ids: modelIds,
      operation,
      options
    })
  }

  /**
   * 获取模型类型列表
   */
  async getModelTypes(): Promise<Array<{
    type: string
    name: string
    description: string
    supported_features: string[]
    required_fields: string[]
  }>> {
    return httpClient.get<Array<{
      type: string
      name: string
      description: string
      supported_features: string[]
      required_fields: string[]
    }>>('/models-management/model-types')
  }

  /**
   * 验证模型配置
   */
  async validateModelConfig(config: ModelCreate): Promise<{
    valid: boolean
    errors: string[]
    warnings: string[]
  }> {
    return httpClient.post<{
      valid: boolean
      errors: string[]
      warnings: string[]
    }>('/models-management/models/validate', config)
  }

  // Store需要的额外方法
  /**
   * 获取模型配置列表
   */
  async getModelConfigurations(): Promise<any[]> {
    return this.getModels().then(response => response.models || [])
  }

  /**
   * 运行模型测试
   */
  async runModelTest(request: any): Promise<any> {
    return this.runPerformanceTest(request)
  }

  /**
   * 获取推荐模型
   */
  async getRecommendedModel(taskType: string, performanceRequirements?: any): Promise<any> {
    return this.recommendOptimalModel({
      task_type: taskType,
      performance_requirements: performanceRequirements
    }).then(response => response.model_info || null)
  }

  /**
   * 创建模型配置
   */
  async createModelConfiguration(config: any): Promise<any> {
    return this.createModel(config)
  }

  /**
   * 更新模型配置
   */
  async updateModelConfiguration(configId: string, updates: any): Promise<any> {
    return this.updateModel(configId, updates)
  }

  /**
   * 删除模型配置
   */
  async deleteModelConfiguration(configId: string): Promise<void> {
    return this.deleteModel(configId)
  }

  /**
   * 获取模型统计信息
   */
  async getModelStatistics(): Promise<any> {
    return this.getAllModelsPerformance().then(data => ({
      total_models: data.length,
      active_models: data.filter((m: any) => m.status === 'active').length,
      performance_data: data
    }))
  }
}

// 创建并导出API实例
export const modelsAPI = new ModelsAPI()
