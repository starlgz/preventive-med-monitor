import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HenanWsjkwSource(BaseSource):
    """
    河南省卫生健康委员会招聘采集插件
    """
    source_id: str = "henan_wsjkw"
    name: str = "河南省卫健委人才招聘"
    category: str = "official"
    province: str = "河南"
    base_url: str = "https://wsjkw.henan.gov.cn/wsjkw/index/rsxx/index.html"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取河南省卫健委人才招聘列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://wsjkw.henan.gov.cn/wsjkw/index/rsxx/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "拟聘", "遴选", "招录", "选拔", "考核"]):
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=urljoin(url, href),
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="河南",
                                city="郑州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取异常 {url}: {e}")

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "html.parser")
                title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                title = title_tag.text.strip() if title_tag else "河南省卫健委招聘公告"

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
                logger.error(f"[{self.source_id}] 解析异常: {e}")
                return None

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
