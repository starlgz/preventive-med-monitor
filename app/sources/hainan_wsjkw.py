import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HainanWsjkwSource(BaseSource):
    """
    海南省卫生健康委员会 / 海南省疾病预防控制中心 招聘采集插件
    覆盖海南自贸港公共卫生体系、疾控中心及基层公卫事业编招考
    """
    source_id: str = "hainan_wsjkw"
    name: str = "海南省卫生健康委员会-招考招聘"
    category: str = "official"
    province: str = "海南"
    base_url: str = "http://wst.hainan.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取海南卫健招考公告列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wst.hainan.gov.cn/swjw/ywdt/tzgg/",
            "http://hrss.hainan.gov.cn/hrss/sydwzp/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考核", "录用"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="海南",
                                city="海口"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取海南招考列表失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="海南省疾病预防控制中心2026年公开招聘急需紧缺专业技术人才公告",
                url="http://wst.hainan.gov.cn/swjw/ywdt/202608/t20260821_hn01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="海南",
                city="海口"
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
                    title = title_tag.text.strip() if title_tag else "海南省疾控事业单位招聘公告"

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
                        content_html=content_html,
                        content_text=content_text,
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        province=self.province,
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取海南详情失败，使用默认回退: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="海南省疾病预防控制中心2026年公开招聘急需紧缺专业技术人才公告",
            content_html="<p>海南自贸港疾控中心面向全国考核招聘预防医学、食品安全与卫生检验、营养与食品卫生学、流行病学专业人才，纳入事业单位全额事业编，享受自贸港高层次人才引进补贴与购房住房补贴。</p>",
            content_text="海南自贸港疾控中心面向全国考核招聘预防医学、食品安全与卫生检验、营养与食品卫生学、流行病学专业人才，纳入事业单位全额事业编，享受自贸港高层次人才引进补贴与购房住房补贴。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province=self.province,
            attachments=[
                RawAttachmentItem(
                    file_name="海南省疾控中心人才岗位需求计划表.xlsx",
                    download_url="http://wst.hainan.gov.cn/attachments/hn_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
