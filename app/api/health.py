from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from app.core.database import get_db
from app.core.config import settings
from app.models.entities import MajorCatalog
from app.schemas.health import HealthResponse, ApiOverviewResponse

router = APIRouter(tags=["System"])

@router.get("/", response_model=ApiOverviewResponse, summary="系统欢迎页")
async def root():
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/api/v1/health"
    }

@router.get("/api/v1/health", response_model=HealthResponse, summary="系统健康检查")
async def health_check(db: AsyncSession = Depends(get_db)):
    # 1. 检查 SQLite 连通性
    try:
        res = await db.execute(text("SELECT 1"))
        db_alive = (res.scalar() == 1)
        db_status = "connected"
    except Exception as e:
        db_alive = False
        db_status = f"error: {str(e)}"
        
    # 2. 统计已载入的专业目录数
    try:
        count_res = await db.execute(select(func.count(MajorCatalog.id)))
        catalogs_count = count_res.scalar() or 0
    except Exception:
        catalogs_count = 0
        
    return {
        "status": "healthy" if db_alive else "unhealthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "type": "SQLite 3",
            "url": settings.DATABASE_URL,
            "status": db_status,
            "connected": db_alive
        },
        "major_catalogs_count": catalogs_count
    }
