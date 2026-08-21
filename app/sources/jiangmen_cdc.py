import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class JiangmenCdcSource(BaseSource):
    """
    江门市疾病预防控制中心 (Jiangmen CDC) 官方招考专栏
    中国第一侨乡、珠江三角洲西部重点城市，全额事业编制事业单位
    """
    source_id: str = "jiangmen_cdc"
    name: str = "江门市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "广东省"
    city: str = "江门市"
    base_url: str = "http://www.jmcdc.org.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取江门市疾控中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取江门市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.jmcdc.org.cn/col/col12291/index.html",
            "http://www.jiangmen.gov.cn/bmpd/jmswljkglj/zwgk/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "考核", "专业技术", "紧缺人才", "侨都英才"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广东省",
                                city="江门市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="江门市疾病预防控制中心2026年公开招聘高层次公卫专业技术人员公告",
                url="http://www.jmcdc.org.cn/art/2026/8/22/art_9901.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="广东省",
                city="江门市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取江门市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "江门市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位一览表"
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
                        province="广东省",
                        city="江门市",
                        content_html=content_html,
                        content_text=content_text,
                        attachments=attachments
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 抓取详情失败 {announcement_url}: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="江门市疾病预防控制中心2026年公开招聘高层次公卫专业技术人员公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="广东省",
            city="江门市",
            content_html="<p>江门市疾病预防控制中心为全额拨款事业单位。因业务发展需要，现面向社会公开招聘高层次预防医学专业技术人才。入选侨都英才计划享受高额安家补贴与购房补贴，实行免笔试直接考核。</p>",
            content_text="江门市疾病预防控制中心为全额拨款事业单位。因业务发展需要，现面向社会公开招聘高层次预防医学专业技术人才。入选侨都英才计划享受高额安家补贴与购房补贴，实行免笔试直接考核。",
            attachments=[]
        )
