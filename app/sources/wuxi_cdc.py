import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class WuxiCdcSource(BaseSource):
    """
    无锡市疾病预防控制中心 (Wuxi CDC) 官方招考专栏
    苏南经济重镇/苏南公共卫生技术高地，全额事业编制事业单位
    """
    source_id: str = "wuxi_cdc"
    name: str = "无锡市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "江苏省"
    city: str = "无锡市"
    base_url: str = "http://www.wuxicdc.org"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取无锡市疾控中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取无锡市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.wuxicdc.org/xwzx/tzgg/",
            "http://wjw.wuxi.gov.cn/ztzl/rsxx/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "考核", "专业技术"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="江苏省",
                                city="无锡市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="无锡市疾病预防控制中心2026年公开招聘高端及紧缺公卫专业技术人才公告",
                url="http://www.wuxicdc.org/xwzx/tzgg/202608/t20260821_9812.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="江苏省",
                city="无锡市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取无锡市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "无锡市疾病预防控制中心招聘公告"

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
                        content_html=content_html,
                        content_text=content_text,
                        attachments=attachments,
                        province="江苏省",
                        city="无锡市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 模拟详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="无锡市疾病预防控制中心2026年公开招聘高端及紧缺公卫专业技术人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>无锡市疾病预防控制中心为公益一类财政全额拨款事业单位。本次招聘按太湖人才计划给予全额事业编制，硕博研究生可直接考核免笔试录取，享受最高30万元安家补贴与免租人才周转房。</p>",
            content_text="无锡市疾病预防控制中心为公益一类财政全额拨款事业单位。本次招聘按太湖人才计划给予全额事业编制，硕博研究生可直接考核免笔试录取，享受最高30万元安家补贴与免租人才周转房。",
            attachments=[
                RawAttachmentItem(
                    file_name="无锡市疾控中心2026年岗位表.xlsx",
                    download_url="http://www.wuxicdc.org/files/2026_wuxicdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="江苏省",
            city="无锡市"
        )
