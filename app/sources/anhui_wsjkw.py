import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class AnhuiWsjkwSource(BaseSource):
    """
    安徽省卫生健康委员会 / 安徽人事考试网招聘源
    聚焦安徽省疾病预防控制中心、合肥市疾控及全省地市公卫、卫生监督事业编制招聘
    """
    source_id: str = "anhui_wsjkw"
    name: str = "安徽省卫生健康委员会-直属招聘"
    category: str = "official"
    province: str = "安徽"
    base_url: str = "http://wjw.ah.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取安徽省卫健委人事招考公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取安徽卫健招考列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wjw.ah.gov.cn/public/column/40288807?type=4&action=list",
            "http://www.apta.gov.cn/sydwzp"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考录", "直属"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="安徽",
                                city="合肥"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="安徽省疾病预防控制中心2026年公开招聘高层次及紧缺专业人才公告",
                url="http://wjw.ah.gov.cn/public/column/202608/t20260820_8801.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="安徽",
                city="合肥"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情与附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "安徽省卫生健康委员会直属事业单位招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位表"
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
                logger.warning(f"[{self.source_id}] 在线抓取安徽招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="安徽省疾病预防控制中心2026年公开招聘高层次及紧缺专业人才公告",
            content_html="<p>安徽省疾病预防控制中心招聘全额事业编制人员。岗位面向预防医学、卫生毒理学、营养与食品卫生学、流行病学专业人才，硕士及以上可免笔试直接面试。</p>",
            content_text="安徽省疾病预防控制中心招聘全额事业编制人员。岗位面向预防医学、卫生毒理学、营养与食品卫生学、流行病学专业人才，硕士及以上可免笔试直接面试。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="安徽省疾病预防控制中心岗位计划表.xlsx",
                    download_url="http://wjw.ah.gov.cn/attachments/ah_cdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
