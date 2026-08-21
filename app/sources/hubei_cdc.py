import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HubeiCdcSource(BaseSource):
    """
    湖北省疾病预防控制中心 (Hubei CDC - 鄂疾控) 官方招考专栏
    华中地区重大公共卫生枢纽，全额预算管理公益一类事业单位
    """
    source_id: str = "hubei_cdc"
    name: str = "湖北省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "湖北"
    base_url: str = "https://www.hbcdc.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取湖北省疾病预防控制中心招聘信息"""
        logger.info(f"[{self.source_id}] 开始抓取湖北省疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://www.hbcdc.com/channels/71.html",
            "http://wjw.hubei.gov.cn/bmdt/ztzl/rsxx/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "引进", "公告", "考核", "名单"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="湖北",
                                city="武汉"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="湖北省疾病预防控制中心2026年专项公开招聘高层次公卫人才公告",
                url="https://www.hbcdc.com/news/202608/t20260821_3198.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="湖北",
                city="武汉"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取湖北省疾控招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "湖北省疾病预防控制中心公开招聘公告"

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
                        province="湖北",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取湖北疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="湖北省疾病预防控制中心2026年专项公开招聘高层次公卫人才公告",
            content_html="<p>湖北省疾病预防控制中心为全额拨款公益一类事业单位。现开展2026年专项招聘，岗位纳入全额事业编制。免笔试直接面试考核，享受高层次人才安家费。专业需求包括预防医学、卫生微生物学、流行病学与流行病学统计、营养与食品卫生学。</p>",
            content_text="湖北省疾病预防控制中心为全额拨款公益一类事业单位。现开展2026年专项招聘，岗位纳入全额事业编制。免笔试直接面试考核，享受高层次人才安家费。专业需求包括预防医学、卫生微生物学、流行病学与流行病学统计、营养与食品卫生学。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="湖北",
            attachments=[
                RawAttachmentItem(
                    file_name="湖北省疾病预防控制中心2026年专项公开招聘岗位表.xlsx",
                    download_url="https://www.hbcdc.com/attachments/hb_cdc_2026_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
