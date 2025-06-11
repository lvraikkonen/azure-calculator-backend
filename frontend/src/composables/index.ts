/**
 * Composables 入口文件
 * 统一导出所有组合式函数
 */

// 认证相关
export { useAuth } from './useAuth'

// 聊天相关
export { useChat } from './useChat'

// 模型管理
export { useModels } from './useModels'

// 计费管理
export { useBilling } from './useBilling'

// 主题和UI
export { useTheme } from './useTheme'

// 通知管理
export { useNotification } from './useNotification'
export type { NotificationType, NotificationOptions } from './useNotification'

// 权限控制
export { usePermission } from './usePermission'
export type { PermissionRule, RolePermissions } from './usePermission'

// 表单验证
export { useValidation } from './useValidation'
export type { ValidationRule, FieldValidation, FormValidation } from './useValidation'

// WebSocket通信
export { useWebSocket } from './useWebSocket'
export type { WebSocketMessage, WebSocketOptions } from './useWebSocket'

/**
 * 组合式函数使用指南
 * 
 * 1. useAuth - 认证管理
 *    - 登录/登出逻辑
 *    - 权限检查
 *    - 路由守卫
 *    - Token管理
 * 
 * 2. useChat - 聊天功能
 *    - 对话管理
 *    - 消息发送
 *    - 模型选择
 *    - 输入处理
 * 
 * 3. useModels - 模型管理
 *    - 模型选择
 *    - 性能测试
 *    - 配置管理
 *    - 推荐算法
 * 
 * 4. useBilling - 计费管理
 *    - 使用统计
 *    - 成本计算
 *    - 报告生成
 *    - 告警监控
 * 
 * 5. useTheme - 主题管理
 *    - 主题切换
 *    - 布局控制
 *    - 响应式设计
 *    - 用户偏好
 * 
 * 6. useNotification - 通知系统
 *    - 消息提示
 *    - 错误处理
 *    - 进度反馈
 *    - 用户交互
 * 
 * 7. usePermission - 权限控制
 *    - 角色管理
 *    - 功能权限
 *    - 路由保护
 *    - 操作授权
 * 
 * 8. useValidation - 表单验证
 *    - 字段验证
 *    - 规则定义
 *    - 错误处理
 *    - 提交控制
 * 
 * 9. useWebSocket - 实时通信
 *    - 连接管理
 *    - 消息处理
 *    - 状态同步
 *    - 错误恢复
 */
