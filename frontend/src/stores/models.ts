import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  ModelInfo, 
  ModelConfiguration,
  ModelPerformanceData,
  ModelTestRequest,
  ModelTestResult 
} from '@/types'
import { modelService } from '@/services'

export const useModelsStore = defineStore('models', () => {
  // 状态
  const availableModels = ref<ModelInfo[]>([])
  const modelConfigurations = ref<ModelConfiguration[]>([])
  const selectedModelId = ref<string | null>(null)
  const performanceData = ref<Record<string, ModelPerformanceData>>({})
  const testResults = ref<Record<string, ModelTestResult[]>>({})
  const isLoading = ref(false)
  const isTesting = ref(false)
  const lastError = ref<string | null>(null)
  const lastUpdated = ref<Date | null>(null)

  // 计算属性
  const selectedModel = computed(() => 
    availableModels.value.find(model => model.id === selectedModelId.value) || null
  )

  const selectedModelConfig = computed(() => 
    modelConfigurations.value.find(config => config.id === selectedModelId.value) || null
  )

  const modelsByProvider = computed(() => {
    const grouped: Record<string, ModelInfo[]> = {}
    availableModels.value.forEach(model => {
      const provider = model.provider || 'unknown'
      if (!grouped[provider]) {
        grouped[provider] = []
      }
      grouped[provider].push(model)
    })
    return grouped
  })

  const activeModels = computed(() =>
    availableModels.value.filter(model => model.is_active === true)
  )

  const modelCount = computed(() => availableModels.value.length)

  const hasPerformanceData = computed(() => (modelId: string) => 
    !!performanceData.value[modelId]
  )

  // 获取可用模型列表
  const fetchAvailableModels = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const models = await modelService.getAvailableModels()
      availableModels.value = models
      lastUpdated.value = new Date()
      
      // 如果没有选中的模型，选择第一个可用的
      if (!selectedModelId.value && models.length > 0) {
        selectedModelId.value = models[0].id
      }
    } catch (error) {
      console.error('获取模型列表失败:', error)
      lastError.value = '获取模型列表失败'
    } finally {
      isLoading.value = false
    }
  }

  // 获取模型配置
  const fetchModelConfigurations = async (): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const configs = await modelService.getModelConfigurations()
      modelConfigurations.value = configs
    } catch (error) {
      console.error('获取模型配置失败:', error)
      lastError.value = '获取模型配置失败'
    } finally {
      isLoading.value = false
    }
  }

  // 选择模型
  const selectModel = (modelId: string): boolean => {
    const model = availableModels.value.find(m => m.id === modelId)
    if (model) {
      // 检查模型状态，如果没有status字段，默认认为是可用的
      const isActive = model.status === 'active' || !model.status
      if (isActive) {
        selectedModelId.value = modelId
        return true
      }
    }
    return false
  }

  // 获取模型性能数据
  const fetchModelPerformance = async (modelId: string): Promise<void> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const performance = await modelService.getModelPerformance(modelId)
      performanceData.value[modelId] = performance
    } catch (error) {
      console.error('获取模型性能数据失败:', error)
      lastError.value = '获取模型性能数据失败'
    } finally {
      isLoading.value = false
    }
  }

  // 运行模型测试
  const runModelTest = async (request: ModelTestRequest): Promise<ModelTestResult | null> => {
    try {
      isTesting.value = true
      lastError.value = null
      
      const result = await modelService.runModelTest(request)
      
      // 保存测试结果
      if (!testResults.value[request.model_id]) {
        testResults.value[request.model_id] = []
      }
      testResults.value[request.model_id].unshift(result)
      
      // 限制保存的测试结果数量
      if (testResults.value[request.model_id].length > 10) {
        testResults.value[request.model_id] = testResults.value[request.model_id].slice(0, 10)
      }
      
      return result
    } catch (error) {
      console.error('模型测试失败:', error)
      lastError.value = '模型测试失败'
      return null
    } finally {
      isTesting.value = false
    }
  }

  // 获取推荐模型
  const getRecommendedModel = async (
    taskType: string = 'general',
    performanceRequirements?: Record<string, any>
  ): Promise<ModelInfo | null> => {
    try {
      const recommendation = await modelService.getRecommendedModel(taskType, performanceRequirements)
      return recommendation
    } catch (error) {
      console.error('获取推荐模型失败:', error)
      lastError.value = '获取推荐模型失败'
      return null
    }
  }

  // 创建模型配置
  const createModelConfiguration = async (config: Partial<ModelConfiguration>): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const newConfig = await modelService.createModelConfiguration(config)
      modelConfigurations.value.push(newConfig)
      
      return true
    } catch (error) {
      console.error('创建模型配置失败:', error)
      lastError.value = '创建模型配置失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 更新模型配置
  const updateModelConfiguration = async (
    configId: string, 
    updates: Partial<ModelConfiguration>
  ): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const updatedConfig = await modelService.updateModelConfiguration(configId, updates)
      
      // 更新本地状态
      const index = modelConfigurations.value.findIndex(config => config.id === configId)
      if (index !== -1) {
        modelConfigurations.value[index] = updatedConfig
      }
      
      return true
    } catch (error) {
      console.error('更新模型配置失败:', error)
      lastError.value = '更新模型配置失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 删除模型配置
  const deleteModelConfiguration = async (configId: string): Promise<boolean> => {
    try {
      isLoading.value = true
      lastError.value = null
      
      await modelService.deleteModelConfiguration(configId)
      
      // 从本地状态中移除
      modelConfigurations.value = modelConfigurations.value.filter(config => config.id !== configId)
      
      return true
    } catch (error) {
      console.error('删除模型配置失败:', error)
      lastError.value = '删除模型配置失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 获取模型统计信息
  const getModelStatistics = async (): Promise<Record<string, any> | null> => {
    try {
      const stats = await modelService.getModelStatistics()
      return stats
    } catch (error) {
      console.error('获取模型统计失败:', error)
      lastError.value = '获取模型统计失败'
      return null
    }
  }

  // 清除性能数据缓存
  const clearPerformanceCache = (modelId?: string) => {
    if (modelId) {
      delete performanceData.value[modelId]
    } else {
      performanceData.value = {}
    }
  }

  // 清除测试结果
  const clearTestResults = (modelId?: string) => {
    if (modelId) {
      delete testResults.value[modelId]
    } else {
      testResults.value = {}
    }
  }

  // 清除错误
  const clearError = () => {
    lastError.value = null
  }

  // 刷新所有数据
  const refreshAllData = async (): Promise<void> => {
    await Promise.all([
      fetchAvailableModels(),
      fetchModelConfigurations()
    ])
  }

  return {
    // 状态
    availableModels: readonly(availableModels),
    modelConfigurations: readonly(modelConfigurations),
    selectedModelId: readonly(selectedModelId),
    performanceData: readonly(performanceData),
    testResults: readonly(testResults),
    isLoading: readonly(isLoading),
    isTesting: readonly(isTesting),
    lastError: readonly(lastError),
    lastUpdated: readonly(lastUpdated),
    
    // 计算属性
    selectedModel,
    selectedModelConfig,
    modelsByProvider,
    activeModels,
    modelCount,
    hasPerformanceData,
    
    // 方法
    fetchAvailableModels,
    fetchModelConfigurations,
    selectModel,
    fetchModelPerformance,
    runModelTest,
    getRecommendedModel,
    createModelConfiguration,
    updateModelConfiguration,
    deleteModelConfiguration,
    getModelStatistics,
    clearPerformanceCache,
    clearTestResults,
    clearError,
    refreshAllData
  }
}, {
  persist: {
    key: 'models-store',
    storage: localStorage,
    paths: ['selectedModelId', 'lastUpdated']
  }
})
