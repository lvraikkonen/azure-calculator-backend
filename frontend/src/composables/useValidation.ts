import { ref, computed, reactive } from 'vue'
import { useNotification } from './useNotification'

export interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  email?: boolean
  url?: boolean
  number?: boolean
  integer?: boolean
  positive?: boolean
  custom?: (value: any) => boolean | string
  message?: string
}

export interface FieldValidation {
  value: any
  rules: ValidationRule[]
  error: string | null
  touched: boolean
  valid: boolean
}

export interface FormValidation {
  [fieldName: string]: FieldValidation
}

/**
 * 表单验证相关的组合式函数
 * 提供完整的表单验证解决方案
 */
export function useValidation() {
  const { validation: notify } = useNotification()

  // 表单状态
  const form = reactive<FormValidation>({})
  const isValidating = ref(false)
  const submitAttempted = ref(false)

  // 计算属性
  const isFormValid = computed(() => {
    return Object.values(form).every(field => field.valid)
  })

  const hasErrors = computed(() => {
    return Object.values(form).some(field => field.error !== null)
  })

  const touchedFields = computed(() => {
    return Object.values(form).filter(field => field.touched)
  })

  const errorCount = computed(() => {
    return Object.values(form).filter(field => field.error !== null).length
  })

  // 预定义验证规则
  const rules = {
    required: (message = '此字段为必填项'): ValidationRule => ({
      required: true,
      message
    }),

    minLength: (min: number, message?: string): ValidationRule => ({
      minLength: min,
      message: message || `最少需要${min}个字符`
    }),

    maxLength: (max: number, message?: string): ValidationRule => ({
      maxLength: max,
      message: message || `最多允许${max}个字符`
    }),

    email: (message = '请输入有效的邮箱地址'): ValidationRule => ({
      email: true,
      message
    }),

    url: (message = '请输入有效的URL地址'): ValidationRule => ({
      url: true,
      message
    }),

    number: (message = '请输入有效的数字'): ValidationRule => ({
      number: true,
      message
    }),

    integer: (message = '请输入整数'): ValidationRule => ({
      integer: true,
      message
    }),

    positive: (message = '请输入正数'): ValidationRule => ({
      positive: true,
      message
    }),

    range: (min: number, max: number, message?: string): ValidationRule => ({
      min,
      max,
      message: message || `值必须在${min}到${max}之间`
    }),

    pattern: (regex: RegExp, message = '格式不正确'): ValidationRule => ({
      pattern: regex,
      message
    }),

    custom: (validator: (value: any) => boolean | string, message = '验证失败'): ValidationRule => ({
      custom: validator,
      message
    }),

    // 常用模式
    username: (): ValidationRule[] => [
      rules.required(),
      rules.minLength(3),
      rules.maxLength(20),
      rules.pattern(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线')
    ],

    password: (): ValidationRule[] => [
      rules.required(),
      rules.minLength(8),
      rules.pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, '密码必须包含大小写字母和数字')
    ],

    phone: (): ValidationRule[] => [
      rules.required(),
      rules.pattern(/^1[3-9]\d{9}$/, '请输入有效的手机号码')
    ],

    idCard: (): ValidationRule[] => [
      rules.required(),
      rules.pattern(/^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/, '请输入有效的身份证号码')
    ]
  }

  // 添加字段
  const addField = (
    fieldName: string,
    initialValue: any = '',
    validationRules: ValidationRule[] = []
  ): void => {
    form[fieldName] = {
      value: initialValue,
      rules: validationRules,
      error: null,
      touched: false,
      valid: true
    }
  }

  // 移除字段
  const removeField = (fieldName: string): void => {
    delete form[fieldName]
  }

  // 设置字段值
  const setFieldValue = (fieldName: string, value: any): void => {
    if (form[fieldName]) {
      form[fieldName].value = value
      validateField(fieldName)
    }
  }

  // 设置字段为已触摸
  const touchField = (fieldName: string): void => {
    if (form[fieldName]) {
      form[fieldName].touched = true
    }
  }

  // 验证单个字段
  const validateField = (fieldName: string): boolean => {
    const field = form[fieldName]
    if (!field) return true

    const { value, rules } = field
    
    for (const rule of rules) {
      const error = validateValue(value, rule)
      if (error) {
        field.error = error
        field.valid = false
        return false
      }
    }

    field.error = null
    field.valid = true
    return true
  }

  // 验证值
  const validateValue = (value: any, rule: ValidationRule): string | null => {
    // 必填验证
    if (rule.required && (value === null || value === undefined || value === '')) {
      return rule.message || '此字段为必填项'
    }

    // 如果值为空且不是必填，跳过其他验证
    if (value === null || value === undefined || value === '') {
      return null
    }

    // 最小值验证
    if (rule.min !== undefined && Number(value) < rule.min) {
      return rule.message || `值不能小于${rule.min}`
    }

    // 最大值验证
    if (rule.max !== undefined && Number(value) > rule.max) {
      return rule.message || `值不能大于${rule.max}`
    }

    // 最小长度验证
    if (rule.minLength !== undefined && String(value).length < rule.minLength) {
      return rule.message || `最少需要${rule.minLength}个字符`
    }

    // 最大长度验证
    if (rule.maxLength !== undefined && String(value).length > rule.maxLength) {
      return rule.message || `最多允许${rule.maxLength}个字符`
    }

    // 邮箱验证
    if (rule.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(String(value))) {
        return rule.message || '请输入有效的邮箱地址'
      }
    }

    // URL验证
    if (rule.url) {
      try {
        new URL(String(value))
      } catch {
        return rule.message || '请输入有效的URL地址'
      }
    }

    // 数字验证
    if (rule.number && isNaN(Number(value))) {
      return rule.message || '请输入有效的数字'
    }

    // 整数验证
    if (rule.integer && !Number.isInteger(Number(value))) {
      return rule.message || '请输入整数'
    }

    // 正数验证
    if (rule.positive && Number(value) <= 0) {
      return rule.message || '请输入正数'
    }

    // 正则表达式验证
    if (rule.pattern && !rule.pattern.test(String(value))) {
      return rule.message || '格式不正确'
    }

    // 自定义验证
    if (rule.custom) {
      const result = rule.custom(value)
      if (result !== true) {
        return typeof result === 'string' ? result : (rule.message || '验证失败')
      }
    }

    return null
  }

  // 验证整个表单
  const validateForm = (): boolean => {
    isValidating.value = true
    let isValid = true

    for (const fieldName in form) {
      const fieldValid = validateField(fieldName)
      if (!fieldValid) {
        isValid = false
      }
    }

    isValidating.value = false
    return isValid
  }

  // 重置表单
  const resetForm = (): void => {
    for (const fieldName in form) {
      const field = form[fieldName]
      field.error = null
      field.touched = false
      field.valid = true
    }
    submitAttempted.value = false
  }

  // 重置字段
  const resetField = (fieldName: string): void => {
    const field = form[fieldName]
    if (field) {
      field.error = null
      field.touched = false
      field.valid = true
    }
  }

  // 清除错误
  const clearErrors = (): void => {
    for (const fieldName in form) {
      form[fieldName].error = null
    }
  }

  // 清除字段错误
  const clearFieldError = (fieldName: string): void => {
    if (form[fieldName]) {
      form[fieldName].error = null
    }
  }

  // 设置字段错误
  const setFieldError = (fieldName: string, error: string): void => {
    if (form[fieldName]) {
      form[fieldName].error = error
      form[fieldName].valid = false
    }
  }

  // 获取字段值
  const getFieldValue = (fieldName: string): any => {
    return form[fieldName]?.value
  }

  // 获取表单值
  const getFormValues = (): Record<string, any> => {
    const values: Record<string, any> = {}
    for (const fieldName in form) {
      values[fieldName] = form[fieldName].value
    }
    return values
  }

  // 设置表单值
  const setFormValues = (values: Record<string, any>): void => {
    for (const fieldName in values) {
      if (form[fieldName]) {
        form[fieldName].value = values[fieldName]
      }
    }
  }

  // 提交表单
  const submitForm = async (
    onSubmit: (values: Record<string, any>) => Promise<void> | void
  ): Promise<boolean> => {
    submitAttempted.value = true
    
    // 标记所有字段为已触摸
    for (const fieldName in form) {
      touchField(fieldName)
    }

    // 验证表单
    const isValid = validateForm()

    if (!isValid) {
      notify.invalid('表单验证', '请检查并修正表单中的错误')
      return false
    }

    try {
      await onSubmit(getFormValues())
      notify.success()
      return true
    } catch (error) {
      notify.invalid('提交失败', error instanceof Error ? error.message : '提交表单时发生错误')
      return false
    }
  }

  // 批量添加字段
  const addFields = (fields: Record<string, {
    value?: any
    rules?: ValidationRule[]
  }>): void => {
    for (const [fieldName, config] of Object.entries(fields)) {
      addField(fieldName, config.value, config.rules || [])
    }
  }

  return {
    // 状态
    form,
    isValidating,
    submitAttempted,
    
    // 计算属性
    isFormValid,
    hasErrors,
    touchedFields,
    errorCount,
    
    // 规则
    rules,
    
    // 字段管理
    addField,
    removeField,
    addFields,
    
    // 值管理
    setFieldValue,
    getFieldValue,
    setFormValues,
    getFormValues,
    
    // 验证
    validateField,
    validateForm,
    validateValue,
    
    // 状态管理
    touchField,
    resetForm,
    resetField,
    clearErrors,
    clearFieldError,
    setFieldError,
    
    // 表单提交
    submitForm
  }
}
