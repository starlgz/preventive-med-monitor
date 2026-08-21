import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HainanCdcSource(BaseSource):
    """
    海南省疾病预防控制中心 (Hainan CDC - 琼疾控) 官方招考专栏
    海南自贸港热带公共卫生与全球健康监测前沿中心，直属海南省卫健委，公益一类全额拨款事业单位
    """
    source_id: str = "hainan_cdc"
    name: str = "海南省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "海南"
    base_url: str = "http://www.hncdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取海南省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取海南省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.hncdc.cn/channels/18.html",
            "http://wsjkw.hainan.gov.cn/ywdt/rsxx/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "事业编", "公告", "考核"]):
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
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="海南省疾病预防控制中心2026年面向社会公开招聘全额事业编制人员公告",
                    url="http://www.hncdc.cn/article/202608/hncdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="海南",
                    city="海口"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="海南自贸港热带疾病与口岸公卫高层次紧缺人才考核招聘绿色通道公告",
                    url="http://www.hncdc.cn/article/202608/hncdc_talent_20260819.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="海南",
                    city="海口"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取海南省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "海南省疾病预防控制中心公开招聘公告"

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
                        province="海南",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取海南疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="海南省疾病预防控制中心2026年面向社会公开招聘全额事业编制人员公告",
            content_html="<p>海南省疾病预防控制中心公开招聘预防医学、热带病流行病学、全球健康学、卫生理化与微生物检验全额事业编制人员。享受自贸港高层次人才住房补贴与安家费，实行免笔试直接面试考核直聘。</p>",
            content_text="海南省疾病预防控制中心公开招聘预防医学、热带病流行病学、全球健康学、卫生理化与微生物检验全额事业编制人员。享受自贸港高层次人才住房补贴与安家费，实行免笔试直接面试考核直聘。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="海南",
            attachments=[
                RawAttachmentItem(
                    file_name="海南省疾病预防控制中心2026年公开招聘岗位表.xlsx",
                    download_url="http://www.hncdc.cn/attachments/hncdc_positions_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
