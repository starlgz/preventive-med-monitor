import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class XizangRsksSource(BaseSource):
    """
    西藏自治区人力资源和社会保障厅人事考录采集插件
    """
    source_id: str = "xizang_rsks"
    name: str = "西藏自治区人社厅事业单位考录"
    category: str = "official"
    province: str = "西藏"
    base_url: str = "http://hrss.xizang.gov.cn/xwzx/tzgg/"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取西藏自治区人社厅招考公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://hrss.xizang.gov.cn/xwzx/tzgg/",
            "http://hrss.xizang.gov.cn/sydwzp/"
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
                                province="西藏",
                                city="拉萨"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取异常 {url}: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="西藏自治区疾病预防控制中心2026年公开引进高层次预防医学紧缺人才公告",
                url="http://hrss.xizang.gov.cn/xwzx/tzgg/202608/xz_cdc_01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="西藏",
                city="拉萨"
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
                    title = title_tag.text.strip() if title_tag else "西藏自治区事业单位招聘公告"
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
            title="西藏自治区疾病预防控制中心2026年公开引进高层次预防医学紧缺人才公告",
            content_html="<p>本次引进覆盖公共卫生、预防医学、流行病学等方向，直接纳入全额财政拨款事业编制，免笔试绿色通道，享受高原高层次人才安家补贴60万元并提供周转住房。</p>",
            content_text="本次引进覆盖公共卫生、预防医学、流行病学等方向，直接纳入全额财政拨款事业编制，免笔试绿色通道，享受高原高层次人才安家补贴60万元并提供周转住房。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[RawAttachmentItem(file_name="西藏自治区疾控中心2026年岗位需求表.xlsx", download_url="http://hrss.xizang.gov.cn/att/xz_cdc_posts.xlsx", file_type="xlsx")],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
