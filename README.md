# Azure AI顾问服务 - 后端系统

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

> 基于FastAPI构建的云原生AI顾问后端系统，支持多租户管理、智能推荐引擎和实时定价计算

## 🚀 当前进度 - Phase1完成

**里程碑**：`2025-04-14` 完成基础架构搭建  
✅ 健康检查端点已上线  
✅ 认证体系完成开发  
✅ 数据库基础架构就绪

### 已实现功能
| 模块         | 功能点                     | 验证方法                     | 状态 |
|--------------|---------------------------|-----------------------------|------|
| 基础设施     | 健康检查端点               | `GET /api/v1/health`        | ✅   |
| 认证授权     | JWT令牌认证                | `POST /api/v1/auth/login`   | ✅   |
|              | LDAP域集成                 | 管理员LDAP测试接口          | ✅   |
| 用户管理     | 用户注册/登录              | `POST /api/v1/users/`       | ✅   |
|              | 密码哈希存储               | Bcrypt算法验证              | ✅   |
| 数据库       | 异步PostgreSQL连接         | 查看启动日志                | ✅   |
|              | Alembic迁移管理            | 执行`alembic upgrade head` | ✅   |
| 可观测性     | 结构化日志系统             | 查看`logs/app.log`          | ✅   |

## ⚙️ 快速启动
```bash
# 安装依赖
poetry install

# 配置环境变量
cp .env.example .env

# 启动服务（开发模式）
uvicorn app.main:app --reload
```

## 📡 API验证示例
```bash
# 健康检查
curl -X GET "http://localhost:8000/api/v1/health" 

# 预期响应
{"status":"healthy","app":"Azure Calculator backend API","version":"0.0.1"}
```

## 🔧 环境配置
```ini
# .env 示例
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ai_advisor

LDAP_ENABLED=false
LDAP_SERVER=ldap.example.com
```

## 📌 技术要求
- **运行环境**: Python 3.9+ / Node.js 16+
- **核心框架**: 
  - FastAPI 0.100.0+
  - SQLAlchemy 2.0+
- **数据库**: 
  - PostgreSQL 14+ (开发环境)
  - Azure Cosmos DB (生产环境)

## 🧪 测试验证
```bash
# 运行单元测试
pytest tests/

# 当前测试覆盖率
pytest --cov=app --cov-report=html
```

## 📍 后续规划
**Phase2 - LLM集成** (预计2025-04-15启动)
- [ ] Azure OpenAI服务集成
- [ ] 对话历史管理API
- [ ] Markdown响应解析器

[查看完整项目路线图](./docs/roadmap.md)

---

> 项目文档持续更新中，技术细节请参考 [API文档](http://localhost:8000/docs)  
> 贡献指南请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md)