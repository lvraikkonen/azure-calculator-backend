import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify()
  ],
  shortcuts: [
    // 布局相关
    ['flex-center', 'flex items-center justify-center'],
    ['flex-between', 'flex items-center justify-between'],
    ['flex-col-center', 'flex flex-col items-center justify-center'],
    
    // 按钮样式
    ['btn-base', 'px-4 py-2 rounded-lg font-medium transition-all duration-200 cursor-pointer'],
    ['btn-primary', 'btn-base bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500'],
    ['btn-secondary', 'btn-base bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-2 focus:ring-gray-500'],
    ['btn-danger', 'btn-base bg-red-600 text-white hover:bg-red-700 focus:ring-2 focus:ring-red-500'],
    
    // 卡片样式
    ['card', 'bg-white rounded-lg shadow-sm border border-gray-200 p-4'],
    ['card-hover', 'card hover:shadow-md transition-shadow duration-200'],
    
    // 输入框样式
    ['input-base', 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'],
    
    // 文本样式
    ['text-primary', 'text-gray-900'],
    ['text-secondary', 'text-gray-600'],
    ['text-muted', 'text-gray-500'],
    
    // 间距
    ['space-y-4', 'space-y-4'],
    ['space-x-4', 'space-x-4']
  ],
  theme: {
    colors: {
      primary: {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a'
      }
    }
  }
})
