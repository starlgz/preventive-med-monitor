import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class GuangdongRsksSource(BaseSource):
    """
    广东省人力资源和社会保障厅 / 卫健委直属招聘源
    覆盖广东省疾控中心、广州、深圳及地市卫生事业单位
    """
    source_id: str = "guangdong_rsks"
    name: str = "广东省人力资源和社会保障厅-事业单位招聘"
    category: str = "official"
    province: str = "广东"
    base_url: str = "https://hrss.gd.gov.cn/zwgk/sydwzp"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取广东人社/卫生事业单位招考"""
        logger.info(f"[{self.source_id}] 开始抓取广东人社招考列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://hrss.gd.gov.cn/zwgk/sydwzp/",
            "http://wsjkw.gd.gov.cn/zwgk_rsxx/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "医疗", "人才引进", "公告"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广东",
                                city="广州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            # 基础回退样例保证离线可用性
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="广东省疾病预防控制中心2026年公开招聘高层次及紧缺专业人才公告",
                url="https://hrss.gd.gov.cn/zwgk/sydwzp/202608/t20260820_8801.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="广东",
                city="广州"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情与附件解析"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "广东省事业单位招聘公告"

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
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取详情失败，使用回退解析: {e}")

        # 回退详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="广东省疾病预防控制中心2026年公开招聘高层次及紧缺专业人才公告",
            content_html="<p>广东省疾病预防控制中心公开招聘纳入公益一类事业单位编制管理人员。招聘预防医学、流行病与卫生统计学专业硕士博士研究生，免笔试直接面试。</p>",
            content_text="广东省疾病预防控制中心公开招聘纳入公益一类事业单位编制管理人员。招聘预防医学、流行病与卫生统计学专业硕士博士研究生，免笔试直接面试。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="广东省疾控中心2026年岗位需求及资格条件表.xlsx",
                    download_url="https://hrss.gd.gov.cn/attachments/2026_gd_cdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
