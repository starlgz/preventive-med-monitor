# =========================================================================
# 全国预防医学事业单位招聘实时监测系统 (V1.1)
# Docker 镜像构建规范 (Multi-Stage / Python 3.11-slim)
# =========================================================================

FROM python:3.11-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 安装系统基础依赖与时区数据
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    sqlite3 \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 库
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目代码
COPY . .

# 确保数据目录与目录权限
RUN mkdir -p /app/data /app/data/catalogs /app/logs

# 暴露 FastAPI Web / API 服务端口
EXPOSE 8000

# 健康检查探针
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/v1/health || exit 1

# 启动命令
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
