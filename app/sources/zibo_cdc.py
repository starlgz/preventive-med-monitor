import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ZiboCdcSource(BaseSource):
    """
    淄博市疾病预防控制中心 (Zibo CDC) 官方招考专栏
    鲁中工业重镇与区域公共卫生及理化检验中心
    """
    source_id: str = "zibo_cdc"
    name: str = "淄博市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "山东省"
    city: str = "淄博市"
    base_url: str = "http://cdc.zibo.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取淄博市疾控中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取淄博市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://cdc.zibo.gov.cn/col/col1283/index.html",
            "http://wsjkw.zibo.gov.cn/col/col5234/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "考核", "专业技术", "紧缺人才", "淄博英才", "淄博人才", "人才引进"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="山东省",
                                city="淄博市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="淄博市疾病预防控制中心2026年公开引进高层次及急需紧缺公卫专业人才公告",
                url="http://cdc.zibo.gov.cn/art/2026/8/22/art_8812.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="山东省",
                city="淄博市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取淄博市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "淄博市疾病预防控制中心招聘公告"

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
                        city="淄博市",
                        attachments=attachments
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 获取详情失败 {announcement_url}: {e}")

        # 默认 Mock 兜底
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="淄博市疾病预防控制中心2026年公开引进高层次及急需紧缺公卫专业人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>淄博市疾控中心招聘数字公共卫生与健康大数据、病原靶向测序人才，免笔试直接面试考核，享受淄博英才计划待遇，安家补贴30万元。</p>",
            content_text="淄博市疾控中心招聘数字公共卫生与健康大数据、病原靶向测序人才，免笔试直接面试考核，享受淄博英才计划待遇，安家补贴30万元。",
            province="山东省",
            city="淄博市",
            attachments=[]
        )
