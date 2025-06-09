# Vue 3 + TypeScript + Vite 前端开发指令文档

> **目标**: 为AI对话系统构建企业级前端应用  
> **技术栈**: Vue 3.4+ + TypeScript 5.3+ + Vite 5.0+  
> **开发模式**: Composition API + `<script setup>`  

## 📋 项目概述

### 核心功能需求
- **用户认证系统**: 支持LDAP和本地登录
- **实时聊天界面**: 支持多模型对话、RAG增强
- **对话管理**: 历史记录、搜索、导出功能
- **模型管理**: 模型选择、参数配置、性能监控
- **管理后台**: 用户管理、系统配置、数据可视化
- **响应式设计**: 支持桌面端、平板、移动端

### 技术架构要求
```json
{
  "framework": "Vue 3.4+",
  "language": "TypeScript 5.3+",
  "buildTool": "Vite 5.0+",
  "stateManagement": "Pinia 2.1+",
  "router": "Vue Router 4.2+",
  "uiFramework": "Element Plus 2.4+",
  "styling": "UnoCSS 0.58+",
  "httpClient": "Axios 1.6+ + VueUse 10.7+",
  "testing": "Vitest 1.0+ + Vue Test Utils 2.4+",
  "codeQuality": "ESLint 8+ + Prettier 3+ + Husky 8+"
}
```

## 🏗️ 项目结构规范

### 完整目录结构
```
ai-chat-frontend/
├── public/                          # 静态资源
│   ├── favicon.ico
│   └── robots.txt
├── src/
│   ├── components/                  # 组件库
│   │   ├── base/                   # 基础组件（原子级）
│   │   │   ├── Button/
│   │   │   │   ├── index.vue
│   │   │   │   ├── types.ts
│   │   │   │   └── Button.test.ts
│   │   │   ├── Input/
│   │   │   ├── Modal/
│   │   │   ├── Loading/
│   │   │   └── index.ts            # 统一导出
│   │   ├── business/               # 业务组件（分子级）
│   │   │   ├── ChatMessage/
│   │   │   │   ├── index.vue
│   │   │   │   ├── types.ts
│   │   │   │   └── components/     # 子组件
│   │   │   ├── ModelSelector/
│   │   │   ├── UserAvatar/
│   │   │   ├── ConversationList/
│   │   │   └── index.ts
│   │   └── layout/                 # 布局组件（有机体）
│   │       ├── AppHeader/
│   │       ├── AppSidebar/
│   │       ├── AppFooter/
│   │       ├── AppLayout/
│   │       └── index.ts
│   ├── views/                      # 页面视图
│   │   ├── auth/
│   │   │   ├── LoginView.vue
│   │   │   ├── RegisterView.vue
│   │   │   └── components/
│   │   ├── chat/
│   │   │   ├── ChatView.vue
│   │   │   ├── components/
│   │   │   │   ├── ChatSidebar.vue
│   │   │   │   ├── ChatHeader.vue
│   │   │   │   ├── ChatMessages.vue
│   │   │   │   └── ChatInput.vue
│   │   │   └── composables/
│   │   │       └── useChat.ts
│   │   ├── admin/
│   │   │   ├── DashboardView.vue
│   │   │   ├── UserManageView.vue
│   │   │   ├── ModelManageView.vue
│   │   │   └── components/
│   │   └── error/
│   │       ├── 404View.vue
│   │       └── 500View.vue
│   ├── composables/                # 组合式函数
│   │   ├── useAuth.ts             # 认证逻辑
│   │   ├── useChat.ts             # 聊天逻辑
│   │   ├── useWebSocket.ts        # WebSocket连接
│   │   ├── useTheme.ts            # 主题切换
│   │   ├── usePermission.ts       # 权限控制
│   │   └── useApi.ts              # API调用封装
│   ├── stores/                     # Pinia状态管理
│   │   ├── auth.ts                # 认证状态
│   │   ├── chat.ts                # 聊天状态
│   │   ├── models.ts              # 模型状态
│   │   ├── ui.ts                  # UI状态
│   │   └── index.ts               # 状态入口
│   ├── services/                   # API服务层
│   │   ├── api/
│   │   │   ├── auth.ts            # 认证API
│   │   │   ├── chat.ts            # 聊天API
│   │   │   ├── models.ts          # 模型API
│   │   │   ├── users.ts           # 用户API
│   │   │   └── admin.ts           # 管理API
│   │   ├── http.ts                # HTTP客户端
│   │   ├── websocket.ts           # WebSocket客户端
│   │   └── storage.ts             # 本地存储服务
│   ├── types/                      # TypeScript类型定义
│   │   ├── api.ts                 # API响应类型
│   │   ├── chat.ts                # 聊天相关类型
│   │   ├── user.ts                # 用户相关类型
│   │   ├── model.ts               # 模型相关类型
│   │   └── global.d.ts            # 全局类型声明
│   ├── utils/                      # 工具函数
│   │   ├── format.ts              # 格式化工具
│   │   ├── validation.ts          # 验证工具
│   │   ├── constants.ts           # 常量定义
│   │   ├── helpers.ts             # 辅助函数
│   │   └── index.ts               # 工具函数导出
│   ├── assets/                     # 静态资源
│   │   ├── styles/
│   │   │   ├── variables.css      # CSS变量
│   │   │   ├── global.css         # 全局样式
│   │   │   └── themes/            # 主题样式
│   │   ├── images/                # 图片资源
│   │   └── icons/                 # 图标资源
│   ├── router/                     # 路由配置
│   │   ├── index.ts               # 路由主文件
│   │   ├── guards.ts              # 路由守卫
│   │   └── routes/                # 路由模块
│   │       ├── auth.ts
│   │       ├── chat.ts
│   │       ├── admin.ts
│   │       └── index.ts
│   ├── plugins/                    # Vue插件
│   │   ├── element-plus.ts
│   │   ├── pinia.ts
│   │   ├── router.ts
│   │   └── index.ts
│   ├── App.vue                     # 根组件
│   └── main.ts                     # 应用入口
├── tests/                          # 测试文件
│   ├── components/
│   ├── utils/
│   ├── setup.ts                   # 测试配置
│   └── __mocks__/                 # Mock文件
├── docs/                          # 文档
│   ├── README.md
│   ├── CONTRIBUTING.md
│   └── API.md
├── .vscode/                       # VSCode配置
│   ├── settings.json
│   ├── extensions.json
│   └── launch.json
├── package.json
├── tsconfig.json
├── vite.config.ts
├── uno.config.ts
├── eslint.config.js
├── .prettierrc
├── .gitignore
└── README.md
```

## 📦 Phase 1: 项目初始化与配置

### 1.1 创建项目并安装依赖

```bash
# 创建Vue 3项目
npm create vue@latest ai-chat-frontend
cd ai-chat-frontend

# 核心依赖
npm install @vueuse/core element-plus @element-plus/icons-vue
npm install axios pinia vue-router@4
npm install @unocss/reset unocss

# 开发依赖
npm install -D @types/node @vitejs/plugin-vue-jsx
npm install -D unplugin-auto-import unplugin-vue-components
npm install -D vitest @vue/test-utils jsdom happy-dom
npm install -D eslint @vue/eslint-config-typescript
npm install -D prettier @vue/eslint-config-prettier
npm install -D husky lint-staged @commitlint/cli @commitlint/config-conventional
npm install -D sass
```

### 1.2 Vite配置文件

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import { resolve } from 'path'
import UnoCSS from 'unocss/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    vueJsx(),
    UnoCSS(),
    AutoImport({
      imports: [
        'vue',
        'vue-router',
        'pinia',
        '@vueuse/core'
      ],
      resolvers: [ElementPlusResolver()],
      dts: 'src/types/auto-imports.d.ts',
      eslintrc: {
        enabled: true
      }
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/types/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@views': resolve(__dirname, 'src/views'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@services': resolve(__dirname, 'src/services'),
      '@assets': resolve(__dirname, 'src/assets')
    }
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          ui: ['element-plus'],
          utils: ['axios', '@vueuse/core']
        }
      }
    }
  },
  test: {
    environment: 'happy-dom',
    setupFiles: ['tests/setup.ts']
  }
})
```

### 1.3 TypeScript配置

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@views/*": ["./src/views/*"],
      "@utils/*": ["./src/utils/*"],
      "@types/*": ["./src/types/*"],
      "@stores/*": ["./src/stores/*"],
      "@services/*": ["./src/services/*"],
      "@assets/*": ["./src/assets/*"]
    },
    "types": ["vite/client", "element-plus/global", "node"]
  },
  "include": [
    "src/**/*.ts",
    "src/**/*.d.ts",
    "src/**/*.tsx",
    "src/**/*.vue",
    "tests/**/*.ts"
  ],
  "exclude": ["node_modules", "dist"]
}
```

### 1.4 代码规范配置

```javascript
// eslint.config.js
import vue from 'eslint-plugin-vue'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import prettier from 'eslint-plugin-prettier'

export default [
  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        extraFileExtensions: ['.vue']
      }
    },
    plugins: {
      vue,
      '@typescript-eslint': typescript,
      prettier
    },
    rules: {
      // Vue规则
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'error',
      'vue/component-name-in-template-casing': ['error', 'PascalCase'],
      'vue/component-definition-name-casing': ['error', 'PascalCase'],
      'vue/prefer-import-from-vue': 'error',
      
      // TypeScript规则
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/explicit-function-return-type': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      
      // 通用规则
      'prefer-const': 'error',
      'no-var': 'error',
      'object-shorthand': 'error',
      'prefer-template': 'error'
    }
  }
]
```

```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "none",
  "printWidth": 100,
  "endOfLine": "lf",
  "vueIndentScriptAndStyle": true
}
```

### 1.5 Git Hooks配置

```json
// package.json 添加scripts
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix",
    "format": "prettier --write .",
    "type-check": "vue-tsc --noEmit",
    "prepare": "husky install"
  },
  "lint-staged": {
    "*.{js,ts,vue}": ["eslint --fix", "prettier --write"],
    "*.{css,scss,html,md}": ["prettier --write"]
  }
}
```

```bash
# .husky/pre-commit
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx lint-staged
```

## 🧩 Phase 2: 类型定义系统

### 2.1 API响应类型

```typescript
// src/types/api.ts
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface ApiError {
  code: number
  message: string
  details?: Record<string, any>
}

// 认证相关类型
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: string
  username: string
  full_name: string
  email: string
  is_active: boolean
  is_superuser: boolean
  groups?: string
  auth_source: 'local' | 'ldap'
  created_at: string
  last_login?: string
}
```

### 2.2 聊天相关类型

```typescript
// src/types/chat.ts
export interface ChatMessage {
  id: string
  conversation_id: string
  content: string
  role: 'user' | 'assistant'
  model_id?: string
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

export interface Conversation {
  id: string
  title: string
  user_id: string
  created_at: string
  updated_at: string
  last_message?: string
  message_count: number
}

export interface MessageCreate {
  content: string
  conversation_id?: string
  model_id?: string
  use_rag?: boolean
}

export interface ConversationSummary {
  id: string
  title: string
  last_message: string
  updated_at: string
  message_count: number
}
```

### 2.3 模型相关类型

```typescript
// src/types/model.ts
export interface ModelInfo {
  id: string
  name: string
  display_name: string
  description?: string
  model_type: string
  model_name: string
  capabilities: string[]
  input_price?: number
  output_price?: number
  max_tokens?: number
  is_active: boolean
  created_at: string
}

export interface ModelSelection {
  model_id: string
  parameters?: Record<string, any>
}

export interface ModelPerformance {
  model_id: string
  avg_response_time: number
  success_rate: number
  total_requests: number
  last_updated: string
}
```

## 🔧 Phase 3: 服务层实现

### 3.1 HTTP客户端封装

```typescript
// src/services/http.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@stores/auth'
import router from '@/router'
import type { ApiResponse, ApiError } from '@types/api'

class HttpClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.setupInterceptors()
  }

  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        const authStore = useAuthStore()
        if (authStore.token) {
          config.headers.Authorization = `Bearer ${authStore.token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        return response
      },
      (error) => {
        if (error.response) {
          const { status, data } = error.response
          
          switch (status) {
            case 401:
              const authStore = useAuthStore()
              authStore.logout()
              router.push('/login')
              ElMessage.error('登录已过期，请重新登录')
              break
            case 403:
              ElMessage.error('权限不足')
              break
            case 404:
              ElMessage.error('请求的资源不存在')
              break
            case 500:
              ElMessage.error('服务器内部错误')
              break
            default:
              ElMessage.error(data?.message || '请求失败')
          }
        } else if (error.request) {
          ElMessage.error('网络连接失败')
        } else {
          ElMessage.error('请求配置错误')
        }

        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url, config)
    return response.data.data
  }

  async post<T, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async put<T, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config)
    return response.data.data
  }

  // 文件上传
  async upload<T>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    const config: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }

    if (onProgress) {
      config.onUploadProgress = (progressEvent) => {
        const progress = Math.round(
          (progressEvent.loaded * 100) / (progressEvent.total || 1)
        )
        onProgress(progress)
      }
    }

    const response = await this.instance.post<ApiResponse<T>>(url, formData, config)
    return response.data.data
  }
}

export const httpClient = new HttpClient()
```

### 3.2 API服务实现

```typescript
// src/services/api/auth.ts
import { httpClient } from '@services/http'
import type { LoginRequest, LoginResponse, UserInfo } from '@types/api'

export class AuthAPI {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '登录失败')
    }

    return response.json()
  }

  async getCurrentUser(): Promise<UserInfo> {
    return httpClient.get<UserInfo>('/auth/me')
  }

  async register(userData: {
    username: string
    email: string
    password: string
    full_name?: string
  }): Promise<UserInfo> {
    return httpClient.post<UserInfo>('/auth/register', userData)
  }

  async logout(): Promise<void> {
    // 这里可以调用后端登出接口（如果有的话）
    return Promise.resolve()
  }
}

export const authAPI = new AuthAPI()
```

```typescript
// src/services/api/chat.ts
import { httpClient } from '@services/http'
import type {
  ChatMessage,
  Conversation,
  ConversationSummary,
  MessageCreate
} from '@types/chat'

export class ChatAPI {
  async sendMessage(message: MessageCreate): Promise<ChatMessage> {
    return httpClient.post<ChatMessage>('/chat/messages/', message)
  }

  async getConversations(): Promise<ConversationSummary[]> {
    return httpClient.get<ConversationSummary[]>('/chat/conversations/')
  }

  async getConversation(id: string): Promise<Conversation & { messages: ChatMessage[] }> {
    return httpClient.get<Conversation & { messages: ChatMessage[] }>(`/chat/conversations/${id}`)
  }

  async updateConversationTitle(id: string, title: string): Promise<void> {
    return httpClient.patch<void>(`/chat/conversations/${id}`, { title })
  }

  async deleteConversation(id: string): Promise<void> {
    return httpClient.delete<void>(`/chat/conversations/${id}`)
  }

  async addFeedback(messageId: string, feedback: {
    feedback_type: 'like' | 'dislike'
    comment?: string
  }): Promise<void> {
    return httpClient.post<void>('/chat/feedback/', {
      message_id: messageId,
      ...feedback
    })
  }
}

export const chatAPI = new ChatAPI()
```

```typescript
// src/services/api/models.ts
import { httpClient } from '@services/http'
import type { ModelInfo } from '@types/model'

export class ModelsAPI {
  async getAvailableModels(): Promise<ModelInfo[]> {
    return httpClient.get<ModelInfo[]>('/chat/models/')
  }

  async recommendOptimalModel(
    taskType: string = 'general',
    performanceRequirements?: Record<string, any>
  ): Promise<{
    recommended_model_id: string
    model_info: ModelInfo
    recommendation_reason: string
  }> {
    return httpClient.post('/chat/models/recommend', {
      task_type: taskType,
      performance_requirements: performanceRequirements
    })
  }
}

export const modelsAPI = new ModelsAPI()
```

### 3.3 WebSocket服务

```typescript
// src/services/websocket.ts
import { ElMessage } from 'element-plus'

export interface WebSocketMessage {
  type: 'message' | 'typing' | 'error' | 'connected' | 'disconnected'
  data: any
  timestamp: string
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Array<(data: any) => void>> = new Map()

  constructor(url: string) {
    this.url = url
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectAttempts = 0
          this.emit('connected', {})
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.emit(message.type, message.data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = () => {
          console.log('WebSocket disconnected')
          this.emit('disconnected', {})
          this.handleReconnect()
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.emit('error', { error })
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      
      setTimeout(() => {
        this.connect().catch((error) => {
          console.error('Reconnection failed:', error)
        })
      }, this.reconnectDelay * this.reconnectAttempts)
    } else {
      ElMessage.error('WebSocket connection failed after multiple attempts')
    }
  }

  send(type: string, data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type,
        data,
        timestamp: new Date().toISOString()
      }
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  on(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)
  }

  off(event: string, callback: (data: any) => void): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      const index = eventListeners.indexOf(callback)
      if (index > -1) {
        eventListeners.splice(index, 1)
      }
    }
  }

  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.forEach(callback => callback(data))
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}
```

## 🗃️ Phase 4: 状态管理（Pinia）

### 4.1 认证状态管理

```typescript
// src/stores/auth.ts
import { defineStore } from 'pinia'
import { authAPI } from '@services/api/auth'
import type { UserInfo, LoginRequest } from '@types/api'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<UserInfo | null>(null)
  const token = ref<string | null>(null)
  const isLoading = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_superuser || false)
  const userRoles = computed(() => {
    if (!user.value?.groups) return []
    return user.value.groups.split(',').map(role => role.trim())
  })

  // 动作
  const login = async (credentials: LoginRequest): Promise<void> => {
    isLoading.value = true
    try {
      const response = await authAPI.login(credentials)
      token.value = response.access_token
      
      // 获取用户信息
      user.value = await authAPI.getCurrentUser()
      
      // 持久化存储
      localStorage.setItem('auth_token', token.value)
      
      ElMessage.success('登录成功')
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const logout = async (): Promise<void> => {
    try {
      await authAPI.logout()
    } catch (error) {
      console.warn('Logout API call failed:', error)
    } finally {
      // 清除状态
      user.value = null
      token.value = null
      localStorage.removeItem('auth_token')
      
      ElMessage.success('已安全登出')
    }
  }

  const initializeAuth = async (): Promise<void> => {
    const savedToken = localStorage.getItem('auth_token')
    if (savedToken) {
      token.value = savedToken
      try {
        user.value = await authAPI.getCurrentUser()
      } catch (error) {
        // Token无效，清除状态
        logout()
        throw error
      }
    }
  }

  const updateUserInfo = async (): Promise<void> => {
    if (!token.value) return
    
    try {
      user.value = await authAPI.getCurrentUser()
    } catch (error) {
      console.error('Failed to update user info:', error)
    }
  }

  const hasPermission = (permission: string): boolean => {
    if (!user.value) return false
    if (user.value.is_superuser) return true
    
    // 这里可以根据实际权限系统进行调整
    return userRoles.value.includes(permission)
  }

  return {
    // 状态
    user: readonly(user),
    token: readonly(token),
    isLoading: readonly(isLoading),
    
    // 计算属性
    isAuthenticated,
    isAdmin,
    userRoles,
    
    // 动作
    login,
    logout,
    initializeAuth,
    updateUserInfo,
    hasPermission
  }
})
```

### 4.2 聊天状态管理

```typescript
// src/stores/chat.ts
import { defineStore } from 'pinia'
import { chatAPI } from '@services/api/chat'
import type {
  ChatMessage,
  Conversation,
  ConversationSummary,
  MessageCreate
} from '@types/chat'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const conversations = ref<ConversationSummary[]>([])
  const currentConversation = ref<(Conversation & { messages: ChatMessage[] }) | null>(null)
  const isLoading = ref(false)
  const isSending = ref(false)

  // 计算属性
  const currentMessages = computed(() => currentConversation.value?.messages || [])
  const hasConversations = computed(() => conversations.value.length > 0)

  // 动作
  const loadConversations = async (): Promise<void> => {
    isLoading.value = true
    try {
      conversations.value = await chatAPI.getConversations()
    } catch (error) {
      console.error('Failed to load conversations:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const loadConversation = async (id: string): Promise<void> => {
    isLoading.value = true
    try {
      currentConversation.value = await chatAPI.getConversation(id)
    } catch (error) {
      console.error('Failed to load conversation:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const sendMessage = async (messageData: MessageCreate): Promise<ChatMessage> => {
    isSending.value = true
    try {
      const message = await chatAPI.sendMessage(messageData)
      
      // 如果当前对话存在，添加消息
      if (currentConversation.value) {
        currentConversation.value.messages.push(message)
      }
      
      // 更新对话列表
      await loadConversations()
      
      return message
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    } finally {
      isSending.value = false
    }
  }

  const createConversation = async (title?: string): Promise<void> => {
    // 创建新对话就是发送第一条消息
    currentConversation.value = null
  }

  const updateConversationTitle = async (id: string, title: string): Promise<void> => {
    try {
      await chatAPI.updateConversationTitle(id, title)
      
      // 更新本地状态
      const conversation = conversations.value.find(conv => conv.id === id)
      if (conversation) {
        conversation.title = title
      }
      
      if (currentConversation.value && currentConversation.value.id === id) {
        currentConversation.value.title = title
      }
    } catch (error) {
      console.error('Failed to update conversation title:', error)
      throw error
    }
  }

  const deleteConversation = async (id: string): Promise<void> => {
    try {
      await chatAPI.deleteConversation(id)
      
      // 更新本地状态
      conversations.value = conversations.value.filter(conv => conv.id !== id)
      
      // 如果删除的是当前对话，清空当前对话
      if (currentConversation.value && currentConversation.value.id === id) {
        currentConversation.value = null
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      throw error
    }
  }

  const addMessageToCurrentConversation = (message: ChatMessage): void => {
    if (currentConversation.value) {
      currentConversation.value.messages.push(message)
    }
  }

  const clearCurrentConversation = (): void => {
    currentConversation.value = null
  }

  return {
    // 状态
    conversations: readonly(conversations),
    currentConversation: readonly(currentConversation),
    isLoading: readonly(isLoading),
    isSending: readonly(isSending),
    
    // 计算属性
    currentMessages,
    hasConversations,
    
    // 动作
    loadConversations,
    loadConversation,
    sendMessage,
    createConversation,
    updateConversationTitle,
    deleteConversation,
    addMessageToCurrentConversation,
    clearCurrentConversation
  }
})
```

### 4.3 模型状态管理

```typescript
// src/stores/models.ts
import { defineStore } from 'pinia'
import { modelsAPI } from '@services/api/models'
import type { ModelInfo } from '@types/model'

export const useModelsStore = defineStore('models', () => {
  // 状态
  const models = ref<ModelInfo[]>([])
  const selectedModel = ref<ModelInfo | null>(null)
  const isLoading = ref(false)
  const ragEnabled = ref(false)

  // 计算属性
  const availableModels = computed(() => models.value.filter(model => model.is_active))
  const hasSelectedModel = computed(() => !!selectedModel.value)

  // 动作
  const loadModels = async (): Promise<void> => {
    isLoading.value = true
    try {
      models.value = await modelsAPI.getAvailableModels()
      
      // 如果没有选中模型且有可用模型，自动选择第一个
      if (!selectedModel.value && availableModels.value.length > 0) {
        selectedModel.value = availableModels.value[0]
      }
    } catch (error) {
      console.error('Failed to load models:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const selectModel = (modelId: string): void => {
    const model = models.value.find(m => m.id === modelId)
    if (model) {
      selectedModel.value = model
      // 保存到本地存储
      localStorage.setItem('selected_model_id', modelId)
    }
  }

  const getOptimalModel = async (
    taskType: string = 'general',
    requirements?: Record<string, any>
  ): Promise<ModelInfo | null> => {
    try {
      const recommendation = await modelsAPI.recommendOptimalModel(taskType, requirements)
      return recommendation.model_info
    } catch (error) {
      console.error('Failed to get optimal model:', error)
      return null
    }
  }

  const toggleRag = (): void => {
    ragEnabled.value = !ragEnabled.value
    localStorage.setItem('rag_enabled', ragEnabled.value.toString())
  }

  const initializeModels = (): void => {
    // 恢复RAG状态
    const savedRagState = localStorage.getItem('rag_enabled')
    if (savedRagState !== null) {
      ragEnabled.value = savedRagState === 'true'
    }
    
    // 恢复选中的模型
    const savedModelId = localStorage.getItem('selected_model_id')
    if (savedModelId && models.value.length > 0) {
      const model = models.value.find(m => m.id === savedModelId)
      if (model) {
        selectedModel.value = model
      }
    }
  }

  return {
    // 状态
    models: readonly(models),
    selectedModel: readonly(selectedModel),
    isLoading: readonly(isLoading),
    ragEnabled: readonly(ragEnabled),
    
    // 计算属性
    availableModels,
    hasSelectedModel,
    
    // 动作
    loadModels,
    selectModel,
    getOptimalModel,
    toggleRag,
    initializeModels
  }
})
```

## 🎨 Phase 5: 组件库开发

### 5.1 基础组件

```vue
<!-- src/components/base/Button/index.vue -->
<template>
  <button
    :class="buttonClasses"
    :disabled="disabled || loading"
    :type="nativeType"
    @click="handleClick"
  >
    <el-icon v-if="loading" class="is-loading">
      <Loading />
    </el-icon>
    <el-icon v-else-if="icon" :size="iconSize">
      <component :is="icon" />
    </el-icon>
    <span v-if="$slots.default" class="button-text">
      <slot />
    </span>
  </button>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface ButtonProps {
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'text' | 'default'
  size?: 'large' | 'default' | 'small'
  disabled?: boolean
  loading?: boolean
  icon?: Component
  iconSize?: number
  round?: boolean
  circle?: boolean
  nativeType?: 'button' | 'submit' | 'reset'
}

interface ButtonEmits {
  click: [event: MouseEvent]
}

const props = withDefaults(defineProps<ButtonProps>(), {
  type: 'default',
  size: 'default',
  nativeType: 'button',
  iconSize: 16
})

const emit = defineEmits<ButtonEmits>()

const buttonClasses = computed(() => [
  'ai-button',
  `ai-button--${props.type}`,
  `ai-button--${props.size}`,
  {
    'is-disabled': props.disabled,
    'is-loading': props.loading,
    'is-round': props.round,
    'is-circle': props.circle,
    'is-icon-only': !$slots.default && props.icon
  }
])

const handleClick = (event: MouseEvent): void => {
  if (props.disabled || props.loading) return
  emit('click', event)
}
</script>

<style scoped>
.ai-button {
  @apply inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.ai-button--default {
  @apply text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 focus:ring-blue-500;
}

.ai-button--primary {
  @apply text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500;
}

.ai-button--success {
  @apply text-white bg-green-600 hover:bg-green-700 focus:ring-green-500;
}

.ai-button--warning {
  @apply text-white bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500;
}

.ai-button--danger {
  @apply text-white bg-red-600 hover:bg-red-700 focus:ring-red-500;
}

.ai-button--info {
  @apply text-white bg-gray-600 hover:bg-gray-700 focus:ring-gray-500;
}

.ai-button--text {
  @apply text-blue-600 bg-transparent hover:bg-blue-50 focus:ring-blue-500;
}

.ai-button--large {
  @apply px-6 py-3 text-base;
}

.ai-button--small {
  @apply px-3 py-1 text-xs;
}

.ai-button.is-round {
  @apply rounded-full;
}

.ai-button.is-circle {
  @apply rounded-full w-10 h-10 p-0;
}

.ai-button.is-disabled {
  @apply opacity-50 cursor-not-allowed;
}

.ai-button .is-loading {
  @apply animate-spin;
}

.button-text {
  @apply ml-2;
}

.ai-button.is-icon-only .button-text {
  @apply ml-0;
}
</style>
```

### 5.2 业务组件

```vue
<!-- src/components/business/ChatMessage/index.vue -->
<template>
  <div
    :class="messageClasses"
    class="chat-message"
  >
    <UserAvatar
      v-if="!isOwn && showAvatar"
      :user="message.user"
      class="message-avatar"
      size="small"
    />
    
    <div class="message-content">
      <div v-if="showHeader" class="message-header">
        <span class="message-author">{{ message.user?.name || 'AI助手' }}</span>
        <span class="message-time">{{ formatMessageTime(message.created_at) }}</span>
      </div>
      
      <div class="message-body">
        <MessageContent
          :content="message.content"
          :type="message.type || 'text'"
        />
      </div>
      
      <div v-if="showActions" class="message-actions">
        <el-button
          v-if="!isOwn"
          text
          size="small"
          @click="handleLike"
        >
          <el-icon><ThumbsUp /></el-icon>
        </el-button>
        <el-button
          text
          size="small"
          @click="handleCopy"
        >
          <el-icon><CopyDocument /></el-icon>
        </el-button>
        <el-button
          v-if="isOwn"
          text
          size="small"
          @click="handleEdit"
        >
          <el-icon><Edit /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@stores/auth'
import { chatAPI } from '@services/api/chat'
import type { ChatMessage } from '@types/chat'
import UserAvatar from '@components/business/UserAvatar/index.vue'
import MessageContent from './components/MessageContent.vue'

interface Props {
  message: ChatMessage
  showHeader?: boolean
  showActions?: boolean
  showAvatar?: boolean
}

interface Emits {
  edit: [message: ChatMessage]
  like: [messageId: string]
}

const props = withDefaults(defineProps<Props>(), {
  showHeader: true,
  showActions: true,
  showAvatar: true
})

const emit = defineEmits<Emits>()

const authStore = useAuthStore()

const isOwn = computed(() => props.message.role === 'user')

const messageClasses = computed(() => [
  'chat-message',
  {
    'chat-message--own': isOwn.value,
    'chat-message--other': !isOwn.value
  }
])

const formatMessageTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
  
  if (diffInMinutes < 1) {
    return '刚刚'
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes}分钟前`
  } else if (diffInMinutes < 1440) {
    return `${Math.floor(diffInMinutes / 60)}小时前`
  } else {
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

const handleLike = async (): Promise<void> => {
  try {
    await chatAPI.addFeedback(props.message.id, {
      feedback_type: 'like'
    })
    emit('like', props.message.id)
    ElMessage.success('已点赞')
  } catch (error) {
    ElMessage.error('点赞失败')
  }
}

const handleCopy = async (): Promise<void> => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleEdit = (): void => {
  emit('edit', props.message)
}
</script>

<style scoped>
.chat-message {
  @apply flex gap-3 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors;
}

.chat-message--own {
  @apply flex-row-reverse;
}

.chat-message--own .message-content {
  @apply items-end;
}

.message-content {
  @apply flex flex-col gap-2 max-w-[70%];
}

.message-header {
  @apply flex items-center gap-2 text-xs text-gray-500;
}

.chat-message--own .message-header {
  @apply flex-row-reverse;
}

.message-author {
  @apply font-medium;
}

.message-body {
  @apply bg-white dark:bg-gray-700 rounded-lg p-3 shadow-sm border border-gray-200 dark:border-gray-600;
}

.chat-message--own .message-body {
  @apply bg-blue-600 text-white border-blue-600;
}

.message-actions {
  @apply flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity;
}

.chat-message:hover .message-actions {
  @apply opacity-100;
}

.chat-message--own .message-actions {
  @apply flex-row-reverse;
}
</style>
```

## 📱 Phase 6: 页面视图开发

### 6.1 聊天主页面

```vue
<!-- src/views/chat/ChatView.vue -->
<template>
  <div class="chat-view">
    <AppLayout>
      <template #sidebar>
        <ChatSidebar />
      </template>
      
      <template #main>
        <div class="chat-main">
          <ChatHeader />
          <ChatMessages />
          <ChatInput />
        </div>
      </template>
    </AppLayout>
  </div>
</template>

<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import { useChat } from '@/composables/useChat'
import AppLayout from '@components/layout/AppLayout/index.vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatHeader from './components/ChatHeader.vue'
import ChatMessages from './components/ChatMessages.vue'
import ChatInput from './components/ChatInput.vue'

// 设置页面标题
useTitle('AI智能对话')

// 初始化聊天功能
const { initializeChat } = useChat()

onMounted(() => {
  initializeChat()
})
</script>

<style scoped>
.chat-view {
  @apply h-screen overflow-hidden;
}

.chat-main {
  @apply flex flex-col h-full;
}
</style>
```

### 6.2 聊天组合式函数

```typescript
// src/composables/useChat.ts
import { useChatStore } from '@stores/chat'
import { useModelsStore } from '@stores/models'
import { useWebSocket } from './useWebSocket'
import type { MessageCreate } from '@types/chat'

export const useChat = () => {
  const chatStore = useChatStore()
  const modelsStore = useModelsStore()
  
  // 解构响应式状态
  const {
    conversations,
    currentConversation,
    isLoading,
    isSending,
    currentMessages,
    hasConversations
  } = storeToRefs(chatStore)

  const {
    selectedModel,
    ragEnabled
  } = storeToRefs(modelsStore)

  // WebSocket连接
  const {
    connect: connectWebSocket,
    disconnect: disconnectWebSocket,
    isConnected,
    send: sendWebSocketMessage
  } = useWebSocket()

  // 发送消息
  const sendMessage = async (content: string): Promise<void> => {
    if (!content.trim() || !selectedModel.value) {
      throw new Error('消息内容不能为空或未选择模型')
    }

    const messageData: MessageCreate = {
      content,
      conversation_id: currentConversation.value?.id,
      model_id: selectedModel.value.id,
      use_rag: ragEnabled.value
    }

    try {
      await chatStore.sendMessage(messageData)
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  }

  // 切换对话
  const switchConversation = async (conversationId: string): Promise<void> => {
    try {
      await chatStore.loadConversation(conversationId)
    } catch (error) {
      console.error('Failed to switch conversation:', error)
      throw error
    }
  }

  // 创建新对话
  const createNewConversation = (): void => {
    chatStore.clearCurrentConversation()
  }

  // 删除对话
  const deleteConversation = async (conversationId: string): Promise<void> => {
    try {
      await chatStore.deleteConversation(conversationId)
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      throw error
    }
  }

  // 更新对话标题
  const updateConversationTitle = async (
    conversationId: string,
    title: string
  ): Promise<void> => {
    try {
      await chatStore.updateConversationTitle(conversationId, title)
    } catch (error) {
      console.error('Failed to update conversation title:', error)
      throw error
    }
  }

  // 初始化聊天功能
  const initializeChat = async (): Promise<void> => {
    try {
      // 加载模型列表
      await modelsStore.loadModels()
      modelsStore.initializeModels()
      
      // 加载对话列表
      await chatStore.loadConversations()
      
      // 连接WebSocket
      await connectWebSocket()
      
    } catch (error) {
      console.error('Failed to initialize chat:', error)
    }
  }

  // 清理资源
  const cleanup = (): void => {
    disconnectWebSocket()
  }

  // 监听WebSocket消息
  watchEffect(() => {
    // 这里可以处理实时消息
  })

  // 组件卸载时清理资源
  onUnmounted(() => {
    cleanup()
  })

  return {
    // 状态
    conversations,
    currentConversation,
    currentMessages,
    isLoading,
    isSending,
    hasConversations,
    selectedModel,
    ragEnabled,
    isConnected,
    
    // 方法
    sendMessage,
    switchConversation,
    createNewConversation,
    deleteConversation,
    updateConversationTitle,
    initializeChat,
    cleanup
  }
}
```

## 🧪 Phase 7: 测试实现

### 7.1 测试配置

```typescript
// tests/setup.ts
import { beforeAll, afterEach } from 'vitest'
import { cleanup } from '@vue/test-utils'

// 清理DOM
afterEach(() => {
  cleanup()
})

// 模拟localStorage
Object.defineProperty(window, 'localStorage', {
  value: {
    store: {} as Record<string, string>,
    getItem(key: string) {
      return this.store[key] || null
    },
    setItem(key: string, value: string) {
      this.store[key] = value
    },
    removeItem(key: string) {
      delete this.store[key]
    },
    clear() {
      this.store = {}
    }
  },
  writable: true
})

// 模拟fetch
global.fetch = vi.fn()

// 模拟clipboard API
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: vi.fn().mockResolvedValue(undefined)
  }
})
```

### 7.2 组件测试示例

```typescript
// tests/components/Button.test.ts
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from '@components/base/Button/index.vue'
import { Loading } from '@element-plus/icons-vue'

describe('Button Component', () => {
  it('renders with default props', () => {
    const wrapper = mount(Button, {
      slots: {
        default: 'Click me'
      }
    })

    expect(wrapper.text()).toContain('Click me')
    expect(wrapper.classes()).toContain('ai-button')
    expect(wrapper.classes()).toContain('ai-button--default')
  })

  it('renders different types correctly', () => {
    const wrapper = mount(Button, {
      props: {
        type: 'primary'
      }
    })

    expect(wrapper.classes()).toContain('ai-button--primary')
  })

  it('emits click event when clicked', async () => {
    const wrapper = mount(Button)
    
    await wrapper.trigger('click')
    
    expect(wrapper.emitted('click')).toBeTruthy()
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('does not emit click when disabled', async () => {
    const wrapper = mount(Button, {
      props: {
        disabled: true
      }
    })
    
    await wrapper.trigger('click')
    
    expect(wrapper.emitted('click')).toBeFalsy()
  })

  it('shows loading state correctly', () => {
    const wrapper = mount(Button, {
      props: {
        loading: true
      }
    })

    expect(wrapper.classes()).toContain('is-loading')
    expect(wrapper.findComponent(Loading).exists()).toBe(true)
    expect(wrapper.attributes('disabled')).toBeDefined()
  })

  it('renders icon when provided', () => {
    const MockIcon = {
      name: 'MockIcon',
      template: '<div>Icon</div>'
    }

    const wrapper = mount(Button, {
      props: {
        icon: MockIcon
      }
    })

    expect(wrapper.findComponent(MockIcon).exists()).toBe(true)
  })
})
```

## 🚀 Phase 8: 构建与部署配置

### 8.1 环境变量配置

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_APP_TITLE=AI智能对话系统（开发环境）
```

```bash
# .env.production
VITE_API_BASE_URL=/api/v1
VITE_WS_URL=wss://your-domain.com/ws
VITE_APP_TITLE=AI智能对话系统
```

### 8.2 Docker配置

```dockerfile
# Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# 复制package文件
COPY package*.json ./
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产环境
FROM nginx:alpine

# 复制构建结果
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;

        # Gzip压缩
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

        # SPA路由处理
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API代理
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # WebSocket代理
        location /ws {
            proxy_pass http://backend:8000/ws;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

## 📋 开发流程与规范

### 开发工作流
1. **功能开发**：从组件开始，自底向上开发
2. **测试驱动**：编写测试用例，确保功能正确性
3. **代码审查**：每个PR需要代码审查
4. **持续集成**：自动化测试和构建
5. **渐进部署**：先部署到测试环境，再到生产环境

### 代码提交规范
```bash
# 提交消息格式
<type>(<scope>): <description>

# 示例
feat(chat): add message streaming support
fix(auth): resolve token refresh issue
docs(readme): update installation guide
```

### 性能目标
- **首屏加载时间**: < 2s
- **路由切换时间**: < 500ms
- **组件渲染时间**: < 100ms
- **包体积大小**: < 1MB (gzipped)
- **Lighthouse评分**: > 90分

## ✅ 验收标准

### 功能验收
- [ ] 用户可以正常登录和登出
- [ ] 用户可以选择AI模型进行对话
- [ ] 用户可以创建、查看、删除对话
- [ ] 用户可以启用/禁用RAG功能
- [ ] 管理员可以管理用户和系统配置
- [ ] 响应式设计在各种设备上正常工作

### 技术验收
- [ ] 代码通过ESLint和TypeScript检查
- [ ] 单元测试覆盖率达到80%以上
- [ ] 所有页面Lighthouse评分90分以上
- [ ] 支持现代浏览器（Chrome 90+, Firefox 88+, Safari 14+）
- [ ] 构建产物大小符合要求

### 用户体验验收
- [ ] 界面美观，交互流畅
- [ ] 错误处理友好，有清晰的反馈
- [ ] 加载状态明确，无白屏现象
- [ ] 支持键盘导航和屏幕阅读器

---

**注意事项**：
1. 严格按照TypeScript类型定义进行开发
2. 所有组件必须包含完整的Props类型定义
3. 使用Composition API和`<script setup>`语法
4. 遵循Vue 3最佳实践和代码规范
5. 确保响应式设计和无障碍访问支持