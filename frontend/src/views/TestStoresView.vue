<template>
  <div class="test-stores-view">
    <el-container>
      <el-header>
        <h1>Phase 4: 状态管理系统测试</h1>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <!-- 认证状态测试 -->
          <el-col :span="12">
            <el-card header="认证状态管理">
              <div class="store-test">
                <p><strong>登录状态:</strong> {{ authStore.isAuthenticated ? '已登录' : '未登录' }}</p>
                <p><strong>用户角色:</strong> {{ authStore.userRole }}</p>
                <p><strong>是否管理员:</strong> {{ authStore.isAdmin ? '是' : '否' }}</p>
                <p><strong>用户名:</strong> {{ authStore.userName || '未设置' }}</p>
                <p><strong>加载状态:</strong> {{ authStore.isLoading ? '加载中' : '空闲' }}</p>
                
                <el-button-group>
                  <el-button @click="testLogin" :loading="authStore.isLoading">
                    测试登录
                  </el-button>
                  <el-button @click="testLogout">
                    测试登出
                  </el-button>
                </el-button-group>
              </div>
            </el-card>
          </el-col>

          <!-- 聊天状态测试 -->
          <el-col :span="12">
            <el-card header="聊天状态管理">
              <div class="store-test">
                <p><strong>对话数量:</strong> {{ chatStore.conversationCount }}</p>
                <p><strong>当前对话:</strong> {{ chatStore.currentConversation?.title || '无' }}</p>
                <p><strong>消息数量:</strong> {{ chatStore.currentMessages.length }}</p>
                <p><strong>连接状态:</strong> {{ chatStore.connectionStatus }}</p>
                <p><strong>发送状态:</strong> {{ chatStore.isSending ? '发送中' : '空闲' }}</p>

                <!-- 模型选择提示 -->
                <div v-if="!modelsStore.selectedModel" class="model-warning">
                  <el-alert
                    title="请先选择聊天模型"
                    type="warning"
                    description="在开始聊天前，请先在模型管理中选择一个聊天模型"
                    :closable="false"
                    show-icon
                  />
                </div>
                <div v-else class="model-info">
                  <el-alert
                    :title="`已选择模型: ${modelsStore.selectedModel.display_name || modelsStore.selectedModel.name}`"
                    type="success"
                    :closable="false"
                    show-icon
                  >
                    <template #default>
                      <div class="model-details">
                        <p class="model-description">
                          <strong>描述:</strong> {{ modelsStore.selectedModel.description || '暂无描述' }}
                        </p>
                        <div class="model-capabilities">
                          <strong>功能:</strong>
                          <el-tag
                            v-for="capability in (modelsStore.selectedModel.capabilities || [])"
                            :key="capability"
                            :type="getCapabilityTagType(capability)"
                            size="small"
                            class="capability-tag"
                          >
                            {{ getCapabilityDisplayName(capability) }}
                          </el-tag>
                          <span v-if="!modelsStore.selectedModel.capabilities || modelsStore.selectedModel.capabilities.length === 0" class="no-capabilities">
                            暂无功能信息
                          </span>
                        </div>

                      </div>
                    </template>
                  </el-alert>
                </div>

                <el-button-group>
                  <el-button
                    @click="testCreateConversation"
                    :loading="chatStore.isLoading"
                    :disabled="!modelsStore.selectedModel"
                  >
                    创建对话
                  </el-button>
                  <el-button
                    @click="testSendMessage"
                    :loading="chatStore.isSending"
                    :disabled="!modelsStore.selectedModel"
                  >
                    发送消息
                  </el-button>
                </el-button-group>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
          <!-- 模型状态测试 -->
          <el-col :span="12">
            <el-card header="模型状态管理">
              <div class="store-test">
                <p><strong>模型数量:</strong> {{ modelsStore.modelCount }}</p>
                <p><strong>选中模型:</strong> {{ modelsStore.selectedModel?.display_name || modelsStore.selectedModel?.name || '无' }}</p>
                <p><strong>活跃模型:</strong> {{ modelsStore.activeModels.length }}</p>
                <p><strong>加载状态:</strong> {{ modelsStore.isLoading ? '加载中' : '空闲' }}</p>
                <p><strong>测试状态:</strong> {{ modelsStore.isTesting ? '测试中' : '空闲' }}</p>

                <!-- 模型列表显示 -->
                <div v-if="modelsStore.activeModels.length > 0" class="model-list">
                  <p><strong>可用模型列表:</strong></p>
                  <el-select
                    v-model="selectedModelId"
                    placeholder="请选择一个模型"
                    style="width: 100%; margin-bottom: 10px;"
                    @change="handleModelSelect"
                  >
                    <el-option
                      v-for="model in modelsStore.activeModels"
                      :key="model.id"
                      :label="`${model.display_name || model.name} (${model.model_type})`"
                      :value="model.id"
                    >
                      <span style="float: left">{{ model.display_name || model.name }}</span>
                      <span style="float: right; color: #8492a6; font-size: 13px">{{ model.model_type }}</span>
                    </el-option>
                  </el-select>
                </div>

                <el-button-group>
                  <el-button @click="testFetchModels" :loading="modelsStore.isLoading">
                    获取模型
                  </el-button>
                  <el-button
                    @click="testSelectModel"
                    :disabled="modelsStore.activeModels.length === 0"
                  >
                    自动选择第一个
                  </el-button>
                </el-button-group>
              </div>
            </el-card>
          </el-col>

          <!-- 计费状态测试 -->
          <el-col :span="12">
            <el-card header="计费状态管理">
              <div class="store-test">
                <p><strong>总Token:</strong> {{ billingStore.totalTokensUsed }}</p>
                <p><strong>总成本:</strong> ${{ billingStore.totalCost.toFixed(4) }}</p>
                <p><strong>剩余余额:</strong> ${{ billingStore.remainingBalance.toFixed(2) }}</p>
                <p><strong>使用百分比:</strong> {{ billingStore.usagePercentage.toFixed(1) }}%</p>
                <p><strong>活跃告警:</strong> {{ billingStore.activeAlerts.length }}</p>
                
                <el-button-group>
                  <el-button @click="testFetchUsage" :loading="billingStore.isLoading">
                    获取使用量
                  </el-button>
                  <el-button @click="testGenerateReport" :loading="billingStore.isGeneratingReport">
                    生成报告
                  </el-button>
                </el-button-group>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
          <!-- UI状态测试 -->
          <el-col :span="24">
            <el-card header="UI状态管理">
              <div class="store-test">
                <el-row :gutter="20">
                  <el-col :span="6">
                    <p><strong>主题:</strong> {{ uiStore.currentTheme }}</p>
                    <p><strong>语言:</strong> {{ uiStore.language }}</p>
                    <p><strong>布局:</strong> {{ uiStore.layoutMode }}</p>
                  </el-col>
                  <el-col :span="6">
                    <p><strong>侧边栏:</strong> {{ uiStore.sidebarCollapsed ? '收起' : '展开' }}</p>
                    <p><strong>字体大小:</strong> {{ uiStore.fontSize }}px</p>
                    <p><strong>动画:</strong> {{ uiStore.animationsEnabled ? '启用' : '禁用' }}</p>
                  </el-col>
                  <el-col :span="6">
                    <p><strong>设备类型:</strong> {{ uiStore.isMobile ? '移动端' : uiStore.isTablet ? '平板' : '桌面端' }}</p>
                    <p><strong>窗口大小:</strong> {{ uiStore.windowSize.width }}x{{ uiStore.windowSize.height }}</p>
                    <p><strong>通知数:</strong> {{ uiStore.unreadNotifications.length }}</p>
                  </el-col>
                  <el-col :span="6">
                    <el-button-group>
                      <el-button @click="uiStore.toggleTheme()">切换主题</el-button>
                      <el-button @click="uiStore.toggleSidebar()">切换侧边栏</el-button>
                      <el-button @click="testNotification">测试通知</el-button>
                    </el-button-group>
                  </el-col>
                </el-row>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 错误显示 -->
        <el-row v-if="hasErrors" style="margin-top: 20px;">
          <el-col :span="24">
            <el-alert
              title="状态管理错误"
              type="error"
              :description="errorMessages"
              show-icon
              :closable="false"
            />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  useAuthStore,
  useChatStore,
  useModelsStore,
  useBillingStore,
  useUIStore
} from '@/stores'

// 使用stores
const authStore = useAuthStore()
const chatStore = useChatStore()
const modelsStore = useModelsStore()
const billingStore = useBillingStore()
const uiStore = useUIStore()

// 响应式数据
const selectedModelId = ref<string>('')

// 功能标签类型映射
const getCapabilityTagType = (capability: string): string => {
  const typeMap: Record<string, string> = {
    'chat': 'primary',
    'completion': 'success',
    'reasoning': 'warning',
    'code': 'info',
    'image': 'danger',
    'audio': 'warning',
    'video': 'danger',
    'embedding': 'info',
    'function_calling': 'success'
  }
  return typeMap[capability.toLowerCase()] || 'default'
}

// 功能显示名称映射
const getCapabilityDisplayName = (capability: string): string => {
  const nameMap: Record<string, string> = {
    'chat': '对话',
    'completion': '文本补全',
    'reasoning': '推理',
    'code': '代码',
    'image': '图像',
    'audio': '音频',
    'video': '视频',
    'embedding': '向量化',
    'function_calling': '函数调用'
  }
  return nameMap[capability.toLowerCase()] || capability
}

// 计算属性
const hasErrors = computed(() => {
  return !!(authStore.lastError || chatStore.lastError || modelsStore.lastError || billingStore.lastError)
})

const errorMessages = computed(() => {
  const errors = [
    authStore.lastError,
    chatStore.lastError,
    modelsStore.lastError,
    billingStore.lastError
  ].filter(Boolean)
  return errors.join('; ')
})

// 测试方法
const testLogin = async () => {
  try {
    console.log('开始登录测试...')
    const success = await authStore.login({
      username: 'admin',
      password: 'admin123'
    })

    console.log('登录结果:', success)
    console.log('认证状态:', authStore.isAuthenticated)
    console.log('用户信息:', authStore.user)
    console.log('Token:', authStore.token)

    if (success) {
      console.log('登录成功！')
    } else {
      console.log('登录失败！')
    }
  } catch (error) {
    console.error('登录测试失败:', error)
  }
}

const testLogout = async () => {
  await authStore.logout()
}

const testCreateConversation = async () => {
  try {
    // 检查是否已选择模型
    if (!modelsStore.selectedModel) {
      console.warn('请先选择一个聊天模型')
      uiStore.addNotification({
        type: 'warning',
        title: '提示',
        message: '请先在模型管理中选择一个聊天模型',
        duration: 3000
      })
      return
    }

    await chatStore.createConversation({
      title: '测试对话',
      initial_message: '你好，这是一个测试消息',
      model_id: modelsStore.selectedModel.id
    })
  } catch (error) {
    console.error('创建对话失败:', error)
  }
}

const testSendMessage = async () => {
  // 检查是否已选择模型
  if (!modelsStore.selectedModel) {
    console.warn('请先选择一个聊天模型')
    uiStore.addNotification({
      type: 'warning',
      title: '提示',
      message: '请先在模型管理中选择一个聊天模型',
      duration: 3000
    })
    return
  }

  if (!chatStore.currentConversationId) {
    await testCreateConversation()
  }

  try {
    await chatStore.sendMessage({
      content: '这是一条测试消息',
      conversation_id: chatStore.currentConversationId!,
      model_id: modelsStore.selectedModel.id
    })
  } catch (error) {
    console.error('发送消息失败:', error)
  }
}

const testFetchModels = async () => {
  try {
    await modelsStore.fetchAvailableModels()
  } catch (error) {
    console.error('获取模型失败:', error)
  }
}

// 处理下拉选择模型
const handleModelSelect = (modelId: string) => {
  console.log('用户选择模型ID:', modelId)

  if (modelId) {
    const success = modelsStore.selectModel(modelId)
    console.log('选择模型结果:', success)
    console.log('当前选中模型ID:', modelsStore.selectedModelId)
    console.log('当前选中模型对象:', modelsStore.selectedModel)

    const selectedModel = modelsStore.activeModels.find(m => m.id === modelId)

    if (success && selectedModel) {
      uiStore.addNotification({
        type: 'success',
        title: '模型选择成功',
        message: `已选择模型: ${selectedModel.display_name || selectedModel.name}`,
        duration: 3000
      })
    } else {
      uiStore.addNotification({
        type: 'error',
        title: '模型选择失败',
        message: '模型可能不可用或状态异常',
        duration: 3000
      })
    }
  }
}

// 自动选择第一个活跃模型（保留原有功能）
const testSelectModel = () => {
  console.log('自动选择第一个活跃模型...')
  console.log('活跃模型数量:', modelsStore.activeModels.length)
  console.log('活跃模型列表:', modelsStore.activeModels)

  if (modelsStore.activeModels.length > 0) {
    const firstActiveModel = modelsStore.activeModels[0]
    console.log('选择第一个活跃模型:', firstActiveModel)

    // 更新下拉选择框的值
    selectedModelId.value = firstActiveModel.id

    // 调用选择处理函数
    handleModelSelect(firstActiveModel.id)
  } else {
    console.warn('没有活跃的模型')
    uiStore.addNotification({
      type: 'warning',
      title: '无活跃模型',
      message: '请先获取模型列表，或检查模型激活状态',
      duration: 3000
    })
  }
}

const testFetchUsage = async () => {
  try {
    await billingStore.fetchCurrentUsage()
  } catch (error) {
    console.error('获取使用量失败:', error)
  }
}

const testGenerateReport = async () => {
  try {
    const today = new Date().toISOString().split('T')[0]
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    await billingStore.generateReport(lastWeek, today, 'summary')
  } catch (error) {
    console.error('生成报告失败:', error)
  }
}

const testNotification = () => {
  uiStore.addNotification({
    type: 'success',
    title: '测试通知',
    message: '这是一个测试通知消息',
    duration: 3000
  })
}

// 初始化UI和认证状态
uiStore.initialize()
authStore.initializeAuth()

// 输出初始状态用于调试
console.log('页面加载时的认证状态:')
console.log('isAuthenticated:', authStore.isAuthenticated)
console.log('user:', authStore.user)
console.log('token:', authStore.token)
</script>

<style scoped>
.test-stores-view {
  padding: 20px;
}

.store-test {
  min-height: 200px;
}

.store-test p {
  margin: 8px 0;
  font-size: 14px;
}

.el-button-group {
  margin-top: 15px;
}

.el-button-group .el-button {
  margin-right: 0;
}

.model-warning, .model-info {
  margin: 10px 0;
}

.model-warning .el-alert {
  margin-bottom: 10px;
}

.model-info .el-alert {
  margin-bottom: 10px;
}

.model-list {
  margin: 15px 0;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.model-list p {
  margin-bottom: 8px;
  font-weight: 500;
}

/* 模型详情样式 */
.model-details {
  margin-top: 8px;
}

.model-description {
  margin: 8px 0;
  color: #606266;
  line-height: 1.4;
}

.model-capabilities {
  margin: 10px 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.capability-tag {
  margin: 0 4px 4px 0;
}

.no-capabilities {
  color: #909399;
  font-style: italic;
  margin-left: 8px;
}


</style>
