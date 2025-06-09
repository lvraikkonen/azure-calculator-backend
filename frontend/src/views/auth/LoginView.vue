<template>
  <div class="login-view flex-center min-h-screen">
    <div class="card max-w-md w-full mx-4">
      <div class="text-center mb-6">
        <h2 class="text-2xl font-bold text-primary mb-2">用户登录</h2>
        <p class="text-secondary">请输入您的用户名和密码</p>
      </div>
      
      <el-form 
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-width="0"
        size="large"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            prefix-icon="User"
            clearable
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            show-password
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            class="w-full"
            :loading="isLoading"
            @click="handleLogin"
          >
            {{ isLoading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="text-center">
        <el-button link @click="goBack">
          返回首页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { authAPI, storage } from '@/services'
import type { LoginRequest } from '@/types'

const router = useRouter()
const loginFormRef = ref<FormInstance>()
const isLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ]
}

const handleLogin = async (): Promise<void> => {
  if (!loginFormRef.value) return

  try {
    const valid = await loginFormRef.value.validate()
    if (!valid) return

    isLoading.value = true

    // 使用认证服务进行登录
    const credentials: LoginRequest = {
      username: loginForm.username,
      password: loginForm.password
    }

    console.log('🔐 开始登录，凭据:', credentials)

    // 保存调试信息到localStorage
    const debugLog: string[] = []
    debugLog.push(`🔐 开始登录，用户名: ${credentials.username}`)

    const response = await authAPI.login(credentials)
    console.log('✅ 登录响应:', response)
    debugLog.push(`✅ 登录响应成功，token类型: ${response.token_type}`)

    // 验证token格式
    if (!response.access_token) {
      throw new Error('登录响应中缺少access_token')
    }

    console.log('💾 保存token:', response.access_token.substring(0, 20) + '...')
    debugLog.push(`💾 Token长度: ${response.access_token.length}`)
    debugLog.push(`💾 Token前缀: ${response.access_token.substring(0, 20)}...`)

    // 保存认证信息
    storage.setAuthToken(response.access_token)

    // 验证token是否正确保存
    const savedToken = storage.getAuthToken()
    console.log('🔍 验证保存的token:', savedToken?.substring(0, 20) + '...')
    debugLog.push(`🔍 保存验证: ${savedToken ? '成功' : '失败'}`)

    // 同时检查原生localStorage
    const rawToken = window.localStorage.getItem('auth_token')
    console.log('🔍 原生localStorage中的token:', rawToken?.substring(0, 20) + '...')
    debugLog.push(`🔍 原生localStorage: ${rawToken ? '存在' : '不存在'}`)

    // 获取用户信息
    console.log('👤 获取用户信息...')
    debugLog.push('👤 开始获取用户信息...')

    const userInfo = await authAPI.getCurrentUser()
    storage.setUserInfo(userInfo)
    debugLog.push(`👤 用户信息获取成功: ${userInfo.username}`)

    // 保存调试日志
    localStorage.setItem('login_debug_log', JSON.stringify(debugLog))

    ElMessage.success('登录成功！')
    console.log('✅ 登录成功，用户信息:', userInfo)
    console.log('🎉 登录流程完成，请查看上面的日志信息')

    // 临时注释跳转，方便查看日志
    // router.push('/')

    // 5秒后自动跳转
    setTimeout(() => {
      console.log('🔄 5秒后自动跳转到首页')
      router.push('/')
    }, 5000)
  } catch (error) {
    console.error('❌ 登录错误:', error)
    ElMessage.error(`登录失败: ${error instanceof Error ? error.message : '未知错误'}`)
  } finally {
    isLoading.value = false
  }
}

const goBack = (): void => {
  router.push('/')
}
</script>

<style scoped>
.login-view {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
