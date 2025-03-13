FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.0.0 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        freetds-dev \
        freetds-bin \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# 复制项目依赖文件
COPY pyproject.toml poetry.lock* ./

# 安装项目依赖
RUN poetry install --no-dev --no-root

# 复制项目文件
COPY . .

# 创建非 root 用户并切换
RUN addgroup --system app \
    && adduser --system --group app \
    && chown -R app:app /app
USER app

# 运行应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]