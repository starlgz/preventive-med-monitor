"""
Custom Sources API (用户自定义低代码爬虫接口)
- /api/v1/sources/custom (GET, POST)
- /api/v1/sources/custom/{id} (PUT, DELETE)
- /api/v1/sources/custom/test (POST 沙箱实时调试)
- /api/v1/sources/custom/{id}/run (POST 手动触发抓取)
"""
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.models.entities import CustomSource
from app.engine.generic_crawler import GenericCrawlerEngine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Custom Sources"])

class SandboxTestRequest(BaseModel):
    protocol: str = Field("html_list", description="协议类型: html_list | json_api | rss")
    request: Dict[str, Any] = Field(..., description="请求配置 (url, method, headers, etc)")
    list_extractor: Dict[str, Any] = Field(..., description="列表提取器配置")
    detail_extractor: Optional[Dict[str, Any]] = None

class CustomSourceCreateRequest(BaseModel):
    source_key: str = Field(..., description="唯一英文标识")
    name: str = Field(..., description="数据源名称")
    province: str = Field("全国", description="归属省份")
    protocol: str = Field("html_list", description="协议类型")
    rule: Dict[str, Any] = Field(..., description="完整规则配置")
    cron_expr: Optional[str] = None
    is_active: int = Field(1, description="是否启用 (1/0)")

class CustomSourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    province: Optional[str] = None
    protocol: Optional[str] = None
    rule: Optional[Dict[str, Any]] = None
    cron_expr: Optional[str] = None
    is_active: Optional[int] = None

@router.post("/sources/custom/test")
async def test_custom_source_sandbox(req: SandboxTestRequest):
    """
    爬虫沙箱即时测试: 抓取 1 页并提取前 5 条公告，返回状态码、耗时和解析结果
    """
    engine = GenericCrawlerEngine(timeout=15.0)
    rule_dict = req.model_dump()
    try:
        result = await engine.execute_crawl(rule_dict, max_items=5)
        return {
            "code": 200,
            "message": "沙箱测试执行成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"Sandbox test failed: {e}", exc_info=True)
        return {
            "code": 400,
            "message": f"沙箱抓取/解析失败: {str(e)}",
            "data": {
                "status_code": 500,
                "cost_ms": 0,
                "total_extracted": 0,
                "items": [],
                "error": str(e)
            }
        }

@router.get("/sources/custom")
async def list_custom_sources(db: AsyncSession = Depends(get_db)):
    """
    获取所有自定义爬虫列表
    """
    stmt = select(CustomSource).order_by(CustomSource.id.desc())
    res = await db.execute(stmt)
    records = res.scalars().all()
    
    data = []
    for r in records:
        try:
            r_json = json.loads(r.rule_json)
        except Exception:
            r_json = {}
        data.append({
            "id": r.id,
            "source_key": r.source_key,
            "name": r.name,
            "province": r.province,
            "protocol": r.protocol,
            "rule": r_json,
            "cron_expr": r.cron_expr,
            "is_active": r.is_active,
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
            "last_status": r.last_status,
            "last_error": r.last_error,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"code": 200, "data": data, "total": len(data)}

@router.post("/sources/custom")
async def create_custom_source(req: CustomSourceCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    新建自定义爬虫
    """
    # 检查 key 是否已存在
    check_stmt = select(CustomSource).where(CustomSource.source_key == req.source_key)
    existing = (await db.execute(check_stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail=f"标识 '{req.source_key}' 已存在")

    record = CustomSource(
        source_key=req.source_key,
        name=req.name,
        province=req.province,
        protocol=req.protocol,
        rule_json=json.dumps(req.rule, ensure_ascii=False),
        cron_expr=req.cron_expr,
        is_active=req.is_active,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"code": 200, "message": "创建成功", "data": {"id": record.id, "source_key": record.source_key}}

@router.put("/sources/custom/{source_id}")
async def update_custom_source(source_id: int, req: CustomSourceUpdateRequest, db: AsyncSession = Depends(get_db)):
    """
    更新自定义爬虫
    """
    stmt = select(CustomSource).where(CustomSource.id == source_id)
    record = (await db.execute(stmt)).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="未找到对应自定义源")

    if req.name is not None:
        record.name = req.name
    if req.province is not None:
        record.province = req.province
    if req.protocol is not None:
        record.protocol = req.protocol
    if req.rule is not None:
        record.rule_json = json.dumps(req.rule, ensure_ascii=False)
    if req.cron_expr is not None:
        record.cron_expr = req.cron_expr
    if req.is_active is not None:
        record.is_active = req.is_active
    record.updated_at = datetime.now()

    await db.commit()
    return {"code": 200, "message": "更新成功"}

@router.delete("/sources/custom/{source_id}")
async def delete_custom_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """
    删除自定义爬虫
    """
    stmt = delete(CustomSource).where(CustomSource.id == source_id)
    await db.execute(stmt)
    await db.commit()
    return {"code": 200, "message": "删除成功"}
