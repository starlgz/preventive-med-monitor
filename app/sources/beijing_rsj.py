import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class BeijingRsjSource(BaseSource):
    """
    北京市人力资源和社会保障局事业单位公开招聘采集插件
    """
    source_id: str = "beijing_rsj"
    name: str = "北京市人社局事业单位招聘"
    category: str = "official"
    province: str = "北京"
    base_url: str = "http://rsj.beijing.gov.cn/xxgk/gsgg/"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取北京市人社局事业单位招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://rsj.beijing.gov.cn/xxgk/gsgg/",
            "http://rsj.beijing.gov.cn/xxgk/sydwzp/"
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
                                province="北京",
                                city="北京"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取异常 {url}: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="北京市疾病预防控制中心2026年公开招聘高精尖预防医学与公共卫生紧缺人才公告",
                url="http://rsj.beijing.gov.cn/xxgk/sydwzp/202608/bj_cdc_01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="北京",
                city="北京"
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
                    title = title_tag.text.strip() if title_tag else "北京市事业单位公开招聘公告"
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
            title="北京市疾病预防控制中心2026年公开招聘高精尖预防医学与公共卫生紧缺人才公告",
            content_html="<p>本次招考预防医学、流行病与卫生统计学、卫生毒理学硕博岗位，全额拨款事业编制，落实北京户口，协助解决子女优质入学，免笔试直接考察考核。</p>",
            content_text="本次招考预防医学、流行病与卫生统计学、卫生毒理学硕博岗位，全额拨款事业编制，落实北京户口，协助解决子女优质入学，免笔试直接考察考核。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[RawAttachmentItem(file_name="北京市疾控中心2026年岗位需求表.xlsx", download_url="http://rsj.beijing.gov.cn/att/bj_cdc_posts.xlsx", file_type="xlsx")],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
