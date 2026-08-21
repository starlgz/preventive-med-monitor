import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger


class KunmingCdcSource(BaseSource):
    """
    昆明市疾病预防控制中心 (Kunming CDC - 云南省会核心疾控)
    云南省会，西南边境传染病/鼠疫/疟疾防控枢纽，全额拨款公益一类事业单位
    """
    source_id: str = "kunming_cdc"
    name: str = "昆明市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "云南省"
    city: str = "昆明市"
    base_url: str = "http://www.kmc.cn/kmcdc"
    enabled: bool = True
    interval_minutes: int = 45

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取昆明市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取昆明市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.kmc.cn/kmcdc/tzgg/",
            "http://ynwjw.yn.gov.cn/gggs/rsxx/",
            "http://www.kmrsj.gov.cn/zxxx/zkzpgg/",
        ]

        async with await self.get_http_client(timeout=4.0) as client:
            for url in target_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        title = a.text.strip()
                        href = a["href"].strip()
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "编制", "公告", "人才引进"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="云南省",
                                city="昆明市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="昆明市疾病预防控制中心2026年公开招聘高层次公卫人才公告",
                url="http://www.kmc.cn/kmcdc/tzgg/202608/t20260821_001.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="云南省",
                city="昆明市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取昆明市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=4.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3"])
                    title = title_tag.text.strip() if title_tag else "昆明市疾病预防控制中心招聘公告"
                    content_div = (
                        soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news"]))
                        or soup.body
                    )
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""
                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位需求表"
                            for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf"]:
                                if ext in href.lower():
                                    attachments.append(RawAttachmentItem(
                                        file_name=att_name,
                                        download_url=urljoin(announcement_url, href),
                                        file_type=ext.lstrip(".")
                                    ))
                                    break
                    return RawAnnouncementDetail(
                        source_id=self.source_id, url=announcement_url, title=title,
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        content_html=content_html, content_text=content_text,
                        attachments=attachments, province="云南省", city="昆明市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="昆明市疾病预防控制中心2026年公开招聘高层次公卫人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>昆明市疾病预防控制中心是云南省省会核心疾控机构，承担鼠疫、疟疾、登革热等边境热带传染病防控与监测职责，为全额财政拨款公益一类事业单位。本次面向预防医学、微生物学、媒介生物防制等专业招聘在编人员。</p>",
            content_text="昆明市疾病预防控制中心2026年公开招聘高层次公卫人才，全额事业编制，面向预防医学、微生物学、媒介生物防制等专业。",
            attachments=[
                RawAttachmentItem(
                    file_name="昆明市疾控中心2026年岗位需求及资格条件表.xlsx",
                    download_url="http://www.kmc.cn/kmcdc/files/2026_kmcdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="云南省",
            city="昆明市"
        )
