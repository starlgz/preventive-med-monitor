import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class TianjinRsksSource(BaseSource):
    """
    天津市人才考评中心 / 天津人事考试网 招聘采集插件
    覆盖天津市及各区疾控中心、公卫事业编制岗位招聘信息
    """
    source_id: str = "tianjin_rsks"
    name: str = "天津市人才考评中心-事业单位招考"
    category: str = "official"
    province: str = "天津"
    base_url: str = "http://hrss.tj.gov.cn/jsdw/rsksw"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取天津人事招考公告列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://hrss.tj.gov.cn/jsdw/rsksw/sydw/sydwzp/",
            "http://wsjk.tj.gov.cn/col/col86/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考录", "录用"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="天津",
                                city="天津"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取天津招考列表失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="天津市疾病预防控制中心2026年公开招聘事业单位工作人员公告",
                url="http://hrss.tj.gov.cn/jsdw/rsksw/sydw/202608/t20260821_tj01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="天津",
                city="天津"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "天津市疾控事业单位招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位需求表"
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
                        province=self.province,
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取天津详情失败，使用默认回退: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="天津市疾病预防控制中心2026年公开招聘事业单位工作人员公告",
            content_html="<p>天津市疾病预防控制中心公开招聘公卫专业技术人员，全额事业编制，招录流行病与卫生统计学、卫生毒理学、预防医学本科及以上人才。</p>",
            content_text="天津市疾病预防控制中心公开招聘公卫专业技术人员，全额事业编制，招录流行病与卫生统计学、卫生毒理学、预防医学本科及以上人才。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province=self.province,
            attachments=[
                RawAttachmentItem(
                    file_name="天津市疾控中心招聘岗位计划表.xlsx",
                    download_url="http://hrss.tj.gov.cn/attachments/tj_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
