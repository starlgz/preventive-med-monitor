import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import logger
from app.core.init_db import init_database
from app.scheduler.manager import scheduler_manager
from app.api.health import router as health_router
from app.api.sources import router as sources_router
from app.api.parsers import router as parsers_router
from app.api.extractors import router as extractors_router
from app.api.rules import router as rules_router
from app.api.bianzhi import router as bianzhi_router
from app.api.priorities import router as priorities_router
from app.api.notifications import router as notifications_router
from app.api.filters import router as filters_router
from app.api.bot import router as bot_router
from app.web.dashboard import router as web_router
from app.api.ai import router as ai_router
from app.api.pipeline import router as pipeline_router
from app.api.custom_sources import router as custom_sources_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    await init_database()
    logger.info("Database initialized successfully.")
    
    # 启动定时调度器
    scheduler_manager.start()
    yield
    
    # 关闭调度器
    scheduler_manager.shutdown()
    logger.info(f"Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    description="基于 FastAPI + Vue 3 的预防医学事业单位招聘实时监测与管理控制台",
    version="2.0.0",
    lifespan=lifespan
)

# 静态资源与构建物托管 (Vue 3 Assets)
static_assets_path = os.path.join(os.path.dirname(__file__), "static", "dist", "assets")
if os.path.exists(static_assets_path):
    app.mount("/assets", StaticFiles(directory=static_assets_path), name="static_assets")

# 挂载 API 路由
app.include_router(health_router)
app.include_router(sources_router, prefix="/api/v1")
app.include_router(parsers_router, prefix="/api/v1")
app.include_router(extractors_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(bianzhi_router, prefix="/api/v1")
app.include_router(priorities_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(filters_router, prefix="/api/v1")
app.include_router(bot_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(custom_sources_router, prefix="/api/v1")

# 挂载 Web SPA 页面与大盘 REST API
app.include_router(web_router)
