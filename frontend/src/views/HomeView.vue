<template>
  <div class="home-view flex-center min-h-screen">
    <div class="card max-w-md w-full mx-4">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-primary mb-4">
          AI智能对话系统
        </h1>
        <p class="text-secondary mb-6">
          欢迎使用AI智能对话系统，请先登录以开始使用。
        </p>
        <div class="space-y-4">
          <el-button 
            type="primary" 
            size="large" 
            class="w-full"
            @click="goToLogin"
          >
            立即登录
          </el-button>
          <el-button 
            size="large" 
            class="w-full"
            @click="testApiConnection"
            :loading="isTestingApi"
          >
            测试API连接
          </el-button>
        </div>
        
        <!-- API连接状态显示 -->
        <div v-if="apiStatus" class="mt-4 p-3 rounded-lg" :class="apiStatusClass">
          <p class="text-sm">{{ apiStatus }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { HealthCheckResponse, ApiResponse } from '@/types'
import { httpClient, authAPI } from '@/services'

const router = useRouter()
const isTestingApi = ref(false)
const apiStatus = ref('')
const apiConnected = ref<boolean | null>(null)

const apiStatusClass = computed(() => {
  if (apiConnected.value === true) {
    return 'bg-green-100 text-green-800 border border-green-200'
  } else if (apiConnected.value === false) {
    return 'bg-red-100 text-red-800 border border-red-200'
  }
  return 'bg-gray-100 text-gray-800 border border-gray-200'
})

const goToLogin = (): void => {
  router.push('/login')
}

const testApiConnection = async (): Promise<void> => {
  isTestingApi.value = true
  apiStatus.value = '正在测试API连接...'

  try {
    // 使用新的HTTP客户端服务
    const data = await httpClient.get<HealthCheckResponse>('/health')
    apiConnected.value = true
    apiStatus.value = `API连接成功！状态: ${data.status}`
    ElMessage.success('API连接正常')
  } catch (error) {
    apiConnected.value = false
    apiStatus.value = `API连接失败: ${error instanceof Error ? error.message : '未知错误'}`
    ElMessage.error('API连接失败，请检查后端服务是否启动')
  } finally {
    isTestingApi.value = false
  }
}
</script>

<style scoped>
.home-view {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
