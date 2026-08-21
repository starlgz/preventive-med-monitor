# 全国预防医学事业单位招聘实时监测系统

> 专为预防医学专业打造的高精度、全自动化事业单位招聘监控系统。

## 🎯 Phase 1 架构特性
1. **轻量与现代化**：基于 Python 3.11+ / FastAPI / SQLAlchemy 2.0 (异步 aiosqlite) / Loguru。
2. **专业目录可插拔**：专业代码不硬编码，通过 JSON 与数据库动态管理，支持年份版本、本硕分级与独立更新。
3. **岗位级编制判定设计**：数据表以岗位为最小分析单元，支持证据链与置信度溯源。
4. **五级通知优先级预留**：S (5星在编即将截止)、A (5星在编)、B (4星在编)、C (3星及以下)、D (待确认)。
5. **容器化支持**：内置 Dockerfile 与 Docker Compose 编排。

---

## 🚀 启动与测试指南

### 1. 方式一：本地 Python 运行 (快速开发模式)

```bash
# 1. 进入项目目录
cd /root/.openclaw/workspace/preventive_med_monitor

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 FastAPI 服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 方式二：Docker Compose 运行 (生产部署模式)

```bash
# 进入项目目录
cd /root/.openclaw/workspace/preventive_med_monitor

# 构建并后台启动容器
docker compose up -d --build

# 查看容器运行状态
docker compose ps

# 查看实时日志
docker compose logs -f
```

---

## 🩺 健康检查与 API 验证

* **健康检查接口 (JSON)**: `http://localhost:8000/api/v1/health`
* **Swagger 交互式文档**: `http://localhost:8000/docs`
* **ReDoc 接口文档**: `http://localhost:8000/redoc`
