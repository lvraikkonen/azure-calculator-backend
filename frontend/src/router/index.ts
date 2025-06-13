import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue')
  },
  {
    path: '/test-stores',
    name: 'TestStores',
    component: () => import('@/views/TestStoresView.vue')
  },
  {
    path: '/debug-auth',
    name: 'DebugAuth',
    component: () => import('@/views/DebugAuthView.vue')
  },
  {
    path: '/test-composables',
    name: 'TestComposables',
    component: () => import('@/views/TestComposablesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 确保认证状态已初始化
  if (!authStore.isAuthenticated) {
    authStore.initializeAuth()
  }

  console.log('🛡️ 路由守卫检查:', {
    path: to.path,
    requiresAuth: to.meta.requiresAuth,
    isAuthenticated: authStore.isAuthenticated,
    hasUser: !!authStore.user,
    hasToken: !!authStore.token
  })

  // 检查路由是否需要认证
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    console.log('🚫 未登录用户访问受保护路由，重定向到登录页面')
    // 未登录用户重定向到登录页面，并保存原始路径
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } else {
    console.log('✅ 路由访问允许')
    next()
  }
})

export default router
