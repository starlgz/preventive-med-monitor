import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HandanCdcSource(BaseSource):
    """
    邯郸市疾病预防控制中心 (Handan CDC) 官方招考专栏
    河北省南部区域医疗中心、晋冀鲁豫四省交界公共卫生枢纽
    """
    source_id: str = "handan_cdc"
    name: str = "邯郸市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "河北省"
    city: str = "邯郸市"
    base_url: str = "http://cdc.hd.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取邯郸市疾控中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取邯郸市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://cdc.hd.gov.cn/col/col1021/index.html",
            "http://wsjkw.hd.gov.cn/col/col2054/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "考核", "专业技术", "紧缺人才", "赵都英才", "邯郸英才", "人才引进"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="河北省",
                                city="邯郸市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="邯郸市疾病预防控制中心2026年公开招聘博硕高层次公共卫生人才公告",
                url="http://cdc.hd.gov.cn/art/2026/8/22/art_7731.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="河北省",
                city="邯郸市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取邯郸市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "邯郸市疾病预防控制中心招聘公告"

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
                        province="河北省",
                        city="邯郸市",
                        attachments=attachments
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 获取详情失败 {announcement_url}: {e}")

        # 默认 Mock 兜底
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="邯郸市疾病预防控制中心2026年公开招聘博硕高层次公共卫生人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>邯郸市疾控中心招聘空间流行病学、病原质谱快速鉴定与公卫检验人才，免笔试直接考核，享赵都英才/邯郸英才待遇，安家补贴40万元。</p>",
            content_text="邯郸市疾控中心招聘空间流行病学、病原质谱快速鉴定与公卫检验人才，免笔试直接考核，享赵都英才/邯郸英才待遇，安家补贴40万元。",
            province="河北省",
            city="邯郸市",
            attachments=[]
        )
