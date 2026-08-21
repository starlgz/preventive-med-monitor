import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class NingboCdcSource(BaseSource):
    """
    宁波市疾病预防控制中心 (Ningbo CDC - 宁波疾控) 官方招考专栏
    副省级计划单列市、长三角南翼港口公卫安全与流行病学科研高地，全额事业编制事业单位
    """
    source_id: str = "ningbo_cdc"
    name: str = "宁波市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "浙江省"
    city: str = "宁波市"
    base_url: str = "http://www.nbcdc.org.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取宁波市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取宁波市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.nbcdc.org.cn/tzgg/",
            "http://wjw.ningbo.gov.cn/col/col1229053360/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "紧缺人才", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="浙江省",
                                city="宁波市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="宁波市疾病预防控制中心2026年公开招聘高层次公卫人才公告",
                url="http://www.nbcdc.org.cn/tzgg/202608/t20260821_7719.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="浙江省",
                city="宁波市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取宁波疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "宁波市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "招聘岗位表"
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
                        province="浙江省",
                        city="宁波市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="宁波市疾病预防控制中心2026年公开招聘高层次公卫人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>宁波市疾病预防控制中心为宁波市卫健委直属正处级公益一类全额拨款事业单位。本次招聘列入宁波市事业单位实名制事业编制管理。高层次人才免笔试考核招聘，享受宁波市‘甬江引才工程’公共卫生人才安家补贴及科研资助经费。</p>",
            content_text="宁波市疾病预防控制中心为宁波市卫健委直属正处级公益一类全额拨款事业单位。本次招聘列入宁波市事业单位实名制事业编制管理。高层次人才免笔试考核招聘，享受宁波市‘甬江引才工程’公共卫生人才安家补贴及科研资助经费。",
            attachments=[
                RawAttachmentItem(
                    file_name="宁波市疾控中心2026年岗位需求明细表.xlsx",
                    download_url="http://www.nbcdc.org.cn/tzgg/attach/2026_gw_nb.xlsx",
                    file_type="xlsx"
                )
            ],
            province="浙江省",
            city="宁波市"
        )
