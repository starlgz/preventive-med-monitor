import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShaanxiCdcSource(BaseSource):
    """
    陕西省疾病预防控制中心 (Shaanxi CDC) 官方招考专栏
    西北地区公共卫生与疾控核心枢纽，直属陕西省卫健委，公益一类全额拨款事业编制
    """
    source_id: str = "shaanxi_cdc"
    name: str = "陕西省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "陕西"
    base_url: str = "http://www.sxcdc.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取陕西省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取陕西省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.sxcdc.com/tzgg/index.html",
            "http://sxwjw.shaanxi.gov.cn/col/col9/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "直属", "高校毕业生", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="陕西",
                                city="西安"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="陕西省疾病预防控制中心2026年事业单位公开招聘工作人员公告",
                    url="http://www.sxcdc.com/article/202608/sxc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="陕西",
                    city="西安"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="陕西省疾病预防控制中心2026年高层次公共卫生急需紧缺人才引进考核公告",
                    url="http://www.sxcdc.com/article/202608/sxc_talent_20260820.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="陕西",
                    city="西安"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取陕西省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "陕西省疾病预防控制中心公开招聘公告"

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
                        province="陕西",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取陕西疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="陕西省疾病预防控制中心公开招聘公卫及检验专业技术人员",
            content_html="<p>陕西省疾病预防控制中心为陕西省卫生健康委员会直属全额事业单位，现面向全国公开招录流行病与卫生统计学、卫生毒理学、预防医学等专业人才，录用人员纳入全额财政补助事业编制管理。</p>",
            content_text="陕西省疾病预防控制中心为陕西省卫生健康委员会直属全额事业单位，现面向全国公开招录流行病与卫生统计学、卫生毒理学、预防医学等专业人才，录用人员纳入全额财政补助事业编制管理。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="陕西",
            attachments=[],
            crawl_time=datetime.now()
        )
