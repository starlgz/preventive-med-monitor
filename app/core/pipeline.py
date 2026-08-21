import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.entities import Announcement, Job, Notification, Source, Attachment
from app.sources.registry import SourceRegistry
from app.extractors.service import JobExtractionService
from app.rules.matcher_service import MajorMatcherService
from app.rules.bianzhi_service import BianzhiService
from app.rules.priority_service import PriorityService
from app.notifications.service import NotificationCenter

logger = logging.getLogger(__name__)

class FullAutomationPipeline:
    """
    全链路自动化监控流水线
    Step 1: 扫描并执行采集源爬取（包括公告正文与附件关联）
    Step 2: 岗位结构化抽取与特征画像提取 (JobExtractionService)
    Step 3: 预防医学五星专业匹配打分 (MajorMatcherService)
    Step 4: 编制三色判定与置信度量化 (BianzhiService)
    Step 5: 通知优先级判定 (PriorityService)
    Step 6: 多渠道去重告警推送 (NotificationCenter)
    """

    @classmethod
    async def run_pipeline(
        cls,
        session: AsyncSession,
        source_key: Optional[str] = None,
        auto_push_notifications: bool = True
    ) -> Dict[str, Any]:
        stats = {
            "start_time": datetime.now().isoformat(),
            "crawled_announcements": 0,
            "new_announcements": 0,
            "extracted_jobs": 0,
            "matched_5star_jobs": 0,
            "evaluated_bianzhi_jobs": 0,
            "priority_evaluated_jobs": 0,
            "pushed_notifications": 0,
            "errors": []
        }

        # -------------------------------------------------------------
        # Step 1: 扫描并执行采集源爬取
        # -------------------------------------------------------------
        SourceRegistry.discover_and_register()
        sources_to_crawl = []
        if source_key:
            src_cls = SourceRegistry.get(source_key)
            if src_cls:
                sources_to_crawl.append(src_cls)
        else:
            sources_to_crawl = SourceRegistry.get_all()

        logger.info(f"📡 [Step 1] 正在执行数据源采集，涉及源数量: {len(sources_to_crawl)}")
        for source_cls in sources_to_crawl:
            try:
                plugin = source_cls() if callable(source_cls) else source_cls
                announcements = await plugin.fetch_announcements()
                stats["crawled_announcements"] += len(announcements)
                for item in announcements:
                    item_url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else "")
                    item_title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else "")
                    item_source_id = getattr(item, "source_id", plugin.source_id)

                    # 检查是否已有
                    existing = (await session.execute(
                        select(Announcement).where(Announcement.url == item_url)
                    )).scalars().first()

                    if not existing:
                        # 尝试抓取详情与附件
                        detail = None
                        try:
                            detail = await plugin.fetch_detail(item_url)
                        except Exception:
                            pass

                        content_raw = detail.content_text if detail else ""
                        anno = Announcement(
                            source_id=item_source_id,
                            title=item_title,
                            url=item_url,
                            content_raw=content_raw,
                            province=getattr(plugin, "province", "全国")
                        )
                        session.add(anno)
                        await session.flush()
                        stats["new_announcements"] += 1

                        # 保存附件记录
                        if detail and getattr(detail, "attachments", None):
                            for att in detail.attachments:
                                att_obj = Attachment(
                                    announcement_id=anno.id,
                                    file_name=att.file_name,
                                    file_type=att.file_type,
                                    download_url=att.download_url,
                                    file_size=getattr(att, "file_size", 0)
                                )
                                session.add(att_obj)
                            await session.flush()
            except Exception as e:
                err_msg = f"Crawl {getattr(source_cls, 'source_id', str(source_cls))} error: {str(e)}"
                logger.error(f"采集源抓取失败: {str(e)}")
                stats["errors"].append(err_msg)

        await session.commit()

        # -------------------------------------------------------------
        # Step 2: 岗位结构化抽取与特征画像提取
        # -------------------------------------------------------------
        logger.info("⚙️ [Step 2] 正在执行公告与附件结构化岗位解析与持久化...")
        all_annos = (await session.execute(select(Announcement))).scalars().all()
        for anno in all_annos:
            try:
                extract_res = await JobExtractionService.extract_and_save_jobs(session, anno.id)
                stats["extracted_jobs"] += extract_res.get("new_saved", 0)
            except Exception as e:
                logger.warning(f"公告 {anno.id} 提取岗位失败: {str(e)}")

        await session.commit()

        # -------------------------------------------------------------
        # Step 3: 预防医学五星专业匹配
        # -------------------------------------------------------------
        logger.info("⭐ [Step 3] 正在执行预防医学专业匹配与星级评定...")
        match_res = await MajorMatcherService.run_batch_match(session)
        stats["matched_5star_jobs"] = match_res.get("evaluated_count", 0)
        await session.commit()

        # -------------------------------------------------------------
        # Step 4: 编制三色与置信度量化判定
        # -------------------------------------------------------------
        logger.info("🟢🟡🔴 [Step 4] 正在执行编制类型三色与置信度量化研判...")
        bianzhi_res = await BianzhiService.run_batch_evaluation(session)
        stats["evaluated_bianzhi_jobs"] = bianzhi_res.get("evaluated_count", 0)
        await session.commit()

        # -------------------------------------------------------------
        # Step 5: 优先级划分 (S/A/B/C/D)
        # -------------------------------------------------------------
        logger.info("🎯 [Step 5] 正在执行综合优先级划分与临期急聘置顶...")
        priority_res = await PriorityService.run_batch_priority_evaluation(session)
        stats["priority_evaluated_jobs"] = priority_res.get("evaluated_count", 0)
        await session.commit()

        # -------------------------------------------------------------
        # Step 6: 多渠道去重告警推送
        # -------------------------------------------------------------
        if auto_push_notifications:
            logger.info("📣 [Step 6] 正在执行全渠道 (Telegram/企微/邮件) 增量推送...")
            push_res = await NotificationCenter.push_pending_notifications(session)
            stats["pushed_notifications"] = push_res.get("pushed_count", 0)
            await session.commit()

        stats["end_time"] = datetime.now().isoformat()
        logger.info(f"✅ 全链路流水线执行完毕: {stats}")
        return stats
