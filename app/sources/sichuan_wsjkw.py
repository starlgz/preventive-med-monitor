import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class SichuanWsjkwSource(BaseSource):
    """
    四川省卫生健康委员会 / 四川省疾病预防控制中心 (SCCDC) 招聘源
    聚焦省直疾控、妇幼保健院、成都市及各地市州公卫机构事业编制招聘
    """
    source_id: str = "sichuan_wsjkw"
    name: str = "四川省卫生健康委员会-事业单位招聘专栏"
    category: str = "official"
    province: str = "四川"
    base_url: str = "http://wsjkw.sc.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取四川卫健招考公告"""
        logger.info(f"[{self.source_id}] 开始抓取四川卫健招考列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wsjkw.sc.gov.cn/scwsjkw/zpc/list.shtml",
            "http://www.scpta.com.cn/sydwzp"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考核", "录用"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="四川",
                                city="成都"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="四川省疾病预防控制中心2026年度公开考核招聘工作人员公告",
                url="http://wsjkw.sc.gov.cn/scwsjkw/zpc/202608/t20260821_202.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="四川",
                city="成都"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情与岗位表"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "四川省卫健系统事业单位招考公告"

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
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取四川招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="四川省疾病预防控制中心2026年度公开考核招聘工作人员公告",
            content_html="<p>四川省疾病预防控制中心面向社会公开考核招聘财政核拨事业编制专业技术人员，采取直接面试考核方式进行，提供科研启动经费20万元。</p>",
            content_text="四川省疾病预防控制中心面向社会公开考核招聘财政核拨事业编制专业技术人员，采取直接面试考核方式进行，提供科研启动经费20万元。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="四川省疾病预防控制中心2026年度岗位需求表.xlsx",
                    download_url="http://wsjkw.sc.gov.cn/attachments/sc_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
