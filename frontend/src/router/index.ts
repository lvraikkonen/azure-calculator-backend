import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
