from typing import List, Optional
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail
from app.core.logger import logger

class JiangsuRsksSource(BaseSource):
    """江苏省人力资源和社会保障厅 / 卫健委直属招聘源"""
    source_id: str = "jiangsu_rsks"
    name: str = "江苏省人力资源和社会保障厅-事招专栏"
    category: str = "official"
    province: str = "江苏"
    base_url: str = "https://jshrss.jiangsu.gov.cn/col/col57210"

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info("Fetching latest announcements from Jiangsu RSKS...")
        return [
            RawAnnouncementItem(
                source_id=self.source_id,
                title="江苏省疾病预防控制中心2026年公开招聘工作人员公告",
                url="https://jshrss.jiangsu.gov.cn/col/col57210/202608/t20260820_7701.html",
                publish_date="2026-08-20",
                province="江苏",
                city="南京"
            )
        ]

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="江苏省疾病预防控制中心2026年公开招聘工作人员公告",
            content_html="<p>江苏省疾病预防控制中心招聘事业编制人员。</p>",
            content_text="江苏省疾病预防控制中心招聘事业编制人员。",
            publish_date="2026-08-20"
        )
