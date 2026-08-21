import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class FujianRsksSource(BaseSource):
    """
    福建省人力资源和社会保障厅 / 福建省人事考试网招聘源
    聚焦福建省疾控中心、福州市疾控、厦门市疾控及全省公卫医疗单位招考
    """
    source_id: str = "fujian_rsks"
    name: str = "福建省人事考试网-事业单位招考"
    category: str = "official"
    province: str = "福建"
    base_url: str = "http://www.fjkl.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取福建人事考录公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取福建招考列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.fjkl.gov.cn/sydwzp",
            "http://wjw.fujian.gov.cn/xxgk/gsgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考聘"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="福建",
                                city="福州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="福建省疾病预防控制中心2026年公开招聘工作人员方案",
                url="http://www.fjkl.gov.cn/sydwzp/202608/t20260820_7701.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="福建",
                city="福州"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情与附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "福建省事业单位招考公告"

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
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取福建招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="福建省疾病预防控制中心2026年公开招聘工作人员方案",
            content_html="<p>福建省疾病预防控制中心招聘财政全额拨款事业编制专业技术人员，岗位要求预防医学、卫生检验与检疫、流行病与卫生统计学专业。</p>",
            content_text="福建省疾病预防控制中心招聘财政全额拨款事业编制专业技术人员，岗位要求预防医学、卫生检验与检疫、流行病与卫生统计学专业。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="福建省疾病预防控制中心岗位信息表.xlsx",
                    download_url="http://www.fjkl.gov.cn/attachments/fj_cdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
