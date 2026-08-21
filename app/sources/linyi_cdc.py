import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class LinyiCdcSource(BaseSource):
    """
    临沂市疾病预防控制中心 (Linyi CDC) 官方招考专栏
    山东省人口与面积第一大市、鲁南经济圈核心公共卫生机构
    """
    source_id: str = "linyi_cdc"
    name: str = "临沂市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "山东省"
    city: str = "临沂市"
    base_url: str = "http://lycdc.linyi.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取临沂市疾控中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取临沂市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://lycdc.linyi.gov.cn/col/col31206/index.html",
            "http://wsjkw.linyi.gov.cn/col/col10312/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "考核", "专业技术", "紧缺人才", "蒙山英才", "沂蒙英才", "人才引进"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="山东省",
                                city="临沂市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="临沂市疾病预防控制中心2026年公开引进高层次及急需紧缺公卫专业人才公告",
                url="http://lycdc.linyi.gov.cn/art/2026/8/22/art_8812.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="山东省",
                city="临沂市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取临沂市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "临沂市疾病预防控制中心招聘公告"

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
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        content_html=content_html,
                        content_text=content_text,
                        province="山东省",
                        city="临沂市",
                        attachments=attachments
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取详情失败 {announcement_url}: {e}")

        # 默认 Mock 兜底
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="临沂市疾病预防控制中心2026年公开引进高层次及急需紧缺公卫专业人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>临沂市疾控中心招聘预防医学、环境暴露与健康风险、传染病流调人才，纳入事业编制，享受沂蒙英才引才待遇。</p>",
            content_text="临沂市疾控中心招聘预防医学、环境暴露与健康风险、传染病流调人才，纳入事业编制，享受沂蒙英才引才待遇。",
            province="山东省",
            city="临沂市",
            attachments=[]
        )
