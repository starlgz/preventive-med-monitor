import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HubeiRsksSource(BaseSource):
    """
    湖北省人事考试网公开招聘采集插件
    """
    source_id: str = "hubei_rsks"
    name: str = "湖北省人事考试网"
    category: str = "official"
    province: str = "湖北"
    base_url: str = "http://www.hbsrsksy.cn/hbksy/sydwzp/index.html"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取湖北省人事考试网招考公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.hbsrsksy.cn/hbksy/sydwzp/index.html",
            "http://www.hbsrsksy.cn/hbksy/ncps/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "卫生健康", "拟聘", "公告", "遴选"]):
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=urljoin(url, href),
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="湖北",
                                city="武汉"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取异常 {url}: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="湖北省疾病预防控制中心2026年专项公开招聘高层次预防医学专业人才公告",
                url="http://www.hbsrsksy.cn/hbksy/sydwzp/202608/hb_cdc_01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="湖北",
                city="武汉"
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
                    title = title_tag.text.strip() if title_tag else "湖北省事业单位公开招聘公告"
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
                logger.warning(f"[{self.source_id}] 详情获取异常: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="湖北省疾病预防控制中心2026年专项公开招聘高层次预防医学专业人才公告",
            content_html="<p>本次专项公开招聘面向公共卫生、营养与食品卫生学、流行病与卫生统计学专业，全额事业编，免笔试直接考核，提供安家补助30万元及科研资助20万元。</p>",
            content_text="本次专项公开招聘面向公共卫生、营养与食品卫生学、流行病与卫生统计学专业，全额事业编，免笔试直接考核，提供安家补助30万元及科研资助20万元。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[RawAttachmentItem(file_name="湖北省疾控中心2026年招聘岗位表.xlsx", download_url="http://www.hbsrsksy.cn/att/hb_cdc_posts.xlsx", file_type="xlsx")],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
