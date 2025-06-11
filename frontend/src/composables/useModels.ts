import { computed, ref } from 'vue'
import { useModelsStore } from '@/stores/models'
import { useUIStore } from '@/stores/ui'
import type { 
  ModelInfo, 
  ModelConfiguration,
  ModelTestRequest,
  ModelTestResult 
} from '@/types'

/**
 * 模型管理相关的组合式函数
 * 基于 ModelsStore 提供高级模型管理逻辑
 */
export function useModels() {
  const modelsStore = useModelsStore()
  const uiStore = useUIStore()

  // 本地状态
  const testPrompt = ref('')
  const testParameters = ref({
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 1.0
  })

  // 响应式状态
  const availableModels = computed(() => modelsStore.availableModels)
  const activeModels = computed(() => modelsStore.activeModels)
  const selectedModel = computed(() => modelsStore.selectedModel)
  const selectedModelId = computed(() => modelsStore.selectedModelId)
  const modelConfigurations = computed(() => modelsStore.modelConfigurations)
  const selectedModelConfig = computed(() => modelsStore.selectedModelConfig)
  const modelsByProvider = computed(() => modelsStore.modelsByProvider)
  const performanceData = computed(() => modelsStore.performanceData)
  const testResults = computed(() => modelsStore.testResults)
  const isLoading = computed(() => modelsStore.isLoading)
  const isTesting = computed(() => modelsStore.isTesting)
  const lastError = computed(() => modelsStore.lastError)
  const modelCount = computed(() => modelsStore.modelCount)

  // 模型选择
  const selectModel = (modelId: string): boolean => {
    try {
      const success = modelsStore.selectModel(modelId)
      
      if (success) {
        const model = availableModels.value.find(m => m.id === modelId)
        uiStore.addNotification({
          type: 'success',
          title: '模型已选择',
          message: `已选择模型：${model?.name || modelId}`
        })
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '选择失败',
          message: '该模型当前不可用'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '选择失败',
        message: error instanceof Error ? error.message : '选择模型时发生错误'
      })
      return false
    }
  }

  // 获取模型列表
  const fetchModels = async (): Promise<void> => {
    try {
      uiStore.showLoading('正在加载模型列表...')
      await modelsStore.fetchAvailableModels()
      
      uiStore.addNotification({
        type: 'success',
        title: '模型列表已更新',
        message: `共加载 ${modelsStore.modelCount} 个模型`
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '加载失败',
        message: error instanceof Error ? error.message : '加载模型列表失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 获取模型配置
  const fetchConfigurations = async (): Promise<void> => {
    try {
      await modelsStore.fetchModelConfigurations()
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '配置加载失败',
        message: error instanceof Error ? error.message : '加载模型配置失败'
      })
    }
  }

  // 运行模型测试
  const runTest = async (
    modelId?: string,
    prompt?: string,
    parameters?: Record<string, any>
  ): Promise<ModelTestResult | null> => {
    const targetModelId = modelId || selectedModelId.value
    const testPromptText = prompt || testPrompt.value
    
    if (!targetModelId) {
      uiStore.addNotification({
        type: 'warning',
        title: '请选择模型',
        message: '请先选择要测试的模型'
      })
      return null
    }

    if (!testPromptText.trim()) {
      uiStore.addNotification({
        type: 'warning',
        title: '请输入测试内容',
        message: '请输入测试提示词'
      })
      return null
    }

    try {
      uiStore.showLoading('正在运行模型测试...')
      
      const request: ModelTestRequest = {
        model_id: targetModelId,
        test_prompts: [testPromptText.trim()],
        parameters: parameters || testParameters.value
      }

      const result = await modelsStore.runModelTest(request)

      if (result) {
        uiStore.addNotification({
          type: 'success',
          title: '测试完成',
          message: `模型测试完成，平均响应时间：${result.summary.avg_response_time}ms`
        })
        return result
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '测试失败',
          message: modelsStore.lastError || '模型测试失败'
        })
        return null
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '测试失败',
        message: error instanceof Error ? error.message : '运行测试时发生错误'
      })
      return null
    } finally {
      uiStore.hideLoading()
    }
  }

  // 获取模型性能数据
  const fetchPerformance = async (modelId?: string): Promise<void> => {
    const targetModelId = modelId || selectedModelId.value
    
    if (!targetModelId) {
      uiStore.addNotification({
        type: 'warning',
        title: '请选择模型',
        message: '请先选择要查看性能的模型'
      })
      return
    }

    try {
      uiStore.showLoading('正在加载性能数据...')
      await modelsStore.fetchModelPerformance(targetModelId)
      
      uiStore.addNotification({
        type: 'success',
        title: '性能数据已更新',
        message: '模型性能数据加载完成'
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '加载失败',
        message: error instanceof Error ? error.message : '加载性能数据失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 获取推荐模型
  const getRecommendation = async (
    taskType: string = 'general',
    requirements?: Record<string, any>
  ): Promise<ModelInfo | null> => {
    try {
      uiStore.showLoading('正在分析推荐模型...')
      
      const recommendation = await modelsStore.getRecommendedModel(taskType, requirements)
      
      if (recommendation) {
        uiStore.addNotification({
          type: 'info',
          title: '推荐模型',
          message: `推荐使用：${recommendation.name}`
        })
        return recommendation
      } else {
        uiStore.addNotification({
          type: 'warning',
          title: '无推荐结果',
          message: '未找到符合要求的推荐模型'
        })
        return null
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '推荐失败',
        message: error instanceof Error ? error.message : '获取推荐模型失败'
      })
      return null
    } finally {
      uiStore.hideLoading()
    }
  }

  // 创建模型配置
  const createConfiguration = async (config: Partial<ModelConfiguration>): Promise<boolean> => {
    try {
      uiStore.showLoading('正在创建配置...')
      
      const success = await modelsStore.createModelConfiguration(config)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '配置已创建',
          message: '模型配置创建成功'
        })
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '创建失败',
          message: modelsStore.lastError || '创建配置失败'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '创建失败',
        message: error instanceof Error ? error.message : '创建配置时发生错误'
      })
      return false
    } finally {
      uiStore.hideLoading()
    }
  }

  // 更新模型配置
  const updateConfiguration = async (
    configId: string, 
    updates: Partial<ModelConfiguration>
  ): Promise<boolean> => {
    try {
      uiStore.showLoading('正在更新配置...')
      
      const success = await modelsStore.updateModelConfiguration(configId, updates)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '配置已更新',
          message: '模型配置更新成功'
        })
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '更新失败',
          message: modelsStore.lastError || '更新配置失败'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '更新失败',
        message: error instanceof Error ? error.message : '更新配置时发生错误'
      })
      return false
    } finally {
      uiStore.hideLoading()
    }
  }

  // 删除模型配置
  const deleteConfiguration = async (configId: string): Promise<boolean> => {
    try {
      uiStore.showLoading('正在删除配置...')
      
      const success = await modelsStore.deleteModelConfiguration(configId)
      
      if (success) {
        uiStore.addNotification({
          type: 'success',
          title: '配置已删除',
          message: '模型配置删除成功'
        })
        return true
      } else {
        uiStore.addNotification({
          type: 'error',
          title: '删除失败',
          message: modelsStore.lastError || '删除配置失败'
        })
        return false
      }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '删除失败',
        message: error instanceof Error ? error.message : '删除配置时发生错误'
      })
      return false
    } finally {
      uiStore.hideLoading()
    }
  }

  // 刷新所有数据
  const refreshAll = async (): Promise<void> => {
    try {
      uiStore.showLoading('正在刷新数据...')
      await modelsStore.refreshAllData()
      
      uiStore.addNotification({
        type: 'success',
        title: '数据已刷新',
        message: '所有模型数据已更新'
      })
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: '刷新失败',
        message: error instanceof Error ? error.message : '刷新数据失败'
      })
    } finally {
      uiStore.hideLoading()
    }
  }

  // 清除错误
  const clearError = (): void => {
    modelsStore.clearError()
  }

  // 清除缓存
  const clearCache = (modelId?: string): void => {
    modelsStore.clearPerformanceCache(modelId)
    modelsStore.clearTestResults(modelId)
    
    uiStore.addNotification({
      type: 'info',
      title: '缓存已清除',
      message: modelId ? `已清除模型 ${modelId} 的缓存` : '已清除所有缓存'
    })
  }

  return {
    // 状态
    availableModels,
    activeModels,
    selectedModel,
    selectedModelId,
    modelConfigurations,
    selectedModelConfig,
    modelsByProvider,
    performanceData,
    testResults,
    isLoading,
    isTesting,
    lastError,
    modelCount,
    
    // 本地状态
    testPrompt,
    testParameters,
    
    // 模型操作
    selectModel,
    fetchModels,
    fetchConfigurations,
    runTest,
    fetchPerformance,
    getRecommendation,
    
    // 配置管理
    createConfiguration,
    updateConfiguration,
    deleteConfiguration,
    
    // 工具函数
    refreshAll,
    clearError,
    clearCache
  }
}
