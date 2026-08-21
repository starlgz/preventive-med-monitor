import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
import httpx

from app.core.config import settings
from app.core.logger import logger
from app.core.database import AsyncSessionLocal
from app.models.entities import Source, Announcement, CrawlLog, CustomSource
from app.sources.registry import SourceRegistry
from app.engine.generic_crawler import GenericCrawlerEngine
import json

class TaskScheduler:
    """
    任务调度与运行管理器
    """
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=20.0,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
        return self._http_client

    async def sync_sources_to_db(self):
        """
        将注册的插件元数据同步注册进 SQLite sources 表
        """
        # 确保插件已发现后再同步（懒加载发现机制）
        SourceRegistry.discover_and_register()
        plugins = SourceRegistry.get_all()
        async with AsyncSessionLocal() as session:
            for plugin in plugins:
                res = await session.execute(select(Source).where(Source.source_id == plugin.source_id))
                existing = res.scalars().first()
                if not existing:
                    new_source = Source(
                        source_id=plugin.source_id,
                        name=plugin.name,
                        category=plugin.category,
                        province=plugin.province,
                        base_url=plugin.base_url,
                        driver_type=plugin.driver_type,
                        is_active=1,
                        health_score=1.0
                    )
                    session.add(new_source)
                    logger.info(f"Initialized source in DB: [{plugin.source_id}] {plugin.name}")
            await session.commit()

    async def run_single_source(self, source_id: str) -> Dict[str, Any]:
        """
        执行单个数据源采集，包含独立熔断、错误隔离与日志入库
        """
        plugin = SourceRegistry.get(source_id)
        if not plugin:
            return {"source_id": source_id, "status": "FAILED", "items_found": 0, "new_saved": 0, "error": "Plugin not found"}

        logger.info(f"🚀 Starting crawl task for: [{plugin.source_id}] {plugin.name}")
        client = await self.get_http_client()
        
        status = "SUCCESS"
        error_msg = None
        items_found = 0
        new_saved = 0
        
        try:
            raw_announcements = await plugin.fetch_announcements(client)
            items_found = len(raw_announcements)
            logger.info(f"[{plugin.name}] Found {items_found} raw announcement items.")
            
            async with AsyncSessionLocal() as session:
                for raw in raw_announcements:
                    # 检查是否已抓取过相同 URL
                    res = await session.execute(select(Announcement).where(Announcement.url == raw.url))
                    existing = res.scalars().first()
                    if not existing:
                        ann = Announcement(
                            source_id=plugin.source_id,
                            title=raw.title,
                            url=raw.url,
                            publish_date=raw.publish_date,
                            province=raw.province,
                            city=raw.city,
                            content_raw=raw.content_raw,
                            attachments_json=str(raw.attachments_raw) if raw.attachments_raw else None,
                            is_processed=0
                        )
                        session.add(ann)
                        new_saved += 1
                
                # 更新 source 表的健康度与最后抓取时间
                res = await session.execute(select(Source).where(Source.source_id == source_id))
                src_db = res.scalars().first()
                if src_db:
                    src_db.last_crawl_at = datetime.utcnow()
                    src_db.health_score = min(1.0, src_db.health_score + 0.1)

                # 记录抓取日志
                log = CrawlLog(
                    source_id=plugin.source_id,
                    status="SUCCESS",
                    items_found=items_found,
                    jobs_extracted=0,
                    error_message=None
                )
                session.add(log)
                await session.commit()
                
            logger.info(f"✅ [{plugin.name}] Crawl finished: {items_found} found, {new_saved} new saved.")
            
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(f"❌ [{plugin.name}] Crawl failed: {e}")
            
            # 记录失败日志并扣减健康度
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Source).where(Source.source_id == source_id))
                src_db = res.scalars().first()
                if src_db:
                    src_db.health_score = max(0.0, src_db.health_score - 0.2)
                    if src_db.health_score <= 0.2:
                        logger.warning(f"⚠️ Source [{plugin.source_id}] health low ({src_db.health_score}), circuit breaker triggered.")
                
                log = CrawlLog(
                    source_id=plugin.source_id,
                    status="FAILED",
                    items_found=0,
                    jobs_extracted=0,
                    error_message=error_msg
                )
                session.add(log)
                await session.commit()

        return {
            "source_id": source_id,
            "status": status,
            "items_found": items_found,
            "new_saved": new_saved,
            "error": error_msg
        }

    async def run_custom_source(self, custom_source_id: int) -> Dict[str, Any]:
        """
        执行单个用户自定义爬虫，带抓取、去重与流水线入库
        """
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CustomSource).where(CustomSource.id == custom_source_id))
            src_db = res.scalars().first()
            if not src_db:
                return {"id": custom_source_id, "status": "FAILED", "items_found": 0, "new_saved": 0, "error": "Custom source not found"}

            source_name = src_db.name
            source_key = src_db.source_key
            province = src_db.province
            try:
                rule_dict = json.loads(src_db.rule_json)
            except Exception as e:
                return {"id": custom_source_id, "status": "FAILED", "items_found": 0, "new_saved": 0, "error": f"Invalid JSON: {e}"}

        logger.info(f"🚀 Starting custom crawl task for: [{source_key}] {source_name}")
        engine = GenericCrawlerEngine(timeout=15.0)
        status = "SUCCESS"
        error_msg = None
        items_found = 0
        new_saved = 0

        try:
            crawl_res = await engine.execute_crawl(rule_dict, max_items=20)
            items = crawl_res.get("items", [])
            items_found = len(items)

            async with AsyncSessionLocal() as session:
                for item in items:
                    url = item.get("url")
                    title = item.get("title")
                    if not url or not title:
                        continue

                    # 检查是否已抓取过相同 URL
                    res = await session.execute(select(Announcement).where(Announcement.url == url))
                    existing = res.scalars().first()
                    if not existing:
                        pub_date = None
                        if item.get("date"):
                            try:
                                pub_date = datetime.strptime(item["date"][:10], "%Y-%m-%d")
                            except Exception:
                                pub_date = datetime.now()
                        ann = Announcement(
                            source_id=source_key,
                            title=title,
                            url=url,
                            publish_date=pub_date or datetime.now(),
                            province=province,
                            city=None,
                            content_raw=item.get("content"),
                            is_processed=0
                        )
                        session.add(ann)
                        new_saved += 1

                # 更新 CustomSource 状态
                res = await session.execute(select(CustomSource).where(CustomSource.id == custom_source_id))
                curr = res.scalars().first()
                if curr:
                    curr.last_run_at = datetime.now()
                    curr.last_status = "SUCCESS"
                    curr.last_error = None
                await session.commit()
                logger.info(f"✅ Custom source [{source_name}] finished: {items_found} found, {new_saved} new saved.")

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(f"❌ Custom source [{source_name}] crawl failed: {e}")
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(CustomSource).where(CustomSource.id == custom_source_id))
                curr = res.scalars().first()
                if curr:
                    curr.last_run_at = datetime.now()
                    curr.last_status = "FAILED"
                    curr.last_error = error_msg
                await session.commit()

        return {
            "id": custom_source_id,
            "source_key": source_key,
            "status": status,
            "items_found": items_found,
            "new_saved": new_saved,
            "error": error_msg
        }

    async def run_all_sources(self):
        """
        轮询所有启用的数据源
        """
        logger.info("🔄 Triggering scheduled crawl for all active sources...")
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Source).where(Source.is_active == 1))
            sources = res.scalars().all()
            
        for src in sources:
            # 错峰防封，每个源间隔 2 秒
            await self.run_single_source(src.source_id)
            await asyncio.sleep(2)
            
        # 同时抓取启用的用户自定义源
        async with AsyncSessionLocal() as session:
            res_c = await session.execute(select(CustomSource).where(CustomSource.is_active == 1))
            custom_sources = res_c.scalars().all()
        for c_src in custom_sources:
            await self.run_custom_source(c_src.id)
            await asyncio.sleep(2)

        logger.info("🏁 All active sources crawl round finished.")

    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        """
        plugins = SourceRegistry.get_all()
        return {
            "is_running": self._is_running,
            "interval_minutes": settings.SCHEDULER_INTERVAL_MINUTES,
            "active_sources_count": len(plugins),
            "total_plugins_count": len(plugins)
        }

    def start(self):
        """
        启动后台定时调度器
        """
        if not self._is_running:
            self.scheduler.add_job(
                self.run_all_sources,
                "interval",
                minutes=settings.SCHEDULER_INTERVAL_MINUTES,
                id="all_sources_crawler",
                replace_existing=True
            )
            self.scheduler.start()
            self._is_running = True
            logger.info(f"⏰ TaskScheduler started! Polling every {settings.SCHEDULER_INTERVAL_MINUTES} minutes.")
            # 同步最新插件元数据到 DB，使新增数据源自动纳入后续轮询
            self.start_sync_sources()

    def start_sync_sources(self):
        """同步注册最新插件元数据到 DB（供启动时调用，确保新增数据源自动计入后台调度）"""
        import asyncio
        try:
            asyncio.create_task(self.sync_sources_to_db())
            logger.info("🔄 已触发将最新插件元数据同步至 sources 表...")
        except Exception as e:
            logger.warning(f"同步 sources 到 DB 失败: {e}")

    def shutdown(self):
        """
        停止后台调度器
        """
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("TaskScheduler stopped.")

scheduler_manager = TaskScheduler()
