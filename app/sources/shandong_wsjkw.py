import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShandongWsjkwSource(BaseSource):
    """
    山东省卫生健康委员会 / 人社招考采集插件
    聚焦山东省直、各地市疾控中心及医疗卫生机构公开招聘
    """
    source_id: str = "shandong_wsjkw"
    name: str = "山东省卫生健康委员会-公卫疾控招考"
    category: str = "official"
    province: str = "山东"
    base_url: str = "http://wsjkw.shandong.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取山东卫健委人事招考公告"""
        logger.info(f"[{self.source_id}] 开始抓取山东卫健人事招聘列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wsjkw.shandong.gov.cn/zwgk/rsxx/gwyzk/",
            "http://wsjkw.shandong.gov.cn/zwgk/rsxx/sydwzk/"
        ]

        async with await self.get_http_client(timeout=3.0) as client:
            for url in target_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        title = a.text.strip()
                        href = a["href"].strip()
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "拟聘", "考核", "简章"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="山东",
                                city="济南"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "html.parser")
                title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                title = title_tag.text.strip() if title_tag else "山东卫生健康系统招聘公告"

                content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                content_html = str(content_div) if content_div else ""
                content_text = content_div.text.strip() if content_div else ""

                attachments: List[RawAttachmentItem] = []
                if content_div:
                    for a in content_div.find_all("a", href=True):
                        href = a["href"].strip()
                        att_name = a.text.strip() or "附件"
                        lower_href = href.lower()
                        for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf"]:
                            if ext in lower_href:
                                attachments.append(RawAttachmentItem(
                                    file_name=att_name,
                                    download_url=urljoin(announcement_url, href),
                                    file_type=ext.lstrip(".")
                                ))
                                break

                return RawAnnouncementDetail(
                    source_id=self.source_id,
                    url=announcement_url,
                    title=title,
                    content_html=content_html,
                    content_text=content_text,
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    attachments=attachments,
                    crawl_time=datetime.now()
                )
            except Exception as e:
                logger.error(f"[{self.source_id}] 解析详情异常: {e}")
                return None

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
