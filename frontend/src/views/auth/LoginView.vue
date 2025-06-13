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
import { ref, reactive, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { authAPI, storage } from '@/services'
import { useAuthStore } from '@/stores/auth'
import type { LoginRequest } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
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

    // 使用认证store进行登录
    const credentials: LoginRequest = {
      username: loginForm.username,
      password: loginForm.password
    }

    console.log('🔐 开始登录，凭据:', credentials)

    // 保存调试信息到localStorage
    const debugLog: string[] = []
    debugLog.push(`🔐 开始登录，用户名: ${credentials.username}`)

    // 通过认证store登录
    const loginSuccess = await authStore.login(credentials)

    if (!loginSuccess) {
      throw new Error('登录失败，请检查用户名和密码')
    }

    console.log('✅ 登录成功，认证状态已更新')
    debugLog.push(`✅ 登录成功，认证状态: ${authStore.isAuthenticated}`)
    debugLog.push(`👤 用户信息: ${authStore.user?.username}`)
    debugLog.push(`🔑 Token状态: ${authStore.token ? '已设置' : '未设置'}`)

    // 保存调试日志
    localStorage.setItem('login_debug_log', JSON.stringify(debugLog))

    ElMessage.success('登录成功！')
    console.log('✅ 登录成功，用户信息:', authStore.user)
    console.log('🎉 登录流程完成，认证状态已更新')

    // 获取重定向路径，如果没有则跳转到聊天页面
    const redirectPath = route.query.redirect as string || '/chat'
    console.log('🔄 登录成功，跳转到:', redirectPath)
    console.log('🔍 当前认证状态:', authStore.isAuthenticated)

    // 等待一下确保状态更新完成，然后跳转
    await nextTick()
    router.push(redirectPath)
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
