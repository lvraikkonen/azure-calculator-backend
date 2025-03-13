# Azure AI顾问服务 - 后端系统

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

> 基于FastAPI构建的云原生AI顾问后端系统，支持多租户管理、智能推荐引擎和实时定价计算

## 🚀 当前进度 - Phase2完成

**里程碑**：`2025-04-15` 完成智能对话核心功能  
✅ 聊天API与LLM集成  
✅ 对话上下文管理  
✅ 结构化推荐方案生成

### 已实现功能
| 模块         | 功能点                     | 验证方法                     | 状态 |
|--------------|---------------------------|-----------------------------|------|
| **智能对话** | 创建/继续对话              | `POST /api/v1/chat/messages`| ✅   |
|              | 获取对话历史               | `GET /api/v1/chat/conversations/{id}` | ✅ |
|              | OpenAI兼容LLM集成         | 查看`llm_service.py`        | ✅   |
|              | 结构化推荐方案生成         | 检查响应中的recommendation字段 | ✅ |
|              | 用户反馈系统              | `POST /api/v1/chat/feedback` | ✅  |
| **基础设施** | 异步消息处理               | 查看`conversation_service.py` | ✅ |
|              | 对话原子性操作            | 测试中断电恢复场景          | ✅   |

## ⚙️ 快速启动
```bash
# 安装LLM依赖
poetry add openai>=1.12.0

# 启动带Swagger文档的服务
uvicorn app.main:app --reload --port 8080
```

## 📡 API验证示例
```bash
# 获取访问令牌
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser", "password":"testpass"}' | jq -r '.access_token')

# 发起智能对话
curl -X POST "http://localhost:8000/api/v1/chat/messages/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "我需要高可用性的云数据库方案",
    "context": {"budget": "1000美元/月"}
  }'

# 获取对话详情
CONV_ID="你的对话ID"
curl -X GET "http://localhost:8000/api/v1/chat/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN"
```

## 🔧 环境配置
```ini
# .env 新增配置
OPENAI_API_KEY=sk-your-key-here
OPENAI_API_BASE=https://api.openai.com/v1  # 或自定义端点

# 对话保留策略
MAX_CONVERSATION_AGE=30  # 保留最近30天的对话
```

## 📌 技术要求
- **新增依赖**:
  - `openai>=1.12.0`
  - `tenacity>=8.2.0` (重试逻辑)
- **LLM服务**:
  - OpenAI API 或兼容服务 (Azure OpenAI, LocalAI等)

## 🧪 测试验证
```bash
# 运行单元测试
pytest tests/

# 当前测试覆盖率
pytest --cov=app --cov-report=html
```

## 📍 后续规划
**Phase3 - 生产就绪化** (预计2025-04-20启动)
- [ ] 流式响应支持
- [ ] 对话内容审计日志
- [ ] 多模型路由策略
- [ ] 成本估算引擎集成

**性能目标**:
```yaml
并发能力: 100+ TPS (4核8G实例)
响应延迟: <1500ms (p99)
推荐准确率: >85% (基于用户反馈)
```

[查看完整技术白皮书](./docs/whitepaper.md) | [API测试报告](./docs/test_report.md)
```

---

> 项目文档持续更新中，技术细节请参考 [API文档](http://localhost:8000/docs)  
> 贡献指南请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md)